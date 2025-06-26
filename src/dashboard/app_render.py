"""
Steam インディーゲーム市場分析ダッシュボード - Render版
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import sys
import warnings
from datetime import datetime
import time
from pathlib import Path

# パス設定 (Render対応)
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Render環境検出
IS_RENDER = os.getenv('RENDER') == 'true' or 'onrender.com' in os.getenv('RENDER_EXTERNAL_URL', '')

# 分析モジュールのインポート (エラーハンドリング付き)
try:
    from src.analyzers.market_analyzer import MarketAnalyzer
    from src.analyzers.success_analyzer import SuccessAnalyzer  
    from src.analyzers.data_quality_checker import DataQualityChecker
    ANALYZERS_AVAILABLE = True
except ImportError as e:
    st.warning(f"分析モジュールのインポートエラー: {e}")
    ANALYZERS_AVAILABLE = False

# AI洞察生成モジュール
AI_INSIGHTS_AVAILABLE = False
try:
    if ANALYZERS_AVAILABLE:
        from src.analyzers.ai_insights_generator import AIInsightsGenerator
        
        # APIキー確認
        if IS_RENDER:
            api_key = os.getenv("GEMINI_API_KEY")
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            
        if api_key:
            AI_INSIGHTS_AVAILABLE = True
        else:
            st.info("🤖 AI洞察機能: Gemini APIキーが設定されていません")
    else:
        st.info("🤖 AI洞察機能: 分析モジュールが利用できません")
except ImportError as e:
    st.info(f"🤖 AI洞察機能: インポートエラー {e}")

# デモ用AI洞察生成関数
def generate_demo_insights(data_summary: str, section: str) -> str:
    """デモ用AI洞察（固定メッセージ）"""
    demo_insights = {
        "market": "🎮 市場概況: インディーゲーム市場は多様性に富み、低価格帯ゲームが主流を占めています。プラットフォーム対応とユーザーレビューの質が成功の鍵となっています。",
        "genre": "🎯 ジャンル分析: Actionジャンルが最も競争が激しく、Adventure・Casualジャンルにニッチな機会があります。複合ジャンルのゲームが高い評価を得る傾向があります。",
        "pricing": "💰 価格戦略: 中価格帯（$10-30）が最適なスイートスポットです。無料ゲームは高いダウンロード数を獲得できますが、収益化に課題があります。",
        "comprehensive": "📈 総合評価: インディーゲーム市場は創造性とユーザーエンゲージメントが重視される環境です。データドリブンな開発戦略が成功確率を高めます。"
    }
    return demo_insights.get(section, "🤖 AI分析データを処理中です...")

warnings.filterwarnings("ignore")

# 環境変数読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="Steam インディーゲーム市場分析",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# デモデータ生成関数
def load_demo_data():
    """Render用デモデータ生成"""
    np.random.seed(42)  # 再現性のため
    
    # サンプルデータ生成
    demo_data = {
        'app_id': range(1, 549),
        'name': [f'Demo Game {i}' for i in range(1, 549)],
        'type': ['game'] * 548,
        'is_free': np.random.choice([True, False], 548, p=[0.3, 0.7]),
        'price_final': np.random.exponential(1500, 548),
        'price_usd': np.random.exponential(15, 548),
        'release_date': pd.date_range('2020-01-01', periods=548, freq='D'),
        'platforms_windows': np.random.choice([True, False], 548, p=[0.9, 0.1]),
        'platforms_mac': np.random.choice([True, False], 548, p=[0.6, 0.4]),
        'platforms_linux': np.random.choice([True, False], 548, p=[0.5, 0.5]),
        'platform_count': np.random.randint(1, 4, 548),
        'positive_reviews': np.random.poisson(100, 548),
        'negative_reviews': np.random.poisson(20, 548),
        'total_reviews': lambda x: x['positive_reviews'] + x['negative_reviews'],
        'rating': np.random.beta(8, 2, 548) * 100,  # 80%平均の評価
        'is_indie': [True] * 548,
        'primary_genre': np.random.choice(['Action', 'Adventure', 'Casual', 'RPG', 'Strategy'], 548),
        'primary_developer': [f'Developer {i%50}' for i in range(548)],
        'primary_publisher': [f'Publisher {i%30}' for i in range(548)],
        'price_category': np.random.choice(['無料', '低価格', '中価格', 'プレミアム'], 548, p=[0.3, 0.4, 0.2, 0.1])
    }
    
    df = pd.DataFrame(demo_data)
    df['total_reviews'] = df['positive_reviews'] + df['negative_reviews']
    df['positive_percentage'] = (df['positive_reviews'] / df['total_reviews'] * 100).fillna(0)
    
    return df

@st.cache_data(ttl=60)
def load_data():
    """データの読み込み - Render対応"""
    
    # データベース接続設定の取得
    db_config = None
    
    try:
        if IS_RENDER:
            # Render環境
            if all(os.getenv(key) for key in ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']):
                db_config = {
                    "host": os.getenv("POSTGRES_HOST"),
                    "port": int(os.getenv("POSTGRES_PORT", 5432)),
                    "database": os.getenv("POSTGRES_DB"),
                    "user": os.getenv("POSTGRES_USER"),
                    "password": os.getenv("POSTGRES_PASSWORD"),
                }
                st.info("🔗 Renderデータベース接続を試行中...")
            else:
                # DB設定なし → デモモード
                st.warning("🌟 デモモード: サンプルデータを表示しています")
                st.caption("💡 実際のデータを表示するには、Render環境変数でデータベース設定を行ってください")
                return load_demo_data()
        else:
            # ローカル環境
            if os.getenv("POSTGRES_HOST"):
                db_config = {
                    "host": os.getenv("POSTGRES_HOST", "postgres"),
                    "port": int(os.getenv("POSTGRES_PORT", 5432)),
                    "database": os.getenv("POSTGRES_DB", "steam_analytics"),
                    "user": os.getenv("POSTGRES_USER", "steam_user"),
                    "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
                }
            else:
                # 環境変数なし → デモモード
                st.warning("🌟 デモモード: サンプルデータを表示しています")
                st.caption("💡 実際のデータを表示するには、.envファイルでデータベース設定を行ってください")
                return load_demo_data()
    except Exception as e:
        st.warning(f"🌟 デモモード: 設定読み込みエラー ({e})")
        return load_demo_data()
    
    # データベース接続がない場合はデモモード
    if db_config is None:
        st.warning("🌟 デモモード: データベース設定がありません")
        return load_demo_data()
    
    try:
        # SQLAlchemy エンジン作成
        engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}",
            connect_args={
                "connect_timeout": 5,
                "application_name": "streamlit_render",
            },
            pool_timeout=10,
            pool_recycle=3600,
        )

        # クエリ実行 - 実際のテーブル構造に合わせて修正
        query = """
        SELECT 
            app_id,
            name,
            type,
            is_free,
            price_initial,
            price_final,
            price_final::float / 100 as price_usd,  -- セント単位をドル単位に変換
            release_date_text as release_date,
            platforms_windows,
            platforms_mac, 
            platforms_linux,
            (platforms_windows::int + platforms_mac::int + platforms_linux::int) as platform_count,
            genres,
            categories,
            COALESCE(positive_reviews, 0) as positive_reviews,
            COALESCE(negative_reviews, 0) as negative_reviews,
            (COALESCE(positive_reviews, 0) + COALESCE(negative_reviews, 0)) as total_reviews,
            CASE 
                WHEN (COALESCE(positive_reviews, 0) + COALESCE(negative_reviews, 0)) > 0 
                THEN (COALESCE(positive_reviews, 0)::float / (COALESCE(positive_reviews, 0) + COALESCE(negative_reviews, 0))) * 100
                ELSE 75.0 
            END as rating,
            created_at
        FROM games 
        WHERE type = 'game'
        ORDER BY created_at DESC
        LIMIT 548
        """
        df = pd.read_sql_query(query, engine)
        
        # 基本的なデータクリーニング
        df = df.fillna(0)
        
        # 日付処理
        if 'release_date' in df.columns:
            df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
        
        st.success(f"✅ 実際のデータベースから {len(df)} 件のゲームデータを読み込みました")
        return df

    except Exception as e:
        st.warning(f"🌟 デモモード: データベース接続エラー ({str(e)[:100]}...)")
        st.caption("💡 外部データベースに接続できないため、サンプルデータを表示しています")
        return load_demo_data()

def main():
    """メインアプリケーション"""
    st.title("🎮 Steam インディーゲーム市場分析")
    st.markdown("---")
    
    # データ読み込み
    with st.spinner("データを読み込み中..."):
        df = load_data()
    
    if df is None:
        st.error("❌ 予期しないエラーが発生しました。")
        return
    
    # 基本統計表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総ゲーム数", f"{len(df):,}")
    with col2:
        avg_price = df['price_usd'].mean() if 'price_usd' in df.columns else 0
        st.metric("平均価格", f"${avg_price:.2f}")
    with col3:
        free_games = len(df[df.get('is_free', False) == True]) if 'is_free' in df.columns else 0
        st.metric("無料ゲーム", f"{free_games:,}")
    with col4:
        avg_rating = df['rating'].mean() if 'rating' in df.columns else 0
        st.metric("平均評価", f"{avg_rating:.1f}%")
    
    # データテーブル
    st.markdown("## 📊 データプレビュー")
    st.dataframe(df.head(10))
    
    # AI洞察セクション
    st.markdown("## 🤖 AI市場分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🤖 AI分析洞察を生成", key="ai_insight"):
            if AI_INSIGHTS_AVAILABLE:
                with st.spinner("AI分析中..."):
                    try:
                        ai_generator = AIInsightsGenerator()
                        data_summary = {
                            'total_games': len(df),
                            'avg_price': avg_price,
                            'free_ratio': (free_games / len(df) * 100) if len(df) > 0 else 0
                        }
                        insight = ai_generator.generate_market_overview_insight(data_summary)
                        st.info(insight)
                    except Exception as e:
                        st.error(f"AI洞察生成エラー: {e}")
            else:
                # デモモード用AI洞察
                with st.spinner("デモAI分析中..."):
                    time.sleep(1)
                    demo_insight = generate_demo_insights("", "market")
                    st.info(demo_insight)
                    st.caption("💡 実際の環境では、Gemini APIによる詳細な分析が提供されます")
    
    with col2:
        if st.button("📊 新しいデータを収集", key="collect_data"):
            if IS_RENDER:
                st.info("🚀 バックグラウンドでデータ収集を開始しました")
                st.caption("💡 収集完了まで5-10分程度かかります。ページを更新して新しいデータを確認してください。")
                
                # バックグラウンドタスクとしてデータ収集を実行
                try:
                    import subprocess
                    import sys
                    
                    # 非同期でデータ収集スクリプトを実行
                    subprocess.Popen([
                        sys.executable, 
                        "scripts/collect_steam_data_render.py"
                    ], cwd="/workspace")
                    
                    st.success("✅ データ収集タスクを開始しました")
                    
                except Exception as e:
                    st.error(f"❌ データ収集開始エラー: {e}")
            else:
                st.warning("⚠️  この機能はRender環境でのみ利用可能です")
                st.caption("💡 ローカル環境では collect_indie_games.py を直接実行してください")

if __name__ == "__main__":
    main()