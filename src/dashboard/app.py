"""
Steam インディーゲーム市場分析ダッシュボード

Streamlitを使用したインタラクティブなデータ可視化ダッシュボード
"""

import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import sys
import warnings
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append('/workspace')

# 分析モジュールのインポート
from src.analyzers.market_analyzer import MarketAnalyzer
from src.analyzers.success_analyzer import SuccessAnalyzer

warnings.filterwarnings('ignore')

# 環境変数読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="Steam インディーゲーム市場分析",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 1rem;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}
.insight-box {
    background-color: #e8f4f8;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #17a2b8;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """データの読み込み（キャッシュ機能付き）"""
    try:
        # データベース接続設定
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
        
        # SQLAlchemy エンジン作成
        engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
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
        
        df = pd.read_sql_query(query, engine)
        
        # 基本的な前処理
        df['price_usd'] = df['price_final'] / 100
        df.loc[df['is_free'] == True, 'price_usd'] = 0
        
        # インディーゲーム判定
        def is_indie_game(row):
            if row['genres'] is None:
                return False
            if any('Indie' in str(genre) for genre in row['genres'] if genre):
                return True
            if (row['developers'] is not None and row['publishers'] is not None and 
                len(row['developers']) <= 2 and set(row['developers']) == set(row['publishers'])):
                return True
            return False
        
        df['is_indie'] = df.apply(is_indie_game, axis=1)
        
        # その他の前処理
        df['primary_genre'] = df['genres'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Other'
        )
        
        df['primary_developer'] = df['developers'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Unknown'
        )
        
        df['platform_count'] = (
            df['platforms_windows'].astype(int) + 
            df['platforms_mac'].astype(int) + 
            df['platforms_linux'].astype(int)
        )
        
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
        
        df['price_category'] = df['price_usd'].apply(price_category)
        
        return df
        
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return None

def display_market_overview(df):
    """市場概要の表示"""
    st.markdown('<div class="main-header">🎮 Steam インディーゲーム市場概要</div>', unsafe_allow_html=True)
    
    # 基本統計
    total_games = len(df)
    indie_games = len(df[df['is_indie'] == True])
    indie_ratio = indie_games / total_games * 100
    
    # メトリクス表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="総ゲーム数",
            value=f"{total_games:,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="インディーゲーム数",
            value=f"{indie_games:,}",
            delta=f"{indie_ratio:.1f}%"
        )
    
    with col3:
        paid_games = len(df[df['price_usd'] > 0])
        st.metric(
            label="有料ゲーム",
            value=f"{paid_games:,}",
            delta=f"{paid_games/total_games*100:.1f}%"
        )
    
    with col4:
        avg_price = df[df['price_usd'] > 0]['price_usd'].mean()
        st.metric(
            label="平均価格",
            value=f"${avg_price:.2f}",
            delta=None
        )

def display_genre_analysis(df):
    """ジャンル分析の表示"""
    st.markdown("## 🎮 ジャンル別分析")
    
    indie_df = df[df['is_indie'] == True]
    
    # ジャンル分布
    genre_counts = indie_df['primary_genre'].value_counts().head(10)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### トップ10ジャンル")
        st.bar_chart(genre_counts)
    
    with col2:
        st.markdown("### ジャンル詳細統計")
        genre_stats = indie_df.groupby('primary_genre').agg({
            'app_id': 'count',
            'price_usd': 'mean',
            'platform_count': 'mean'
        }).round(2)
        
        genre_stats.columns = ['ゲーム数', '平均価格', '平均プラットフォーム数']
        genre_stats = genre_stats.sort_values('ゲーム数', ascending=False).head(10)
        
        st.dataframe(genre_stats, use_container_width=True)

def display_price_analysis(df):
    """価格分析の表示"""
    st.markdown("## 💰 価格戦略分析")
    
    indie_df = df[df['is_indie'] == True]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 価格帯分布")
        price_dist = indie_df['price_category'].value_counts()
        st.bar_chart(price_dist)
    
    with col2:
        st.markdown("### インディー vs 非インディー価格比較")
        
        # 価格比較データ
        comparison_data = {
            'インディーゲーム': [
                indie_df[indie_df['price_usd'] > 0]['price_usd'].mean(),
                indie_df[indie_df['price_usd'] > 0]['price_usd'].median()
            ],
            '非インディーゲーム': [
                df[(df['is_indie'] == False) & (df['price_usd'] > 0)]['price_usd'].mean(),
                df[(df['is_indie'] == False) & (df['price_usd'] > 0)]['price_usd'].median()
            ]
        }
        
        comparison_df = pd.DataFrame(comparison_data, index=['平均価格', '中央値'])
        st.dataframe(comparison_df.round(2), use_container_width=True)

def display_platform_analysis(df):
    """プラットフォーム分析の表示"""
    st.markdown("## 🖥️ プラットフォーム戦略分析")
    
    indie_df = df[df['is_indie'] == True]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### プラットフォーム対応率")
        
        platform_stats = {
            'Windows': indie_df['platforms_windows'].mean() * 100,
            'Mac': indie_df['platforms_mac'].mean() * 100,
            'Linux': indie_df['platforms_linux'].mean() * 100
        }
        
        platform_df = pd.DataFrame.from_dict(platform_stats, orient='index', columns=['対応率%'])
        st.bar_chart(platform_df)
    
    with col2:
        st.markdown("### プラットフォーム数別分布")
        platform_dist = indie_df['platform_count'].value_counts().sort_index()
        st.bar_chart(platform_dist)

def display_developer_analysis(df):
    """開発者分析の表示"""
    st.markdown("## 👥 開発者エコシステム分析")
    
    indie_df = df[df['is_indie'] == True]
    
    # 開発者別統計
    developer_stats = indie_df.groupby('primary_developer').agg({
        'app_id': 'count',
        'price_usd': 'mean'
    }).round(2)
    
    developer_stats.columns = ['ゲーム数', '平均価格']
    active_developers = developer_stats[developer_stats['ゲーム数'] >= 2].sort_values('ゲーム数', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 活発な開発者 TOP 10")
        st.dataframe(active_developers.head(10), use_container_width=True)
    
    with col2:
        st.markdown("### 開発者分布統計")
        
        total_devs = len(developer_stats)
        solo_devs = len(developer_stats[developer_stats['ゲーム数'] == 1])
        multi_devs = len(developer_stats[developer_stats['ゲーム数'] >= 2])
        
        dev_stats = {
            '総開発者数': total_devs,
            '単発開発者': solo_devs,
            '複数作品開発者': multi_devs,
            '平均作品数': developer_stats['ゲーム数'].mean()
        }
        
        for label, value in dev_stats.items():
            if isinstance(value, float):
                st.metric(label, f"{value:.1f}")
            else:
                st.metric(label, f"{value:,}")

def display_insights_and_recommendations():
    """洞察と推奨事項の表示"""
    st.markdown("## 💡 市場洞察と推奨事項")
    
    # 洞察ボックス
    insights = [
        {
            "title": "🎯 市場構造",
            "content": "インディーゲームがSteam市場の主要セグメントを形成。多様な開発者による活発な競争市場。"
        },
        {
            "title": "💰 価格戦略",
            "content": "低価格戦略が主流だが、品質による差別化で高価格帯も成功可能。$5-15の価格帯が最も競争激化。"
        },
        {
            "title": "🖥️ プラットフォーム戦略", 
            "content": "Windows対応は必須。Mac/Linux対応により差別化可能。マルチプラットフォーム対応が競争優位。"
        },
        {
            "title": "🎮 ジャンル動向",
            "content": "特定ジャンルの独占はなく、ニッチ分野での専門化が有効。新規参入の余地あり。"
        }
    ]
    
    for insight in insights:
        with st.container():
            st.markdown(f"""
            <div class="insight-box">
                <h4>{insight['title']}</h4>
                <p>{insight['content']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 推奨事項
    st.markdown("### 🚀 新規参入者への推奨事項")
    
    recommendations = [
        "**価格設定**: $5-15の価格帯での競争力確保",
        "**プラットフォーム**: Windows必須、Mac/Linux対応で差別化",
        "**ジャンル選択**: ニッチジャンルでの専門化による競争回避",
        "**品質重視**: ユーザーレビューと評価の重要性",
        "**コミュニティ**: 開発段階からのコミュニティ構築"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        st.markdown(f"{i}. {rec}")

def main():
    """メインアプリケーション"""
    
    # サイドバー
    st.sidebar.title("🎮 Steam Analytics")
    st.sidebar.markdown("---")
    
    # データ読み込み状況
    with st.sidebar:
        with st.spinner("データを読み込み中..."):
            df = load_data()
    
    if df is None:
        st.error("データの読み込みに失敗しました。データベース接続を確認してください。")
        return
    
    st.sidebar.success(f"✅ {len(df):,}件のゲームデータを読み込み")
    
    # 分析オプション
    st.sidebar.markdown("### 📊 分析オプション")
    
    # フィルタリングオプション
    show_only_indie = st.sidebar.checkbox("インディーゲームのみ表示", value=True)
    
    if show_only_indie:
        df = df[df['is_indie'] == True]
        st.sidebar.info(f"フィルタ後: {len(df):,}件")
    
    # 価格範囲フィルタ
    price_range = st.sidebar.slider(
        "価格範囲 ($)",
        min_value=0.0,
        max_value=float(df['price_usd'].max()),
        value=(0.0, 50.0),
        step=1.0
    )
    
    df = df[(df['price_usd'] >= price_range[0]) & (df['price_usd'] <= price_range[1])]
    
    # メインコンテンツ
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 分析セクション")
    
    sections = {
        "市場概要": "overview",
        "ジャンル分析": "genre", 
        "価格分析": "price",
        "プラットフォーム分析": "platform",
        "開発者分析": "developer",
        "洞察・推奨事項": "insights"
    }
    
    selected_section = st.sidebar.radio("表示する分析:", list(sections.keys()))
    
    # セクション表示
    if selected_section == "市場概要":
        display_market_overview(df)
    elif selected_section == "ジャンル分析":
        display_genre_analysis(df)
    elif selected_section == "価格分析":
        display_price_analysis(df)
    elif selected_section == "プラットフォーム分析":
        display_platform_analysis(df)
    elif selected_section == "開発者分析":
        display_developer_analysis(df)
    elif selected_section == "洞察・推奨事項":
        display_insights_and_recommendations()
    
    # フッター
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 情報")
    st.sidebar.info(
        f"**更新日**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\\n"
        f"**データ件数**: {len(df):,}件\\n"
        f"**分析期間**: Steam APIデータ"
    )
    
    # データ品質情報
    with st.sidebar.expander("データ品質情報"):
        st.write(f"- 総ゲーム数: {len(df):,}")
        st.write(f"- 価格データあり: {len(df[df['price_usd'] > 0]):,}")
        st.write(f"- ジャンルデータあり: {len(df[df['genres'].notna()]):,}")
        st.write(f"- 開発者データあり: {len(df[df['developers'].notna()]):,}")

if __name__ == "__main__":
    main()