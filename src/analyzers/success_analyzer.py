"""
インディーゲーム成功要因分析モジュール

ゲームの成功指標（レビュー数、評価等）を基に、
成功要因やパターンを分析し、データ駆動型の戦略提案を行う。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# 相対インポートの処理
try:
    from ..config.database import get_db_session
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from config.database import get_db_session
    except ImportError:
        try:
            from src.config.database import get_db_session
        except ImportError:
            get_db_session = None  # フォールバック用


@dataclass
class SuccessFactorResult:
    """成功要因分析結果データクラス"""
    factor_type: str
    success_rate: float
    game_count: int
    avg_rating: float
    avg_price: float
    recommendations: List[str]


class SuccessAnalyzer:
    """インディーゲーム成功要因分析クラス（強化版）"""

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
        
        self.data = None
        self.indie_data = None
        
    def load_data(self) -> pd.DataFrame:
        """データベースからゲームデータを読み込み"""
        
        query = """
        SELECT 
            app_id,
            name,
            type,
            is_free,
            short_description,
            developers,
            publishers,
            price_currency,
            price_initial,
            price_final,
            price_discount_percent,
            release_date_text,
            release_date_coming_soon,
            platforms_windows,
            platforms_mac,
            platforms_linux,
            genres,
            categories,
            positive_reviews,
            negative_reviews,
            total_reviews,
            created_at
        FROM games
        WHERE type = 'game'
        ORDER BY created_at DESC;
        """
        
        self.data = pd.read_sql_query(query, self.engine)
        self._preprocess_data()
        
        print(f"✅ データ読み込み完了: {len(self.data):,}件のゲーム")
        return self.data
    
    def _preprocess_data(self) -> None:
        """データの前処理"""
        
        # 価格データの変換（セント → ドル）
        self.data['price_usd'] = self.data['price_final'] / 100
        self.data.loc[self.data['is_free'] == True, 'price_usd'] = 0
        
        # インディーゲーム判定
        def is_indie_game(row):
            """インディーゲーム判定ロジック"""
            if row['genres'] is None:
                return False
                
            # ジャンルにIndieが含まれる
            if any('Indie' in str(genre) for genre in row['genres'] if genre):
                return True
                
            # 開発者とパブリッシャーが同じ（セルフパブリッシング）
            if (row['developers'] is not None and row['publishers'] is not None and 
                len(row['developers']) <= 2 and set(row['developers']) == set(row['publishers'])):
                return True
                
            return False
        
        self.data['is_indie'] = self.data.apply(is_indie_game, axis=1)
        
        # レビューデータの処理
        self.data['total_reviews'] = self.data['total_reviews'].fillna(0)
        self.data['positive_reviews'] = self.data['positive_reviews'].fillna(0)
        self.data['negative_reviews'] = self.data['negative_reviews'].fillna(0)
        
        # 評価率の計算
        self.data['positive_ratio'] = np.where(
            self.data['total_reviews'] > 0,
            self.data['positive_reviews'] / self.data['total_reviews'],
            0
        )
        
        # ジャンルデータの処理
        self.data['primary_genre'] = self.data['genres'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Other'
        )
        
        # 開発者データの処理
        self.data['primary_developer'] = self.data['developers'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Unknown'
        )
        
        # プラットフォーム数の計算
        self.data['platform_count'] = (
            self.data['platforms_windows'].astype(int) + 
            self.data['platforms_mac'].astype(int) + 
            self.data['platforms_linux'].astype(int)
        )
        
        # 価格帯カテゴリ
        def price_category(price):
            if price == 0:
                return 'Free'
            elif price < 5:
                return 'Budget ($0-5)'
            elif price < 15:
                return 'Mid-range ($5-15)'
            elif price < 30:
                return 'Premium ($15-30)'
            else:
                return 'AAA ($30+)'
        
        self.data['price_category'] = self.data['price_usd'].apply(price_category)
        
        # インディーゲームのみのデータフレーム
        self.indie_data = self.data[self.data['is_indie'] == True].copy()
        
    def create_success_analysis_report(self) -> str:
        """成功要因分析レポートの生成（簡易版）"""
        
        if self.indie_data is None:
            self.load_data()
            
        # レビューがあるゲームのみを対象
        reviewed_games = self.indie_data[self.indie_data['total_reviews'] > 0].copy()
        
        if len(reviewed_games) == 0:
            return "\\n⚠️  レビューデータが不足しており、成功要因分析を実行できません。\\n"
        
        # 基本統計
        total_reviewed = len(reviewed_games)
        avg_reviews = reviewed_games['total_reviews'].mean()
        avg_rating = reviewed_games['positive_ratio'].mean()
        
        # ジャンル別分析
        genre_stats = reviewed_games.groupby('primary_genre').agg({
            'total_reviews': 'mean',
            'positive_ratio': 'mean',
            'app_id': 'count'
        }).round(2)
        
        genre_stats = genre_stats[genre_stats['app_id'] >= 2].sort_values('total_reviews', ascending=False)
        
        # 価格別分析
        price_stats = reviewed_games.groupby('price_category').agg({
            'total_reviews': 'mean',
            'positive_ratio': 'mean',
            'app_id': 'count'
        }).round(2)
        
        # トップゲーム
        top_games = reviewed_games.nlargest(5, 'total_reviews')[['name', 'total_reviews', 'positive_ratio', 'price_usd']]
        
        report = f"""
🏆 インディーゲーム成功要因分析レポート
{'='*60}

📊 分析対象:
  • レビューありゲーム: {total_reviewed:,}件
  • 平均レビュー数: {avg_reviews:.1f}
  • 平均評価率: {avg_rating:.1%}

🎮 ジャンル別パフォーマンス TOP 5:"""
        
        for genre, stats in genre_stats.head(5).iterrows():
            report += f"""
  • {genre}: 平均{stats['total_reviews']:.0f}レビュー, 評価率{stats['positive_ratio']:.1%} ({stats['app_id']}件)"""
        
        report += f"""

💰 価格帯別パフォーマンス:"""
        
        for price_cat, stats in price_stats.iterrows():
            report += f"""
  • {price_cat}: 平均{stats['total_reviews']:.0f}レビュー, 評価率{stats['positive_ratio']:.1%} ({stats['app_id']}件)"""
        
        report += f"""

🏅 トップパフォーマー:"""
        
        for _, game in top_games.iterrows():
            report += f"""
  • {game['name']}: {game['total_reviews']:.0f}レビュー, 評価率{game['positive_ratio']:.1%}, ${game['price_usd']:.2f}"""
        
        report += f"""

💡 成功のための推奨事項:
  1. 高パフォーマンスジャンルでの開発を検討
  2. 適切な価格設定による市場参入
  3. 品質重視の開発でユーザー満足度向上
  4. マルチプラットフォーム対応検討
  5. コミュニティとの密接な関係構築

📈 市場機会:
  • ニッチジャンルでの専門化
  • 未開拓価格帯での差別化
  • 新興プラットフォームへの早期参入
        """
        
        return report.strip()
    
    # ===== 新しい非同期成功要因分析メソッド =====
    
    async def analyze_price_success_correlation_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        価格と成功率の相関分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            価格別成功率データ
        """
        try:
            price_success_query = text("""
                WITH game_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        price_final/100.0 as price_usd,
                        positive_reviews,
                        negative_reviews,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE WHEN genres::text LIKE '%Indie%' THEN 1 ELSE 0 END as is_indie,
                        CASE 
                            WHEN positive_reviews >= 50 AND 
                                 CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.8 
                            THEN 1 ELSE 0 
                        END as is_successful
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 10
                      AND genres::text LIKE '%Indie%'
                ),
                price_tiers AS (
                    SELECT *,
                        CASE 
                            WHEN price_usd = 0 THEN 'Free'
                            WHEN price_usd <= 5 THEN '$0-$5'
                            WHEN price_usd <= 10 THEN '$5-$10'
                            WHEN price_usd <= 20 THEN '$10-$20'
                            WHEN price_usd <= 30 THEN '$20-$30'
                            ELSE '$30+'
                        END as price_tier
                    FROM game_metrics
                )
                SELECT 
                    price_tier,
                    COUNT(*) as total_games,
                    SUM(is_successful) as successful_games,
                    CAST(SUM(is_successful) AS FLOAT) / COUNT(*) * 100 as success_rate,
                    AVG(rating) as avg_rating,
                    AVG(price_usd) as avg_price,
                    AVG(positive_reviews + negative_reviews) as avg_total_reviews
                FROM price_tiers
                GROUP BY price_tier
                ORDER BY 
                    CASE price_tier
                        WHEN 'Free' THEN 0
                        WHEN '$0-$5' THEN 1
                        WHEN '$5-$10' THEN 2
                        WHEN '$10-$20' THEN 3
                        WHEN '$20-$30' THEN 4
                        ELSE 5
                    END;
            """)
            
            result = await session.execute(price_success_query)
            price_data = [dict(row._mapping) for row in result]
            
            # データの後処理
            for tier in price_data:
                tier['success_rate'] = round(tier['success_rate'] or 0, 1)
                tier['avg_rating'] = round(tier['avg_rating'] or 0, 3)
                tier['avg_price'] = round(tier['avg_price'] or 0, 2)
                tier['avg_total_reviews'] = round(tier['avg_total_reviews'] or 0, 0)
            
            return {
                'price_success_analysis': price_data,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"価格成功率分析エラー: {e}")
            return {}

    async def analyze_genre_success_patterns_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        ジャンル別成功パターン分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            ジャンル別成功パターンデータ
        """
        try:
            genre_success_query = text("""
                WITH game_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        genres,
                        price_final/100.0 as price_usd,
                        positive_reviews,
                        negative_reviews,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE 
                            WHEN positive_reviews >= 50 AND 
                                 CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.8 
                            THEN 1 ELSE 0 
                        END as is_successful
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 10
                      AND genres::text LIKE '%Indie%'
                      AND genres IS NOT NULL
                      AND array_length(genres, 1) > 0
                )
                SELECT 
                    UNNEST(genres) as genre,
                    COUNT(*) as total_games,
                    SUM(is_successful) as successful_games,
                    CAST(SUM(is_successful) AS FLOAT) / COUNT(*) * 100 as success_rate,
                    AVG(rating) as avg_rating,
                    AVG(price_usd) as avg_price,
                    AVG(positive_reviews) as avg_positive_reviews
                FROM game_metrics
                GROUP BY UNNEST(genres)
                HAVING COUNT(*) >= 5
                ORDER BY success_rate DESC, total_games DESC
                LIMIT 15;
            """)
            
            result = await session.execute(genre_success_query)
            genre_data = [dict(row._mapping) for row in result]
            
            # データの後処理
            for genre in genre_data:
                genre['success_rate'] = round(genre['success_rate'] or 0, 1)
                genre['avg_rating'] = round(genre['avg_rating'] or 0, 3)
                genre['avg_price'] = round(genre['avg_price'] or 0, 2)
                genre['avg_positive_reviews'] = round(genre['avg_positive_reviews'] or 0, 0)
            
            return {
                'genre_success_analysis': genre_data,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"ジャンル成功パターン分析エラー: {e}")
            return {}

    async def analyze_platform_strategy_success_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        プラットフォーム戦略と成功率の分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            プラットフォーム戦略成功データ
        """
        try:
            platform_success_query = text("""
                WITH game_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        price_final/100.0 as price_usd,
                        positive_reviews,
                        negative_reviews,
                        platforms_windows,
                        platforms_mac,
                        platforms_linux,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE 
                            WHEN positive_reviews >= 50 AND 
                                 CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.8 
                            THEN 1 ELSE 0 
                        END as is_successful,
                        (CASE WHEN platforms_windows THEN 1 ELSE 0 END +
                         CASE WHEN platforms_mac THEN 1 ELSE 0 END +
                         CASE WHEN platforms_linux THEN 1 ELSE 0 END) as platform_count
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 10
                      AND genres::text LIKE '%Indie%'
                ),
                platform_strategies AS (
                    SELECT *,
                        CASE 
                            WHEN platform_count = 1 AND platforms_windows THEN 'Windows Only'
                            WHEN platform_count = 2 AND platforms_windows AND platforms_mac THEN 'Windows + Mac'
                            WHEN platform_count = 3 THEN 'Multi-Platform'
                            WHEN platform_count >= 2 THEN 'Multi-Platform'
                            ELSE 'Other'
                        END as platform_strategy
                    FROM game_metrics
                )
                SELECT 
                    platform_strategy,
                    COUNT(*) as total_games,
                    SUM(is_successful) as successful_games,
                    CAST(SUM(is_successful) AS FLOAT) / COUNT(*) * 100 as success_rate,
                    AVG(rating) as avg_rating,
                    AVG(price_usd) as avg_price,
                    AVG(platform_count) as avg_platform_count
                FROM platform_strategies
                WHERE platform_strategy != 'Other'
                GROUP BY platform_strategy
                ORDER BY success_rate DESC;
            """)
            
            result = await session.execute(platform_success_query)
            platform_data = [dict(row._mapping) for row in result]
            
            # データの後処理
            for strategy in platform_data:
                strategy['success_rate'] = round(strategy['success_rate'] or 0, 1)
                strategy['avg_rating'] = round(strategy['avg_rating'] or 0, 3)
                strategy['avg_price'] = round(strategy['avg_price'] or 0, 2)
                strategy['avg_platform_count'] = round(strategy['avg_platform_count'] or 0, 1)
            
            return {
                'platform_success_analysis': platform_data,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"プラットフォーム戦略分析エラー: {e}")
            return {}

    async def generate_success_recommendations_async(self, session: AsyncSession) -> List[str]:
        """
        成功要因に基づく戦略提案生成（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            戦略提案のリスト
        """
        recommendations = []
        
        try:
            # 各種分析結果を取得
            tasks = [
                self.analyze_price_success_correlation_async(session),
                self.analyze_genre_success_patterns_async(session),
                self.analyze_platform_strategy_success_async(session)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            price_data, genre_data, platform_data = results
            
            # 価格戦略の提案
            if not isinstance(price_data, Exception) and price_data.get('price_success_analysis'):
                best_price_tier = max(price_data['price_success_analysis'], 
                                    key=lambda x: x['success_rate'])
                recommendations.append(
                    f"最適価格帯「{best_price_tier['price_tier']}」で成功率{best_price_tier['success_rate']}%を実現"
                )
            
            # ジャンル戦略の提案
            if not isinstance(genre_data, Exception) and genre_data.get('genre_success_analysis'):
                top_genre = genre_data['genre_success_analysis'][0]
                recommendations.append(
                    f"高成功率ジャンル「{top_genre['genre']}」での特化戦略（成功率{top_genre['success_rate']}%）"
                )
            
            # プラットフォーム戦略の提案
            if not isinstance(platform_data, Exception) and platform_data.get('platform_success_analysis'):
                best_platform = max(platform_data['platform_success_analysis'], 
                                  key=lambda x: x['success_rate'])
                recommendations.append(
                    f"推奨プラットフォーム戦略「{best_platform['platform_strategy']}」で成功率{best_platform['success_rate']}%"
                )
            
            # 総合戦略提案
            recommendations.extend([
                "コミュニティ重視のマーケティングでレビュー数増加を図る",
                "早期アクセスでユーザーフィードバックを活用した開発",
                "SNS・YouTubeでのインフルエンサーマーケティング展開"
            ])
            
        except Exception as e:
            self.logger.error(f"戦略提案生成エラー: {e}")
            recommendations.append("データ分析に基づく戦略提案の生成中にエラーが発生しました")
        
        return recommendations

    async def generate_comprehensive_success_report_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        包括的な成功要因分析レポート生成（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            包括的成功分析レポート
        """
        try:
            # 各種分析を並行実行
            tasks = [
                self.analyze_price_success_correlation_async(session),
                self.analyze_genre_success_patterns_async(session),
                self.analyze_platform_strategy_success_async(session),
                self.generate_success_recommendations_async(session)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果の統合
            report = {
                'report_id': f"success_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'price_analysis': results[0] if not isinstance(results[0], Exception) else {},
                'genre_analysis': results[1] if not isinstance(results[1], Exception) else {},
                'platform_analysis': results[2] if not isinstance(results[2], Exception) else {},
                'recommendations': results[3] if not isinstance(results[3], Exception) else [],
                'report_status': 'completed',
                'error_count': sum(1 for r in results if isinstance(r, Exception))
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"包括成功分析レポート生成エラー: {e}")
            return {
                'report_id': f"success_analysis_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'report_status': 'failed'
            }


# 新しい非同期テスト関数
async def main_async():
    """非同期メイン実行関数（成功要因分析テスト用）"""
    analyzer = SuccessAnalyzer()
    
    if get_db_session:
        async with get_db_session() as session:
            print("🎯 成功要因分析を実行中...")
            report = await analyzer.generate_comprehensive_success_report_async(session)
            
            print("🎮 Steam インディーゲーム成功要因分析レポート")
            print("=" * 60)
            
            if report.get('price_analysis', {}).get('price_success_analysis'):
                print("\n💰 価格別成功率:")
                for price in report['price_analysis']['price_success_analysis']:
                    print(f"  {price['price_tier']:10s}: {price['success_rate']:5.1f}% "
                          f"({price['successful_games']}/{price['total_games']})")
            
            if report.get('genre_analysis', {}).get('genre_success_analysis'):
                print("\n🏆 ジャンル別成功率 TOP5:")
                for i, genre in enumerate(report['genre_analysis']['genre_success_analysis'][:5], 1):
                    print(f"  {i}. {genre['genre']:15s}: {genre['success_rate']:5.1f}% "
                          f"({genre['successful_games']}/{genre['total_games']})")
            
            if report.get('platform_analysis', {}).get('platform_success_analysis'):
                print("\n🖥️ プラットフォーム戦略別成功率:")
                for platform in report['platform_analysis']['platform_success_analysis']:
                    print(f"  {platform['platform_strategy']:15s}: {platform['success_rate']:5.1f}% "
                          f"({platform['successful_games']}/{platform['total_games']})")
            
            if report.get('recommendations'):
                print("\n💡 戦略提案:")
                for i, rec in enumerate(report['recommendations'], 1):
                    print(f"  {i}. {rec}")
            
            print(f"\n📅 分析日時: {report['generated_at']}")
            print(f"🎯 分析状況: {report['report_status']}")
    else:
        print("⚠️ データベース接続機能が利用できません。同期版分析を実行します。")
        main()


# 使用例とテスト関数
def main():
    """メイン実行関数（テスト用）"""
    
    print("🏆 Steam インディーゲーム成功要因分析を開始")
    
    try:
        analyzer = SuccessAnalyzer()
        
        # データ読み込み
        analyzer.load_data()
        
        # レポート生成
        print("\\n📄 成功分析レポート生成...")
        report = analyzer.create_success_analysis_report()
        print(report)
        
        print("\\n✅ 成功要因分析完了")
        
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 従来の同期分析
    print("🏆 Steam インディーゲーム成功要因分析（同期版）")
    main()
    
    print("\n" + "="*60)
    print("🚀 新しい非同期成功要因分析を実行")
    asyncio.run(main_async())