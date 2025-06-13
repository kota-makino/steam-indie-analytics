"""
インディーゲームデータ収集スクリプト

Steam Store API（認証不要）を使用してインディーゲームの情報を収集し、
PostgreSQLデータベースに保存します。
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Any

import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# データベース接続設定
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'steam_analytics'),
    'user': os.getenv('POSTGRES_USER', 'steam_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'steam_password')
}


class IndieGameCollector:
    """インディーゲーム データコレクター"""
    
    def __init__(self):
        self.session = None
        self.db_conn = None
        self.collected_games = []
        
        # インディーゲーム識別キーワード
        self.indie_keywords = [
            'indie', 'independent', 'pixel', 'retro', 'adventure', 
            'casual', 'puzzle', 'platformer', 'roguelike', 'survival',
            'crafting', 'sandbox', 'exploration', 'story', 'narrative'
        ]
        
        # 大手パブリッシャー（除外対象）
        self.major_publishers = [
            'valve', 'electronic arts', 'ea', 'activision', 'ubisoft', 
            'bethesda', 'square enix', 'capcom', 'bandai namco', 'sega', 
            'take-two', 'nintendo', 'sony', 'microsoft', 'rockstar'
        ]
    
    async def __aenter__(self):
        """非同期コンテキスト開始"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # データベース接続
        self.db_conn = psycopg2.connect(**DB_CONFIG)
        self.db_conn.autocommit = True
        
        await self.create_tables()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキスト終了"""
        if self.session:
            await self.session.close()
        if self.db_conn:
            self.db_conn.close()
    
    async def create_tables(self):
        """データベーステーブルを作成"""
        
        create_games_table = """
        CREATE TABLE IF NOT EXISTS games (
            app_id INTEGER PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            type VARCHAR(50),
            is_free BOOLEAN DEFAULT FALSE,
            detailed_description TEXT,
            short_description TEXT,
            developers TEXT[],
            publishers TEXT[],
            price_currency VARCHAR(10),
            price_initial INTEGER,
            price_final INTEGER,
            price_discount_percent INTEGER,
            release_date_text VARCHAR(100),
            release_date_coming_soon BOOLEAN,
            platforms_windows BOOLEAN DEFAULT FALSE,
            platforms_mac BOOLEAN DEFAULT FALSE,
            platforms_linux BOOLEAN DEFAULT FALSE,
            genres TEXT[],
            categories TEXT[],
            positive_reviews INTEGER,
            negative_reviews INTEGER,
            total_reviews INTEGER,
            recommendation_score FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_reviews_table = """
        CREATE TABLE IF NOT EXISTS game_reviews (
            id SERIAL PRIMARY KEY,
            app_id INTEGER REFERENCES games(app_id),
            total_positive INTEGER DEFAULT 0,
            total_negative INTEGER DEFAULT 0,
            total_reviews INTEGER DEFAULT 0,
            review_score INTEGER DEFAULT 0,
            review_score_desc VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # インデックス作成
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_games_name ON games(name);",
            "CREATE INDEX IF NOT EXISTS idx_games_type ON games(type);",
            "CREATE INDEX IF NOT EXISTS idx_games_developers ON games USING GIN(developers);",
            "CREATE INDEX IF NOT EXISTS idx_games_genres ON games USING GIN(genres);",
            "CREATE INDEX IF NOT EXISTS idx_games_total_reviews ON games(total_reviews);",
        ]
        
        cursor = self.db_conn.cursor()
        
        try:
            cursor.execute(create_games_table)
            cursor.execute(create_reviews_table)
            
            for index_sql in create_indexes:
                cursor.execute(index_sql)
            
            print("✅ データベーステーブルを作成/確認しました")
            
        except Exception as e:
            print(f"❌ テーブル作成エラー: {e}")
        finally:
            cursor.close()
    
    async def get_popular_indie_games(self, limit: int = 100) -> List[int]:
        """人気インディーゲームのApp IDリストを取得"""
        
        # 有名なインディーゲームのApp IDリスト（手動キュレーション）
        known_indie_games = [
            413150,  # Stardew Valley
            250900,  # The Binding of Isaac: Rebirth
            105600,  # Terraria
            211820,  # Starbound
            367520,  # Hollow Knight
            391540,  # Undertale
            257350,  # Hyper Light Drifter
            447040,  # A Hat in Time
            268910,  # Cuphead
            574240,  # Ori and the Will of the Wisps
            387290,  # Ori and the Blind Forest
            593110,  # Dead Cells
            588650,  # Subnautica
            444090,  # Payday 2 (実はメジャーだが、例として)
            230410,  # Warframe (F2P)
            311210,  # Call of Duty: Black Ops III (メジャータイトル、テスト用)
        ]
        
        print(f"🎯 {len(known_indie_games)}件の人気インディーゲームから開始")
        
        # Steam Spy APIから追加のインディーゲーム情報も取得可能（将来的に）
        # ここでは既知のリストを返す
        return known_indie_games[:limit]
    
    async def get_game_details(self, app_id: int) -> Optional[Dict[str, Any]]:
        """ゲーム詳細情報を取得"""
        
        url = "https://store.steampowered.com/api/appdetails"
        params = {
            'appids': app_id,
            'l': 'english',
            'cc': 'us'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    app_data = data.get(str(app_id))
                    
                    if app_data and app_data.get('success'):
                        return app_data.get('data')
                    else:
                        print(f"⚠️  App ID {app_id}: データ取得失敗")
                        return None
                else:
                    print(f"❌ App ID {app_id}: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            print(f"❌ App ID {app_id}: エラー - {e}")
            return None
    
    async def get_game_reviews(self, app_id: int) -> Optional[Dict[str, Any]]:
        """ゲームレビュー情報を取得"""
        
        url = f"https://store.steampowered.com/api/appreviews/{app_id}"
        params = {
            'json': 1,
            'language': 'all',
            'review_type': 'all',
            'purchase_type': 'all',
            'num_per_page': 0,  # 統計情報のみ取得
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success') == 1:
                        return data.get('query_summary', {})
                    
        except Exception as e:
            print(f"❌ レビュー取得エラー (App ID {app_id}): {e}")
        
        return None
    
    def is_indie_game(self, game_data: Dict[str, Any]) -> bool:
        """ゲームがインディーゲームかどうかを判定"""
        
        # 開発者情報での判定
        developers = game_data.get('developers', [])
        publishers = game_data.get('publishers', [])
        
        # 大手パブリッシャーの場合は除外
        for publisher in publishers:
            if any(major.lower() in publisher.lower() for major in self.major_publishers):
                return False
        
        # ジャンル情報での判定
        genres = game_data.get('genres', [])
        for genre in genres:
            genre_desc = genre.get('description', '').lower()
            if 'indie' in genre_desc or 'independent' in genre_desc:
                return True
        
        # カテゴリでの判定
        categories = game_data.get('categories', [])
        for category in categories:
            cat_desc = category.get('description', '').lower()
            if 'indie' in cat_desc:
                return True
        
        # 開発者とパブリッシャーが同じ場合（セルフパブリッシング）
        if developers and publishers and set(developers) == set(publishers):
            return True
        
        # 小規模チーム（開発者が1-2社）
        if len(developers) <= 2:
            return True
        
        return False
    
    async def save_game_to_db(self, game_data: Dict[str, Any], review_data: Optional[Dict[str, Any]] = None):
        """ゲーム情報をデータベースに保存"""
        
        cursor = self.db_conn.cursor()
        
        try:
            # 価格情報の処理
            price_overview = game_data.get('price_overview', {})
            price_currency = price_overview.get('currency')
            price_initial = price_overview.get('initial')
            price_final = price_overview.get('final')
            price_discount = price_overview.get('discount_percent')
            
            # リリース日情報の処理
            release_date = game_data.get('release_date', {})
            release_date_text = release_date.get('date')
            release_coming_soon = release_date.get('coming_soon', False)
            
            # プラットフォーム情報の処理
            platforms = game_data.get('platforms', {})
            platforms_windows = platforms.get('windows', False)
            platforms_mac = platforms.get('mac', False)
            platforms_linux = platforms.get('linux', False)
            
            # ジャンル・カテゴリ情報の処理
            genres = [g.get('description') for g in game_data.get('genres', [])]
            categories = [c.get('description') for c in game_data.get('categories', [])]
            
            # レビュー情報の処理
            positive_reviews = None
            negative_reviews = None
            total_reviews = None
            
            if review_data:
                positive_reviews = review_data.get('total_positive', 0)
                negative_reviews = review_data.get('total_negative', 0)
                total_reviews = review_data.get('total_reviews', 0)
            
            # ゲーム情報をINSERT (ON CONFLICT DO UPDATE)
            insert_game_sql = """
            INSERT INTO games (
                app_id, name, type, is_free, detailed_description, short_description,
                developers, publishers, price_currency, price_initial, price_final, price_discount_percent,
                release_date_text, release_date_coming_soon,
                platforms_windows, platforms_mac, platforms_linux,
                genres, categories, positive_reviews, negative_reviews, total_reviews,
                updated_at
            ) VALUES (
                %(app_id)s, %(name)s, %(type)s, %(is_free)s, %(detailed_description)s, %(short_description)s,
                %(developers)s, %(publishers)s, %(price_currency)s, %(price_initial)s, %(price_final)s, %(price_discount_percent)s,
                %(release_date_text)s, %(release_date_coming_soon)s,
                %(platforms_windows)s, %(platforms_mac)s, %(platforms_linux)s,
                %(genres)s, %(categories)s, %(positive_reviews)s, %(negative_reviews)s, %(total_reviews)s,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (app_id) DO UPDATE SET
                name = EXCLUDED.name,
                detailed_description = EXCLUDED.detailed_description,
                short_description = EXCLUDED.short_description,
                positive_reviews = EXCLUDED.positive_reviews,
                negative_reviews = EXCLUDED.negative_reviews,
                total_reviews = EXCLUDED.total_reviews,
                updated_at = CURRENT_TIMESTAMP
            """
            
            game_params = {
                'app_id': game_data.get('steam_appid'),
                'name': game_data.get('name'),
                'type': game_data.get('type'),
                'is_free': game_data.get('is_free', False),
                'detailed_description': game_data.get('detailed_description'),
                'short_description': game_data.get('short_description'),
                'developers': game_data.get('developers', []),
                'publishers': game_data.get('publishers', []),
                'price_currency': price_currency,
                'price_initial': price_initial,
                'price_final': price_final,
                'price_discount_percent': price_discount,
                'release_date_text': release_date_text,
                'release_date_coming_soon': release_coming_soon,
                'platforms_windows': platforms_windows,
                'platforms_mac': platforms_mac,
                'platforms_linux': platforms_linux,
                'genres': genres,
                'categories': categories,
                'positive_reviews': positive_reviews,
                'negative_reviews': negative_reviews,
                'total_reviews': total_reviews,
            }
            
            cursor.execute(insert_game_sql, game_params)
            
            # レビュー詳細情報も保存
            if review_data:
                insert_review_sql = """
                INSERT INTO game_reviews (
                    app_id, total_positive, total_negative, total_reviews, 
                    review_score, review_score_desc
                ) VALUES (
                    %(app_id)s, %(total_positive)s, %(total_negative)s, %(total_reviews)s,
                    %(review_score)s, %(review_score_desc)s
                )
                """
                
                review_params = {
                    'app_id': game_data.get('steam_appid'),
                    'total_positive': review_data.get('total_positive', 0),
                    'total_negative': review_data.get('total_negative', 0),
                    'total_reviews': review_data.get('total_reviews', 0),
                    'review_score': review_data.get('review_score', 0),
                    'review_score_desc': review_data.get('review_score_desc'),
                }
                
                cursor.execute(insert_review_sql, review_params)
            
            print(f"✅ 保存完了: {game_data.get('name')} (ID: {game_data.get('steam_appid')})")
            
        except Exception as e:
            print(f"❌ DB保存エラー: {e}")
        finally:
            cursor.close()
    
    async def collect_indie_games(self, limit: int = 20):
        """インディーゲーム情報の収集を実行"""
        
        print(f"🚀 インディーゲームデータ収集開始 (最大{limit}件)")
        print("=" * 60)
        
        # 対象ゲームのApp IDリストを取得
        app_ids = await self.get_popular_indie_games(limit)
        
        indie_count = 0
        total_processed = 0
        
        for i, app_id in enumerate(app_ids):
            total_processed += 1
            
            print(f"\n📊 進捗: {i+1}/{len(app_ids)} - App ID {app_id}")
            
            # ゲーム詳細情報を取得
            game_data = await self.get_game_details(app_id)
            if not game_data:
                continue
            
            print(f"  🎮 ゲーム名: {game_data.get('name', 'N/A')}")
            print(f"  🏢 開発者: {game_data.get('developers', ['N/A'])}")
            print(f"  📋 ジャンル: {[g.get('description') for g in game_data.get('genres', [])]}")
            
            # インディーゲーム判定
            is_indie = self.is_indie_game(game_data)
            print(f"  🔍 インディーゲーム判定: {'✅ YES' if is_indie else '❌ NO'}")
            
            if is_indie:
                indie_count += 1
                
                # レビューデータを取得
                review_data = await self.get_game_reviews(app_id)
                if review_data:
                    total_reviews = review_data.get('total_reviews', 0)
                    print(f"  📝 レビュー数: {total_reviews:,}")
                
                # データベースに保存
                await self.save_game_to_db(game_data, review_data)
                self.collected_games.append({
                    'app_id': app_id,
                    'name': game_data.get('name'),
                    'developers': game_data.get('developers'),
                    'total_reviews': review_data.get('total_reviews', 0) if review_data else 0,
                })
            
            # レート制限対策（1秒待機）
            await asyncio.sleep(1)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 収集結果サマリー")
        print("=" * 60)
        print(f"🔍 処理済みゲーム: {total_processed}件")
        print(f"✅ インディーゲーム: {indie_count}件")
        print(f"📈 インディー判定率: {indie_count/total_processed*100:.1f}%")
        
        if self.collected_games:
            print(f"\n🏆 収集したインディーゲーム TOP 5:")
            # レビュー数でソート
            sorted_games = sorted(self.collected_games, key=lambda x: x['total_reviews'], reverse=True)
            for i, game in enumerate(sorted_games[:5]):
                print(f"  {i+1}. {game['name']} - {game['total_reviews']:,} レビュー")


async def main():
    """メイン実行関数"""
    
    print("🎮 Steam インディーゲーム データ収集ツール")
    print("=" * 60)
    
    async with IndieGameCollector() as collector:
        await collector.collect_indie_games(limit=15)  # 15件から開始
    
    print("\n🎉 データ収集完了!")


if __name__ == "__main__":
    asyncio.run(main())