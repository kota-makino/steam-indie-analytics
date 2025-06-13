"""
Steam Web API からインディーゲーム情報を収集するモジュール

このモジュールは以下の機能を提供します:
- Steam Web API からゲーム一覧を取得
- 個別ゲームの詳細情報を取得
- レビューデータの収集
- レート制限の管理とリトライ処理
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SteamGameData:
    """Steam ゲームデータを格納するデータクラス"""

    app_id: int
    name: str
    type: str
    is_free: bool
    detailed_description: Optional[str] = None
    short_description: Optional[str] = None
    developers: Optional[List[str]] = None
    publishers: Optional[List[str]] = None
    price_overview: Optional[Dict[str, Any]] = None
    release_date: Optional[Dict[str, Any]] = None
    platforms: Optional[Dict[str, bool]] = None
    categories: Optional[List[Dict[str, Any]]] = None
    genres: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    positive_reviews: Optional[int] = None
    negative_reviews: Optional[int] = None
    total_reviews: Optional[int] = None
    recommendation_score: Optional[float] = None


class SteamAPIRateLimiter:
    """Steam API のレート制限を管理するクラス

    Steam Web API の制限（200リクエスト/5分）に対応した
    レート制限とリトライ機能を提供
    """

    def __init__(self, max_requests: int = 200, time_window: int = 300) -> None:
        """
        Args:
            max_requests: 制限時間内の最大リクエスト数（デフォルト: 200）
            time_window: 制限時間（秒）（デフォルト: 300 = 5分）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """レート制限チェックを行い、必要に応じて待機"""
        async with self._lock:
            now = datetime.now()
            # 制限時間を過ぎた古いリクエスト記録を削除
            cutoff_time = now - timedelta(seconds=self.time_window)
            self.requests = [
                req_time for req_time in self.requests if req_time > cutoff_time
            ]

            # 制限に達している場合は待機
            if len(self.requests) >= self.max_requests:
                sleep_time = (self.requests[0] - cutoff_time).total_seconds()
                logger.info(f"レート制限により {sleep_time:.1f}秒待機します")
                await asyncio.sleep(sleep_time)
                self.requests = self.requests[1:]

            # 現在時刻を記録
            self.requests.append(now)


class SteamAPIClient:
    """Steam Web API クライアント

    Steam Web API との通信を担当し、レート制限やエラーハンドリングを実装
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Args:
            api_key: Steam Web API キー（環境変数から自動取得）
        """
        self.api_key = api_key or os.getenv("STEAM_API_KEY")
        if not self.api_key:
            msg = (
                "Steam API キーが設定されていません。"
                "STEAM_API_KEY環境変数を設定してください。"
            )
            raise ValueError(msg)

        self.base_url = "https://api.steampowered.com"
        self.store_url = "https://store.steampowered.com/api"
        self.rate_limiter = SteamAPIRateLimiter()

        # セッション設定
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def __aenter__(self) -> "SteamAPIClient":
        """非同期コンテキストマネージャー（開始）"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """非同期コンテキストマネージャー（終了）"""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def _make_request(
        self, url: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """APIリクエストを実行（リトライ機能付き）

        Args:
            url: リクエストURL
            params: URLパラメータ

        Returns:
            APIレスポンス（JSON形式）

        Raises:
            aiohttp.ClientError: HTTPエラー
            asyncio.TimeoutError: タイムアウト
        """
        await self.rate_limiter.acquire()

        if not self.session:
            msg = (
                "セッションが初期化されていません。"
                "withステートメントを使用してください。"
            )
            raise RuntimeError(msg)

        try:
            async with self.session.get(url, params=params or {}) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"APIリクエストエラー: {url} - {str(e)}")
            raise
        except asyncio.TimeoutError:
            logger.error(f"APIリクエストタイムアウト: {url}")
            raise

    async def get_app_list(self) -> List[Dict[str, Any]]:
        """Steam の全アプリケーション一覧を取得

        Returns:
            アプリケーション一覧（[{appid, name}, ...]形式）
        """
        url = f"{self.base_url}/ISteamApps/GetAppList/v2/"
        params = {"key": self.api_key}

        try:
            response = await self._make_request(url, params)
            apps = response.get("applist", {}).get("apps", [])
            logger.info(f"Steam アプリケーション一覧を取得: {len(apps)}件")
            return apps
        except Exception as e:
            logger.error(f"アプリケーション一覧取得エラー: {str(e)}")
            return []

    async def get_app_details(self, app_id: int) -> Optional[SteamGameData]:
        """個別ゲームの詳細情報を取得

        Args:
            app_id: Steam アプリケーションID

        Returns:
            ゲーム詳細情報（SteamGameData形式）
        """
        url = f"{self.store_url}/appdetails"
        params = {"appids": app_id, "l": "english", "cc": "us"}  # 言語設定  # 国設定

        try:
            response = await self._make_request(url, params)
            app_data = response.get(str(app_id))

            if not app_data or not app_data.get("success"):
                logger.warning(f"アプリID {app_id} の詳細情報が取得できませんでした")
                return None

            data = app_data.get("data", {})

            # SteamGameData オブジェクトを作成
            game_data = SteamGameData(
                app_id=app_id,
                name=data.get("name", ""),
                type=data.get("type", ""),
                is_free=data.get("is_free", False),
                detailed_description=data.get("detailed_description"),
                short_description=data.get("short_description"),
                developers=data.get("developers", []),
                publishers=data.get("publishers", []),
                price_overview=data.get("price_overview"),
                release_date=data.get("release_date"),
                platforms=data.get("platforms"),
                categories=data.get("categories", []),
                genres=data.get("genres", []),
            )

            logger.info(f"ゲーム詳細情報を取得: {game_data.name} (ID: {app_id})")
            return game_data

        except Exception as e:
            logger.error(f"アプリ詳細情報取得エラー (ID: {app_id}): {str(e)}")
            return None

    async def get_app_reviews(
        self, app_id: int, num_per_page: int = 100
    ) -> Dict[str, Any]:
        """ゲームのレビューデータを取得

        Args:
            app_id: Steam アプリケーションID
            num_per_page: 1ページあたりのレビュー数（最大100）

        Returns:
            レビューデータ（統計情報含む）
        """
        url = f"{self.store_url}/appreviews/{app_id}"
        params = {
            "json": 1,
            "language": "all",
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": min(num_per_page, 100),
        }

        try:
            response = await self._make_request(url, params)

            if response.get("success") != 1:
                logger.warning(f"アプリID {app_id} のレビューが取得できませんでした")
                return {}

            query_summary = response.get("query_summary", {})
            reviews = response.get("reviews", [])

            logger.info(f"レビューデータを取得: {len(reviews)}件 (ID: {app_id})")

            return {
                "total_positive": query_summary.get("total_positive", 0),
                "total_negative": query_summary.get("total_negative", 0),
                "total_reviews": query_summary.get("total_reviews", 0),
                "review_score": query_summary.get("review_score", 0),
                "review_score_desc": query_summary.get("review_score_desc", ""),
                "reviews": reviews[:10],  # 最新10件のレビューのみ保存
            }

        except Exception as e:
            logger.error(f"レビューデータ取得エラー (ID: {app_id}): {str(e)}")
            return {}

    async def filter_indie_games(
        self, apps: List[Dict[str, Any]], sample_size: int = 1000
    ) -> List[int]:
        """インディーゲームを識別・フィルタリング

        Args:
            apps: アプリケーション一覧
            sample_size: 処理するアプリの最大数

        Returns:
            インディーゲームのアプリIDリスト
        """
        # インディーゲームの識別キーワード
        indie_keywords = [
            "indie",
            "independent",
            "small",
            "solo",
            "pixel",
            "retro",
            "casual",
            "adventure",
            "puzzle",
            "platformer",
            "roguelike",
        ]

        indie_app_ids = []

        # 名前でフィルタリング（第一段階）
        for app in apps[:sample_size]:
            name = app.get("name", "").lower()
            if any(keyword in name for keyword in indie_keywords):
                indie_app_ids.append(app["appid"])

        count = len(indie_app_ids)
        logger.info(f"名前ベースフィルタリング: {count}件のインディーゲーム候補を抽出")

        # 詳細情報でのフィルタリング（第二段階）
        confirmed_indie_games = []

        for app_id in indie_app_ids[:100]:  # 最初の100件のみ詳細チェック
            game_data = await self.get_app_details(app_id)
            if game_data and self._is_indie_game(game_data):
                confirmed_indie_games.append(app_id)

        confirmed_count = len(confirmed_indie_games)
        logger.info(
            f"詳細情報ベースフィルタリング: {confirmed_count}件のインディーゲームを確認"
        )
        return confirmed_indie_games

    def _is_indie_game(self, game_data: SteamGameData) -> bool:
        """ゲームデータからインディーゲームかどうかを判定

        Args:
            game_data: ゲーム詳細データ

        Returns:
            インディーゲームの場合True
        """
        # ジャンルベースの判定
        if game_data.genres:
            indie_genres = ["indie", "independent", "casual", "adventure"]
            for genre in game_data.genres:
                desc = genre.get("description", "").lower()
                if any(keyword in desc for keyword in indie_genres):
                    return True

        # カテゴリベースの判定
        if game_data.categories:
            for category in game_data.categories:
                if "indie" in category.get("description", "").lower():
                    return True

        # 開発者情報ベースの判定（大手パブリッシャーを除外）
        major_publishers = [
            "valve",
            "activision",
            "electronic arts",
            "ubisoft",
            "bethesda",
            "square enix",
            "capcom",
            "bandai namco",
            "sega",
            "take-two",
        ]

        if game_data.publishers:
            for publisher in game_data.publishers:
                if any(major in publisher.lower() for major in major_publishers):
                    return False

        return True


# 使用例とテスト関数
async def test_steam_api() -> None:
    """Steam API の動作テスト"""

    # APIキーの確認
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key or api_key == "your_steam_api_key_here":
        print("⚠️  Steam API キーが設定されていません")
        print("   https://steamcommunity.com/dev/apikey でキーを取得し、")
        print("   .env ファイルの STEAM_API_KEY を設定してください")
        return

    async with SteamAPIClient() as client:
        print("🎮 Steam API 接続テスト開始...")

        # 1. アプリケーション一覧取得テスト
        print("\n📋 アプリケーション一覧取得テスト...")
        apps = await client.get_app_list()
        if apps:
            print(f"✅ {len(apps)}件のアプリケーションを取得しました")
            print(f"   例: {apps[0]['name']} (ID: {apps[0]['appid']})")
        else:
            print("❌ アプリケーション一覧の取得に失敗しました")
            return

        # 2. ゲーム詳細情報取得テスト（有名なインディーゲーム：Stardew Valley）
        print("\n🎯 ゲーム詳細情報取得テスト...")
        stardew_valley_id = 413150  # Stardew Valley のアプリID
        game_data = await client.get_app_details(stardew_valley_id)

        if game_data:
            print(f"✅ ゲーム詳細情報を取得しました")
            print(f"   名前: {game_data.name}")
            print(f"   開発者: {game_data.developers}")
            print(
                f"   ジャンル: {[g.get('description') for g in game_data.genres or []]}"
            )
            print(f"   無料: {game_data.is_free}")
        else:
            print("❌ ゲーム詳細情報の取得に失敗しました")

        # 3. レビューデータ取得テスト
        print("\n📝 レビューデータ取得テスト...")
        review_data = await client.get_app_reviews(stardew_valley_id)

        if review_data:
            print(f"✅ レビューデータを取得しました")
            print(f"   総レビュー数: {review_data.get('total_reviews', 0):,}")
            print(f"   肯定的レビュー: {review_data.get('total_positive', 0):,}")
            print(f"   否定的レビュー: {review_data.get('total_negative', 0):,}")
            print(f"   評価スコア: {review_data.get('review_score_desc', 'N/A')}")
        else:
            print("❌ レビューデータの取得に失敗しました")

        # 4. インディーゲームフィルタリングテスト
        print("\n🔍 インディーゲームフィルタリングテスト...")
        indie_games = await client.filter_indie_games(apps[:500], sample_size=500)

        if indie_games:
            print(f"✅ {len(indie_games)}件のインディーゲームを特定しました")
            print(f"   最初の5件: {indie_games[:5]}")
        else:
            print("❌ インディーゲームの特定に失敗しました")

        print("\n🎉 Steam API テスト完了！")


if __name__ == "__main__":
    # テスト実行
    asyncio.run(test_steam_api())
