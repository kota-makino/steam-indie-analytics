#!/usr/bin/env python3
"""
Render環境データベース初期化（軽量版）
ビルド時またはワンタイム実行用
"""

import os
import psycopg2
from urllib.parse import urlparse


def init_database():
    """データベース初期化実行"""
    print("🚀 Render PostgreSQL データベース初期化開始")

    # DATABASE_URL取得
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URLが設定されていません")
        return False

    try:
        # DATABASE_URL解析
        parsed_url = urlparse(database_url)
        db_config = {
            "host": parsed_url.hostname,
            "port": parsed_url.port or 5432,
            "database": parsed_url.path[1:],
            "user": parsed_url.username,
            "password": parsed_url.password,
        }

        print(
            f"🔗 接続先: {db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

        # データベース接続
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()

        # テーブル存在確認
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'games'
            )
        """
        )
        table_exists = cursor.fetchone()[0]

        if table_exists:
            print("✅ gamesテーブルは既に存在します")

            # データ数確認
            cursor.execute("SELECT COUNT(*) FROM games")
            count = cursor.fetchone()[0]
            print(f"📊 既存データ数: {count}件")

            if count == 0:
                print("🎯 サンプルデータを投入します")
                insert_sample_data(cursor)
        else:
            print("🛠️ gamesテーブルを作成します")
            create_games_table(cursor)
            print("🎯 サンプルデータを投入します")
            insert_sample_data(cursor)

        cursor.close()
        conn.close()

        print("✅ データベース初期化完了")
        return True

    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        return False


def create_games_table(cursor):
    """gamesテーブル作成"""
    sql = """
    CREATE TABLE IF NOT EXISTS games (
        app_id INTEGER PRIMARY KEY,
        name VARCHAR(500) NOT NULL,
        type VARCHAR(50) DEFAULT 'game',
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
    
    CREATE INDEX IF NOT EXISTS idx_games_name ON games(name);
    CREATE INDEX IF NOT EXISTS idx_games_type ON games(type);
    CREATE INDEX IF NOT EXISTS idx_games_genres ON games USING GIN(genres);
    """

    cursor.execute(sql)
    print("✅ gamesテーブル作成完了")


def insert_sample_data(cursor):
    """サンプルデータ投入"""
    sample_games = [
        (
            413150,
            "Stardew Valley",
            "game",
            False,
            "You've inherited your grandfather's old farm plot in Stardew Valley.",
            ["ConcernedApe"],
            ["ConcernedApe"],
            1498,
            ["Simulation", "RPG", "Indie"],
            98000,
            2000,
            100000,
            True,
            True,
            True,
        ),
        (
            367520,
            "Hollow Knight",
            "game",
            False,
            "Forge your own path in Hollow Knight!",
            ["Team Cherry"],
            ["Team Cherry"],
            1499,
            ["Metroidvania", "Action", "Indie"],
            85000,
            3000,
            88000,
            True,
            True,
            True,
        ),
        (
            391540,
            "Undertale",
            "game",
            False,
            "The RPG game where you don't have to destroy anyone.",
            ["tobyfox"],
            ["tobyfox"],
            999,
            ["RPG", "Indie"],
            75000,
            2500,
            77500,
            True,
            True,
            True,
        ),
    ]

    insert_sql = """
    INSERT INTO games (
        app_id, name, type, is_free, short_description,
        developers, publishers, price_final, genres,
        positive_reviews, negative_reviews, total_reviews,
        platforms_windows, platforms_mac, platforms_linux
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (app_id) DO NOTHING
    """

    for game in sample_games:
        cursor.execute(insert_sql, game)
        print(f"   ✅ 追加: {game[1]}")

    print(f"✅ サンプルデータ投入完了: {len(sample_games)}件")


if __name__ == "__main__":
    success = init_database()
    exit(0 if success else 1)
