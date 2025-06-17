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
from src.analyzers.data_quality_checker import DataQualityChecker

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

def display_success_analysis(df):
    """成功要因分析の表示"""
    st.markdown("## 🎯 成功要因分析")
    
    # レビューデータがあるゲームをフィルタ
    reviewed_df = df[(df['positive_reviews'] > 0) | (df['negative_reviews'] > 0)].copy()
    
    if len(reviewed_df) == 0:
        st.warning("⚠️ レビューデータがあるゲームが見つかりません。")
        return
    
    # 成功指標の計算
    reviewed_df['total_reviews'] = reviewed_df['positive_reviews'] + reviewed_df['negative_reviews']
    reviewed_df['rating'] = reviewed_df['positive_reviews'] / reviewed_df['total_reviews']
    
    # 成功ティアの定義
    def classify_success(row):
        if row['positive_reviews'] >= 100 and row['rating'] >= 0.8:
            return 'Highly Successful'
        elif row['positive_reviews'] >= 50 and row['rating'] >= 0.75:
            return 'Successful'
        elif row['positive_reviews'] >= 20 and row['rating'] >= 0.7:
            return 'Moderately Successful'
        else:
            return 'Below Average'
    
    reviewed_df['success_tier'] = reviewed_df.apply(classify_success, axis=1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 成功ティア分布")
        success_dist = reviewed_df['success_tier'].value_counts()
        st.bar_chart(success_dist)
    
    with col2:
        st.markdown("### 💰 成功ティア別平均価格")
        success_price = reviewed_df.groupby('success_tier')['price_usd'].mean().round(2)
        st.bar_chart(success_price)
    
    # 成功要因の詳細分析
    st.markdown("### 🔍 価格帯別成功率")
    
    # 価格帯の定義
    def price_tier(price):
        if price == 0:
            return 'Free'
        elif price <= 5:
            return '$0-$5'
        elif price <= 15:
            return '$5-$15'
        elif price <= 30:
            return '$15-$30'
        else:
            return '$30+'
    
    reviewed_df['price_tier'] = reviewed_df['price_usd'].apply(price_tier)
    
    # 価格帯別成功率
    price_success = reviewed_df.groupby('price_tier').agg({
        'success_tier': lambda x: (x.isin(['Highly Successful', 'Successful'])).mean() * 100,
        'app_id': 'count',
        'rating': 'mean',
        'price_usd': 'mean'
    }).round(2)
    
    price_success.columns = ['成功率%', 'ゲーム数', '平均評価', '平均価格']
    st.dataframe(price_success, use_container_width=True)
    
    # 成功ゲームの特徴
    st.markdown("### 🏆 高成功ゲームの特徴")
    
    successful_games = reviewed_df[reviewed_df['success_tier'].isin(['Highly Successful', 'Successful'])]
    
    if len(successful_games) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_price = successful_games['price_usd'].mean()
            st.metric("平均価格", f"${avg_price:.2f}")
        
        with col2:
            avg_rating = successful_games['rating'].mean()
            st.metric("平均評価率", f"{avg_rating:.1%}")
        
        with col3:
            avg_platforms = successful_games['platform_count'].mean()
            st.metric("平均対応プラットフォーム", f"{avg_platforms:.1f}")
        
        # トップ成功ゲーム
        st.markdown("### 🥇 トップパフォーマンスゲーム")
        top_games = successful_games.nlargest(10, 'positive_reviews')[
            ['name', 'positive_reviews', 'rating', 'price_usd', 'primary_genre']
        ].copy()
        top_games['rating'] = top_games['rating'].apply(lambda x: f"{x:.1%}")
        top_games['price_usd'] = top_games['price_usd'].apply(lambda x: f"${x:.2f}")
        top_games.columns = ['ゲーム名', 'ポジティブレビュー', '評価率', '価格', 'ジャンル']
        
        st.dataframe(top_games, use_container_width=True)
    else:
        st.info("成功ゲームのデータが不足しています。")

def display_quality_analysis():
    """データ品質分析の表示"""
    st.markdown("## 📊 データ品質分析")
    
    try:
        # データ品質チェッカーのインスタンス化
        quality_checker = DataQualityChecker()
        
        with st.spinner("データ品質をチェック中..."):
            quality_result = quality_checker.check_basic_quality_sync()
        
        if quality_result:
            # 品質スコア表示
            quality_score = quality_result.get('quality_score', 0)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "データ品質スコア", 
                    f"{quality_score}%",
                    delta=None
                )
            
            with col2:
                metrics = quality_result.get('quality_metrics', {})
                total_games = metrics.get('total_games', 0)
                st.metric("総データ件数", f"{total_games:,}")
            
            with col3:
                missing_names = metrics.get('missing_names', 0)
                completeness = ((total_games - missing_names) / total_games * 100) if total_games > 0 else 0
                st.metric("データ完全性", f"{completeness:.1f}%")
            
            # 品質評価
            st.markdown("### 📈 品質評価")
            
            if quality_score >= 90:
                st.success("🟢 **優秀**: データ品質は非常に高く、分析に適しています。")
            elif quality_score >= 75:
                st.info("🟡 **良好**: データ品質は良好ですが、一部改善の余地があります。")
            elif quality_score >= 60:
                st.warning("🟠 **注意**: データ品質に問題があり、クリーニングが推奨されます。")
            else:
                st.error("🔴 **改善必要**: データ品質が低く、大幅な改善が必要です。")
            
            # 詳細メトリクス
            st.markdown("### 🔍 詳細品質メトリクス")
            
            quality_details = {
                "指標": ["総ゲーム数", "ゲーム名欠損", "ジャンル欠損", "価格データ欠損"],
                "値": [
                    f"{metrics.get('total_games', 0):,}",
                    f"{metrics.get('missing_names', 0):,}",
                    f"{metrics.get('missing_genres', 0):,}",
                    f"{metrics.get('missing_prices', 0):,}"
                ],
                "完全性%": [
                    "100.0%",
                    f"{(1 - metrics.get('missing_names', 0) / max(total_games, 1)) * 100:.1f}%",
                    f"{(1 - metrics.get('missing_genres', 0) / max(total_games, 1)) * 100:.1f}%",
                    f"{(1 - metrics.get('missing_prices', 0) / max(total_games, 1)) * 100:.1f}%"
                ]
            }
            
            quality_df = pd.DataFrame(quality_details)
            st.dataframe(quality_df, use_container_width=True)
            
            # 改善提案
            st.markdown("### 💡 品質改善提案")
            
            recommendations = [
                "✅ 定期的なデータ品質モニタリングの実施",
                "🔧 欠損データの自動補完機能の導入",
                "⚡ リアルタイムデータ検証の強化",
                "📊 品質メトリクスダッシュボードの設置",
                "🚨 異常データアラート機能の実装"
            ]
            
            for rec in recommendations:
                st.markdown(f"- {rec}")
        
        else:
            st.error("データ品質チェックに失敗しました。")
            
    except Exception as e:
        st.error(f"データ品質分析でエラーが発生しました: {e}")
        st.info("データベース接続を確認してください。")

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
        "成功要因分析": "success",
        "データ品質": "quality",
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
    elif selected_section == "成功要因分析":
        display_success_analysis(df)
    elif selected_section == "データ品質":
        display_quality_analysis()
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