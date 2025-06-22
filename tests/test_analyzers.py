"""
分析モジュールのテスト

市場分析、成功要因分析、AI洞察生成、データ品質チェック機能の
包括的なテストを実行します。
"""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.analyzers.data_quality_checker import DataQualityChecker
from src.analyzers.market_analyzer import MarketAnalyzer
from src.analyzers.success_analyzer import SuccessAnalyzer

# AI機能のテスト（オプション）
try:
    from src.analyzers.ai_insights_generator import AIInsightsGenerator
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class TestMarketAnalyzer:
    """MarketAnalyzerクラスのテストスイート"""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """テスト用のサンプルデータ"""
        return pd.DataFrame({
            'app_id': [1, 2, 3, 4, 5],
            'name': ['Game A', 'Game B', 'Game C', 'Game D', 'Game E'],
            'price_usd': [9.99, 0.0, 14.99, 29.99, 4.99],
            'total_reviews': [1000, 500, 2000, 150, 800],
            'rating': [0.85, 0.92, 0.78, 0.95, 0.88],
            'primary_genre': ['Action', 'Indie', 'Strategy', 'Adventure', 'Puzzle'],
            'price_category': ['低価格帯', '無料', '中価格帯', '高価格帯', '低価格帯'],
            'is_indie': [True, True, True, True, True]
        })

    @pytest.fixture
    def analyzer(self, sample_data):
        """テスト用のMarketAnalyzerインスタンス"""
        analyzer = MarketAnalyzer()
        analyzer.df = sample_data
        return analyzer

    def test_initialization(self):
        """MarketAnalyzerの初期化テスト"""
        analyzer = MarketAnalyzer()
        assert analyzer.df is None
        assert analyzer.engine is not None

    def test_get_basic_statistics(self, analyzer, sample_data):
        """基本統計情報の取得テスト"""
        stats = analyzer.get_basic_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_games' in stats
        assert 'avg_price' in stats
        assert 'avg_rating' in stats
        assert 'total_reviews' in stats
        
        assert stats['total_games'] == len(sample_data)
        assert stats['avg_price'] == sample_data['price_usd'].mean()
        assert stats['avg_rating'] == sample_data['rating'].mean()

    def test_get_price_distribution(self, analyzer):
        """価格分布の取得テスト"""
        distribution = analyzer.get_price_distribution()
        
        assert isinstance(distribution, dict)
        assert '無料' in distribution
        assert '低価格帯' in distribution
        assert '中価格帯' in distribution
        assert '高価格帯' in distribution
        
        # サンプルデータに基づく期待値
        assert distribution['無料'] == 1
        assert distribution['低価格帯'] == 2
        assert distribution['中価格帯'] == 1
        assert distribution['高価格帯'] == 1

    def test_get_genre_analysis(self, analyzer):
        """ジャンル分析の取得テスト"""
        genre_analysis = analyzer.get_genre_analysis()
        
        assert isinstance(genre_analysis, pd.DataFrame)
        assert 'game_count' in genre_analysis.columns
        assert 'avg_rating' in genre_analysis.columns
        assert 'avg_price' in genre_analysis.columns
        assert 'avg_reviews' in genre_analysis.columns
        
        # データ件数の確認
        assert len(genre_analysis) == 5  # 5つの異なるジャンル

    def test_get_rating_vs_price_analysis(self, analyzer):
        """評価vs価格分析のテスト"""
        analysis = analyzer.get_rating_vs_price_analysis()
        
        assert isinstance(analysis, pd.DataFrame)
        assert 'price_category' in analysis.columns
        assert 'avg_rating' in analysis.columns
        assert 'game_count' in analysis.columns

    def test_get_market_overview(self, analyzer):
        """市場概要データの取得テスト"""
        overview = analyzer.get_market_overview()
        
        assert isinstance(overview, dict)
        
        # 基本統計情報の確認
        assert 'total_games' in overview
        assert 'avg_price' in overview
        assert 'price_distribution' in overview
        assert 'genre_stats' in overview
        
        # データ型の確認
        assert isinstance(overview['total_games'], int)
        assert isinstance(overview['avg_price'], float)
        assert isinstance(overview['price_distribution'], dict)

    def test_create_price_trend_chart_data(self, analyzer):
        """価格トレンドチャートデータの作成テスト"""
        chart_data = analyzer.create_price_trend_chart()
        
        assert isinstance(chart_data, dict)
        assert 'data' in chart_data
        assert 'layout' in chart_data
        
        # Plotlyフィギュアオブジェクトの構造確認
        assert isinstance(chart_data['data'], list)
        assert isinstance(chart_data['layout'], dict)

    def test_error_handling_empty_data(self):
        """空のデータに対するエラーハンドリング"""
        analyzer = MarketAnalyzer()
        analyzer.df = pd.DataFrame()  # 空のDataFrame
        
        # 空データでも例外が発生しないことを確認
        stats = analyzer.get_basic_statistics()
        assert stats['total_games'] == 0

    def test_data_filtering(self, analyzer, sample_data):
        """データフィルタリング機能のテスト"""
        # 評価が0.8以上のゲームのフィルタリング
        high_rated = sample_data[sample_data['rating'] >= 0.8]
        
        analyzer.df = high_rated
        stats = analyzer.get_basic_statistics()
        
        assert stats['total_games'] == 4  # 0.8以上の評価は4件
        assert stats['avg_rating'] >= 0.8


class TestSuccessAnalyzer:
    """SuccessAnalyzerクラスのテストスイート"""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """成功分析用のサンプルデータ"""
        return pd.DataFrame({
            'app_id': [1, 2, 3, 4, 5, 6],
            'name': ['Hit Game', 'Average Game', 'Niche Game', 'Popular Game', 'Failed Game', 'Sleeper Hit'],
            'rating': [0.95, 0.75, 0.85, 0.90, 0.60, 0.88],
            'total_reviews': [10000, 500, 100, 5000, 50, 1200],
            'price_usd': [19.99, 9.99, 24.99, 14.99, 29.99, 12.99],
            'primary_genre': ['Action', 'Strategy', 'Puzzle', 'Adventure', 'Action', 'Indie'],
            'price_category': ['中価格帯', '低価格帯', '高価格帯', '中価格帯', '高価格帯', '中価格帯']
        })

    @pytest.fixture
    def analyzer(self, sample_data):
        """テスト用のSuccessAnalyzerインスタンス"""
        analyzer = SuccessAnalyzer()
        analyzer.df = sample_data
        return analyzer

    def test_initialization(self):
        """SuccessAnalyzerの初期化テスト"""
        analyzer = SuccessAnalyzer()
        assert analyzer.df is None
        assert analyzer.engine is not None

    def test_identify_successful_games(self, analyzer):
        """成功ゲームの識別テスト"""
        successful = analyzer.identify_successful_games()
        
        assert isinstance(successful, pd.DataFrame)
        assert len(successful) > 0
        
        # 成功ゲームは高評価かつ多レビューであることを確認
        for _, game in successful.iterrows():
            assert game['rating'] >= 0.8 or game['total_reviews'] >= 1000

    def test_analyze_success_factors(self, analyzer):
        """成功要因の分析テスト"""
        factors = analyzer.analyze_success_factors()
        
        assert isinstance(factors, dict)
        assert 'by_genre' in factors
        assert 'by_price_category' in factors
        assert 'correlations' in factors
        
        # ジャンル別成功率の確認
        genre_factors = factors['by_genre']
        assert isinstance(genre_factors, pd.DataFrame)
        assert 'success_rate' in genre_factors.columns

    def test_get_success_metrics(self, analyzer):
        """成功指標の取得テスト"""
        metrics = analyzer.get_success_metrics()
        
        assert isinstance(metrics, dict)
        assert 'successful_games_count' in metrics
        assert 'success_rate' in metrics
        assert 'avg_successful_rating' in metrics
        assert 'avg_successful_reviews' in metrics

    def test_create_success_analysis_report(self, analyzer):
        """成功分析レポートの作成テスト"""
        report = analyzer.create_success_analysis_report()
        
        assert isinstance(report, str)
        assert len(report) > 0
        assert '成功要因分析' in report or 'Success Analysis' in report

    def test_find_outliers(self, analyzer, sample_data):
        """外れ値検出のテスト"""
        # 高評価・低レビューのニッチゲーム検出
        niche_games = sample_data[
            (sample_data['rating'] >= 0.8) & 
            (sample_data['total_reviews'] <= 200)
        ]
        
        assert len(niche_games) > 0
        assert 'Niche Game' in niche_games['name'].values

    def test_price_success_correlation(self, analyzer, sample_data):
        """価格と成功の相関分析テスト"""
        # 価格カテゴリ別の平均評価を計算
        price_rating_corr = sample_data.groupby('price_category')['rating'].mean()
        
        assert isinstance(price_rating_corr, pd.Series)
        assert len(price_rating_corr) > 0


class TestDataQualityChecker:
    """DataQualityCheckerクラスのテストスイート"""

    @pytest.fixture
    def sample_data_with_issues(self) -> pd.DataFrame:
        """品質問題を含むサンプルデータ"""
        return pd.DataFrame({
            'app_id': [1, 2, 3, 4, 5, 1],  # 重複あり
            'name': ['Game A', '', 'Game C', 'Game D', None, 'Game A Duplicate'],  # 空値あり
            'price_usd': [9.99, -5.0, 14.99, 10000.0, 4.99, 9.99],  # 負の値、異常値あり
            'rating': [0.85, 1.5, 0.78, -0.1, 0.88, 0.85],  # 範囲外値あり
            'total_reviews': [1000, None, 2000, 150, 800, 1000],  # Null値あり
            'primary_genre': ['Action', 'Unknown', 'Strategy', '', 'Puzzle', 'Action']  # 空値あり
        })

    @pytest.fixture
    def checker(self, sample_data_with_issues):
        """テスト用のDataQualityCheckerインスタンス"""
        checker = DataQualityChecker()
        checker.df = sample_data_with_issues
        return checker

    def test_initialization(self):
        """DataQualityCheckerの初期化テスト"""
        checker = DataQualityChecker()
        assert checker.df is None
        assert checker.engine is not None

    def test_check_data_completeness(self, checker):
        """データ完全性チェックのテスト"""
        completeness = checker.check_data_completeness()
        
        assert isinstance(completeness, dict)
        
        # 各カラムの完全性スコアを確認
        assert 'name' in completeness
        assert 'price_usd' in completeness
        assert 'rating' in completeness
        
        # 完全性スコアは0-1の範囲
        for column, score in completeness.items():
            assert 0 <= score <= 1

    def test_identify_duplicates(self, checker):
        """重複データの識別テスト"""
        duplicates = checker.identify_duplicates()
        
        assert isinstance(duplicates, list)
        assert len(duplicates) > 0  # サンプルデータには重複あり
        
        # app_idの重複が検出されることを確認
        duplicate_info = duplicates[0]
        assert 'app_id' in duplicate_info['column']

    def test_identify_outliers(self, checker):
        """外れ値の識別テスト"""
        outliers = checker.identify_outliers()
        
        assert isinstance(outliers, list)
        assert len(outliers) > 0  # サンプルデータには外れ値あり
        
        # 価格の外れ値が検出されることを確認
        price_outliers = [o for o in outliers if 'price' in o['column']]
        assert len(price_outliers) > 0

    def test_check_data_constraints(self, checker):
        """データ制約チェックのテスト"""
        violations = checker.check_data_constraints()
        
        assert isinstance(violations, list)
        assert len(violations) > 0  # サンプルデータには制約違反あり
        
        # 評価値の範囲制約違反が検出されることを確認
        rating_violations = [v for v in violations if 'rating' in v['column']]
        assert len(rating_violations) > 0

    def test_generate_quality_report(self, checker):
        """品質レポートの生成テスト"""
        report = checker.generate_quality_report()
        
        assert isinstance(report, str)
        assert len(report) > 0
        assert 'データ品質レポート' in report or 'Data Quality Report' in report

    def test_calculate_quality_score(self, checker):
        """品質スコアの計算テスト"""
        score = checker.calculate_quality_score()
        
        assert isinstance(score, float)
        assert 0 <= score <= 100  # 0-100の範囲

    def test_missing_value_analysis(self, checker, sample_data_with_issues):
        """欠損値分析のテスト"""
        missing_analysis = sample_data_with_issues.isnull().sum()
        
        assert missing_analysis['name'] > 0  # nameに欠損値あり
        assert missing_analysis['total_reviews'] > 0  # total_reviewsに欠損値あり

    def test_data_type_validation(self, checker, sample_data_with_issues):
        """データ型バリデーションのテスト"""
        # 数値カラムの型チェック
        numeric_columns = ['price_usd', 'rating', 'total_reviews']
        
        for col in numeric_columns:
            if col in sample_data_with_issues.columns:
                # 非数値データの検出
                non_numeric = sample_data_with_issues[col].apply(
                    lambda x: not pd.isna(x) and not isinstance(x, (int, float))
                ).sum()
                # このテストでは数値型で設定されているので0であるべき
                assert non_numeric == 0


@pytest.mark.skipif(not AI_AVAILABLE, reason="AI機能が利用できません")
class TestAIInsightsGenerator:
    """AIInsightsGeneratorクラスのテストスイート"""

    @pytest.fixture
    def sample_summary(self) -> str:
        """AI分析用のサンプル要約データ"""
        return """
        総ゲーム数: 877件
        平均価格: $12.45
        平均評価: 0.82
        主要ジャンル: Action(401件), Adventure(187件), Casual(155件)
        価格分布: 無料(264件), 低価格帯(325件), 中価格帯(288件)
        """

    @pytest.fixture
    def generator(self):
        """テスト用のAIInsightsGeneratorインスタンス"""
        return AIInsightsGenerator()

    def test_initialization(self, generator):
        """AIInsightsGeneratorの初期化テスト"""
        assert generator.model is not None

    def test_generate_market_insight_with_mock(self, generator, sample_summary):
        """市場洞察生成のテスト（モック使用）"""
        expected_insight = "インディーゲーム市場は活発で、特にActionジャンルが人気です。"
        
        with patch.object(generator.model, 'generate_content') as mock_generate:
            mock_response = MagicMock()
            mock_response.text = expected_insight
            mock_generate.return_value = mock_response
            
            result = generator.generate_market_insight(sample_summary)
            
            assert isinstance(result, str)
            assert result == expected_insight
            mock_generate.assert_called_once()

    def test_generate_genre_insight_with_mock(self, generator, sample_summary):
        """ジャンル洞察生成のテスト（モック使用）"""
        expected_insight = "Actionジャンルが最も競争が激しく、新規参入には差別化が重要です。"
        
        with patch.object(generator.model, 'generate_content') as mock_generate:
            mock_response = MagicMock()
            mock_response.text = expected_insight
            mock_generate.return_value = mock_response
            
            result = generator.generate_genre_insight(sample_summary)
            
            assert isinstance(result, str)
            assert result == expected_insight

    def test_error_handling(self, generator):
        """AI生成エラーハンドリングのテスト"""
        with patch.object(generator.model, 'generate_content') as mock_generate:
            mock_generate.side_effect = Exception("API Error")
            
            result = generator.generate_market_insight("test data")
            
            assert isinstance(result, str)
            assert "AI分析は現在利用できません" in result

    def test_fallback_response(self, generator):
        """フォールバックレスポンスのテスト"""
        # 空の入力に対するフォールバック
        result = generator.generate_market_insight("")
        
        assert isinstance(result, str)
        assert len(result) > 0


class TestIntegrationAnalytics:
    """分析モジュール間の統合テスト"""

    @pytest.fixture
    def comprehensive_data(self) -> pd.DataFrame:
        """包括的なテストデータ"""
        return pd.DataFrame({
            'app_id': range(1, 101),  # 100ゲーム
            'name': [f'Game {i}' for i in range(1, 101)],
            'price_usd': [round(5 + (i % 20) * 2.5, 2) for i in range(100)],
            'rating': [0.6 + (i % 40) * 0.01 for i in range(100)],
            'total_reviews': [50 + i * 100 for i in range(100)],
            'primary_genre': ['Action', 'Adventure', 'Casual', 'Strategy', 'Puzzle'][0:100:1] * 20,
            'price_category': ['低価格帯', '中価格帯', '高価格帯', '低価格帯', '中価格帯'][0:100:1] * 20
        })

    def test_market_and_success_analysis_integration(self, comprehensive_data):
        """市場分析と成功分析の統合テスト"""
        # MarketAnalyzer
        market_analyzer = MarketAnalyzer()
        market_analyzer.df = comprehensive_data
        market_overview = market_analyzer.get_market_overview()
        
        # SuccessAnalyzer
        success_analyzer = SuccessAnalyzer()
        success_analyzer.df = comprehensive_data
        success_metrics = success_analyzer.get_success_metrics()
        
        # 統合結果の検証
        assert market_overview['total_games'] == len(comprehensive_data)
        assert success_metrics['successful_games_count'] <= len(comprehensive_data)
        
        # 成功率の整合性確認
        success_rate = success_metrics['success_rate']
        assert 0 <= success_rate <= 100

    def test_quality_check_integration(self, comprehensive_data):
        """データ品質チェックの統合テスト"""
        # 意図的にデータ品質問題を作成
        problematic_data = comprehensive_data.copy()
        problematic_data.loc[0, 'rating'] = -0.5  # 無効な評価値
        problematic_data.loc[1, 'price_usd'] = -10.0  # 負の価格
        problematic_data.loc[2, 'name'] = None  # 空の名前
        
        checker = DataQualityChecker()
        checker.df = problematic_data
        
        quality_score = checker.calculate_quality_score()
        violations = checker.check_data_constraints()
        
        # 品質問題が検出されることを確認
        assert quality_score < 100  # 完璧でないスコア
        assert len(violations) > 0  # 制約違反が検出される


if __name__ == "__main__":
    pytest.main([__file__, "-v"])