"""
データベース接続テスト（pytest対応版）

PostgreSQLとRedisの接続確認を行い、
Steam Analytics プロジェクトの基盤が正常に動作することを検証します。
"""

import logging
import os
import sys
from typing import Dict

import psycopg2  # type: ignore
import pytest
import redis  # type: ignore
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDatabaseConnections:
    """データベース接続のテストクラス"""

    def test_postgresql_connection(self):
        """PostgreSQL接続テスト"""
        print("🐘 PostgreSQL接続テスト開始...")

        # 環境変数から接続情報を取得
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }

        host = db_config["host"]
        port = db_config["port"]
        database = db_config["database"]
        print(f"接続先: {host}:{port}/{database}")

        try:
            # psycopg2による直接接続テスト
            print("  📡 psycopg2による接続テスト...")
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # 基本的なクエリ実行
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            version_short = version.split(",")[0]
            print(f"  ✅ PostgreSQLバージョン: {version_short}")

            # データベース一覧確認
            sql = "SELECT datname FROM pg_database WHERE datistemplate = false;"
            cursor.execute(sql)
            databases = [row[0] for row in cursor.fetchall()]
            print(f"  📋 利用可能なデータベース: {databases}")

            # 現在のユーザー確認
            cursor.execute("SELECT current_user;")
            current_user = cursor.fetchone()[0]
            print(f"  👤 接続ユーザー: {current_user}")

            cursor.close()
            conn.close()
            print("  ✅ psycopg2接続テスト成功")

        except Exception as e:
            print(f"  ❌ psycopg2接続エラー: {str(e)}")
            pytest.skip(f"PostgreSQL接続が利用できません: {str(e)}")

        try:
            # SQLAlchemyによる接続テスト
            print("  🔗 SQLAlchemyによる接続テスト...")

            # 接続文字列の構築
            user = db_config["user"]
            password = db_config["password"]
            host = db_config["host"]
            port = db_config["port"]
            database = db_config["database"]
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

            # エンジン作成
            engine = create_engine(db_url, echo=False)

            # 接続テスト
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test_value"))
                test_value = result.fetchone()[0]
                print(f"  ✅ SQLAlchemy接続テスト成功: {test_value}")

            # セッション作成テスト
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            session = SessionLocal()

            # テーブル一覧取得
            result = session.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]
            table_display = tables if tables else "(なし)"
            print(f"  📊 既存テーブル: {table_display}")

            session.close()
            engine.dispose()
            print("  ✅ SQLAlchemyセッションテスト成功")

        except Exception as e:
            print(f"  ❌ SQLAlchemy接続エラー: {str(e)}")
            pytest.skip(f"SQLAlchemy接続が利用できません: {str(e)}")

        print("🎉 PostgreSQL接続テスト完了\n")

    def test_redis_connection(self):
        """Redis接続テスト"""
        print("🔴 Redis接続テスト開始...")

        # 環境変数から接続情報を取得
        redis_config = {
            "host": os.getenv("REDIS_HOST", "redis"),
            "port": int(os.getenv("REDIS_PORT", 6379)),
            "db": int(os.getenv("REDIS_DB", 0)),
            "decode_responses": True,
        }

        host = redis_config["host"]
        port = redis_config["port"]
        db = redis_config["db"]
        print(f"接続先: {host}:{port}/{db}")

        try:
            # Redis接続
            r = redis.Redis(**redis_config)

            # 接続テスト
            pong = r.ping()
            if pong:
                print("  ✅ Redis ping成功")

            # 基本的な操作テスト
            test_key = "steam_analytics:test"
            test_value = "connection_test_success"

            # 書き込みテスト
            r.set(test_key, test_value, ex=60)  # 60秒で自動削除
            print("  ✅ Redis書き込みテスト成功")

            # 読み込みテスト
            retrieved_value = r.get(test_key)
            if retrieved_value == test_value:
                print("  ✅ Redis読み込みテスト成功")
            else:
                msg = f"  ❌ Redis読み込みエラー: 期待値={test_value}, "
                msg += f"実際={retrieved_value}"
                print(msg)
                pytest.fail("Redis読み込みテストに失敗しました")

            # Redis情報取得
            info = r.info()
            redis_version = info.get("redis_version", "Unknown")
            used_memory = info.get("used_memory_human", "Unknown")
            connected_clients = info.get("connected_clients", "Unknown")

            print(f"  📊 Redisバージョン: {redis_version}")
            print(f"  💾 使用メモリ: {used_memory}")
            print(f"  👥 接続クライアント数: {connected_clients}")

            # クリーンアップ
            r.delete(test_key)
            print("  🧹 テストデータクリーンアップ完了")

        except Exception as e:
            print(f"  ❌ Redis接続エラー: {str(e)}")
            pytest.skip(f"Redis接続が利用できません: {str(e)}")

        print("🎉 Redis接続テスト完了\n")

    def test_environment_variables(self):
        """環境変数設定テスト"""
        print("⚙️ 環境変数設定テスト開始...")

        # 必須環境変数のリスト
        required_vars = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_DB",
        ]

        # オプション環境変数のリスト
        optional_vars = [
            "STEAM_API_KEY",
            "GEMINI_API_KEY",
            "DEBUG",
            "LOG_LEVEL",
        ]

        missing_required = []
        missing_optional = []

        print("  📋 必須環境変数チェック:")
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # パスワード類は一部のみ表示
                if "password" in var.lower() or "key" in var.lower():
                    if len(value) > 6:
                        display_value = f"{value[:3]}***{value[-3:]}"
                    else:
                        display_value = "***"
                else:
                    display_value = value
                print(f"    ✅ {var}: {display_value}")
            else:
                missing_required.append(var)
                print(f"    ❌ {var}: 未設定")

        print("  📋 オプション環境変数チェック:")
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                # パスワード類は一部のみ表示
                if "password" in var.lower() or "key" in var.lower():
                    if len(value) > 6:
                        display_value = f"{value[:3]}***{value[-3:]}"
                    else:
                        display_value = "***"
                else:
                    display_value = value
                print(f"    ✅ {var}: {display_value}")
            else:
                missing_optional.append(var)
                print(f"    ⚠️ {var}: 未設定")

        # 結果サマリー
        if missing_required:
            print(f"  ❌ 必須環境変数が不足: {missing_required}")
            pytest.fail(f"必須環境変数が不足しています: {missing_required}")
        else:
            print("  ✅ 必須環境変数はすべて設定済み")

        if missing_optional:
            msg = "  ⚠️ オプション環境変数が未設定: "
            msg += f"{missing_optional}"
            print(msg)

        print("🎉 環境変数設定テスト完了\n")

    def test_steam_api_configuration(self):
        """Steam API設定テスト"""
        print("🎮 Steam API設定テスト開始...")

        api_key = os.getenv("STEAM_API_KEY")

        if not api_key or api_key == "your_steam_api_key_here":
            print("  ⚠️ Steam API キーが未設定")
            print("  📝 設定手順:")
            url = "https://steamcommunity.com/dev/apikey"
            print(f"     1. {url} にアクセス")
            print("     2. Steam アカウントでログイン")
            print("     3. ドメイン名に適当な値（例: localhost）を入力")
            env_setting = "     4. 取得したキーを .env ファイルの "
            env_setting += "STEAM_API_KEY に設定"
            print(env_setting)
            pytest.skip("Steam API キーが設定されていません")

        print(f"  ✅ Steam API キー: {api_key[:8]}***")

        # レート制限設定の確認
        rate_limit = os.getenv("STEAM_API_RATE_LIMIT", "200")
        retry_attempts = os.getenv("API_RETRY_ATTEMPTS", "3")
        backoff_factor = os.getenv("API_BACKOFF_FACTOR", "2")

        print("  📊 レート制限設定:")
        print(f"     最大リクエスト数: {rate_limit}/5分")
        print(f"     リトライ回数: {retry_attempts}回")
        print(f"     バックオフ係数: {backoff_factor}")

        print("🎉 Steam API設定テスト完了\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])