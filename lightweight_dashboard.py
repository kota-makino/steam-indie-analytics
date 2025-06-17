#!/usr/bin/env python3
"""
軽量化されたSteamインディーゲーム市場分析ダッシュボード
Dev Container環境で確実に動作するバージョン
"""

import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# 環境変数読み込み
load_dotenv()

# ページ設定（シンプル版）
st.set_page_config(
    page_title="Steam インディーゲーム市場分析",
    page_icon="🎮",
    layout="wide"
)

@st.cache_data(ttl=300)  # 5分キャッシュ
def load_game_data():
    """データベースからゲームデータを読み込み"""
    
    try:
        # データベース接続設定
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
        
        engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
        # 基本クエリ
        query = text("""
            SELECT 
                app_id,
                name,
                type,
                is_free,
                developers,
                publishers,
                price_final,
                genres,
                categories,
                positive_reviews,
                negative_reviews,
                total_reviews,
                platforms_windows,
                platforms_mac,
                platforms_linux
            FROM games
            WHERE type = 'game'
            ORDER BY created_at DESC
            LIMIT 1000;
        """)
        
        df = pd.read_sql_query(query, engine)
        
        # 基本的な前処理
        df['price_usd'] = df['price_final'] / 100
        df.loc[df['is_free'] == True, 'price_usd'] = 0
        
        # インディーゲーム判定（簡易版）
        df['is_indie'] = df['genres'].apply(
            lambda x: bool(x and any('Indie' in str(genre) for genre in x if genre))
        )
        
        # プラットフォーム数
        df['platform_count'] = (
            df['platforms_windows'].astype(int) + 
            df['platforms_mac'].astype(int) + 
            df['platforms_linux'].astype(int)
        )
        
        # ジャンル処理
        df['primary_genre'] = df['genres'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Other'
        )
        
        # 価格カテゴリ
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

def main():
    """メインアプリケーション"""
    
    # ヘッダー
    st.title("🎮 Steam インディーゲーム市場分析")
    st.write("**データ駆動型の市場洞察ダッシュボード**")
    
    # データ読み込み
    with st.spinner("データを読み込み中..."):
        df = load_game_data()
    
    if df is None:
        st.error("データの読み込みに失敗しました。")
        return
    
    # サイドバー
    st.sidebar.title("📊 分析オプション")
    
    # フィルター
    show_indie_only = st.sidebar.checkbox("インディーゲームのみ表示", value=True)
    
    if show_indie_only:
        df_filtered = df[df['is_indie'] == True]
        st.sidebar.success(f"✅ {len(df_filtered):,}件のインディーゲーム")
    else:
        df_filtered = df
        st.sidebar.info(f"📊 {len(df_filtered):,}件の全ゲーム")
    
    # 価格フィルター
    max_price = float(df_filtered['price_usd'].max()) if len(df_filtered) > 0 else 100.0
    price_range = st.sidebar.slider(
        "価格範囲 ($)",
        0.0, max_price, (0.0, min(50.0, max_price)),
        step=1.0
    )
    
    df_filtered = df_filtered[
        (df_filtered['price_usd'] >= price_range[0]) & 
        (df_filtered['price_usd'] <= price_range[1])
    ]
    
    # メイン統計
    st.header("📊 市場概要")
    
    if len(df_filtered) > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("ゲーム数", f"{len(df_filtered):,}")
        
        with col2:
            indie_count = len(df_filtered[df_filtered['is_indie'] == True])
            indie_ratio = indie_count / len(df_filtered) * 100 if len(df_filtered) > 0 else 0
            st.metric("インディー比率", f"{indie_ratio:.1f}%")
        
        with col3:
            paid_games = df_filtered[df_filtered['price_usd'] > 0]
            avg_price = paid_games['price_usd'].mean() if len(paid_games) > 0 else 0
            st.metric("平均価格", f"${avg_price:.2f}")
        
        with col4:
            avg_platforms = df_filtered['platform_count'].mean()
            st.metric("平均対応プラットフォーム", f"{avg_platforms:.1f}")
        
        # ジャンル分析
        st.header("🎮 ジャンル分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("人気ジャンル TOP 10")
            genre_counts = df_filtered['primary_genre'].value_counts().head(10)
            if len(genre_counts) > 0:
                st.bar_chart(genre_counts)
            else:
                st.info("データがありません")
        
        with col2:
            st.subheader("ジャンル別統計")
            if len(df_filtered) > 0:
                genre_stats = df_filtered.groupby('primary_genre').agg({
                    'app_id': 'count',
                    'price_usd': 'mean',
                    'platform_count': 'mean'
                }).round(2)
                
                genre_stats.columns = ['ゲーム数', '平均価格', '平均プラットフォーム数']
                genre_stats = genre_stats.sort_values('ゲーム数', ascending=False).head(10)
                
                st.dataframe(genre_stats, use_container_width=True)
        
        # 価格分析
        st.header("💰 価格分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("価格帯分布")
            price_dist = df_filtered['price_category'].value_counts()
            if len(price_dist) > 0:
                st.bar_chart(price_dist)
        
        with col2:
            st.subheader("価格統計")
            paid_df = df_filtered[df_filtered['price_usd'] > 0]
            if len(paid_df) > 0:
                price_stats = {
                    '平均価格': f"${paid_df['price_usd'].mean():.2f}",
                    '中央値': f"${paid_df['price_usd'].median():.2f}",
                    '最高価格': f"${paid_df['price_usd'].max():.2f}",
                    '最低価格': f"${paid_df['price_usd'].min():.2f}"
                }
                
                for label, value in price_stats.items():
                    st.write(f"**{label}**: {value}")
        
        # プラットフォーム分析
        st.header("🖥️ プラットフォーム分析")
        
        platform_stats = {
            'Windows': df_filtered['platforms_windows'].mean() * 100,
            'Mac': df_filtered['platforms_mac'].mean() * 100,
            'Linux': df_filtered['platforms_linux'].mean() * 100
        }
        
        platform_df = pd.DataFrame.from_dict(platform_stats, orient='index', columns=['対応率%'])
        st.bar_chart(platform_df)
        
        # 洞察
        st.header("💡 市場洞察")
        
        insights = []
        
        if indie_ratio > 50:
            insights.append(f"🎯 **市場構造**: インディーゲームが市場の主要セグメント ({indie_ratio:.1f}%)")
        
        if avg_price < 10:
            insights.append(f"💰 **価格戦略**: 低価格戦略が主流 (平均${avg_price:.2f})")
        
        if platform_stats['Windows'] > 90:
            insights.append("🖥️ **プラットフォーム**: Windows対応が必須")
        
        insights.append("📈 **成長機会**: ニッチジャンルでの専門化とマルチプラットフォーム対応")
        
        for insight in insights:
            st.write(insight)
    
    else:
        st.warning("選択した条件に合うゲームが見つかりませんでした。")
    
    # フッター
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 情報")
    st.sidebar.info(f"**更新**: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()