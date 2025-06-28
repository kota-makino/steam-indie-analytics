#!/usr/bin/env python3
"""
データベース設定とセッション管理モジュール

SQLAlchemy 2.0を使用したPostgreSQLデータベース接続の管理。
非同期セッションとエンジンの設定を提供。
"""

import os
import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import logging

# 環境変数読み込み
load_dotenv()

# ログ設定
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """データベース設定クラス"""

    def __init__(self):
        """データベース設定の初期化（DATABASE_URL優先対応）"""
        # DATABASE_URLが設定されている場合は優先使用（Render等のクラウドプラットフォーム）
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            # DATABASE_URLをパースして接続情報を取得
            from urllib.parse import urlparse

            parsed_url = urlparse(database_url)

            self.host = parsed_url.hostname
            self.port = parsed_url.port or 5432
            self.database = parsed_url.path[1:]  # '/'を除去
            self.user = parsed_url.username
            self.password = parsed_url.password

            # 接続URL構築（DATABASE_URLベース）
            self.sync_url = database_url
            # asyncpg用にスキーマを変更
            self.async_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        else:
            # 従来の個別環境変数方式（ローカル開発環境）
            self.host = os.getenv("POSTGRES_HOST", "localhost")
            self.port = int(os.getenv("POSTGRES_PORT", 5433))
            self.database = os.getenv("POSTGRES_DB", "steam_analytics")
            self.user = os.getenv("POSTGRES_USER", "steam_user")
            self.password = os.getenv("POSTGRES_PASSWORD", "steam_password")

            # 接続URL構築
            self.sync_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self.async_url = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_sync_engine(self) -> Engine:
        """同期エンジンの取得"""
        return create_engine(
            self.sync_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )

    def get_async_engine(self) -> AsyncEngine:
        """非同期エンジンの取得"""
        return create_async_engine(
            self.async_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )


# グローバル設定インスタンス
db_config = DatabaseConfig()

# 同期エンジンとセッションファクトリ
sync_engine = db_config.get_sync_engine()
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

# 非同期エンジンとセッションファクトリ
try:
    async_engine = db_config.get_async_engine()
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
except ImportError as e:
    logger.warning(f"AsyncPG not available, async functionality disabled: {e}")
    async_engine = None
    AsyncSessionLocal = None


def get_sync_session() -> Session:
    """
    同期データベースセッションの取得

    Returns:
        Session: SQLAlchemy同期セッション
    """
    return SyncSessionLocal()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    非同期データベースセッションの取得（コンテキストマネージャー）

    Yields:
        AsyncSession: SQLAlchemy非同期セッション
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async database functionality is not available. Install asyncpg."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_database_url() -> str:
    """
    データベース接続URLの取得

    Returns:
        str: データベース接続URL
    """
    return db_config.sync_url


def test_connection() -> bool:
    """
    データベース接続テスト

    Returns:
        bool: 接続成功時True、失敗時False
    """
    try:
        from sqlalchemy import text

        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.fetchone()[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


async def test_async_connection() -> bool:
    """
    非同期データベース接続テスト

    Returns:
        bool: 接続成功時True、失敗時False
    """
    if async_engine is None:
        return False

    try:
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return (await result.fetchone())[0] == 1
    except Exception as e:
        logger.error(f"Async database connection test failed: {e}")
        return False


# 使用例とテスト関数
async def main():
    """データベース接続テスト用メイン関数"""

    print("🔍 データベース接続テストを実行中...")

    # 同期接続テスト
    print("📍 同期接続テスト...")
    sync_result = test_connection()
    print(f"   同期接続: {'✅ 成功' if sync_result else '❌ 失敗'}")

    # 非同期接続テスト
    print("📍 非同期接続テスト...")
    async_result = await test_async_connection()
    print(f"   非同期接続: {'✅ 成功' if async_result else '❌ 失敗'}")

    # 設定情報表示
    print(f"\n📊 データベース設定:")
    print(f"   ホスト: {db_config.host}")
    print(f"   ポート: {db_config.port}")
    print(f"   データベース: {db_config.database}")
    print(f"   ユーザー: {db_config.user}")

    # セッション使用例
    if sync_result:
        print(f"\n🔧 セッション使用例:")

        # 同期セッション例
        from sqlalchemy import text

        with get_sync_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM games WHERE type = 'game'")
            )
            game_count = result.scalar()
            print(f"   ゲーム総数（同期）: {game_count:,}")

        # 非同期セッション例
        if async_result:
            from sqlalchemy import text

            async with get_db_session() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM games WHERE type = 'game'")
                )
                async_game_count = result.scalar()
                print(f"   ゲーム総数（非同期）: {async_game_count:,}")


if __name__ == "__main__":
    asyncio.run(main())
