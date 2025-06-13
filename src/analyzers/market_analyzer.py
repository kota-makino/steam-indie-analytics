"""
インディーゲーム市場トレンド分析モジュール

市場の全体的なトレンド、ジャンル別動向、価格戦略などを分析する。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
# import plotly.express as px
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
from datetime import datetime, timedelta
# import seaborn as sns
# import matplotlib.pyplot as plt


class MarketAnalyzer:
    """インディーゲーム市場分析クラス"""

    def __init__(self):
        """初期化"""
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


if __name__ == "__main__":
    main()