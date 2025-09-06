"""
Steam Indie Analytics - スタンドアロン版ダッシュボード
無料デプロイ用（外部データベース不要）

機能:
- JSONファイルからのデータ読み込み
- インタラクティブな可視化
- 市場分析レポート表示
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Any

# ページ設定
st.set_page_config(
    page_title="Steam Indie Analytics - ポートフォリオ版",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Steam Indie Analytics Dashboard - データエンジニア転職ポートフォリオ"
    }
)

# スタイル設定
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    text-align: center;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, #1f77b4, #ff7f0e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e1e8ed;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin: 0.5rem 0;
}

.portfolio-note {
    background: #f0f8ff;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #1f77b4;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data() -> Optional[pd.DataFrame]:
    """JSONデータを読み込んでDataFrameに変換"""
    try:
        data_file = "data.json"
        if not os.path.exists(data_file):
            st.error(f"データファイル '{data_file}' が見つかりません")
            return None
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            st.warning("データファイルが空です")
            return None
        
        # DataFrameに変換
        df = pd.DataFrame(data)
        
        # データ型変換
        numeric_columns = ['price', 'positive_reviews', 'negative_reviews', 'estimated_owners', 'peak_ccu']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 日付変換
        if 'release_date' in df.columns:
            df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
        
        # 計算カラム
        df['total_reviews'] = df.get('positive_reviews', 0) + df.get('negative_reviews', 0)
        df['review_score'] = df.get('positive_reviews', 0) / (df['total_reviews'] + 1) * 100
        
        return df
        
    except Exception as e:
        st.error(f"データ読み込みエラー: {str(e)}")
        return None

def create_overview_metrics(df: pd.DataFrame) -> None:
    """概要メトリクス表示"""
    st.markdown("### 📊 データ概要")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_games = len(df)
        st.metric("総ゲーム数", f"{total_games:,}", help="収集したインディーゲームの総数")
    
    with col2:
        avg_price = df['price'].mean() if 'price' in df.columns else 0
        st.metric("平均価格", f"${avg_price:.2f}", help="インディーゲームの平均価格")
    
    with col3:
        total_reviews = df['total_reviews'].sum() if 'total_reviews' in df.columns else 0
        st.metric("総レビュー数", f"{total_reviews:,}", help="全ゲームの累計レビュー数")
    
    with col4:
        avg_score = df['review_score'].mean() if 'review_score' in df.columns else 0
        st.metric("平均評価", f"{avg_score:.1f}%", help="レビュー平均評価（肯定的レビューの割合）")

def create_price_analysis(df: pd.DataFrame) -> None:
    """価格分析"""
    st.markdown("### 💰 価格分析")
    
    if 'price' in df.columns:
        # 価格帯分布
        col1, col2 = st.columns(2)
        
        with col1:
            price_data = df[df['price'] > 0]['price']
            fig = px.histogram(
                price_data, 
                x='price',
                title="価格帯分布",
                labels={'price': '価格 ($)', 'count': 'ゲーム数'},
                nbins=20
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 価格帯別ボックスプロット
            df_price = df[df['price'] > 0].copy()
            df_price['price_range'] = pd.cut(
                df_price['price'], 
                bins=[0, 5, 10, 20, 50, 100], 
                labels=['$0-5', '$5-10', '$10-20', '$20-50', '$50+']
            )
            
            if 'review_score' in df.columns:
                fig = px.box(
                    df_price, 
                    x='price_range', 
                    y='review_score',
                    title="価格帯別評価スコア",
                    labels={'price_range': '価格帯', 'review_score': '評価スコア (%)'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

def create_genre_analysis(df: pd.DataFrame) -> None:
    """ジャンル分析"""
    st.markdown("### 🎯 ジャンル・タグ分析")
    
    if 'genres' in df.columns:
        # ジャンル別ゲーム数
        genre_counts = {}
        for genres in df['genres'].dropna():
            if isinstance(genres, list):
                for genre in genres:
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        if genre_counts:
            genre_df = pd.DataFrame(
                list(genre_counts.items()), 
                columns=['Genre', 'Count']
            ).sort_values('Count', ascending=False).head(10)
            
            fig = px.bar(
                genre_df, 
                x='Count', 
                y='Genre',
                orientation='h',
                title="人気ジャンル Top10",
                labels={'Count': 'ゲーム数', 'Genre': 'ジャンル'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

def create_review_analysis(df: pd.DataFrame) -> None:
    """レビュー分析"""
    st.markdown("### ⭐ レビュー分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'review_score' in df.columns:
            # 評価スコア分布
            fig = px.histogram(
                df[df['review_score'] > 0], 
                x='review_score',
                title="評価スコア分布",
                labels={'review_score': '評価スコア (%)', 'count': 'ゲーム数'},
                nbins=20
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'total_reviews' in df.columns:
            # レビュー数分布（対数スケール）
            review_data = df[df['total_reviews'] > 0]['total_reviews']
            fig = px.histogram(
                review_data, 
                title="レビュー数分布",
                labels={'value': 'レビュー数', 'count': 'ゲーム数'},
                log_x=True,
                nbins=20
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

def create_success_analysis(df: pd.DataFrame) -> None:
    """成功要因分析"""
    st.markdown("### 🏆 成功要因分析")
    
    # 高評価ゲームの特徴
    if 'review_score' in df.columns and 'total_reviews' in df.columns:
        # 成功ゲーム定義: 評価85%以上 & レビュー100以上
        success_games = df[
            (df['review_score'] >= 85) & 
            (df['total_reviews'] >= 100)
        ]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 成功ゲームの定義")
            st.markdown("""
            - 評価スコア: 85%以上
            - レビュー数: 100以上
            """)
            
            success_count = len(success_games)
            success_rate = (success_count / len(df)) * 100
            
            st.metric("成功ゲーム数", success_count)
            st.metric("成功率", f"{success_rate:.1f}%")
        
        with col2:
            if len(success_games) > 0 and 'price' in df.columns:
                # 成功ゲームの価格分布
                fig = px.histogram(
                    success_games[success_games['price'] > 0], 
                    x='price',
                    title="成功ゲームの価格分布",
                    labels={'price': '価格 ($)', 'count': 'ゲーム数'},
                    nbins=10
                )
                st.plotly_chart(fig, use_container_width=True)

def create_top_games_table(df: pd.DataFrame) -> None:
    """トップゲーム一覧"""
    st.markdown("### 🥇 トップゲーム一覧")
    
    # ソート条件選択
    sort_options = {
        "評価スコア": "review_score",
        "レビュー数": "total_reviews",
        "価格": "price"
    }
    
    sort_by = st.selectbox("ソート条件", list(sort_options.keys()))
    sort_column = sort_options[sort_by]
    
    if sort_column in df.columns:
        display_df = df.nlargest(20, sort_column)[
            ['name', 'review_score', 'total_reviews', 'price', 'release_date']
        ].copy()
        
        # 表示用フォーマット
        if 'review_score' in display_df.columns:
            display_df['review_score'] = display_df['review_score'].round(1)
        if 'price' in display_df.columns:
            display_df['price'] = display_df['price'].round(2)
        
        # カラム名を日本語化
        display_df.columns = ['ゲーム名', '評価スコア(%)', 'レビュー数', '価格($)', 'リリース日']
        
        st.dataframe(display_df, use_container_width=True, height=400)

def main():
    """メイン処理"""
    # ヘッダー
    st.markdown('<div class="main-header">🎮 Steam Indie Analytics</div>', unsafe_allow_html=True)
    
    # ポートフォリオ説明
    st.markdown("""
    <div class="portfolio-note">
    <h4>📋 ポートフォリオについて</h4>
    <p>このダッシュボードは、Steam APIを活用したインディーゲーム市場分析のデモンストレーションです。
    データエンジニア転職用ポートフォリオとして、データ収集・分析・可視化の一連の流れを実装しています。</p>
    <ul>
        <li><strong>データ源:</strong> Steam Web API (2024年6月時点のスナップショット)</li>
        <li><strong>技術スタック:</strong> Python, Streamlit, Plotly, Pandas</li>
        <li><strong>分析範囲:</strong> インディーゲーム825タイトル</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # データ読み込み
    df = load_data()
    
    if df is None:
        st.error("データの読み込みに失敗しました")
        return
    
    # データ情報表示
    with st.expander("📈 データ情報", expanded=False):
        st.write(f"**データ形状:** {df.shape[0]} 行 × {df.shape[1]} 列")
        st.write(f"**データ期間:** {df['release_date'].min()} ～ {df['release_date'].max()}")
        st.write("**主要カラム:**", list(df.columns))
    
    # サイドバーフィルタ
    with st.sidebar:
        st.markdown("### 🔍 フィルタ")
        
        # 価格範囲フィルタ
        if 'price' in df.columns:
            price_range = st.slider(
                "価格範囲 ($)",
                min_value=0.0,
                max_value=float(df['price'].max()),
                value=(0.0, float(df['price'].max())),
                step=1.0
            )
            df = df[(df['price'] >= price_range[0]) & (df['price'] <= price_range[1])]
        
        # リリース年フィルタ
        if 'release_date' in df.columns:
            df['release_year'] = df['release_date'].dt.year
            years = sorted(df['release_year'].dropna().unique())
            if len(years) > 1:
                year_range = st.select_slider(
                    "リリース年",
                    options=years,
                    value=(min(years), max(years))
                )
                df = df[
                    (df['release_year'] >= year_range[0]) & 
                    (df['release_year'] <= year_range[1])
                ]
        
        st.markdown(f"**フィルタ後:** {len(df):,} ゲーム")
    
    # メイン分析表示
    create_overview_metrics(df)
    
    st.markdown("---")
    
    # タブ形式で分析結果表示
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 価格分析", 
        "🎯 ジャンル分析", 
        "⭐ レビュー分析", 
        "🏆 成功要因分析",
        "🥇 トップゲーム"
    ])
    
    with tab1:
        create_price_analysis(df)
    
    with tab2:
        create_genre_analysis(df)
    
    with tab3:
        create_review_analysis(df)
    
    with tab4:
        create_success_analysis(df)
    
    with tab5:
        create_top_games_table(df)
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>🔗 <strong>技術詳細:</strong> 
        <a href="https://github.com/your-username/steam-indie-analytics" target="_blank">GitHub Repository</a> | 
        <a href="https://linkedin.com/in/your-profile" target="_blank">LinkedIn Profile</a>
        </p>
        <p>📧 データエンジニア転職ポートフォリオ - 2024年製作</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()