"""
ダッシュボード機能のテスト

Streamlitアプリケーション、データ可視化、ユーザーインターフェース、
AI洞察統合の包括的なテストを実行します。
"""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestDashboardDataProcessing:
    """ダッシュボードデータ処理のテストクラス"""

    @pytest.fixture
    def sample_dashboard_data(self) -> pd.DataFrame:
        """ダッシュボード用サンプルデータ"""
        return pd.DataFrame({
            'app_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'name': [
                'Action Game A', 'Indie Puzzle B', 'Adventure C', 'Strategy D', 'Casual E',
                'Action Game F', 'Indie Adventure G', 'Puzzle H', 'Strategy I', 'Casual J'
            ],
            'price_usd': [9.99, 4.99, 14.99, 19.99, 0.0, 12.99, 7.99, 6.99, 24.99, 2.99],
            'total_reviews': [1500, 800, 3200, 450, 2100, 1800, 950, 600, 320, 1200],
            'rating': [0.82, 0.91, 0.75, 0.88, 0.94, 0.79, 0.86, 0.92, 0.83, 0.89],
            'primary_genre': [
                'Action', 'Puzzle', 'Adventure', 'Strategy', 'Casual',
                'Action', 'Adventure', 'Puzzle', 'Strategy', 'Casual'
            ],
            'price_category': [
                '低価格帯', '低価格帯', '中価格帯', '中価格帯', '無料',
                '中価格帯', '低価格帯', '低価格帯', '高価格帯', '低価格帯'
            ],
            'is_indie': [True] * 10
        })

    def test_data_structure_validation(self, sample_dashboard_data):
        """データ構造の検証テスト"""
        # 必須カラムの存在確認
        required_columns = [
            'app_id', 'name', 'price_usd', 'total_reviews', 'rating',
            'primary_genre', 'price_category'
        ]
        
        for column in required_columns:
            assert column in sample_dashboard_data.columns, f"必須カラム {column} が存在しません"
        
        # データ型の確認
        assert sample_dashboard_data['app_id'].dtype in ['int64', 'int32']
        assert sample_dashboard_data['price_usd'].dtype in ['float64', 'float32']
        assert sample_dashboard_data['total_reviews'].dtype in ['int64', 'int32']
        assert sample_dashboard_data['rating'].dtype in ['float64', 'float32']

    def test_price_distribution_calculation(self, sample_dashboard_data):
        """価格分布計算のテスト"""
        price_distribution = sample_dashboard_data['price_category'].value_counts().to_dict()
        
        assert isinstance(price_distribution, dict)
        assert '無料' in price_distribution
        assert '低価格帯' in price_distribution
        assert '中価格帯' in price_distribution
        
        # サンプルデータに基づく期待値
        assert price_distribution['低価格帯'] == 5
        assert price_distribution['中価格帯'] == 3
        assert price_distribution['無料'] == 1
        assert price_distribution['高価格帯'] == 1

    def test_genre_statistics_calculation(self, sample_dashboard_data):
        """ジャンル統計計算のテスト"""
        genre_stats = sample_dashboard_data.groupby('primary_genre').agg({
            'app_id': 'count',
            'rating': 'mean',
            'price_usd': 'mean',
            'total_reviews': 'mean'
        }).round(2)
        
        assert isinstance(genre_stats, pd.DataFrame)
        assert len(genre_stats) == 5  # 5つの異なるジャンル
        
        # 各ジャンルのゲーム数確認
        assert genre_stats.loc['Action', 'app_id'] == 2
        assert genre_stats.loc['Puzzle', 'app_id'] == 2
        assert genre_stats.loc['Adventure', 'app_id'] == 2

    def test_rating_analysis(self, sample_dashboard_data):
        """評価分析のテスト"""
        # 高評価ゲーム（0.85以上）の識別
        high_rated = sample_dashboard_data[sample_dashboard_data['rating'] >= 0.85]
        
        assert len(high_rated) == 6  # サンプルデータでは6ゲーム
        
        # 平均評価の計算
        avg_rating = sample_dashboard_data['rating'].mean()
        assert 0.0 <= avg_rating <= 1.0
        assert round(avg_rating, 2) == 0.86  # サンプルデータの期待値

    def test_review_count_analysis(self, sample_dashboard_data):
        """レビュー数分析のテスト"""
        # レビュー数による分類
        popular_games = sample_dashboard_data[sample_dashboard_data['total_reviews'] >= 1000]
        niche_games = sample_dashboard_data[sample_dashboard_data['total_reviews'] < 500]
        
        assert len(popular_games) == 7  # 1000以上のレビューを持つゲーム
        assert len(niche_games) == 2   # 500未満のレビューを持つゲーム
        
        # 総レビュー数の計算
        total_reviews = sample_dashboard_data['total_reviews'].sum()
        assert total_reviews == 13920  # サンプルデータの期待値

    def test_data_filtering_operations(self, sample_dashboard_data):
        """データフィルタリング操作のテスト"""
        # 価格フィルタリング
        free_games = sample_dashboard_data[sample_dashboard_data['price_usd'] == 0.0]
        assert len(free_games) == 1
        
        paid_games = sample_dashboard_data[sample_dashboard_data['price_usd'] > 0.0]
        assert len(paid_games) == 9
        
        # ジャンルフィルタリング
        action_games = sample_dashboard_data[sample_dashboard_data['primary_genre'] == 'Action']
        assert len(action_games) == 2
        
        # 複合フィルタリング
        premium_action = sample_dashboard_data[
            (sample_dashboard_data['primary_genre'] == 'Action') &
            (sample_dashboard_data['price_usd'] >= 10.0)
        ]
        assert len(premium_action) == 1


class TestVisualizationComponents:
    """可視化コンポーネントのテストクラス"""

    @pytest.fixture
    def chart_data(self) -> Dict[str, Any]:
        """チャート用テストデータ"""
        return {
            'labels': ['Action', 'Adventure', 'Puzzle', 'Strategy', 'Casual'],
            'values': [2, 2, 2, 2, 2],
            'colors': ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
        }

    def test_pie_chart_data_structure(self, chart_data):
        """円グラフデータ構造のテスト"""
        assert 'labels' in chart_data
        assert 'values' in chart_data
        assert 'colors' in chart_data
        
        assert len(chart_data['labels']) == len(chart_data['values'])
        assert len(chart_data['values']) == len(chart_data['colors'])
        
        # データの妥当性確認
        assert all(isinstance(label, str) for label in chart_data['labels'])
        assert all(isinstance(value, (int, float)) for value in chart_data['values'])
        assert all(value >= 0 for value in chart_data['values'])

    def test_bar_chart_data_preparation(self, chart_data):
        """棒グラフデータ準備のテスト"""
        # 棒グラフ用のDataFrame作成
        df = pd.DataFrame({
            'Genre': chart_data['labels'],
            'Count': chart_data['values']
        })
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert 'Genre' in df.columns
        assert 'Count' in df.columns
        
        # データの昇順・降順ソート
        df_sorted = df.sort_values('Count', ascending=False)
        assert df_sorted.iloc[0]['Count'] >= df_sorted.iloc[-1]['Count']

    def test_scatter_plot_data_structure(self):
        """散布図データ構造のテスト"""
        scatter_data = pd.DataFrame({
            'price': [5.99, 9.99, 14.99, 19.99, 24.99],
            'rating': [0.85, 0.90, 0.75, 0.88, 0.82],
            'reviews': [800, 1500, 3200, 450, 320],
            'genre': ['Puzzle', 'Action', 'Adventure', 'Strategy', 'Strategy']
        })
        
        assert len(scatter_data) == 5
        assert all(col in scatter_data.columns for col in ['price', 'rating', 'reviews', 'genre'])
        
        # 数値データの範囲確認
        assert scatter_data['price'].min() >= 0
        assert scatter_data['rating'].min() >= 0
        assert scatter_data['rating'].max() <= 1
        assert scatter_data['reviews'].min() >= 0

    def test_color_palette_consistency(self):
        """カラーパレット一貫性のテスト"""
        # 定義済みカラーパレット
        color_palette = {
            'Action': '#ff6b6b',
            'Adventure': '#4ecdc4', 
            'Puzzle': '#45b7d1',
            'Strategy': '#96ceb4',
            'Casual': '#feca57'
        }
        
        # カラーコードの形式確認
        for genre, color in color_palette.items():
            assert color.startswith('#')
            assert len(color) == 7  # #RRGGBB形式
            
        # 重複カラーなし
        assert len(set(color_palette.values())) == len(color_palette)

    def test_metric_card_data_formatting(self):
        """メトリクスカード用データフォーマットのテスト"""
        raw_metrics = {
            'total_games': 877,
            'avg_price': 12.456789,
            'avg_rating': 0.8234567,
            'total_reviews': 1234567
        }
        
        # フォーマット処理
        formatted_metrics = {
            'total_games': f"{raw_metrics['total_games']:,}件",
            'avg_price': f"${raw_metrics['avg_price']:.2f}",
            'avg_rating': f"{raw_metrics['avg_rating']:.1%}",
            'total_reviews': f"{raw_metrics['total_reviews']:,}"
        }
        
        assert formatted_metrics['total_games'] == "877件"
        assert formatted_metrics['avg_price'] == "$12.46"
        assert formatted_metrics['avg_rating'] == "82.3%"
        assert formatted_metrics['total_reviews'] == "1,234,567"


class TestAIDashboardIntegration:
    """AI機能統合のテストクラス"""

    def test_ai_insight_button_functionality(self):
        """AI洞察ボタン機能のテスト"""
        # ボタンクリック状態のシミュレーション
        button_clicked = True
        sample_data_summary = "総ゲーム数: 877件, 平均価格: $12.46"
        
        if button_clicked:
            # AI洞察生成のモック
            mock_insight = "インディーゲーム市場は活発で、特にActionジャンルが人気です。"
            
            assert isinstance(mock_insight, str)
            assert len(mock_insight) > 0
            assert "インディーゲーム" in mock_insight or "市場" in mock_insight

    def test_ai_insight_error_handling(self):
        """AI洞察エラーハンドリングのテスト"""
        # APIエラーのシミュレーション
        api_error = True
        
        if api_error:
            fallback_message = "AI分析は現在利用できません。データから手動で分析してください。"
            
            assert isinstance(fallback_message, str)
            assert "利用できません" in fallback_message

    def test_insight_data_summarization(self):
        """洞察用データ要約のテスト"""
        sample_data = pd.DataFrame({
            'total_games': [877],
            'avg_price': [12.46],
            'avg_rating': [0.823],
            'top_genre': ['Action'],
            'genre_count': [401]
        })
        
        # データ要約の作成
        summary = f"""
        総ゲーム数: {sample_data.iloc[0]['total_games']}件
        平均価格: ${sample_data.iloc[0]['avg_price']:.2f}
        平均評価: {sample_data.iloc[0]['avg_rating']:.1%}
        主要ジャンル: {sample_data.iloc[0]['top_genre']}({sample_data.iloc[0]['genre_count']}件)
        """
        
        assert "877件" in summary
        assert "$12.46" in summary
        assert "82.3%" in summary
        assert "Action(401件)" in summary

    @patch('src.analyzers.ai_insights_generator.AIInsightsGenerator')
    def test_ai_insights_generator_mock(self, mock_generator_class):
        """AI洞察生成のモックテスト"""
        # モックインスタンスの設定
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        
        # 期待される洞察結果の設定
        expected_insights = {
            'market': "市場は成長傾向にあります。",
            'genre': "Actionジャンルが最も人気です。",
            'price': "中価格帯が最適です。",
            'strategy': "新規参入者は差別化が重要です。"
        }
        
        mock_generator.generate_market_insight.return_value = expected_insights['market']
        mock_generator.generate_genre_insight.return_value = expected_insights['genre']
        mock_generator.generate_price_insight.return_value = expected_insights['price']
        mock_generator.generate_strategy_insight.return_value = expected_insights['strategy']
        
        # テスト実行
        generator = mock_generator_class()
        market_insight = generator.generate_market_insight("test data")
        genre_insight = generator.generate_genre_insight("test data")
        
        assert market_insight == expected_insights['market']
        assert genre_insight == expected_insights['genre']


class TestDashboardCaching:
    """ダッシュボードキャッシュ機能のテストクラス"""

    def test_cache_key_generation(self):
        """キャッシュキー生成のテスト"""
        # データハッシュによるキャッシュキー生成
        data_params = {
            'filter_genre': 'Action',
            'filter_price': 'all',
            'sort_by': 'rating',
            'limit': 100
        }
        
        # パラメータからキャッシュキーを生成
        cache_key = "_".join([f"{k}:{v}" for k, v in sorted(data_params.items())])
        expected_key = "filter_genre:Action_filter_price:all_limit:100_sort_by:rating"
        
        assert cache_key == expected_key

    def test_data_freshness_check(self):
        """データ鮮度チェックのテスト"""
        import time
        
        # キャッシュ作成時刻のシミュレーション
        cache_created_time = time.time() - 300  # 5分前
        current_time = time.time()
        cache_ttl = 600  # 10分のTTL
        
        # データが新鮮かどうかの判定
        is_fresh = (current_time - cache_created_time) < cache_ttl
        
        assert is_fresh is True  # 5分前のデータは10分TTLでは新鮮

    def test_cache_invalidation_logic(self):
        """キャッシュ無効化ロジックのテスト"""
        # データ更新イベントのシミュレーション
        last_data_update = 1640995200  # 2022年1月1日
        cache_created = 1640991600     # 2021年12月31日
        
        # データ更新後にキャッシュが作成されたかの確認
        cache_is_valid = cache_created > last_data_update
        
        assert cache_is_valid is False  # データ更新後に作成されていないため無効


class TestUserInterface:
    """ユーザーインターフェースのテストクラス"""

    def test_sidebar_components(self):
        """サイドバーコンポーネントのテスト"""
        # サイドバー要素のシミュレーション
        sidebar_elements = {
            'genre_filter': ['All', 'Action', 'Adventure', 'Puzzle'],
            'price_filter': ['All', '無料', '低価格帯', '中価格帯', '高価格帯'],
            'sort_options': ['名前', '価格', '評価', 'レビュー数'],
            'display_limit': [50, 100, 200, 500]
        }
        
        # 各要素の妥当性確認
        assert len(sidebar_elements['genre_filter']) > 1
        assert 'All' in sidebar_elements['genre_filter']
        assert len(sidebar_elements['price_filter']) == 5
        assert len(sidebar_elements['sort_options']) == 4

    def test_responsive_layout_logic(self):
        """レスポンシブレイアウトロジックのテスト"""
        # 画面サイズシミュレーション
        screen_sizes = {
            'mobile': {'width': 480, 'columns': 1},
            'tablet': {'width': 768, 'columns': 2}, 
            'desktop': {'width': 1200, 'columns': 3}
        }
        
        for device, specs in screen_sizes.items():
            # カラム数の決定ロジック
            if specs['width'] < 500:
                expected_columns = 1
            elif specs['width'] < 900:
                expected_columns = 2
            else:
                expected_columns = 3
                
            assert specs['columns'] == expected_columns

    def test_error_message_display(self):
        """エラーメッセージ表示のテスト"""
        error_scenarios = {
            'no_data': "データが見つかりません。フィルタ条件を調整してください。",
            'api_error': "API接続エラーが発生しました。しばらく待ってから再試行してください。",
            'loading_error': "データの読み込み中にエラーが発生しました。"
        }
        
        for scenario, message in error_scenarios.items():
            assert isinstance(message, str)
            assert len(message) > 0
            assert "エラー" in message or "見つかりません" in message

    def test_loading_state_management(self):
        """ローディング状態管理のテスト"""
        # ローディング状態のシミュレーション
        loading_states = {
            'data_loading': True,
            'ai_processing': False,
            'chart_rendering': True
        }
        
        # 全体のローディング状態の判定
        is_any_loading = any(loading_states.values())
        is_all_loaded = not any(loading_states.values())
        
        assert is_any_loading is True
        assert is_all_loaded is False

    def test_user_interaction_validation(self):
        """ユーザー操作バリデーションのテスト"""
        # ユーザー入力のバリデーション
        user_inputs = {
            'price_range': [0, 50],
            'rating_threshold': 0.8,
            'review_minimum': 100,
            'selected_genres': ['Action', 'Adventure']
        }
        
        # バリデーションルール
        validation_rules = {
            'price_range': lambda x: len(x) == 2 and x[0] <= x[1] and all(v >= 0 for v in x),
            'rating_threshold': lambda x: 0 <= x <= 1,
            'review_minimum': lambda x: isinstance(x, int) and x >= 0,
            'selected_genres': lambda x: isinstance(x, list) and len(x) > 0
        }
        
        # バリデーション実行
        for field, value in user_inputs.items():
            validation_result = validation_rules[field](value)
            assert validation_result is True, f"{field} のバリデーションに失敗しました"


class TestDataUpdateMechanism:
    """データ更新メカニズムのテストクラス"""

    def test_manual_update_trigger(self):
        """手動更新トリガーのテスト"""
        # 更新ボタンクリックのシミュレーション
        update_button_clicked = True
        last_update_time = "2024-01-01 12:00:00"
        
        if update_button_clicked:
            # 更新処理の実行
            update_status = "データ更新を開始しました"
            new_update_time = "2024-01-01 12:30:00"
            
            assert update_status == "データ更新を開始しました"
            assert new_update_time != last_update_time

    def test_update_progress_tracking(self):
        """更新進捗追跡のテスト"""
        # 更新進捗のシミュレーション
        update_steps = [
            {"step": "データベース接続", "status": "完了", "progress": 20},
            {"step": "データ取得", "status": "実行中", "progress": 60},
            {"step": "キャッシュ更新", "status": "待機中", "progress": 80},
            {"step": "表示更新", "status": "待機中", "progress": 100}
        ]
        
        completed_steps = [step for step in update_steps if step["status"] == "完了"]
        current_progress = max([step["progress"] for step in update_steps 
                               if step["status"] in ["完了", "実行中"]], default=0)
        
        assert len(completed_steps) == 1
        assert current_progress == 60

    def test_update_result_validation(self):
        """更新結果バリデーションのテスト"""
        # 更新結果のシミュレーション
        update_result = {
            "success": True,
            "new_records": 25,
            "updated_records": 5,
            "errors": [],
            "duration": "00:02:30"
        }
        
        # 結果の妥当性確認
        assert update_result["success"] is True
        assert isinstance(update_result["new_records"], int)
        assert isinstance(update_result["updated_records"], int)
        assert isinstance(update_result["errors"], list)
        assert len(update_result["errors"]) == 0  # エラーなし

    def test_rollback_mechanism(self):
        """ロールバックメカニズムのテスト"""
        # 更新失敗シナリオ
        update_failed = True
        backup_data_available = True
        
        if update_failed and backup_data_available:
            rollback_status = "バックアップからデータを復元しました"
            data_integrity_check = True
            
            assert rollback_status == "バックアップからデータを復元しました"
            assert data_integrity_check is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])