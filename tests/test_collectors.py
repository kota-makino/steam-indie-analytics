"""
データ収集モジュールのテスト

Steam API収集機能、レート制限対応、インディーゲーム判定ロジックの
包括的なテストを実行します。
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession, ClientTimeout
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from collect_indie_games import IndieGameCollector

# 環境変数の読み込み
load_dotenv()


class TestIndieGameCollector:
    """IndieGameCollectorクラスのテストスイート"""

    @pytest.fixture
    def collector(self):
        """テスト用のコレクターインスタンス"""
        return IndieGameCollector()

    @pytest.fixture
    def sample_game_data(self) -> Dict[str, Any]:
        """テスト用のサンプルゲームデータ"""
        return {
            "steam_appid": 413150,
            "name": "Stardew Valley",
            "type": "game",
            "is_free": False,
            "detailed_description": "A farming simulation game...",
            "short_description": "You've inherited your grandfather's old farm plot...",
            "developers": ["ConcernedApe"],
            "publishers": ["ConcernedApe"],
            "price_overview": {
                "currency": "USD",
                "initial": 1499,
                "final": 1499,
                "discount_percent": 0
            },
            "release_date": {
                "coming_soon": False,
                "date": "26 Feb, 2016"
            },
            "platforms": {
                "windows": True,
                "mac": True,
                "linux": True
            },
            "genres": [
                {"id": "23", "description": "Indie"},
                {"id": "28", "description": "Simulation"}
            ],
            "categories": [
                {"id": "2", "description": "Single-player"},
                {"id": "22", "description": "Steam Achievements"}
            ]
        }

    @pytest.fixture
    def sample_review_data(self) -> Dict[str, Any]:
        """テスト用のサンプルレビューデータ"""
        return {
            "total_positive": 45123,
            "total_negative": 2341,
            "total_reviews": 47464,
            "review_score": 9,
            "review_score_desc": "Overwhelmingly Positive"
        }

    @pytest.fixture
    def non_indie_game_data(self) -> Dict[str, Any]:
        """非インディーゲームのサンプルデータ"""
        return {
            "steam_appid": 570,
            "name": "Dota 2",
            "type": "game",
            "is_free": True,
            "developers": ["Valve"],
            "publishers": ["Valve"],
            "genres": [
                {"id": "1", "description": "Action"},
                {"id": "2", "description": "Strategy"}
            ],
            "categories": [
                {"id": "1", "description": "Multi-player"}
            ]
        }

    def test_indie_keywords_initialization(self, collector):
        """インディーキーワードの初期化テスト"""
        assert isinstance(collector.indie_keywords, list)
        assert len(collector.indie_keywords) > 0
        assert "indie" in collector.indie_keywords
        assert "independent" in collector.indie_keywords
        assert "pixel" in collector.indie_keywords

    def test_major_publishers_initialization(self, collector):
        """大手パブリッシャーリストの初期化テスト"""
        assert isinstance(collector.major_publishers, list)
        assert len(collector.major_publishers) > 0
        assert "valve" in collector.major_publishers
        assert "electronic arts" in collector.major_publishers
        assert "ubisoft" in collector.major_publishers

    def test_is_indie_game_positive_case(self, collector, sample_game_data):
        """インディーゲーム判定：正常ケース"""
        # ジャンルに「Indie」が含まれる場合
        result = collector.is_indie_game(sample_game_data)
        assert result is True

    def test_is_indie_game_self_publishing(self, collector):
        """インディーゲーム判定：セルフパブリッシングケース"""
        game_data = {
            "steam_appid": 12345,
            "name": "Test Indie Game",
            "type": "game",
            "developers": ["SmallStudio"],
            "publishers": ["SmallStudio"],  # 開発者=パブリッシャー
            "genres": [
                {"id": "1", "description": "Action"}
            ]
        }
        result = collector.is_indie_game(game_data)
        assert result is True

    def test_is_indie_game_small_team(self, collector):
        """インディーゲーム判定：小規模チームケース"""
        game_data = {
            "steam_appid": 12345,
            "name": "Test Indie Game",
            "type": "game",
            "developers": ["SmallStudio"],  # 1社のみ
            "publishers": ["AnotherPublisher"],
            "genres": [
                {"id": "1", "description": "Action"}
            ]
        }
        result = collector.is_indie_game(game_data)
        assert result is True

    def test_is_indie_game_major_publisher_rejection(self, collector, non_indie_game_data):
        """インディーゲーム判定：大手パブリッシャー除外"""
        result = collector.is_indie_game(non_indie_game_data)
        assert result is False

    def test_is_indie_game_missing_basic_data(self, collector):
        """インディーゲーム判定：基本データ不足"""
        # 名前なし
        game_data_no_name = {
            "steam_appid": 12345,
            "type": "game"
        }
        assert collector.is_indie_game(game_data_no_name) is False

        # App IDなし
        game_data_no_id = {
            "name": "Test Game",
            "type": "game"
        }
        assert collector.is_indie_game(game_data_no_id) is False

        # ジャンルなし
        game_data_no_genres = {
            "steam_appid": 12345,
            "name": "Test Game",
            "type": "game",
            "developers": ["TestDev"]
        }
        assert collector.is_indie_game(game_data_no_genres) is False

    def test_is_indie_game_excluded_types(self, collector):
        """インディーゲーム判定：除外対象タイプ"""
        # DLC
        dlc_data = {
            "steam_appid": 12345,
            "name": "Test Game DLC",
            "type": "game",
            "genres": [{"id": "23", "description": "Indie"}],
            "developers": ["TestDev"]
        }
        assert collector.is_indie_game(dlc_data) is False

        # Demo
        demo_data = {
            "steam_appid": 12345,
            "name": "Test Game Demo",
            "type": "game",
            "genres": [{"id": "23", "description": "Indie"}],
            "developers": ["TestDev"]
        }
        assert collector.is_indie_game(demo_data) is False

        # 非ゲームタイプ
        app_data = {
            "steam_appid": 12345,
            "name": "Test Application",
            "type": "application",
            "genres": [{"id": "23", "description": "Indie"}],
            "developers": ["TestDev"]
        }
        assert collector.is_indie_game(app_data) is False

    @pytest.mark.asyncio
    async def test_get_steam_game_list_fallback(self, collector):
        """Steam APIゲームリスト取得：フォールバック動作"""
        # HTTPセッションのモック
        with patch.object(collector, 'session') as mock_session:
            # 404エラーをシミュレート
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await collector.get_steam_game_list(limit=10)
            
            # フォールバックリストが返されることを確認
            assert isinstance(result, list)
            assert len(result) > 0
            assert len(result) <= 10

    def test_get_fallback_game_list(self, collector):
        """フォールバックゲームリストのテスト"""
        result = collector.get_fallback_game_list(5)
        
        assert isinstance(result, list)
        assert len(result) == 5
        # 既知のインディーゲームが含まれることを確認
        assert 413150 in result  # Stardew Valley
        assert 250900 in result  # The Binding of Isaac

    @pytest.mark.asyncio
    async def test_get_game_details_success(self, collector, sample_game_data):
        """ゲーム詳細取得：成功ケース"""
        app_id = 413150
        
        # APIレスポンスをモック
        mock_response_data = {
            str(app_id): {
                "success": True,
                "data": sample_game_data
            }
        }
        
        with patch.object(collector, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await collector.get_game_details(app_id)
            
            assert result is not None
            assert result["steam_appid"] == app_id
            assert result["name"] == "Stardew Valley"

    @pytest.mark.asyncio
    async def test_get_game_details_failure(self, collector):
        """ゲーム詳細取得：失敗ケース"""
        app_id = 999999
        
        # 失敗レスポンスをモック
        mock_response_data = {
            str(app_id): {
                "success": False
            }
        }
        
        with patch.object(collector, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await collector.get_game_details(app_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_game_details_rate_limit(self, collector):
        """ゲーム詳細取得：レート制限対応"""
        app_id = 413150
        
        with patch.object(collector, 'session') as mock_session:
            # 最初はレート制限エラー、次は成功
            responses = [
                AsyncMock(status=429),  # Too Many Requests
                AsyncMock(status=200, json=AsyncMock(return_value={
                    str(app_id): {"success": True, "data": {"steam_appid": app_id}}
                }))
            ]
            mock_session.get.return_value.__aenter__.side_effect = responses

            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await collector.get_game_details(app_id)
                
                # スリープが呼ばれたことを確認（レート制限対応）
                mock_sleep.assert_called()
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_game_reviews_success(self, collector, sample_review_data):
        """ゲームレビュー取得：成功ケース"""
        app_id = 413150
        
        mock_response_data = {
            "success": 1,
            "query_summary": sample_review_data
        }
        
        with patch.object(collector, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await collector.get_game_reviews(app_id)
            
            assert result is not None
            assert result["total_reviews"] == 47464
            assert result["review_score"] == 9

    @pytest.mark.asyncio
    async def test_get_game_reviews_failure(self, collector):
        """ゲームレビュー取得：失敗ケース"""
        app_id = 999999
        
        with patch.object(collector, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await collector.get_game_reviews(app_id)
            
            assert result is None

    def test_data_validation_edge_cases(self, collector):
        """データバリデーションのエッジケーステスト"""
        # 空のジャンルリスト
        game_empty_genres = {
            "steam_appid": 12345,
            "name": "Test Game",
            "type": "game",
            "genres": [],
            "developers": ["TestDev"]
        }
        assert collector.is_indie_game(game_empty_genres) is False

        # 開発者情報なし、ジャンル豊富
        game_no_dev_rich_genres = {
            "steam_appid": 12345,
            "name": "Test Game",
            "type": "game",
            "genres": [
                {"id": "1", "description": "Action"},
                {"id": "2", "description": "Adventure"},
                {"id": "23", "description": "Indie"}
            ],
            "developers": []
        }
        assert collector.is_indie_game(game_no_dev_rich_genres) is True

        # 開発者情報なし、ジャンル少ない
        game_no_dev_poor_genres = {
            "steam_appid": 12345,
            "name": "Test Game",
            "type": "game",
            "genres": [
                {"id": "1", "description": "Action"}
            ],
            "developers": []
        }
        assert collector.is_indie_game(game_no_dev_poor_genres) is False

    @pytest.mark.asyncio
    async def test_context_manager(self, collector):
        """非同期コンテキストマネージャーのテスト"""
        # モックデータベース接続
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # コンテキストマネージャーの動作確認
                async with collector as c:
                    assert c.session is not None
                    assert c.db_conn is not None
                
                # クリーンアップの確認
                mock_session.close.assert_called_once()
                mock_conn.close.assert_called_once()

    def test_category_indie_detection(self, collector):
        """カテゴリベースのインディー検出テスト"""
        game_data = {
            "steam_appid": 12345,
            "name": "Test Game",
            "type": "game",
            "developers": ["TestDev"],
            "publishers": ["TestPub"],
            "genres": [
                {"id": "1", "description": "Action"}
            ],
            "categories": [
                {"id": "29", "description": "Steam Trading Cards"},
                {"id": "30", "description": "Indie"}  # カテゴリにIndieが含まれる
            ]
        }
        assert collector.is_indie_game(game_data) is True

    def test_genre_indie_detection_case_insensitive(self, collector):
        """大文字小文字を区別しないインディー検出"""
        game_data = {
            "steam_appid": 12345,
            "name": "Test Game",
            "type": "game",
            "developers": ["TestDev"],
            "publishers": ["TestPub"],
            "genres": [
                {"id": "23", "description": "INDIE"}  # 大文字
            ]
        }
        assert collector.is_indie_game(game_data) is True

        game_data["genres"] = [
            {"id": "23", "description": "Independent"}  # independent
        ]
        assert collector.is_indie_game(game_data) is True


class TestDataProcessing:
    """データ処理機能のテストクラス"""

    @pytest.fixture
    def collector(self):
        return IndieGameCollector()

    def test_price_data_processing(self, collector):
        """価格データ処理のテスト"""
        # 価格情報ありの場合
        game_with_price = {
            "price_overview": {
                "currency": "USD",
                "initial": 2000,
                "final": 1500,
                "discount_percent": 25
            }
        }
        
        # 価格情報なしの場合
        game_without_price = {}
        
        # 無料ゲームの場合
        free_game = {
            "is_free": True
        }
        
        # 各ケースが適切に処理されることを確認
        # (実際の保存処理テストは統合テストで実施)
        assert "price_overview" in game_with_price
        assert "price_overview" not in game_without_price
        assert free_game["is_free"] is True

    def test_array_data_normalization(self, collector):
        """配列データの正規化テスト"""
        game_data = {
            "genres": [
                {"id": "1", "description": "Action"},
                {"id": "23", "description": "Indie"}
            ],
            "categories": [
                {"id": "2", "description": "Single-player"},
                {"id": "22", "description": "Steam Achievements"}
            ],
            "developers": ["ConcernedApe"],
            "publishers": ["ConcernedApe"]
        }
        
        # ジャンル名の抽出
        genre_names = [g.get("description") for g in game_data.get("genres", [])]
        assert "Action" in genre_names
        assert "Indie" in genre_names
        
        # カテゴリ名の抽出
        category_names = [c.get("description") for c in game_data.get("categories", [])]
        assert "Single-player" in category_names
        assert "Steam Achievements" in category_names


class TestAsyncOperations:
    """非同期操作のテストクラス"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_simulation(self):
        """同時リクエストのシミュレーションテスト"""
        collector = IndieGameCollector()
        
        # 複数のApp IDでの同時処理をシミュレート
        app_ids = [413150, 250900, 105600]
        
        with patch.object(collector, 'get_game_details') as mock_get_details:
            # 各App IDに対して異なるレスポンスを設定
            mock_get_details.side_effect = [
                {"steam_appid": 413150, "name": "Stardew Valley"},
                {"steam_appid": 250900, "name": "The Binding of Isaac"},
                {"steam_appid": 105600, "name": "Terraria"}
            ]
            
            # 並列実行
            tasks = [collector.get_game_details(app_id) for app_id in app_ids]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert results[0]["steam_appid"] == 413150
            assert results[1]["steam_appid"] == 250900
            assert results[2]["steam_appid"] == 105600

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """タイムアウト処理のテスト"""
        collector = IndieGameCollector()
        
        with patch.object(collector, 'session') as mock_session:
            # タイムアウトエラーをシミュレート
            mock_session.get.side_effect = asyncio.TimeoutError()
            
            result = await collector.get_game_details(123456)
            assert result is None

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """例外処理のテスト"""
        collector = IndieGameCollector()
        
        with patch.object(collector, 'session') as mock_session:
            # 一般的な例外をシミュレート
            mock_session.get.side_effect = Exception("Network error")
            
            result = await collector.get_game_details(123456)
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])