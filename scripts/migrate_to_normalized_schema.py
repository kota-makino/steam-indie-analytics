#!/usr/bin/env python3
"""
既存の配列型データを正規化スキーマに移行するスクリプト

使用方法:
    python scripts/migrate_to_normalized_schema.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_sync_session
from sqlalchemy import text
import logging
from datetime import datetime
from typing import List, Dict, Set

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SchemaMigrator:
    """スキーマ移行クラス"""
    
    def __init__(self):
        self.session = None
        
    def __enter__(self):
        self.session = get_sync_session()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()
    
    def create_normalized_schema(self):
        """正規化スキーマを作成"""
        logger.info("🏗️  正規化スキーマを作成中...")
        
        # SQLファイルを読み込んで実行
        schema_file = '/workspace/sql/create_normalized_schema.sql'
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # セミコロンで分割して各文を実行
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for stmt in statements:
            if stmt:
                try:
                    self.session.execute(text(stmt))
                    logger.debug(f"実行完了: {stmt[:50]}...")
                except Exception as e:
                    logger.warning(f"スキーマ作成警告: {e}")
        
        self.session.commit()
        logger.info("✅ 正規化スキーマ作成完了")
    
    def migrate_master_data(self):
        """マスタデータの移行"""
        logger.info("📋 マスタデータを移行中...")
        
        # 既存データから一意の値を抽出
        result = self.session.execute(text("""
            SELECT DISTINCT 
                UNNEST(genres) as genre_name
            FROM games 
            WHERE genres IS NOT NULL
        """))
        genres = {row[0] for row in result.fetchall() if row[0]}
        
        result = self.session.execute(text("""
            SELECT DISTINCT 
                UNNEST(developers) as developer_name
            FROM games 
            WHERE developers IS NOT NULL
        """))
        developers = {row[0] for row in result.fetchall() if row[0]}
        
        result = self.session.execute(text("""
            SELECT DISTINCT 
                UNNEST(publishers) as publisher_name
            FROM games 
            WHERE publishers IS NOT NULL
        """))
        publishers = {row[0] for row in result.fetchall() if row[0]}
        
        result = self.session.execute(text("""
            SELECT DISTINCT 
                UNNEST(categories) as category_name
            FROM games 
            WHERE categories IS NOT NULL
        """))
        categories = {row[0] for row in result.fetchall() if row[0]}
        
        # ジャンルマスタ挿入
        logger.info(f"ジャンル: {len(genres)}件")
        for genre in sorted(genres):
            self.session.execute(text("""
                INSERT INTO genres (name) 
                VALUES (:name) 
                ON CONFLICT (name) DO NOTHING
            """), {"name": genre})
        
        # 開発者マスタ挿入（インディー判定付き）
        logger.info(f"開発者: {len(developers)}件")
        for developer in sorted(developers):
            # 簡単なインディー判定ロジック
            is_indie = self._is_indie_developer(developer)
            self.session.execute(text("""
                INSERT INTO developers (name, is_indie) 
                VALUES (:name, :is_indie) 
                ON CONFLICT (name) DO NOTHING
            """), {"name": developer, "is_indie": is_indie})
        
        # パブリッシャーマスタ挿入
        logger.info(f"パブリッシャー: {len(publishers)}件")
        for publisher in sorted(publishers):
            is_major = self._is_major_publisher(publisher)
            self.session.execute(text("""
                INSERT INTO publishers (name, is_major) 
                VALUES (:name, :is_major) 
                ON CONFLICT (name) DO NOTHING
            """), {"name": publisher, "is_major": is_major})
        
        # カテゴリマスタ挿入
        logger.info(f"カテゴリ: {len(categories)}件")
        for category in sorted(categories):
            self.session.execute(text("""
                INSERT INTO categories (name) 
                VALUES (:name) 
                ON CONFLICT (name) DO NOTHING
            """), {"name": category})
        
        self.session.commit()
        logger.info("✅ マスタデータ移行完了")
    
    def migrate_game_data(self):
        """ゲームデータの移行"""
        logger.info("🎮 ゲームデータを移行中...")
        
        # 既存ゲームデータを取得
        result = self.session.execute(text("""
            SELECT 
                app_id, name, type, is_free, short_description,
                price_currency, price_initial, price_final, price_discount_percent,
                release_date_text, release_date_coming_soon,
                platforms_windows, platforms_mac, platforms_linux,
                positive_reviews, negative_reviews, total_reviews,
                genres, developers, publishers, categories,
                created_at
            FROM games
            ORDER BY app_id
        """))
        
        games = result.fetchall()
        logger.info(f"移行対象ゲーム: {len(games)}件")
        
        for i, game in enumerate(games):
            if i % 100 == 0:
                logger.info(f"進捗: {i}/{len(games)} ({i/len(games)*100:.1f}%)")
            
            # インディーゲーム判定
            is_indie = self._determine_indie_status(game)
            
            # リリース日の解析
            release_date = self._parse_release_date(game.release_date_text)
            
            # ゲーム基本情報を挿入
            self.session.execute(text("""
                INSERT INTO games_normalized (
                    app_id, name, type, is_free, short_description,
                    price_currency, price_initial, price_final, price_discount_percent,
                    release_date_text, release_date_coming_soon, release_date,
                    platforms_windows, platforms_mac, platforms_linux,
                    positive_reviews, negative_reviews, total_reviews,
                    is_indie, created_at
                ) VALUES (
                    :app_id, :name, :type, :is_free, :short_description,
                    :price_currency, :price_initial, :price_final, :price_discount_percent,
                    :release_date_text, :release_date_coming_soon, :release_date,
                    :platforms_windows, :platforms_mac, :platforms_linux,
                    :positive_reviews, :negative_reviews, :total_reviews,
                    :is_indie, :created_at
                ) ON CONFLICT (app_id) DO NOTHING
            """), {
                "app_id": game.app_id,
                "name": game.name,
                "type": game.type,
                "is_free": game.is_free,
                "short_description": game.short_description,
                "price_currency": game.price_currency,
                "price_initial": game.price_initial,
                "price_final": game.price_final,
                "price_discount_percent": game.price_discount_percent,
                "release_date_text": game.release_date_text,
                "release_date_coming_soon": game.release_date_coming_soon,
                "release_date": release_date,
                "platforms_windows": game.platforms_windows,
                "platforms_mac": game.platforms_mac,
                "platforms_linux": game.platforms_linux,
                "positive_reviews": game.positive_reviews,
                "negative_reviews": game.negative_reviews,
                "total_reviews": game.total_reviews,
                "is_indie": is_indie,
                "created_at": game.created_at
            })
            
            # 関係テーブルへの挿入
            self._insert_game_relations(game.app_id, game.genres, game.developers, game.publishers, game.categories)
        
        self.session.commit()
        logger.info("✅ ゲームデータ移行完了")
    
    def _insert_game_relations(self, app_id: int, genres: List[str], developers: List[str], 
                             publishers: List[str], categories: List[str]):
        """ゲーム関係テーブルへの挿入"""
        
        # ジャンル関係
        if genres:
            for i, genre in enumerate(genres):
                is_primary = (i == 0)  # 最初のジャンルを主要ジャンルとする
                self.session.execute(text("""
                    INSERT INTO game_genres (game_id, genre_id, is_primary)
                    SELECT :game_id, g.id, :is_primary
                    FROM genres g WHERE g.name = :genre_name
                    ON CONFLICT DO NOTHING
                """), {"game_id": app_id, "genre_name": genre, "is_primary": is_primary})
        
        # 開発者関係
        if developers:
            for i, developer in enumerate(developers):
                is_primary = (i == 0)  # 最初の開発者を主要開発者とする
                self.session.execute(text("""
                    INSERT INTO game_developers (game_id, developer_id, is_primary)
                    SELECT :game_id, d.id, :is_primary
                    FROM developers d WHERE d.name = :developer_name
                    ON CONFLICT DO NOTHING
                """), {"game_id": app_id, "developer_name": developer, "is_primary": is_primary})
        
        # パブリッシャー関係
        if publishers:
            for i, publisher in enumerate(publishers):
                is_primary = (i == 0)  # 最初のパブリッシャーを主要パブリッシャーとする
                self.session.execute(text("""
                    INSERT INTO game_publishers (game_id, publisher_id, is_primary)
                    SELECT :game_id, p.id, :is_primary
                    FROM publishers p WHERE p.name = :publisher_name
                    ON CONFLICT DO NOTHING
                """), {"game_id": app_id, "publisher_name": publisher, "is_primary": is_primary})
        
        # カテゴリ関係
        if categories:
            for category in categories:
                self.session.execute(text("""
                    INSERT INTO game_categories (game_id, category_id)
                    SELECT :game_id, c.id
                    FROM categories c WHERE c.name = :category_name
                    ON CONFLICT DO NOTHING
                """), {"game_id": app_id, "category_name": category})
    
    def _is_indie_developer(self, developer_name: str) -> bool:
        """開発者がインディーかどうかの判定"""
        # 簡単な判定ロジック
        major_publishers = {
            'Electronic Arts', 'Activision', 'Ubisoft', 'Sony', 'Microsoft',
            'Nintendo', 'Take-Two Interactive', 'Square Enix', 'Capcom',
            'Konami', 'Sega', 'Bandai Namco', 'Warner Bros'
        }
        return developer_name not in major_publishers
    
    def _is_major_publisher(self, publisher_name: str) -> bool:
        """大手パブリッシャーかどうかの判定"""
        major_publishers = {
            'Electronic Arts', 'Activision Blizzard', 'Ubisoft', 'Sony Interactive Entertainment',
            'Microsoft Studios', 'Nintendo', 'Take-Two Interactive', 'Square Enix',
            'Capcom', 'Konami', 'Sega', 'Bandai Namco Entertainment', 'Warner Bros. Games',
            'Bethesda Softworks', 'Epic Games', 'Valve Corporation'
        }
        return publisher_name in major_publishers
    
    def _determine_indie_status(self, game) -> bool:
        """ゲームのインディー判定"""
        # ジャンルに'Indie'が含まれている
        if game.genres and 'Indie' in game.genres:
            return True
        
        # 開発者とパブリッシャーが同一で少数
        if (game.developers and game.publishers and 
            len(game.developers) <= 2 and 
            set(game.developers) == set(game.publishers)):
            return True
        
        return False
    
    def _parse_release_date(self, date_text: str):
        """リリース日テキストをパース"""
        if not date_text:
            return None
        
        try:
            # 様々な日付フォーマットに対応
            from dateutil import parser
            return parser.parse(date_text).date()
        except:
            return None
    
    def verify_migration(self):
        """移行結果の検証"""
        logger.info("🔍 移行結果を検証中...")
        
        # 件数確認
        original_count = self.session.execute(text("SELECT COUNT(*) FROM games")).scalar()
        new_count = self.session.execute(text("SELECT COUNT(*) FROM games_normalized")).scalar()
        
        logger.info(f"移行前ゲーム数: {original_count:,}")
        logger.info(f"移行後ゲーム数: {new_count:,}")
        
        # マスタテーブル件数
        genres_count = self.session.execute(text("SELECT COUNT(*) FROM genres")).scalar()
        developers_count = self.session.execute(text("SELECT COUNT(*) FROM developers")).scalar()
        publishers_count = self.session.execute(text("SELECT COUNT(*) FROM publishers")).scalar()
        categories_count = self.session.execute(text("SELECT COUNT(*) FROM categories")).scalar()
        
        logger.info(f"ジャンル: {genres_count:,}件")
        logger.info(f"開発者: {developers_count:,}件")
        logger.info(f"パブリッシャー: {publishers_count:,}件")
        logger.info(f"カテゴリ: {categories_count:,}件")
        
        # 関係テーブル件数
        game_genres_count = self.session.execute(text("SELECT COUNT(*) FROM game_genres")).scalar()
        game_developers_count = self.session.execute(text("SELECT COUNT(*) FROM game_developers")).scalar()
        
        logger.info(f"ゲーム-ジャンル関係: {game_genres_count:,}件")
        logger.info(f"ゲーム-開発者関係: {game_developers_count:,}件")
        
        # インディーゲーム数確認
        indie_count = self.session.execute(text(
            "SELECT COUNT(*) FROM games_normalized WHERE is_indie = true"
        )).scalar()
        logger.info(f"インディーゲーム: {indie_count:,}件")
        
        logger.info("✅ 移行検証完了")


def main():
    """メイン実行関数"""
    logger.info("🚀 データベーススキーマ移行を開始...")
    
    try:
        with SchemaMigrator() as migrator:
            # 1. 正規化スキーマ作成
            migrator.create_normalized_schema()
            
            # 2. マスタデータ移行
            migrator.migrate_master_data()
            
            # 3. ゲームデータ移行
            migrator.migrate_game_data()
            
            # 4. 移行結果検証
            migrator.verify_migration()
        
        logger.info("🎉 データベーススキーマ移行が正常に完了しました！")
        
    except Exception as e:
        logger.error(f"❌ 移行中にエラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    main()