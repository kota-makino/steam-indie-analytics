"""
Render環境用データベース初期化スクリプト
PostgreSQLスキーマ作成とサンプルデータ投入
"""

import os
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

class RenderDatabaseSetup:
    """Render環境用データベースセットアップ"""

    def __init__(self):
        # Render環境のPostgreSQL接続設定
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
        }
        
        # 接続設定の確認
        missing_vars = [k for k, v in self.db_config.items() if v is None]
        if missing_vars:
            raise ValueError(f"必要な環境変数が設定されていません: {missing_vars}")
            
        print("🔗 Render PostgreSQL接続設定:")
        print(f"   Host: {self.db_config['host']}")
        print(f"   Port: {self.db_config['port']}")
        print(f"   Database: {self.db_config['database']}")
        print(f"   User: {self.db_config['user']}")

    def connect_db(self):
        """データベース接続"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = True
            return conn
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            raise

    def load_sql_file(self, file_path: str) -> str:
        """SQLファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"❌ SQLファイル読み込みエラー ({file_path}): {e}")
            raise

    def execute_sql_script(self, conn, sql_script: str, description: str):
        """SQLスクリプト実行"""
        cursor = conn.cursor()
        try:
            print(f"🛠️  {description} 実行中...")
            
            # スクリプトを個別のステートメントに分割して実行
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    try:
                        cursor.execute(statement)
                        if "CREATE TABLE" in statement.upper():
                            table_name = statement.split("TABLE")[1].split("(")[0].strip()
                            print(f"   ✅ テーブル作成: {table_name}")
                        elif "CREATE INDEX" in statement.upper():
                            print(f"   📊 インデックス作成: Statement {i}")
                        elif "CREATE VIEW" in statement.upper():
                            view_name = statement.split("VIEW")[1].split("AS")[0].strip()
                            print(f"   👁️  ビュー作成: {view_name}")
                    except Exception as e:
                        print(f"   ⚠️  ステートメント {i} スキップ: {str(e)[:100]}...")
                        continue
            
            print(f"✅ {description} 完了")
            
        except Exception as e:
            print(f"❌ {description} エラー: {e}")
            raise
        finally:
            cursor.close()

    def create_normalized_schema(self, conn):
        """正規化スキーマ作成"""
        sql_file_path = "/workspace/sql/create_normalized_schema.sql"
        
        if os.path.exists(sql_file_path):
            sql_script = self.load_sql_file(sql_file_path)
            self.execute_sql_script(conn, sql_script, "正規化スキーマ作成")
        else:
            print(f"⚠️  SQLファイルが見つかりません: {sql_file_path}")
            # フォールバック: 基本スキーマを直接作成
            self.create_basic_schema(conn)

    def create_basic_schema(self, conn):
        """基本スキーマ作成（フォールバック）"""
        
        basic_schema_sql = """
        -- 基本的なgamesテーブル作成
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

        -- インデックス作成
        CREATE INDEX IF NOT EXISTS idx_games_name ON games(name);
        CREATE INDEX IF NOT EXISTS idx_games_type ON games(type);
        CREATE INDEX IF NOT EXISTS idx_games_developers ON games USING GIN(developers);
        CREATE INDEX IF NOT EXISTS idx_games_genres ON games USING GIN(genres);
        CREATE INDEX IF NOT EXISTS idx_games_total_reviews ON games(total_reviews);
        """
        
        self.execute_sql_script(conn, basic_schema_sql, "基本スキーマ作成")

    def insert_sample_data(self, conn):
        """サンプルデータ投入"""
        cursor = conn.cursor()
        try:
            print("🎯 サンプルデータ投入中...")
            
            # 既存データ数の確認
            cursor.execute("SELECT COUNT(*) FROM games")
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                print(f"   📊 既存データ: {existing_count}件")
                print("   ✅ サンプルデータは既に投入済みです")
                return
            
            # インディーゲームのサンプルデータ
            sample_games = [
                {
                    'app_id': 413150,
                    'name': 'Stardew Valley',
                    'type': 'game',
                    'is_free': False,
                    'short_description': 'You\'ve inherited your grandfather\'s old farm plot in Stardew Valley.',
                    'developers': ['ConcernedApe'],
                    'publishers': ['ConcernedApe'],
                    'price_final': 1498,
                    'genres': ['Simulation', 'RPG', 'Indie'],
                    'positive_reviews': 98000,
                    'negative_reviews': 2000,
                    'total_reviews': 100000,
                    'platforms_windows': True,
                    'platforms_mac': True,
                    'platforms_linux': True
                },
                {
                    'app_id': 367520,
                    'name': 'Hollow Knight',
                    'type': 'game',
                    'is_free': False,
                    'short_description': 'Forge your own path in Hollow Knight!',
                    'developers': ['Team Cherry'],
                    'publishers': ['Team Cherry'],
                    'price_final': 1499,
                    'genres': ['Metroidvania', 'Action', 'Indie'],
                    'positive_reviews': 85000,
                    'negative_reviews': 3000,
                    'total_reviews': 88000,
                    'platforms_windows': True,
                    'platforms_mac': True,
                    'platforms_linux': True
                },
                {
                    'app_id': 391540,
                    'name': 'Undertale',
                    'type': 'game',
                    'is_free': False,
                    'short_description': 'The RPG game where you don\'t have to destroy anyone.',
                    'developers': ['tobyfox'],
                    'publishers': ['tobyfox'],
                    'price_final': 999,
                    'genres': ['RPG', 'Indie'],
                    'positive_reviews': 75000,
                    'negative_reviews': 2500,
                    'total_reviews': 77500,
                    'platforms_windows': True,
                    'platforms_mac': True,
                    'platforms_linux': True
                }
            ]
            
            insert_sql = """
            INSERT INTO games (
                app_id, name, type, is_free, short_description,
                developers, publishers, price_final, genres,
                positive_reviews, negative_reviews, total_reviews,
                platforms_windows, platforms_mac, platforms_linux
            ) VALUES (
                %(app_id)s, %(name)s, %(type)s, %(is_free)s, %(short_description)s,
                %(developers)s, %(publishers)s, %(price_final)s, %(genres)s,
                %(positive_reviews)s, %(negative_reviews)s, %(total_reviews)s,
                %(platforms_windows)s, %(platforms_mac)s, %(platforms_linux)s
            )
            """
            
            for game in sample_games:
                cursor.execute(insert_sql, game)
                print(f"   ✅ 追加: {game['name']}")
            
            print(f"✅ サンプルデータ投入完了: {len(sample_games)}件")
            
        except Exception as e:
            print(f"❌ サンプルデータ投入エラー: {e}")
            raise
        finally:
            cursor.close()

    def verify_setup(self, conn):
        """セットアップ検証"""
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            print("🔍 データベースセットアップ検証中...")
            
            # テーブル一覧取得
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cursor.fetchall()]
            print(f"   📊 作成されたテーブル: {len(tables)}個")
            for table in tables[:5]:  # 最初の5個を表示
                print(f"      - {table}")
            if len(tables) > 5:
                print(f"      ... 他 {len(tables)-5}個")
            
            # ビュー一覧取得
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'VIEW'
                ORDER BY table_name
            """)
            views = [row['table_name'] for row in cursor.fetchall()]
            print(f"   👁️  作成されたビュー: {len(views)}個")
            for view in views:
                print(f"      - {view}")
            
            # ゲーム数確認
            cursor.execute("SELECT COUNT(*) as count FROM games")
            game_count = cursor.fetchone()['count']
            print(f"   🎮 登録ゲーム数: {game_count}件")
            
            # 最新ゲーム3件表示
            if game_count > 0:
                cursor.execute("""
                    SELECT name, array_length(developers, 1) as dev_count, total_reviews
                    FROM games 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                recent_games = cursor.fetchall()
                print(f"   🏆 最新ゲーム:")
                for game in recent_games:
                    print(f"      - {game['name']} ({game['total_reviews'] or 0} reviews)")
            
            print("✅ データベースセットアップ検証完了")
            
        except Exception as e:
            print(f"❌ セットアップ検証エラー: {e}")
            raise
        finally:
            cursor.close()

    def run_setup(self):
        """フルセットアップ実行"""
        print("🚀 Render PostgreSQL データベースセットアップ開始")
        print("=" * 60)
        
        try:
            # データベース接続
            conn = self.connect_db()
            print("✅ データベース接続成功")
            
            # スキーマ作成
            self.create_normalized_schema(conn)
            
            # サンプルデータ投入
            self.insert_sample_data(conn)
            
            # セットアップ検証
            self.verify_setup(conn)
            
            print("\n" + "=" * 60)
            print("🎉 Render データベースセットアップ完了!")
            print("📊 ダッシュボードでデータ確認可能です")
            print("🔄 実際のデータ収集は collect_indie_games.py を実行してください")
            
        except Exception as e:
            print(f"❌ セットアップ失敗: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()


def main():
    """メイン実行関数"""
    try:
        setup = RenderDatabaseSetup()
        setup.run_setup()
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        exit(1)


if __name__ == "__main__":
    main()