#!/usr/bin/env python3
"""
データ品質チェック機能
収集されたゲームデータの品質を監視し、異常値や欠損データを検出する。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dataclasses import dataclass

# 相対インポートの処理
try:
    from ..config.database import get_db_session
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from config.database import get_db_session
    except ImportError:
        get_db_session = None


@dataclass
class DataQualityReport:
    """データ品質レポート結果"""
    table_name: str
    total_records: int
    quality_score: float
    issues_found: List[str]
    recommendations: List[str]
    check_timestamp: str


class DataQualityChecker:
    """データ品質チェッククラス"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        
        # データベース接続設定
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
        
        # SQLAlchemy エンジン作成
        self.engine = create_engine(
            f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
            f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        )

    async def check_basic_data_quality_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        基本的なデータ品質チェック（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            データ品質チェック結果
        """
        try:
            quality_check_query = text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN name IS NULL OR name = '' THEN 1 END) as missing_names,
                    COUNT(CASE WHEN genres IS NULL OR array_length(genres, 1) = 0 THEN 1 END) as missing_genres,
                    COUNT(CASE WHEN developers IS NULL OR array_length(developers, 1) = 0 THEN 1 END) as missing_developers,
                    COUNT(CASE WHEN price_final IS NULL THEN 1 END) as missing_prices,
                    COUNT(CASE WHEN price_final < 0 THEN 1 END) as negative_prices,
                    COUNT(CASE WHEN price_final > 10000 THEN 1 END) as extreme_prices,
                    COUNT(CASE WHEN positive_reviews IS NULL THEN 1 END) as missing_positive_reviews,
                    COUNT(CASE WHEN negative_reviews IS NULL THEN 1 END) as missing_negative_reviews,
                    COUNT(CASE WHEN positive_reviews < 0 OR negative_reviews < 0 THEN 1 END) as negative_reviews_count,
                    COUNT(CASE WHEN created_at IS NULL THEN 1 END) as missing_timestamps,
                    COUNT(DISTINCT app_id) as unique_app_ids,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE NULL END) as avg_price,
                    STDDEV(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE NULL END) as price_stddev
                FROM games 
                WHERE type = 'game';
            """)
            
            result = await session.execute(quality_check_query)
            quality_data = dict(result.fetchone()._mapping)
            
            # 品質スコア計算
            total_games = quality_data['total_games']
            
            if total_games == 0:
                quality_score = 0.0
                issues = ["データが存在しません"]
            else:
                # 各品質指標の計算
                name_completeness = 1 - (quality_data['missing_names'] / total_games)
                genre_completeness = 1 - (quality_data['missing_genres'] / total_games)
                developer_completeness = 1 - (quality_data['missing_developers'] / total_games)
                price_validity = 1 - (quality_data['negative_prices'] + quality_data['extreme_prices']) / total_games
                review_completeness = 1 - (quality_data['missing_positive_reviews'] + quality_data['missing_negative_reviews']) / (total_games * 2)
                uniqueness = quality_data['unique_app_ids'] / total_games
                
                # 総合品質スコア（0-100）
                quality_score = (name_completeness + genre_completeness + developer_completeness + 
                               price_validity + review_completeness + uniqueness) / 6 * 100
                
                # 問題検出
                issues = []
                if quality_data['missing_names'] > 0:
                    issues.append(f"ゲーム名欠損: {quality_data['missing_names']}件")
                if quality_data['missing_genres'] > 0:
                    issues.append(f"ジャンル情報欠損: {quality_data['missing_genres']}件")
                if quality_data['missing_developers'] > 0:
                    issues.append(f"開発者情報欠損: {quality_data['missing_developers']}件")
                if quality_data['negative_prices'] > 0:
                    issues.append(f"負の価格データ: {quality_data['negative_prices']}件")
                if quality_data['extreme_prices'] > 0:
                    issues.append(f"異常高額価格（$100超）: {quality_data['extreme_prices']}件")
                if quality_data['negative_reviews_count'] > 0:
                    issues.append(f"負のレビュー数: {quality_data['negative_reviews_count']}件")
            
            return {
                'quality_metrics': quality_data,
                'quality_score': round(quality_score, 1),
                'issues_found': issues,
                'check_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"データ品質チェックエラー: {e}")
            return {}

    async def check_data_distribution_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        データ分布チェック（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            データ分布分析結果
        """
        try:
            distribution_query = text("""
                WITH price_stats AS (
                    SELECT 
                        MIN(price_final/100.0) as min_price,
                        MAX(price_final/100.0) as max_price,
                        AVG(price_final/100.0) as avg_price,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_final/100.0) as median_price,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_final/100.0) as q1_price,
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_final/100.0) as q3_price
                    FROM games 
                    WHERE type = 'game' AND price_final > 0
                ),
                review_stats AS (
                    SELECT 
                        MIN(positive_reviews + negative_reviews) as min_reviews,
                        MAX(positive_reviews + negative_reviews) as max_reviews,
                        AVG(positive_reviews + negative_reviews) as avg_reviews,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY positive_reviews + negative_reviews) as median_reviews,
                        COUNT(CASE WHEN positive_reviews + negative_reviews = 0 THEN 1 END) as zero_reviews
                    FROM games 
                    WHERE type = 'game'
                ),
                platform_stats AS (
                    SELECT 
                        COUNT(CASE WHEN platforms_windows THEN 1 END) as windows_count,
                        COUNT(CASE WHEN platforms_mac THEN 1 END) as mac_count,
                        COUNT(CASE WHEN platforms_linux THEN 1 END) as linux_count,
                        COUNT(*) as total_games
                    FROM games 
                    WHERE type = 'game'
                )
                SELECT 
                    p.min_price, p.max_price, p.avg_price, p.median_price, p.q1_price, p.q3_price,
                    r.min_reviews, r.max_reviews, r.avg_reviews, r.median_reviews, r.zero_reviews,
                    pl.windows_count, pl.mac_count, pl.linux_count, pl.total_games
                FROM price_stats p, review_stats r, platform_stats pl;
            """)
            
            result = await session.execute(distribution_query)
            dist_data = dict(result.fetchone()._mapping)
            
            # 分布異常の検出
            anomalies = []
            
            # 価格分布の異常検出
            if dist_data['max_price'] and dist_data['avg_price']:
                price_range = dist_data['max_price'] - dist_data['min_price']
                if price_range > 1000:  # $1000以上の価格幅
                    anomalies.append(f"価格幅が異常に広い: ${dist_data['min_price']:.2f} - ${dist_data['max_price']:.2f}")
                
                # 外れ値検出（IQR方式）
                if dist_data['q3_price'] and dist_data['q1_price']:
                    iqr = dist_data['q3_price'] - dist_data['q1_price']
                    upper_bound = dist_data['q3_price'] + 1.5 * iqr
                    if dist_data['max_price'] > upper_bound:
                        anomalies.append(f"価格外れ値検出: 最高価格${dist_data['max_price']:.2f}が上限${upper_bound:.2f}を超過")
            
            # レビュー分布の異常検出
            if dist_data['zero_reviews'] and dist_data['total_games']:
                zero_review_ratio = dist_data['zero_reviews'] / dist_data['total_games']
                if zero_review_ratio > 0.8:  # 80%以上がレビューなし
                    anomalies.append(f"レビューなしゲームが{zero_review_ratio:.1%}と高比率")
            
            # プラットフォーム分布の異常検出
            if dist_data['total_games'] > 0:
                windows_ratio = dist_data['windows_count'] / dist_data['total_games']
                if windows_ratio < 0.5:  # Windows対応率が50%未満
                    anomalies.append(f"Windows対応率が{windows_ratio:.1%}と低い")
            
            return {
                'distribution_metrics': dist_data,
                'anomalies_detected': anomalies,
                'check_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"データ分布チェックエラー: {e}")
            return {}

    async def check_data_freshness_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        データ鮮度チェック（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            データ鮮度チェック結果
        """
        try:
            freshness_query = text("""
                SELECT 
                    COUNT(*) as total_games,
                    MIN(created_at) as oldest_record,
                    MAX(created_at) as newest_record,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as records_last_24h,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 week' THEN 1 END) as records_last_week,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 month' THEN 1 END) as records_last_month
                FROM games 
                WHERE type = 'game';
            """)
            
            result = await session.execute(freshness_query)
            freshness_data = dict(result.fetchone()._mapping)
            
            # 鮮度評価
            freshness_issues = []
            total_games = freshness_data['total_games']
            
            if total_games > 0:
                recent_ratio = freshness_data['records_last_week'] / total_games
                if recent_ratio < 0.1:  # 最近1週間のデータが10%未満
                    freshness_issues.append(f"最近1週間のデータが{recent_ratio:.1%}と少ない")
                
                daily_ratio = freshness_data['records_last_24h'] / total_games
                if daily_ratio == 0 and total_games > 100:  # 大きなデータセットで日次更新なし
                    freshness_issues.append("過去24時間で新しいデータが追加されていない")
            
            return {
                'freshness_metrics': freshness_data,
                'freshness_issues': freshness_issues,
                'check_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"データ鮮度チェックエラー: {e}")
            return {}

    async def generate_quality_recommendations_async(self, session: AsyncSession) -> List[str]:
        """
        データ品質改善提案生成（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            改善提案のリスト
        """
        recommendations = []
        
        try:
            # 各種品質チェック結果を取得
            tasks = [
                self.check_basic_data_quality_async(session),
                self.check_data_distribution_async(session),
                self.check_data_freshness_async(session)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            basic_quality, distribution, freshness = results
            
            # 基本品質に基づく提案
            if not isinstance(basic_quality, Exception) and basic_quality.get('quality_score', 0) < 80:
                recommendations.append("データ品質スコアが80%未満のため、データクリーニングが必要")
            
            if not isinstance(basic_quality, Exception) and basic_quality.get('issues_found'):
                if any("欠損" in issue for issue in basic_quality['issues_found']):
                    recommendations.append("欠損データの補完または除外処理を実装")
                if any("負の" in issue for issue in basic_quality['issues_found']):
                    recommendations.append("データバリデーション機能を強化")
            
            # 分布に基づく提案
            if not isinstance(distribution, Exception) and distribution.get('anomalies_detected'):
                recommendations.append("外れ値検出・除外機能を導入")
                recommendations.append("データ収集時のバリデーション強化")
            
            # 鮮度に基づく提案
            if not isinstance(freshness, Exception) and freshness.get('freshness_issues'):
                recommendations.append("データ収集の自動化・スケジューリング改善")
                recommendations.append("リアルタイム データ更新の検討")
            
            # 総合的な提案
            recommendations.extend([
                "データ品質監視ダッシュボードの設置",
                "異常データアラート機能の実装",
                "データ品質メトリクスの定期レポート化"
            ])
            
        except Exception as e:
            self.logger.error(f"品質改善提案生成エラー: {e}")
            recommendations.append("データ品質分析中にエラーが発生しました")
        
        return recommendations

    async def generate_comprehensive_quality_report_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        包括的なデータ品質レポート生成（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            包括的品質レポート
        """
        try:
            # 各種品質分析を並行実行
            tasks = [
                self.check_basic_data_quality_async(session),
                self.check_data_distribution_async(session),
                self.check_data_freshness_async(session),
                self.generate_quality_recommendations_async(session)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果の統合
            report = {
                'report_id': f"data_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'basic_quality': results[0] if not isinstance(results[0], Exception) else {},
                'distribution_analysis': results[1] if not isinstance(results[1], Exception) else {},
                'freshness_analysis': results[2] if not isinstance(results[2], Exception) else {},
                'recommendations': results[3] if not isinstance(results[3], Exception) else [],
                'report_status': 'completed',
                'error_count': sum(1 for r in results if isinstance(r, Exception))
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"包括品質レポート生成エラー: {e}")
            return {
                'report_id': f"data_quality_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'report_status': 'failed'
            }

    def check_basic_quality_sync(self) -> Dict[str, Any]:
        """
        基本データ品質チェック（同期版・互換性のため）
        
        Returns:
            基本品質チェック結果
        """
        try:
            with self.engine.connect() as conn:
                basic_query = text("""
                    SELECT 
                        COUNT(*) as total_games,
                        COUNT(CASE WHEN name IS NULL OR name = '' THEN 1 END) as missing_names,
                        COUNT(CASE WHEN genres IS NULL THEN 1 END) as missing_genres,
                        COUNT(CASE WHEN price_final IS NULL THEN 1 END) as missing_prices
                    FROM games 
                    WHERE type = 'game';
                """)
                
                result = conn.execute(basic_query)
                data = dict(result.fetchone()._mapping)
                
                # 品質スコア簡易計算
                total = data['total_games']
                if total > 0:
                    missing_ratio = (data['missing_names'] + data['missing_genres'] + data['missing_prices']) / (total * 3)
                    quality_score = (1 - missing_ratio) * 100
                else:
                    quality_score = 0
                
                return {
                    'quality_metrics': data,
                    'quality_score': round(quality_score, 1),
                    'check_timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"同期品質チェックエラー: {e}")
            return {}


# テスト実行用の非同期メイン関数
async def main_async():
    """非同期メイン実行関数（データ品質チェックテスト用）"""
    checker = DataQualityChecker()
    
    if get_db_session:
        async with get_db_session() as session:
            print("🔍 データ品質チェックを実行中...")
            report = await checker.generate_comprehensive_quality_report_async(session)
            
            print("📊 Steam データ品質レポート")
            print("=" * 50)
            
            if report.get('basic_quality', {}).get('quality_metrics'):
                metrics = report['basic_quality']['quality_metrics']
                score = report['basic_quality']['quality_score']
                print(f"\n📈 品質スコア: {score}%")
                print(f"  総ゲーム数: {metrics['total_games']:,}")
                print(f"  ユニークID数: {metrics['unique_app_ids']:,}")
                if metrics['missing_names'] > 0:
                    print(f"  ゲーム名欠損: {metrics['missing_names']:,}件")
                if metrics['missing_genres'] > 0:
                    print(f"  ジャンル欠損: {metrics['missing_genres']:,}件")
            
            if report.get('basic_quality', {}).get('issues_found'):
                print("\n⚠️ 検出された問題:")
                for issue in report['basic_quality']['issues_found']:
                    print(f"  • {issue}")
            
            if report.get('distribution_analysis', {}).get('anomalies_detected'):
                print("\n🚨 分布異常:")
                for anomaly in report['distribution_analysis']['anomalies_detected']:
                    print(f"  • {anomaly}")
            
            if report.get('freshness_analysis', {}).get('freshness_issues'):
                print("\n⏰ 鮮度問題:")
                for issue in report['freshness_analysis']['freshness_issues']:
                    print(f"  • {issue}")
            
            if report.get('recommendations'):
                print("\n💡 改善提案:")
                for i, rec in enumerate(report['recommendations'], 1):
                    print(f"  {i}. {rec}")
            
            print(f"\n📅 チェック日時: {report['generated_at']}")
            print(f"🎯 レポート状況: {report['report_status']}")
    else:
        print("⚠️ データベース接続機能が利用できません。同期版チェックを実行します。")
        result = checker.check_basic_quality_sync()
        print("📊 基本品質チェック:")
        print(f"品質スコア: {result.get('quality_score', 0)}%")


if __name__ == "__main__":
    asyncio.run(main_async())