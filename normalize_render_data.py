#!/usr/bin/env python3
"""
Render環境での正規化データ処理
gamesテーブルから正規化テーブルへデータを移行
"""

import os
import psycopg2
from urllib.parse import urlparse

def normalize_render_data():
    """正規化データ処理を実行"""
    print("🚀 Render環境 正規化データ処理開始")
    
    # DATABASE_URL取得
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URLが設定されていません")
        return False
    
    try:
        # 接続設定
        parsed_url = urlparse(database_url)
        db_config = {
            "host": parsed_url.hostname,
            "port": parsed_url.port or 5432,
            "database": parsed_url.path[1:],
            "user": parsed_url.username,
            "password": parsed_url.password,
        }
        
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ データベース接続成功")
        
        # 既存の正規化データをクリア
        print("🧹 既存の正規化データをクリア中...")
        cursor.execute("DELETE FROM game_genres")
        cursor.execute("DELETE FROM game_developers") 
        cursor.execute("DELETE FROM game_publishers")
        cursor.execute("DELETE FROM game_categories")
        cursor.execute("DELETE FROM games_normalized")
        cursor.execute("DELETE FROM genres WHERE id > 0")
        cursor.execute("DELETE FROM developers WHERE id > 0") 
        cursor.execute("DELETE FROM publishers WHERE id > 0")
        cursor.execute("DELETE FROM categories WHERE id > 0")
        
        # gamesテーブルからデータ取得
        cursor.execute("""
            SELECT app_id, name, type, is_free, detailed_description, short_description,
                   developers, publishers, price_currency, price_initial, price_final,
                   price_discount_percent, release_date_text, release_date_coming_soon,
                   platforms_windows, platforms_mac, platforms_linux,
                   genres, categories, positive_reviews, negative_reviews, total_reviews,
                   recommendation_score, created_at, updated_at
            FROM games 
            WHERE type = 'game' AND 'Indie' = ANY(genres)
        """)
        
        games_data = cursor.fetchall()
        print(f"📊 処理対象ゲーム: {len(games_data)}件")
        
        # ジャンル、開発者、パブリッシャー、カテゴリのマスタを構築
        genre_dict = {}
        developer_dict = {}
        publisher_dict = {}
        category_dict = {}
        
        # 全ユニーク値を収集
        all_genres = set()
        all_developers = set()
        all_publishers = set()
        all_categories = set()
        
        for game in games_data:
            if game[17]:  # genres
                all_genres.update(game[17])
            if game[6]:   # developers
                all_developers.update(game[6])
            if game[7]:   # publishers
                all_publishers.update(game[7])
            if game[18]:  # categories
                all_categories.update(game[18])
        
        # マスタテーブルにデータ投入
        print("📝 マスタテーブル構築中...")
        
        # ジャンルマスタ
        for i, genre in enumerate(sorted(all_genres), 1):
            cursor.execute("INSERT INTO genres (id, name) VALUES (%s, %s)", (i, genre))
            genre_dict[genre] = i
        
        # 開発者マスタ
        for i, developer in enumerate(sorted(all_developers), 1):
            cursor.execute("INSERT INTO developers (id, name) VALUES (%s, %s)", (i, developer))
            developer_dict[developer] = i
        
        # パブリッシャーマスタ
        for i, publisher in enumerate(sorted(all_publishers), 1):
            cursor.execute("INSERT INTO publishers (id, name) VALUES (%s, %s)", (i, publisher))
            publisher_dict[publisher] = i
        
        # カテゴリマスタ
        for i, category in enumerate(sorted(all_categories), 1):
            cursor.execute("INSERT INTO categories (id, name) VALUES (%s, %s)", (i, category))
            category_dict[category] = i
        
        print(f"  ジャンル: {len(genre_dict)}件")
        print(f"  開発者: {len(developer_dict)}件")
        print(f"  パブリッシャー: {len(publisher_dict)}件")
        print(f"  カテゴリ: {len(category_dict)}件")
        
        # games_normalizedテーブルにデータ投入
        print("🔄 正規化テーブルにデータ投入中...")
        
        processed = 0
        for game in games_data:
            app_id = game[0]
            
            # games_normalizedに基本情報を投入
            cursor.execute("""
                INSERT INTO games_normalized (
                    app_id, name, type, is_free, detailed_description, short_description,
                    price_currency, price_initial, price_final, price_discount_percent,
                    release_date_text, release_date_coming_soon,
                    platforms_windows, platforms_mac, platforms_linux,
                    positive_reviews, negative_reviews, total_reviews,
                    recommendation_score, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (app_id) DO NOTHING
            """, (
                app_id, game[1], game[2], game[3], game[4], game[5],
                game[8], game[9], game[10], game[11],
                game[12], game[13], game[14], game[15], game[16],
                game[19], game[20], game[21], game[22], game[23], game[24]
            ))
            
            # 関連テーブルにデータ投入
            if game[17]:  # genres
                for genre in game[17]:
                    if genre in genre_dict:
                        cursor.execute("""
                            INSERT INTO game_genres (game_id, genre_id) 
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                        """, (app_id, genre_dict[genre]))
            
            if game[6]:   # developers
                for developer in game[6]:
                    if developer in developer_dict:
                        cursor.execute("""
                            INSERT INTO game_developers (game_id, developer_id) 
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                        """, (app_id, developer_dict[developer]))
            
            if game[7]:   # publishers
                for publisher in game[7]:
                    if publisher in publisher_dict:
                        cursor.execute("""
                            INSERT INTO game_publishers (game_id, publisher_id) 
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                        """, (app_id, publisher_dict[publisher]))
            
            if game[18]:  # categories
                for category in game[18]:
                    if category in category_dict:
                        cursor.execute("""
                            INSERT INTO game_categories (game_id, category_id) 
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                        """, (app_id, category_dict[category]))
            
            processed += 1
            if processed % 100 == 0:
                print(f"  進行中: {processed}/{len(games_data)} ({processed/len(games_data)*100:.1f}%)")
        
        # 結果確認
        cursor.execute("SELECT COUNT(*) FROM games_normalized")
        normalized_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM game_genres")
        game_genres_count = cursor.fetchone()[0]
        
        print("✅ 正規化処理完了")
        print(f"📊 結果:")
        print(f"  games_normalized: {normalized_count}件")
        print(f"  game_genres: {game_genres_count}件")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 正規化処理エラー: {e}")
        return False

if __name__ == "__main__":
    success = normalize_render_data()
    exit(0 if success else 1)