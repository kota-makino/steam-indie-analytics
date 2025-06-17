"""
インディーゲーム市場トレンド分析モジュール

市場の全体的なトレンド、ジャンル別動向、価格戦略などを分析し、
包括的な市場洞察を提供する。
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

# 相対インポートを絶対インポートに変更（テスト実行用）
try:
    from ..config.database import get_db_session
except ImportError:
    # テスト実行時の代替インポート
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.database import get_db_session


@dataclass
class MarketTrendResult:
    """市場トレンド分析結果データクラス"""
    trend_type: str
    period: str
    total_games: int
    avg_price: float
    growth_rate: float
    top_genres: List[Dict[str, Any]]
    insights: List[str]


class MarketAnalyzer:
    """インディーゲーム市場分析クラス（非同期対応）"""

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
        
        # SQLAlchemy エンジン作成（互換性のため）
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
        
    def get_market_overview(self) -> Dict[str, Any]:
        """市場概要の取得"""
        
        if self.data is None:
            self.load_data()
            
        total_games = len(self.data)
        indie_games = len(self.indie_data)
        indie_ratio = indie_games / total_games * 100
        
        # 価格統計
        paid_games = self.data[self.data['price_usd'] > 0]
        indie_paid = self.indie_data[self.indie_data['price_usd'] > 0]
        non_indie_paid = self.data[(self.data['is_indie'] == False) & (self.data['price_usd'] > 0)]
        
        overview = {
            'total_games': total_games,
            'indie_games': indie_games,
            'indie_ratio': indie_ratio,
            'avg_price_all': paid_games['price_usd'].mean() if len(paid_games) > 0 else 0,
            'avg_price_indie': indie_paid['price_usd'].mean() if len(indie_paid) > 0 else 0,
            'avg_price_non_indie': non_indie_paid['price_usd'].mean() if len(non_indie_paid) > 0 else 0,
            'median_price_indie': indie_paid['price_usd'].median() if len(indie_paid) > 0 else 0,
            'platform_stats': {
                'windows_rate': self.indie_data['platforms_windows'].mean() * 100,
                'mac_rate': self.indie_data['platforms_mac'].mean() * 100,
                'linux_rate': self.indie_data['platforms_linux'].mean() * 100,
                'avg_platforms': self.indie_data['platform_count'].mean()
            }
        }
        
        return overview
    
    def analyze_genre_trends(self) -> Dict[str, Any]:
        """ジャンル別トレンド分析"""
        
        if self.indie_data is None:
            self.load_data()
            
        # ジャンル別統計
        genre_stats = self.indie_data.groupby('primary_genre').agg({
            'app_id': 'count',
            'price_usd': ['mean', 'median'],
            'platform_count': 'mean'
        }).round(2)
        
        genre_stats.columns = ['game_count', 'avg_price', 'median_price', 'avg_platforms']
        genre_stats = genre_stats.sort_values('game_count', ascending=False)
        
        # 人気ジャンル（上位10）
        top_genres = genre_stats.head(10)
        
        # ジャンル別価格分析
        price_by_genre = self.indie_data.groupby('primary_genre')['price_usd'].describe()
        
        # ジャンル多様性分析
        total_genres = len(genre_stats)
        top_5_share = top_genres.head(5)['game_count'].sum() / len(self.indie_data) * 100
        
        return {
            'genre_stats': genre_stats,
            'top_genres': top_genres,
            'price_by_genre': price_by_genre,
            'diversity_metrics': {
                'total_genres': total_genres,
                'top_5_market_share': top_5_share,
                'hhi_index': self._calculate_hhi_index(genre_stats['game_count'])
            }
        }
    
    def analyze_price_strategies(self) -> Dict[str, Any]:
        """価格戦略分析"""
        
        if self.indie_data is None:
            self.load_data()
            
        # 価格帯分布
        price_distribution = self.indie_data['price_category'].value_counts()
        price_percentages = (price_distribution / len(self.indie_data) * 100).round(1)
        
        # 価格統計
        paid_indie = self.indie_data[self.indie_data['price_usd'] > 0]
        
        price_stats = {
            'distribution': price_distribution.to_dict(),
            'percentages': price_percentages.to_dict(),
            'statistics': {
                'mean': paid_indie['price_usd'].mean(),
                'median': paid_indie['price_usd'].median(),
                'std': paid_indie['price_usd'].std(),
                'q25': paid_indie['price_usd'].quantile(0.25),
                'q75': paid_indie['price_usd'].quantile(0.75),
                'min': paid_indie['price_usd'].min(),
                'max': paid_indie['price_usd'].max()
            }
        }
        
        # ジャンル別価格戦略
        genre_price_strategy = self.indie_data.groupby('primary_genre').agg({
            'price_usd': ['mean', 'median', 'count'],
            'is_free': 'sum'
        }).round(2)
        
        genre_price_strategy.columns = ['avg_price', 'median_price', 'total_games', 'free_games']
        genre_price_strategy['free_ratio'] = (
            genre_price_strategy['free_games'] / genre_price_strategy['total_games'] * 100
        ).round(1)
        
        return {
            'price_stats': price_stats,
            'genre_price_strategy': genre_price_strategy.sort_values('total_games', ascending=False)
        }
    
    def analyze_platform_strategies(self) -> Dict[str, Any]:
        """プラットフォーム戦略分析"""
        
        if self.indie_data is None:
            self.load_data()
            
        # プラットフォーム対応統計
        platform_stats = {
            'windows_only': len(self.indie_data[
                (self.indie_data['platforms_windows'] == True) &
                (self.indie_data['platforms_mac'] == False) &
                (self.indie_data['platforms_linux'] == False)
            ]),
            'windows_mac': len(self.indie_data[
                (self.indie_data['platforms_windows'] == True) &
                (self.indie_data['platforms_mac'] == True) &
                (self.indie_data['platforms_linux'] == False)
            ]),
            'all_platforms': len(self.indie_data[
                (self.indie_data['platforms_windows'] == True) &
                (self.indie_data['platforms_mac'] == True) &
                (self.indie_data['platforms_linux'] == True)
            ]),
            'total_games': len(self.indie_data)
        }
        
        # プラットフォーム対応率
        platform_rates = {
            'windows': self.indie_data['platforms_windows'].mean() * 100,
            'mac': self.indie_data['platforms_mac'].mean() * 100,
            'linux': self.indie_data['platforms_linux'].mean() * 100
        }
        
        # プラットフォーム数別の価格分析
        platform_price_analysis = self.indie_data.groupby('platform_count').agg({
            'price_usd': ['mean', 'median', 'count'],
            'app_id': 'count'
        }).round(2)
        
        # ジャンル別プラットフォーム戦略
        genre_platform = self.indie_data.groupby('primary_genre').agg({
            'platforms_windows': 'mean',
            'platforms_mac': 'mean', 
            'platforms_linux': 'mean',
            'platform_count': 'mean'
        }).round(3) * 100  # パーセンテージに変換
        
        return {
            'platform_stats': platform_stats,
            'platform_rates': platform_rates,
            'platform_price_analysis': platform_price_analysis,
            'genre_platform_strategy': genre_platform.sort_values('platform_count', ascending=False)
        }
    
    def analyze_developer_ecosystem(self) -> Dict[str, Any]:
        """開発者エコシステム分析"""
        
        if self.indie_data is None:
            self.load_data()
            
        # 開発者別統計
        developer_stats = self.indie_data.groupby('primary_developer').agg({
            'app_id': 'count',
            'price_usd': 'mean'
        }).round(2)
        
        developer_stats.columns = ['game_count', 'avg_price']
        developer_stats = developer_stats.sort_values('game_count', ascending=False)
        
        # 開発者分類
        solo_developers = developer_stats[developer_stats['game_count'] == 1]
        prolific_developers = developer_stats[developer_stats['game_count'] >= 3]
        active_developers = developer_stats[developer_stats['game_count'] >= 2]
        
        # エコシステム統計
        ecosystem_stats = {
            'total_developers': len(developer_stats),
            'solo_developers': len(solo_developers),
            'prolific_developers': len(prolific_developers),
            'active_developers': len(active_developers),
            'avg_games_per_developer': developer_stats['game_count'].mean(),
            'median_games_per_developer': developer_stats['game_count'].median(),
            'concentration_ratio': prolific_developers['game_count'].sum() / len(self.indie_data) * 100
        }
        
        # 活発な開発者の特徴
        prolific_analysis = {
            'avg_games': prolific_developers['game_count'].mean(),
            'avg_price': prolific_developers['avg_price'].mean(),
            'price_strategy': 'budget' if prolific_developers['avg_price'].mean() < 10 else 'premium'
        }
        
        return {
            'developer_stats': developer_stats,
            'ecosystem_stats': ecosystem_stats,
            'prolific_analysis': prolific_analysis,
            'top_developers': developer_stats.head(15)
        }
    
    def _calculate_hhi_index(self, market_shares: pd.Series) -> float:
        """ハーフィンダール・ハーシュマン指数（HHI）の計算"""
        
        total = market_shares.sum()
        shares = (market_shares / total * 100) ** 2
        return shares.sum()
    
    def generate_market_insights(self) -> Dict[str, str]:
        """市場洞察の生成"""
        
        overview = self.get_market_overview()
        genre_analysis = self.analyze_genre_trends()
        price_analysis = self.analyze_price_strategies()
        platform_analysis = self.analyze_platform_strategies()
        developer_analysis = self.analyze_developer_ecosystem()
        
        insights = {}
        
        # 市場構造の洞察
        if overview['indie_ratio'] > 50:
            insights['market_structure'] = f"インディーゲームが市場の主要セグメントを形成（{overview['indie_ratio']:.1f}%）"
        else:
            insights['market_structure'] = f"インディーゲームは成長中のニッチ市場（{overview['indie_ratio']:.1f}%）"
        
        # 価格戦略の洞察  
        budget_ratio = price_analysis['price_stats']['percentages'].get('Free', 0) + \
                      price_analysis['price_stats']['percentages'].get('Budget ($0-5)', 0)
        
        if budget_ratio > 60:
            insights['price_strategy'] = f"低価格戦略が主流（{budget_ratio:.1f}%が$5以下）"
        else:
            insights['price_strategy'] = f"価格帯は分散、多様な戦略が共存（低価格{budget_ratio:.1f}%）"
        
        # ジャンル多様性の洞察
        if genre_analysis['diversity_metrics']['hhi_index'] < 1000:
            insights['genre_diversity'] = "ジャンルは高度に多様化、特定ジャンルの独占なし"
        elif genre_analysis['diversity_metrics']['hhi_index'] < 2500:
            insights['genre_diversity'] = "ジャンルは適度に多様化、一部人気ジャンルあり"
        else:
            insights['genre_diversity'] = "特定ジャンルが市場を主導"
        
        # プラットフォーム戦略の洞察
        multi_platform_ratio = (platform_analysis['platform_stats']['windows_mac'] + 
                               platform_analysis['platform_stats']['all_platforms']) / \
                               platform_analysis['platform_stats']['total_games'] * 100
        
        if multi_platform_ratio > 50:
            insights['platform_strategy'] = f"マルチプラットフォーム対応が主流（{multi_platform_ratio:.1f}%）"
        else:
            insights['platform_strategy'] = f"Windows単独リリースが多数（マルチ{multi_platform_ratio:.1f}%）"
        
        # 開発者エコシステムの洞察
        if developer_analysis['ecosystem_stats']['concentration_ratio'] < 20:
            insights['developer_ecosystem'] = "多様な開発者による分散型市場"
        else:
            insights['developer_ecosystem'] = f"一部の活発な開発者が市場をリード（{developer_analysis['ecosystem_stats']['concentration_ratio']:.1f}%）"
        
        return insights
    
    # ===== 新しい非同期分析メソッド =====
    
    async def analyze_genre_trends_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        ジャンル別トレンド分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            ジャンル別統計データ
        """
        try:
            # ジャンル別統計クエリ
            genre_query = text("""
                SELECT 
                    UNNEST(genres) as genre,
                    COUNT(*) as game_count,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price,
                    COUNT(CASE WHEN is_free THEN 1 END) as free_games,
                    AVG(CASE WHEN positive_reviews > 0 THEN 
                        CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) 
                        ELSE 0 END) as avg_rating,
                    AVG(CASE WHEN platforms_windows THEN 1 ELSE 0 END +
                        CASE WHEN platforms_mac THEN 1 ELSE 0 END +
                        CASE WHEN platforms_linux THEN 1 ELSE 0 END) as avg_platforms
                FROM games 
                WHERE type = 'game' 
                  AND genres IS NOT NULL 
                  AND array_length(genres, 1) > 0
                GROUP BY UNNEST(genres)
                HAVING COUNT(*) >= 5
                ORDER BY game_count DESC
                LIMIT 25;
            """)
            
            result = await session.execute(genre_query)
            genre_data = [dict(row._mapping) for row in result]
            
            # データの後処理
            for genre in genre_data:
                genre['avg_price'] = round(genre['avg_price'] or 0, 2)
                genre['avg_rating'] = round(genre['avg_rating'] or 0, 3)
                genre['avg_platforms'] = round(genre['avg_platforms'] or 0, 1)
                genre['free_game_ratio'] = round(
                    (genre['free_games'] / genre['game_count']) * 100, 1
                )
            
            return {
                'genre_stats': genre_data,
                'total_genres': len(genre_data),
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"ジャンル分析エラー: {e}")
            return {}
    
    async def analyze_price_trends_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        価格帯別トレンド分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            価格帯別統計データ
        """
        try:
            # 価格帯別統計クエリ
            price_query = text("""
                SELECT 
                    CASE 
                        WHEN price_final = 0 THEN 'Free'
                        WHEN price_final <= 500 THEN '$0-$5'
                        WHEN price_final <= 1000 THEN '$5-$10'
                        WHEN price_final <= 2000 THEN '$10-$20'
                        WHEN price_final <= 3000 THEN '$20-$30'
                        ELSE '$30+'
                    END as price_range,
                    COUNT(*) as game_count,
                    AVG(CASE WHEN positive_reviews > 0 THEN 
                        CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) 
                        ELSE 0 END) as avg_rating,
                    COUNT(CASE WHEN genres::text LIKE '%Indie%' THEN 1 END) as indie_count,
                    AVG(CASE WHEN platforms_windows THEN 1 ELSE 0 END +
                        CASE WHEN platforms_mac THEN 1 ELSE 0 END +
                        CASE WHEN platforms_linux THEN 1 ELSE 0 END) as avg_platforms
                FROM games 
                WHERE type = 'game'
                GROUP BY 
                    CASE 
                        WHEN price_final = 0 THEN 'Free'
                        WHEN price_final <= 500 THEN '$0-$5'
                        WHEN price_final <= 1000 THEN '$5-$10'
                        WHEN price_final <= 2000 THEN '$10-$20'
                        WHEN price_final <= 3000 THEN '$20-$30'
                        ELSE '$30+'
                    END
                ORDER BY 
                    CASE 
                        WHEN price_final = 0 THEN 0
                        WHEN price_final <= 500 THEN 1
                        WHEN price_final <= 1000 THEN 2
                        WHEN price_final <= 2000 THEN 3
                        WHEN price_final <= 3000 THEN 4
                        ELSE 5
                    END;
            """)
            
            result = await session.execute(price_query)
            price_data = [dict(row._mapping) for row in result]
            
            # データの後処理
            for price_range in price_data:
                price_range['avg_rating'] = round(price_range['avg_rating'] or 0, 3)
                price_range['avg_platforms'] = round(price_range['avg_platforms'] or 0, 1)
                price_range['indie_ratio'] = round(
                    (price_range['indie_count'] / price_range['game_count']) * 100, 1
                )
            
            return {
                'price_distribution': price_data,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"価格分析エラー: {e}")
            return {}
    
    async def analyze_success_factors_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        成功要因分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            成功要因分析データ
        """
        try:
            # 高評価ゲームの特徴分析
            success_query = text("""
                WITH success_metrics AS (
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
                        platforms_windows + platforms_mac + platforms_linux as platform_count,
                        CASE WHEN genres::text LIKE '%Indie%' THEN true ELSE false END as is_indie
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 10
                ),
                success_tiers AS (
                    SELECT *,
                        CASE 
                            WHEN rating >= 0.9 AND positive_reviews >= 100 THEN 'Highly Successful'
                            WHEN rating >= 0.8 AND positive_reviews >= 50 THEN 'Successful'
                            WHEN rating >= 0.7 AND positive_reviews >= 20 THEN 'Moderately Successful'
                            ELSE 'Below Average'
                        END as success_tier
                    FROM success_metrics
                )
                SELECT 
                    success_tier,
                    COUNT(*) as game_count,
                    AVG(price_usd) as avg_price,
                    AVG(platform_count) as avg_platforms,
                    AVG(CASE WHEN is_indie THEN 1.0 ELSE 0.0 END) * 100 as indie_ratio,
                    AVG(rating) as avg_rating
                FROM success_tiers
                GROUP BY success_tier
                ORDER BY 
                    CASE success_tier
                        WHEN 'Highly Successful' THEN 1
                        WHEN 'Successful' THEN 2
                        WHEN 'Moderately Successful' THEN 3
                        ELSE 4
                    END;
            """)
            
            result = await session.execute(success_query)
            success_data = [dict(row._mapping) for row in result]
            
            # データの後処理
            for tier in success_data:
                tier['avg_price'] = round(tier['avg_price'] or 0, 2)
                tier['avg_platforms'] = round(tier['avg_platforms'] or 0, 1)
                tier['indie_ratio'] = round(tier['indie_ratio'] or 0, 1)
                tier['avg_rating'] = round(tier['avg_rating'] or 0, 3)
            
            return {
                'success_analysis': success_data,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"成功要因分析エラー: {e}")
            return {}
    
    async def analyze_market_size_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        市場規模分析（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            市場規模統計データ
        """
        try:
            # 市場規模統計クエリ
            market_query = text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN genres::text LIKE '%Indie%' THEN 1 END) as indie_games,
                    COUNT(CASE WHEN is_free THEN 1 END) as free_games,
                    COUNT(CASE WHEN positive_reviews > 0 THEN 1 END) as reviewed_games,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price,
                    SUM(positive_reviews + negative_reviews) as total_reviews,
                    COUNT(CASE WHEN platforms_windows THEN 1 END) as windows_games,
                    COUNT(CASE WHEN platforms_mac THEN 1 END) as mac_games,
                    COUNT(CASE WHEN platforms_linux THEN 1 END) as linux_games
                FROM games 
                WHERE type = 'game';
            """)
            
            result = await session.execute(market_query)
            market_data = dict(result.fetchone()._mapping)
            
            # 追加の統計計算
            indie_ratio = (market_data['indie_games'] / market_data['total_games']) * 100
            free_ratio = (market_data['free_games'] / market_data['total_games']) * 100
            reviewed_ratio = (market_data['reviewed_games'] / market_data['total_games']) * 100
            
            return {
                'market_overview': {
                    'total_games': market_data['total_games'],
                    'indie_games': market_data['indie_games'],
                    'free_games': market_data['free_games'],
                    'reviewed_games': market_data['reviewed_games'],
                    'avg_price': round(market_data['avg_price'] or 0, 2),
                    'total_reviews': market_data['total_reviews'],
                    'indie_ratio': round(indie_ratio, 1),
                    'free_ratio': round(free_ratio, 1),
                    'reviewed_ratio': round(reviewed_ratio, 1),
                    'platform_coverage': {
                        'windows': market_data['windows_games'],
                        'mac': market_data['mac_games'],
                        'linux': market_data['linux_games']
                    }
                },
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"市場規模分析エラー: {e}")
            return {}
    
    async def generate_market_insights_async(self, session: AsyncSession) -> List[str]:
        """
        市場洞察の生成（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            市場洞察のリスト
        """
        insights = []
        
        try:
            # 各種分析結果を並行取得
            tasks = [
                self.analyze_genre_trends_async(session),
                self.analyze_price_trends_async(session),
                self.analyze_market_size_async(session),
                self.analyze_success_factors_async(session)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            genre_data, price_data, market_data, success_data = results
            
            # 洞察生成
            if not isinstance(genre_data, Exception) and genre_data.get('genre_stats'):
                top_genre = genre_data['genre_stats'][0]
                insights.append(
                    f"最人気ジャンル「{top_genre['genre']}」は{top_genre['game_count']:,}件で市場を牽引"
                )
            
            if not isinstance(market_data, Exception) and market_data.get('market_overview'):
                overview = market_data['market_overview']
                insights.append(
                    f"インディーゲーム比率{overview['indie_ratio']}%で市場に重要な影響"
                )
                insights.append(
                    f"平均価格${overview['avg_price']}で手頃な価格帯が主流"
                )
            
            if not isinstance(price_data, Exception) and price_data.get('price_distribution'):
                free_games = next((p for p in price_data['price_distribution'] 
                                 if p['price_range'] == 'Free'), None)
                if free_games:
                    insights.append(
                        f"無料ゲーム{free_games['game_count']:,}件でフリーミアム戦略が普及"
                    )
            
            if not isinstance(success_data, Exception) and success_data.get('success_analysis'):
                successful_games = [s for s in success_data['success_analysis'] 
                                  if s['success_tier'] in ['Highly Successful', 'Successful']]
                if successful_games:
                    avg_success_price = sum(s['avg_price'] for s in successful_games) / len(successful_games)
                    insights.append(
                        f"成功ゲームの平均価格${avg_success_price:.2f}で最適価格帯が判明"
                    )
            
        except Exception as e:
            self.logger.error(f"洞察生成エラー: {e}")
            insights.append("データ分析中にエラーが発生しました")
        
        return insights
    
    async def generate_comprehensive_report_async(self, session: AsyncSession) -> Dict[str, Any]:
        """
        包括的な市場分析レポート生成（非同期版）
        
        Args:
            session: データベースセッション
            
        Returns:
            包括的分析レポート
        """
        try:
            # 各種分析を並行実行
            tasks = [
                self.analyze_genre_trends_async(session),
                self.analyze_price_trends_async(session),
                self.analyze_market_size_async(session),
                self.analyze_success_factors_async(session),
                self.generate_market_insights_async(session)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果の統合
            report = {
                'report_id': f"market_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'genre_analysis': results[0] if not isinstance(results[0], Exception) else {},
                'price_analysis': results[1] if not isinstance(results[1], Exception) else {},
                'market_overview': results[2] if not isinstance(results[2], Exception) else {},
                'success_analysis': results[3] if not isinstance(results[3], Exception) else {},
                'insights': results[4] if not isinstance(results[4], Exception) else [],
                'report_status': 'completed',
                'error_count': sum(1 for r in results if isinstance(r, Exception))
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"包括レポート生成エラー: {e}")
            return {
                'report_id': f"market_analysis_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'report_status': 'failed'
            }
    
    def create_market_summary_report(self) -> str:
        """市場サマリーレポートの生成"""
        
        overview = self.get_market_overview()
        insights = self.generate_market_insights()
        
        report = f"""
🎮 Steam インディーゲーム市場 分析レポート
{'='*60}

📊 市場概要:
  • 総ゲーム数: {overview['total_games']:,}件
  • インディーゲーム: {overview['indie_games']:,}件 ({overview['indie_ratio']:.1f}%)
  • 平均価格: インディー${overview['avg_price_indie']:.2f} vs 非インディー${overview['avg_price_non_indie']:.2f}

🔍 主要洞察:
  • 市場構造: {insights['market_structure']}
  • 価格戦略: {insights['price_strategy']}
  • ジャンル多様性: {insights['genre_diversity']}
  • プラットフォーム: {insights['platform_strategy']}
  • 開発者動向: {insights['developer_ecosystem']}

🖥️ プラットフォーム対応率:
  • Windows: {overview['platform_stats']['windows_rate']:.1f}%
  • Mac: {overview['platform_stats']['mac_rate']:.1f}%
  • Linux: {overview['platform_stats']['linux_rate']:.1f}%
  • 平均対応数: {overview['platform_stats']['avg_platforms']:.1f}

💡 戦略的示唆:
  • 新規参入: ${overview['median_price_indie']:.2f}前後の価格設定が主流
  • 差別化: マルチプラットフォーム対応とニッチジャンル特化
  • 競争環境: 多様な開発者による活発な競争市場

📈 成長機会:
  • Linux対応による差別化
  • 未開拓ジャンルでの専門化
  • コミュニティ重視の開発戦略
        """
        
        return report.strip()


# 使用例とテスト関数
def main():
    """メイン実行関数（テスト用）"""
    
    print("🔍 Steam インディーゲーム市場分析を開始")
    
    try:
        analyzer = MarketAnalyzer()
        
        # データ読み込み
        analyzer.load_data()
        
        # 各種分析の実行
        print("\n📊 市場概要分析...")
        overview = analyzer.get_market_overview()
        
        print("\n🎮 ジャンルトレンド分析...")
        genre_trends = analyzer.analyze_genre_trends()
        
        print("\n💰 価格戦略分析...")
        price_strategies = analyzer.analyze_price_strategies()
        
        print("\n🖥️ プラットフォーム戦略分析...")
        platform_strategies = analyzer.analyze_platform_strategies()
        
        print("\n👥 開発者エコシステム分析...")
        developer_ecosystem = analyzer.analyze_developer_ecosystem()
        
        # レポート生成
        print("\n📄 市場サマリーレポート生成...")
        report = analyzer.create_market_summary_report()
        print(report)
        
        print("\n✅ 市場分析完了")
        
    except Exception as e:
        print(f"❌ 分析エラー: {e}")


async def main_async():
    """非同期メイン実行関数（新しい分析機能のテスト用）"""
    analyzer = MarketAnalyzer()
    
    async with get_db_session() as session:
        # 包括的分析レポート生成
        print("🔄 包括的市場分析を実行中...")
        report = await analyzer.generate_comprehensive_report_async(session)
        
        print("🎮 Steam市場分析レポート")
        print("=" * 50)
        
        if report.get('market_overview', {}).get('market_overview'):
            overview = report['market_overview']['market_overview']
            print(f"📊 総ゲーム数: {overview['total_games']:,}")
            print(f"🎯 インディーゲーム: {overview['indie_games']:,} ({overview['indie_ratio']}%)")
            print(f"💰 平均価格: ${overview['avg_price']}")
            print(f"🆓 無料ゲーム: {overview['free_games']:,} ({overview['free_ratio']}%)")
        
        if report.get('genre_analysis', {}).get('genre_stats'):
            print(f"\n🏆 TOP 5ジャンル:")
            for i, genre in enumerate(report['genre_analysis']['genre_stats'][:5], 1):
                print(f"  {i}. {genre['genre']}: {genre['game_count']:,}件 (平均${genre['avg_price']})")
        
        if report.get('insights'):
            print("\n💡 市場洞察:")
            for insight in report['insights']:
                print(f"  • {insight}")
        
        print(f"\n📅 分析日時: {report['generated_at']}")
        print(f"🎯 分析状況: {report['report_status']}")


if __name__ == "__main__":
    # 従来の同期分析
    print("🔍 Steam インディーゲーム市場分析（同期版）")
    main()
    
    print("\n" + "="*60)
    print("🚀 新しい非同期分析を実行")
    asyncio.run(main_async())