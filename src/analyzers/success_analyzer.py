"""
インディーゲーム成功要因分析モジュール

ゲームの成功指標（レビュー数、評価等）を基に、
成功要因やパターンを分析する。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


class SuccessAnalyzer:
    """インディーゲーム成功要因分析クラス"""

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
    main()