#!/usr/bin/env python3
"""
AI洞察生成器

Gemini APIを使用してインディーゲーム市場データから
自動的に分析コメントと洞察を生成するモジュール
"""

import os
import sys
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
import json
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("⚠️ google-generativeai が見つかりません。インストールしてください:")
    print("pip install google-generativeai")
    sys.exit(1)

# プロジェクトルートパス追加
sys.path.append('/workspace')


class AIInsightsGenerator:
    """AI分析洞察生成器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Gemini API Key（省略時は環境変数から取得）
        """
        # API Key設定
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API Keyが設定されていません。\n"
                "環境変数GEMINI_API_KEYを設定するか、引数で指定してください。"
            )
        
        # Gemini API設定
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 生成設定
        self.generation_config = {
            'temperature': 0.7,  # 創造性のバランス
            'top_p': 0.8,       # 多様性制御
            'max_output_tokens': 1000,  # 最大出力長
        }
    
    def generate_market_overview_insight(self, data_summary: Dict[str, Any]) -> str:
        """
        市場概要の洞察コメント生成
        
        Args:
            data_summary: 市場データサマリー
            
        Returns:
            str: 生成された洞察コメント
        """
        prompt = f"""
あなたはインディーゲーム市場の専門アナリストです。以下のデータから日本語で洞察に満ちた分析コメントを生成してください。

【データ】
総ゲーム数: {data_summary.get('total_games', 0)}件
無料ゲーム: {data_summary.get('free_games', 0)}件 ({data_summary.get('free_ratio', 0):.1f}%)
平均価格: ¥{data_summary.get('avg_price_jpy', 0):,.0f}
主要ジャンル: {data_summary.get('top_genres', [])}
レビュー率: {data_summary.get('review_ratio', 0):.1f}%

【要求】
- 200-300文字程度
- データの特徴的なポイントを指摘
- 市場トレンドや投資価値について言及
- 専門的だが読みやすい日本語
- 具体的な数値を活用
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            return response.text.strip()
        except Exception as e:
            return f"分析コメント生成エラー: {str(e)}"
    
    def generate_genre_analysis_insight(self, genre_data: pd.DataFrame) -> str:
        """
        ジャンル分析の洞察コメント生成
        
        Args:
            genre_data: ジャンル別統計データ
            
        Returns:
            str: 生成された洞察コメント
        """
        # トップ5ジャンルの情報を抽出
        top_genres = genre_data.head(5)
        genre_summary = []
        
        for _, row in top_genres.iterrows():
            genre_summary.append({
                'name': row.name,
                'count': row.get('app_id', row.get('game_count', 0)),
                'avg_price': row.get('price_usd', 0),
                'rating': row.get('rating', 0)
            })
        
        prompt = f"""
あなたはゲーム業界の市場アナリストです。インディーゲームのジャンル分析データから洞察を生成してください。

【トップ5ジャンルデータ】
{json.dumps(genre_summary, ensure_ascii=False, indent=2)}

【分析要求】
- 250-350文字程度
- ジャンル間の競争状況を分析
- 価格戦略の特徴を指摘
- 開発者への実用的なアドバイス
- 市場機会について言及
- 日本語で専門的かつ実用的に
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            return response.text.strip()
        except Exception as e:
            return f"ジャンル分析コメント生成エラー: {str(e)}"
    
    def generate_price_strategy_insight(self, price_data: Dict[str, Any]) -> str:
        """
        価格戦略の洞察コメント生成
        
        Args:
            price_data: 価格分析データ
            
        Returns:
            str: 生成された洞察コメント
        """
        prompt = f"""
あなたはインディーゲームの価格戦略コンサルタントです。以下の価格データから戦略的洞察を生成してください。

【価格データ】
価格帯分布:
- 無料: {price_data.get('free_percent', 0):.1f}%
- 低価格帯(¥0-750): {price_data.get('budget_percent', 0):.1f}%
- 中価格帯(¥750-2,250): {price_data.get('mid_percent', 0):.1f}%
- 高価格帯(¥2,250-4,500): {price_data.get('premium_percent', 0):.1f}%
- プレミアム(¥4,500+): {price_data.get('luxury_percent', 0):.1f}%

平均価格: ¥{price_data.get('avg_price', 0):,.0f}
価格vs評価相関: {price_data.get('price_rating_correlation', 'N/A')}

【要求】
- 200-300文字程度
- 価格戦略の市場動向を分析
- 最適な価格帯の推奨
- リスクと機会を指摘
- 実践的なアドバイス
- データに基づいた根拠ある分析
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            return response.text.strip()
        except Exception as e:
            return f"価格戦略コメント生成エラー: {str(e)}"
    
    def generate_success_factors_insight(self, success_data: Dict[str, Any]) -> str:
        """
        成功要因分析の洞察コメント生成
        
        Args:
            success_data: 成功要因データ
            
        Returns:
            str: 生成された洞察コメント
        """
        prompt = f"""
あなたはゲーム業界の成功要因研究者です。インディーゲームの成功パターンから実用的な洞察を生成してください。

【成功要因データ】
高評価ゲームの特徴:
- 平均レビュー数: {success_data.get('avg_reviews', 0):,.0f}件
- 平均評価率: {success_data.get('avg_rating', 0):.1%}
- 主要価格帯: {success_data.get('success_price_range', 'N/A')}
- 人気ジャンル: {success_data.get('success_genres', [])}
- プラットフォーム戦略: {success_data.get('platform_strategy', 'N/A')}

【要求】
- 250-350文字程度
- 成功の再現可能なパターンを抽出
- 開発者が実践できる具体的アドバイス
- 失敗要因の回避方法も言及
- データドリブンな根拠
- 実用性重視の日本語
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            return response.text.strip()
        except Exception as e:
            return f"成功要因コメント生成エラー: {str(e)}"
    
    def generate_comprehensive_report(self, all_data: Dict[str, Any]) -> Dict[str, str]:
        """
        包括的なAI分析レポート生成
        
        Args:
            all_data: 全分析データ
            
        Returns:
            Dict[str, str]: セクション別洞察コメント
        """
        report = {}
        
        # 各セクションの洞察を生成
        if 'market_overview' in all_data:
            report['market_overview'] = self.generate_market_overview_insight(
                all_data['market_overview']
            )
        
        if 'genre_analysis' in all_data:
            report['genre_analysis'] = self.generate_genre_analysis_insight(
                all_data['genre_analysis']
            )
        
        if 'price_strategy' in all_data:
            report['price_strategy'] = self.generate_price_strategy_insight(
                all_data['price_strategy']
            )
        
        if 'success_factors' in all_data:
            report['success_factors'] = self.generate_success_factors_insight(
                all_data['success_factors']
            )
        
        return report
    
    def test_api_connection(self) -> bool:
        """
        API接続テスト
        
        Returns:
            bool: 接続成功時True
        """
        try:
            test_prompt = "こんにちは"
            response = self.model.generate_content(test_prompt)
            return bool(response.text)
        except Exception as e:
            print(f"❌ Gemini API接続エラー: {e}")
            return False


def main():
    """テスト実行"""
    try:
        # AI洞察生成器初期化
        ai_generator = AIInsightsGenerator()
        
        # 接続テスト
        print("🤖 Gemini API接続テスト...")
        if ai_generator.test_api_connection():
            print("✅ API接続成功")
        else:
            print("❌ API接続失敗")
            return
        
        # サンプルデータでテスト
        sample_data = {
            'total_games': 548,
            'free_games': 58,
            'free_ratio': 10.6,
            'avg_price_jpy': 1500,
            'top_genres': ['Action', 'Adventure', 'Casual'],
            'review_ratio': 65.2
        }
        
        print("\n📊 市場概要洞察生成テスト...")
        insight = ai_generator.generate_market_overview_insight(sample_data)
        print(f"生成結果:\n{insight}")
        
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    main()