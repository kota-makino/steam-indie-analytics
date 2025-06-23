"""
Steam インディーゲーム市場分析ダッシュボード

Streamlitを使用したインタラクティブなデータ可視化ダッシュボード
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

# パス設定 (Streamlit Cloud対応)
import os
import sys
from pathlib import Path

# プロジェクトルートを動的に取得
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Streamlit Cloud環境検出
IS_STREAMLIT_CLOUD = (
    os.getenv('STREAMLIT_SHARING') == 'true' or 
    'streamlit.io' in os.getenv('HOSTNAME', '') or
    '/mount/src/' in str(current_dir)
)

# 分析モジュールのインポート (エラーハンドリング付き)
try:
    from src.analyzers.market_analyzer import MarketAnalyzer
    from src.analyzers.success_analyzer import SuccessAnalyzer  
    from src.analyzers.data_quality_checker import DataQualityChecker
    ANALYZERS_AVAILABLE = True
except ImportError as e:
    st.error(f"分析モジュールのインポートエラー: {e}")
    ANALYZERS_AVAILABLE = False

# AI洞察生成モジュール
AI_INSIGHTS_AVAILABLE = False
try:
    if ANALYZERS_AVAILABLE:
        from src.analyzers.ai_insights_generator import AIInsightsGenerator
        
        # APIキー確認
        if IS_STREAMLIT_CLOUD:
            api_key = st.secrets.get("api_keys", {}).get("gemini_api_key")
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
    """Streamlit Cloud用デモデータ生成"""
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

# キャッシング設定（キャッシュ無効化）
def get_cached_data():
    """データ取得（キャッシュなし）"""
    return load_data()


@st.cache_data(ttl=600)
def get_market_analysis():
    """キャッシュされた市場分析"""
    if not ANALYZERS_AVAILABLE:
        return {}
    try:
        analyzer = MarketAnalyzer()
        analyzer.load_data()
        return analyzer.get_market_overview()
    except:
        return {}


@st.cache_data(ttl=600)
def get_success_analysis():
    """キャッシュされた成功要因分析"""
    try:
        analyzer = SuccessAnalyzer()
        analyzer.load_data()
        return analyzer.create_success_analysis_report()
    except:
        return ""


# カスタムCSS
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)



@st.cache_data(ttl=60)  # 1分でキャッシュ期限切れ
def load_data():
    """データの読み込み（キャッシュ機能付き）- Streamlit Cloud対応"""
    
    # Streamlit Cloud環境でのデモデータ読み込み
    if IS_STREAMLIT_CLOUD:
        try:
            # Streamlit Secrets からデータベース設定取得
            if 'database' in st.secrets:
                db_config = {
                    "host": st.secrets["database"]["host"],
                    "port": int(st.secrets["database"]["port"]),
                    "database": st.secrets["database"]["database"],
                    "user": st.secrets["database"]["username"],
                    "password": st.secrets["database"]["password"],
                }
            else:
                # デモデータ使用
                st.warning("🌟 デモモード: サンプルデータを表示しています")
                return load_demo_data()
        except Exception:
            st.warning("🌟 デモモード: サンプルデータを表示しています")
            return load_demo_data()
    else:
        # ローカル環境設定
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
    
    try:

        # SQLAlchemy エンジン作成（タイムアウト設定付き）
        engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}",
            connect_args={
                "connect_timeout": 10,  # 接続タイムアウト10秒
                "application_name": "streamlit_dashboard",
            },
            pool_timeout=20,  # プール取得タイムアウト20秒
            pool_recycle=3600,  # 1時間でコネクション再利用
        )

        # インディーゲームのみを取得（プロジェクトの焦点）
        query = """
        SELECT 
            app_id,
            name,
            type,
            is_free,
            short_description,
            price_final,
            price_usd,
            release_date,
            platforms_windows,
            platforms_mac,
            platforms_linux,
            platform_count,
            positive_reviews,
            negative_reviews,
            total_reviews,
            rating,
            is_indie,
            primary_genre,
            primary_developer,
            primary_publisher,
            price_category,
            created_at
        FROM game_analysis_view
        WHERE is_indie = true
        ORDER BY created_at DESC;
        """

        # データベース接続テスト
        from sqlalchemy import text

        with engine.connect() as conn:
            test_result = conn.execute(text("SELECT 1"))
            test_result.fetchone()

        # データ読み込み（正規化ビューから）
        df = pd.read_sql_query(query, engine)

        if len(df) == 0:
            st.warning("⚠️ データベースにゲームデータが見つかりません。")
            st.info(
                "💡 正規化されたデータベーススキーマが必要です。移行スクリプトを実行してください。"
            )
            return None

        # データ型の調整
        df["platforms_windows"] = df["platforms_windows"].astype(bool)
        df["platforms_mac"] = df["platforms_mac"].astype(bool)
        df["platforms_linux"] = df["platforms_linux"].astype(bool)
        df["is_free"] = df["is_free"].astype(bool)
        df["is_indie"] = df["is_indie"].astype(bool)

        # NULLの処理
        df["primary_genre"] = df["primary_genre"].fillna("Unknown")
        df["primary_developer"] = df["primary_developer"].fillna("Unknown")
        df["primary_publisher"] = df["primary_publisher"].fillna("Unknown")
        df["rating"] = df["rating"].fillna(0)

        # レビューデータのNULL処理
        df["positive_reviews"] = df["positive_reviews"].fillna(0).astype(int)
        df["negative_reviews"] = df["negative_reviews"].fillna(0).astype(int)
        df["total_reviews"] = df["total_reviews"].fillna(0).astype(int)

        return df

    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return None


def display_market_overview(df):
    """市場概要の表示"""
    st.markdown("## 🎮 Steam インディーゲーム市場概要")

    # 基本統計
    total_games = len(df)
    free_games = len(df[df["is_free"] == True])
    paid_games = len(df[df["is_free"] == False])

    # メトリクス表示
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="総インディーゲーム数", value=f"{total_games:,}", delta=None)

    with col2:
        st.metric(
            label="無料ゲーム",
            value=f"{free_games:,}",
            delta=f"{free_games/total_games*100:.1f}%",
        )

    with col3:
        avg_price = df[df["price_usd"] > 0]["price_usd"].mean()
        avg_price_jpy = (
            avg_price * 150 if not pd.isna(avg_price) else 0
        )  # 1USD = 150円で計算
        st.metric(
            label="平均価格",
            value=f"¥{avg_price_jpy:.0f}" if avg_price_jpy > 0 else "¥0",
            delta=None,
        )

    # 市場分析の詳細情報
    st.markdown("### 📊 市場分析")

    # ジャンル分布
    if len(df) > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🏷️ ジャンル分布")

            # 複数ジャンル対応でトップ10ジャンルを取得
            try:
                from sqlalchemy import create_engine, text

                engine = create_engine(
                    f"postgresql://{os.getenv('POSTGRES_USER', 'steam_user')}:{os.getenv('POSTGRES_PASSWORD', 'steam_password')}@"
                    f"{os.getenv('POSTGRES_HOST', 'postgres')}:{int(os.getenv('POSTGRES_PORT', 5432))}/{os.getenv('POSTGRES_DB', 'steam_analytics')}"
                )

                multi_genre_overview_query = """
                SELECT 
                    genre.name AS genre_name,
                    COUNT(DISTINCT g.app_id) AS count
                FROM games_normalized g
                INNER JOIN game_genres gg ON g.app_id = gg.game_id
                INNER JOIN genres genre ON gg.genre_id = genre.id
                WHERE g.is_indie = true AND genre.name != 'Indie'
                GROUP BY genre.name
                ORDER BY count DESC
                LIMIT 10
                """

                genre_df = pd.read_sql_query(multi_genre_overview_query, engine)

                if len(genre_df) > 0:
                    import plotly.express as px

                    fig_genre = px.bar(
                        x=genre_df["count"],
                        y=genre_df["genre_name"],
                        orientation="h",
                        title="トップ10ジャンル（複数ジャンル対応）",
                        labels={"x": "ゲーム数", "y": "ジャンル"},
                        color=genre_df["count"],
                        color_continuous_scale="Blues",
                    )
                    fig_genre.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_genre, use_container_width=True)

                    # 総計表示
                    total_multi = genre_df["count"].sum()
                    st.caption(f"総計: {total_multi:,}件（複数ジャンル重複あり）")
                else:
                    st.warning("ジャンルデータを取得できませんでした")

            except Exception as e:
                # フォールバック: primary_genre方式
                st.info("💡 単一ジャンル表示にフォールバック")
                genre_counts = (
                    df[df["primary_genre"] != "Indie"]["primary_genre"]
                    .value_counts()
                    .head(10)
                )

                import plotly.express as px

                fig_genre = px.bar(
                    x=genre_counts.values,
                    y=genre_counts.index,
                    orientation="h",
                    title="トップ10ジャンル",
                    labels={"x": "ゲーム数", "y": "ジャンル"},
                    color=genre_counts.values,
                    color_continuous_scale="Blues",
                )
                fig_genre.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_genre, use_container_width=True)

        with col2:
            st.markdown("#### 💰 価格カテゴリ分布")
            price_counts = df["price_category"].value_counts()

            # 価格順（安い順）で並び替えて表示
            price_order = [
                "無料",
                "低価格帯 (¥0-750)",
                "中価格帯 (¥750-2,250)",
                "高価格帯 (¥2,250-4,500)",
                "プレミアム (¥4,500+)",
            ]
            price_counts_sorted = price_counts.reindex(
                [cat for cat in price_order if cat in price_counts.index]
            ).dropna()

            if len(price_counts_sorted) > 0:
                # パーセント順に並び替え（高い順）
                price_counts_by_percent = price_counts_sorted.sort_values(
                    ascending=False
                )

                fig_price = px.pie(
                    values=price_counts_by_percent.values,
                    names=price_counts_by_percent.index,
                    title="価格帯別分布",
                )

                fig_price.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    direction="clockwise",
                    sort=False,
                    rotation=0,  # 0度（3時方向）からスタート
                    textfont_size=12,
                )
            else:
                # フォールバック：元の順序で表示
                fig_price = px.pie(
                    values=price_counts.values,
                    names=price_counts.index,
                    title="価格帯別分布",
                )
                fig_price.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    direction="clockwise",
                    sort=False,
                    rotation=0,
                )

            fig_price.update_layout(
                height=400,
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05
                ),
            )
            st.plotly_chart(fig_price, use_container_width=True)

            # 価格帯詳細を右側に表示（価格の安い順）
            st.markdown("**価格帯別詳細（安い順）:**")
            total_games = len(df)
            for category in price_order:
                if category in price_counts_sorted.index:
                    count = price_counts_sorted[category]
                    percentage = count / total_games * 100
                    st.caption(f"• {category}: {count}件 ({percentage:.1f}%)")

    # 市場インサイト
    st.markdown("### 💡 市場インサイト")

    col1, col2, col3 = st.columns(3)

    with col1:
        reviewed_games = df[df["total_reviews"] > 0]
        reviewed_ratio = (
            len(reviewed_games) / total_games * 100 if total_games > 0 else 0
        )
        avg_reviews = (
            reviewed_games["total_reviews"].mean() if len(reviewed_games) > 0 else 0
        )

        if reviewed_ratio > 70:
            st.success(f"📝 **活発な市場**: レビュー率{reviewed_ratio:.1f}%")
        elif reviewed_ratio > 50:
            st.info(f"📝 **標準的**: レビュー率{reviewed_ratio:.1f}%")
        else:
            st.warning(f"📝 **静かな市場**: レビュー率{reviewed_ratio:.1f}%")

        if len(reviewed_games) > 0:
            st.caption(f"平均レビュー数: {avg_reviews:,.0f}件")

    with col2:
        if avg_price and not pd.isna(avg_price):
            if avg_price < 10:
                st.success("💰 **低価格戦略**: 手頃な価格設定が主流です")
            elif avg_price < 20:
                st.info("💰 **中価格帯**: バランスの取れた価格設定です")
            else:
                st.warning("💰 **高価格帯**: プレミアム価格戦略が多いです")

    with col3:
        # 無料ゲーム判定：is_freeフラグのみ（価格カテゴリと一致させる）
        free_games = df[df["is_free"] == True]
        free_ratio = len(free_games) / total_games * 100 if total_games > 0 else 0

        if free_ratio > 20:
            st.info(f"🎁 **フリーゲーム**: 無料ゲーム{free_ratio:.1f}%")
        elif free_ratio > 10:
            st.success(f"🎁 **適度な無料**: 無料ゲーム{free_ratio:.1f}%")
        else:
            st.warning(f"🎁 **有料中心**: 無料ゲーム{free_ratio:.1f}%")

        st.caption(f"無料ゲーム: {len(free_games)}件")

    # AI洞察セクション
    if st.button("🤖 AI分析洞察を生成", key="market_ai_insight"):
        if AI_INSIGHTS_AVAILABLE:
            with st.spinner("AI分析中..."):
                try:
                    ai_generator = AIInsightsGenerator()
                    
                    # データサマリー作成
                    data_summary = {
                        'total_games': total_games,
                        'free_games': len(free_games),
                        'free_ratio': free_ratio,
                        'avg_price_jpy': avg_price_jpy if avg_price_jpy > 0 else 0,
                        'top_genres': df['primary_genre'].value_counts().head(3).index.tolist(),
                        'review_ratio': reviewed_ratio
                    }
                    
                    # AI洞察生成
                    insight = ai_generator.generate_market_overview_insight(data_summary)
                    
                    # 洞察表示
                    st.markdown("### 🤖 AI市場分析")
                    st.info(insight)
                    
                except Exception as e:
                    st.error(f"AI洞察生成エラー: {e}")
                    st.caption("💡 Gemini APIキーが設定されているか確認してください")
        else:
            # デモモード用AI洞察
            with st.spinner("デモAI分析中..."):
                time.sleep(1)  # リアルな体験のため
                st.markdown("### 🤖 AI市場分析 (デモ)")
                demo_insight = generate_demo_insights("", "market")
                st.info(demo_insight)
                st.caption("💡 実際の環境では、Gemini APIによる詳細な分析が提供されます")


def display_genre_analysis(df):
    """ジャンル分析の表示（複数ジャンル対応版）"""
    st.markdown("## 🎮 ジャンル別分析")
    st.info(
        "💡 **複数ジャンル対応**: 1つのゲームが複数ジャンルに分類される場合、各ジャンルでカウントされます"
    )

    indie_df = df  # 全てインディーゲーム

    # インタラクティブフィルター
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_games = st.slider("最小ゲーム数", 1, 50, 5)
    with col2:
        price_filter = st.selectbox("価格フィルター", ["全て", "有料のみ", "無料のみ"])
    with col3:
        top_n = st.slider("表示ジャンル数", 5, 20, 10)
    with col4:
        show_multi_genre = st.checkbox("複数ジャンル表示", value=False)

    # フィルタリング適用
    filtered_df = indie_df.copy()
    if price_filter == "有料のみ":
        filtered_df = filtered_df[filtered_df["is_free"] == False]
    elif price_filter == "無料のみ":
        filtered_df = filtered_df[filtered_df["is_free"] == True]

    # 複数ジャンル表示の処理
    multi_genre_df = None
    if show_multi_genre:
        # 複数ジャンルデータを取得（データベースから）
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(
                f"postgresql://{os.getenv('POSTGRES_USER', 'steam_user')}:{os.getenv('POSTGRES_PASSWORD', 'steam_password')}@"
                f"{os.getenv('POSTGRES_HOST', 'postgres')}:{int(os.getenv('POSTGRES_PORT', 5432))}/{os.getenv('POSTGRES_DB', 'steam_analytics')}"
            )

            # 各ゲームの全ジャンルを取得するクエリ
            multi_genre_query = """
            SELECT 
                g.app_id,
                g.name,
                g.price_final / 100.0 AS price_usd,
                g.positive_reviews,
                g.negative_reviews,
                g.total_reviews,
                string_agg(DISTINCT genre.name, ', ' ORDER BY genre.name) AS all_genres
            FROM games_normalized g
            INNER JOIN game_genres gg ON g.app_id = gg.game_id
            INNER JOIN genres genre ON gg.genre_id = genre.id
            WHERE g.is_indie = true AND genre.name != 'Indie'
            GROUP BY g.app_id, g.name, g.price_final, g.positive_reviews, g.negative_reviews, g.total_reviews
            HAVING COUNT(DISTINCT genre.id) > 1
            ORDER BY g.total_reviews DESC
            LIMIT 100
            """

            multi_genre_df = pd.read_sql_query(multi_genre_query, engine)

            if len(multi_genre_df) > 0:
                st.success(
                    f"✅ 複数ジャンルを持つゲーム: {len(multi_genre_df)}件を表示中"
                )

                # 複数ジャンルゲームの詳細表示
                st.markdown("#### 🎮 複数ジャンルゲーム一覧")

                # データフレーム表示用の調整
                display_multi_df = multi_genre_df[
                    ["name", "all_genres", "price_usd", "total_reviews"]
                ].copy()
                display_multi_df.columns = [
                    "ゲーム名",
                    "全ジャンル",
                    "価格($)",
                    "総レビュー数",
                ]
                display_multi_df["価格($)"] = display_multi_df["価格($)"].apply(
                    lambda x: f"${x:.2f}" if x > 0 else "Free"
                )

                st.dataframe(display_multi_df.head(20), use_container_width=True)

                # ジャンル組み合わせ分析
                st.markdown("#### 📊 人気ジャンル組み合わせ")
                genre_combos = multi_genre_df["all_genres"].value_counts().head(10)

                fig_combo = px.bar(
                    x=genre_combos.values,
                    y=genre_combos.index,
                    orientation="h",
                    title="人気のジャンル組み合わせ TOP10",
                    labels={"x": "ゲーム数", "y": "ジャンル組み合わせ"},
                )
                fig_combo.update_layout(height=400)
                st.plotly_chart(fig_combo, use_container_width=True)

                # 複数ジャンル表示の場合はここで処理終了
                return
            else:
                st.warning("複数ジャンルを持つゲームが見つかりませんでした。")

        except Exception as e:
            st.error(f"複数ジャンルデータの取得でエラーが発生しました: {e}")
            st.info("💡 単一ジャンル表示に切り替えて続行します。")

    # 正規化データベースから全ジャンル情報を取得
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(
            f"postgresql://{os.getenv('POSTGRES_USER', 'steam_user')}:{os.getenv('POSTGRES_PASSWORD', 'steam_password')}@"
            f"{os.getenv('POSTGRES_HOST', 'postgres')}:{int(os.getenv('POSTGRES_PORT', 5432))}/{os.getenv('POSTGRES_DB', 'steam_analytics')}"
        )

        # フィルター条件をSQLクエリに適用
        price_condition = ""
        if price_filter == "有料のみ":
            price_condition = "AND g.price_final > 0"
        elif price_filter == "無料のみ":
            price_condition = "AND g.price_final = 0"

        # 複数ジャンル対応のクエリ
        multi_genre_query = f"""
        SELECT 
            genre.name AS genre_name,
            COUNT(DISTINCT g.app_id) AS game_count,
            AVG(g.price_final / 100.0) FILTER (WHERE g.price_final > 0) AS avg_price_usd,
            AVG(g.platforms_windows::int + g.platforms_mac::int + g.platforms_linux::int) AS avg_platform_count,
            SUM(g.positive_reviews) AS total_positive,
            SUM(g.negative_reviews) AS total_negative,
            SUM(g.total_reviews) AS total_reviews,
            AVG(g.positive_reviews::float / NULLIF(g.total_reviews, 0)) FILTER (WHERE g.total_reviews > 0) AS avg_rating
        FROM games_normalized g
        INNER JOIN game_genres gg ON g.app_id = gg.game_id
        INNER JOIN genres genre ON gg.genre_id = genre.id
        WHERE g.is_indie = true 
        AND genre.name != 'Indie'
        {price_condition}
        GROUP BY genre.name
        HAVING COUNT(DISTINCT g.app_id) >= {min_games}
        ORDER BY COUNT(DISTINCT g.app_id) DESC
        LIMIT {top_n}
        """

        genre_stats_df = pd.read_sql_query(multi_genre_query, engine)

        if len(genre_stats_df) == 0:
            st.warning("フィルター条件に該当するジャンルデータがありません。")
            return

        # データフレームをインデックス化
        genre_stats = genre_stats_df.set_index("genre_name")

        # 列名を統一（既存コードとの互換性のため）
        genre_stats = genre_stats.rename(
            columns={
                "game_count": "app_id",
                "avg_price_usd": "price_usd",
                "avg_platform_count": "platform_count",
                "total_positive": "positive_reviews",
                "total_negative": "negative_reviews",
                "avg_rating": "rating",
            }
        )

        # NULLの処理
        genre_stats["price_usd"] = genre_stats["price_usd"].fillna(0)
        genre_stats["rating"] = genre_stats["rating"].fillna(0)

        st.success(f"✅ 複数ジャンル対応: {len(genre_stats)}ジャンルを分析中")

    except Exception as e:
        st.error(f"複数ジャンルデータ取得エラー: {e}")
        # フォールバック: 従来のprimary_genre方式
        st.info("💡 単一ジャンル表示にフォールバック")

        non_indie_df = filtered_df[filtered_df["primary_genre"] != "Indie"].copy()

        if len(non_indie_df) == 0:
            st.warning("Indie以外のジャンルデータがありません。")
            return

        genre_stats = (
            non_indie_df.groupby("primary_genre")
            .agg(
                {
                    "app_id": "count",
                    "price_usd": "mean",
                    "platform_count": "mean",
                    "positive_reviews": "sum",
                    "negative_reviews": "sum",
                }
            )
            .round(2)
        )

        # 最小ゲーム数でフィルター
        genre_stats = genre_stats[genre_stats["app_id"] >= min_games]
        genre_stats = genre_stats.sort_values("app_id", ascending=False).head(top_n)

        # レビュー評価率計算（ゼロ除算対策）
        genre_stats["total_reviews"] = (
            genre_stats["positive_reviews"] + genre_stats["negative_reviews"]
        )
        genre_stats["rating"] = genre_stats.apply(
            lambda row: (
                row["positive_reviews"] / row["total_reviews"]
                if row["total_reviews"] > 0
                else 0
            ),
            axis=1,
        )

    if len(genre_stats) == 0:
        st.warning("フィルター条件に該当するデータがありません。")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 ジャンル別ゲーム数（複数ジャンル対応）")

        # Plotlyの横棒グラフ
        fig_genre = px.bar(
            x=genre_stats["app_id"],
            y=genre_stats.index,
            orientation="h",
            title="ジャンル別ゲーム数",
            labels={"x": "ゲーム数", "y": "ジャンル"},
            color=genre_stats["price_usd"],
            color_continuous_scale="Viridis",
            text=genre_stats["app_id"],
        )
        fig_genre.update_traces(texttemplate="%{text}", textposition="outside")
        fig_genre.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_genre, use_container_width=True)

    with col2:
        st.markdown("### 📊 ジャンル別レビュー数分布")

        # 総レビュー数チャート
        fig_reviews = px.bar(
            x=genre_stats["total_reviews"],
            y=genre_stats.index,
            orientation="h",
            title="ジャンル別総レビュー数",
            labels={"x": "総レビュー数", "y": "ジャンル"},
            color=genre_stats["total_reviews"],
            color_continuous_scale="Viridis",
            text=genre_stats["total_reviews"],
        )
        fig_reviews.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_reviews.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_reviews, use_container_width=True)

    # 詳細データテーブル
    st.markdown("### 📋 詳細統計テーブル")

    display_stats = genre_stats[
        ["app_id", "price_usd", "platform_count", "rating", "total_reviews"]
    ].copy()
    display_stats.columns = [
        "ゲーム数",
        "平均価格(円)",
        "平均プラットフォーム数",
        "評価率",
        "総レビュー数",
    ]
    display_stats["評価率"] = display_stats["評価率"].apply(lambda x: f"{x:.1%}")
    display_stats["平均価格(円)"] = display_stats["平均価格(円)"].apply(
        lambda x: f"¥{x*150:.0f}"
    )
    display_stats["総レビュー数"] = display_stats["総レビュー数"].apply(
        lambda x: f"{x:,.0f}"
    )

    st.dataframe(display_stats, use_container_width=True)

    # ジャンル分析インサイト
    st.markdown("### 💡 ジャンル分析インサイト")

    top_genre = genre_stats.index[0]
    top_genre_count = genre_stats.iloc[0]["app_id"]
    highest_rated = genre_stats.loc[genre_stats["rating"].idxmax()]
    most_expensive = genre_stats.loc[genre_stats["price_usd"].idxmax()]
    most_reviewed = genre_stats.loc[genre_stats["total_reviews"].idxmax()]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info(f"🥇 **最人気ジャンル**\n{top_genre}\n({top_genre_count}件)")

    with col2:
        st.success(
            f"⭐ **最高評価ジャンル**\n{highest_rated.name}\n(評価率{highest_rated['rating']:.1%})"
        )

    with col3:
        st.error(
            f"📝 **最多レビュージャンル**\n{most_reviewed.name}\n({most_reviewed['total_reviews']:,.0f}件)"
        )

    with col4:
        avg_price_jpy = most_expensive["price_usd"] * 150
        st.warning(
            f"💎 **最高価格ジャンル**\n{most_expensive.name}\n(平均¥{avg_price_jpy:.0f})"
        )

    # AI洞察セクション
    if st.button("🤖 AIジャンル分析洞察を生成", key="genre_ai_insight"):
        if AI_INSIGHTS_AVAILABLE:
            with st.spinner("AI分析中..."):
                try:
                    ai_generator = AIInsightsGenerator()
                    
                    # ジャンル分析洞察生成
                    insight = ai_generator.generate_genre_analysis_insight(genre_stats)
                    
                    # 洞察表示
                    st.markdown("### 🤖 AIジャンル分析")
                    st.info(insight)
                    
                except Exception as e:
                    st.error(f"AI洞察生成エラー: {e}")
                    st.caption("💡 Gemini APIキーが設定されているか確認してください")
        else:
            # デモモード用AI洞察
            with st.spinner("デモAI分析中..."):
                time.sleep(1)
                st.markdown("### 🤖 AIジャンル分析 (デモ)")
                demo_insight = generate_demo_insights("", "genre")
                st.info(demo_insight)
                st.caption("💡 実際の環境では、Gemini APIによる詳細な分析が提供されます")


def display_price_analysis(df):
    """価格分析の表示（強化版）"""
    st.markdown("## 💰 価格戦略分析")

    indie_df = df  # 全てインディーゲーム
    
    # 価格帯分類関数（共通利用）
    def price_tier(price):
        if price == 0:
            return "無料"
        elif price <= 5:
            return "低価格帯 (¥0-750)"
        elif price <= 15:
            return "中価格帯 (¥750-2,250)"
        elif price <= 30:
            return "高価格帯 (¥2,250-4,500)"
        else:
            return "プレミアム (¥4,500+)"

    # インタラクティブフィルター
    col1, col2, col3 = st.columns(3)

    with col1:
        max_price_int = int(indie_df["price_usd"].max())
        price_range = st.slider(
            "価格範囲 (USD基準)", 0, max_price_int, (0, min(50, max_price_int))
        )
    with col2:
        # Indieジャンルを除外（既に全データがインディーゲームのため）
        available_genres = [genre for genre in indie_df["primary_genre"].unique()[:10] if genre != "Indie"]
        genre_filter = st.multiselect(
            "ジャンルフィルター", 
            options=available_genres,
            default=[],
            help="🎮 既に全データがインディーゲームです"
        )
    with col3:
        analysis_type = st.selectbox(
            "分析タイプ", ["価格分布", "価格vs評価", "競合比較"]
        )

    # フィルタリング適用（無料ゲームも考慮）
    price_condition = (
        (indie_df["price_usd"] >= price_range[0])
        & (indie_df["price_usd"] <= price_range[1])
    ) | (
        # 無料ゲームで価格範囲の最小値が0の場合は含める
        (price_range[0] == 0)
        & (indie_df["is_free"] == True)
    )

    filtered_df = indie_df[price_condition]

    if genre_filter:
        filtered_df = filtered_df[filtered_df["primary_genre"].isin(genre_filter)]

    if len(filtered_df) == 0:
        st.warning("フィルター条件に該当するデータがありません。")
        return

    if analysis_type == "価格分布":
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📊 価格分布（インタラクティブヒストグラム）")

            # Plotlyヒストグラム（価格を日本円に変換）
            filtered_df_hist = filtered_df.copy()
            filtered_df_hist["price_jpy"] = filtered_df_hist["price_usd"] * 150

            fig_hist = px.histogram(
                filtered_df_hist,
                x="price_jpy",
                nbins=20,
                title="価格分布",
                labels={"price_jpy": "価格 (円)", "count": "ゲーム数"},
                color_discrete_sequence=["#1f77b4"],
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)

        with col2:
            st.markdown("### 🥧 価格帯別割合")

            filtered_df_copy = filtered_df.copy()
            filtered_df_copy["price_tier"] = filtered_df_copy["price_usd"].apply(
                price_tier
            )
            price_dist = filtered_df_copy["price_tier"].value_counts()

            # 価格順（安い順）で並び替えて表示
            price_tier_order = [
                "無料",
                "低価格帯 (¥0-750)",
                "中価格帯 (¥750-2,250)",
                "高価格帯 (¥2,250-4,500)",
                "プレミアム (¥4,500+)",
            ]
            price_dist_sorted = price_dist.reindex(
                [tier for tier in price_tier_order if tier in price_dist.index]
            ).dropna()

            # Plotly円グラフ
            if len(price_dist_sorted) > 0:
                # パーセント順に並び替え（高い順）
                price_dist_by_percent = price_dist_sorted.sort_values(ascending=False)
                
                fig_pie = px.pie(
                    values=price_dist_by_percent.values,
                    names=price_dist_by_percent.index,
                    title="価格帯別分布",
                )
                
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent',
                    direction='clockwise',
                    sort=False,
                    rotation=0,  # 0度（3時方向）からスタート
                    textfont_size=12
                )
            else:
                # フォールバック：元の順序で表示
                fig_pie = px.pie(
                    values=price_dist.values,
                    names=price_dist.index,
                    title="価格帯別分布",
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent',
                    direction='clockwise',
                    sort=False,
                    rotation=0
                )
            
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

    elif analysis_type == "価格vs評価":
        st.markdown("### 📈 価格 vs 評価 相関分析")

        # レビューデータがあるゲームのみ
        reviewed_df = filtered_df[
            filtered_df["positive_reviews"] + filtered_df["negative_reviews"] > 0
        ].copy()

        if len(reviewed_df) > 0:
            # ゼロ除算対策付きの評価率計算
            reviewed_df["total_reviews_calc"] = (
                reviewed_df["positive_reviews"] + reviewed_df["negative_reviews"]
            )
            reviewed_df["rating"] = reviewed_df.apply(
                lambda row: (
                    row["positive_reviews"] / row["total_reviews_calc"]
                    if row["total_reviews_calc"] > 0
                    else 0
                ),
                axis=1,
            )
            reviewed_df["total_reviews"] = (
                reviewed_df["positive_reviews"] + reviewed_df["negative_reviews"]
            )

            col1, col2 = st.columns(2)

            with col1:
                # 散布図（価格を日本円に変換）
                reviewed_df_display = reviewed_df.copy()
                reviewed_df_display["price_jpy"] = (
                    reviewed_df_display["price_usd"] * 150
                )

                fig_scatter = px.scatter(
                    reviewed_df_display,
                    x="price_jpy",
                    y="rating",
                    size="total_reviews",
                    color="primary_genre",
                    hover_name="name",
                    hover_data={"positive_reviews": True, "negative_reviews": True},
                    title="価格 vs 評価率",
                    labels={
                        "price_jpy": "価格 (円)",
                        "rating": "評価率",
                        "total_reviews": "レビュー数",
                    },
                )
                fig_scatter.update_layout(height=500)
                st.plotly_chart(fig_scatter, use_container_width=True)

            with col2:
                # 価格帯別評価
                reviewed_df["price_tier"] = reviewed_df["price_usd"].apply(price_tier)
                price_rating = (
                    reviewed_df.groupby("price_tier")
                    .agg({"rating": "mean", "app_id": "count", "total_reviews": "mean"})
                    .round(3)
                )

                # 価格順でカテゴリを並び替え
                price_tier_order = [
                    "無料",
                    "低価格帯 (¥0-750)",
                    "中価格帯 (¥750-2,250)",
                    "高価格帯 (¥2,250-4,500)",
                    "プレミアム (¥4,500+)",
                ]
                reviewed_df["price_tier"] = pd.Categorical(
                    reviewed_df["price_tier"], categories=price_tier_order, ordered=True
                )

                fig_box = px.box(
                    reviewed_df,
                    x="price_tier",
                    y="rating",
                    title="価格帯別評価分布",
                    labels={"price_tier": "価格帯", "rating": "評価率"},
                )
                fig_box.update_layout(height=500)
                st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.warning("レビューデータがあるゲームが見つかりません。")

    elif analysis_type == "競合比較":
        st.markdown("### ⚔️ インディーゲーム価格帯別競合分析")

        # 価格帯別の競合分析（インディーゲーム内での比較）
        if len(filtered_df) > 0:
            # 価格帯の再計算（日本円）
            def price_tier(price):
                if price == 0:
                    return "無料"
                elif price <= 5:
                    return "低価格帯 (¥0-750)"
                elif price <= 15:
                    return "中価格帯 (¥750-2,250)"
                elif price <= 30:
                    return "高価格帯 (¥2,250-4,500)"
                else:
                    return "プレミアム (¥4,500+)"

            # 価格帯別の分析データ準備
            comparison_df_copy = filtered_df.copy()
            comparison_df_copy["price_tier"] = comparison_df_copy["price_usd"].apply(
                price_tier
            )

            # 価格帯別統計
            tier_stats = (
                comparison_df_copy.groupby("price_tier")
                .agg(
                    {
                        "app_id": "count",
                        "price_usd": ["mean", "median", "max", "min"],
                        "rating": "mean",
                        "total_reviews": "mean",
                    }
                )
                .round(2)
            )

            # 列名を平坦化
            tier_stats.columns = [
                "ゲーム数",
                "平均価格",
                "中央値価格",
                "最高価格",
                "最低価格",
                "平均評価",
                "平均レビュー数",
            ]

            # 価格順で並び替え
            price_tier_order = [
                "無料",
                "低価格帯 (¥0-750)",
                "中価格帯 (¥750-2,250)",
                "高価格帯 (¥2,250-4,500)",
                "プレミアム (¥4,500+)",
            ]
            tier_stats = tier_stats.reindex(
                [tier for tier in price_tier_order if tier in tier_stats.index]
            ).dropna()

            col1, col2 = st.columns(2)

            with col1:
                # 価格帯別ゲーム数の比較
                fig_compare = px.bar(
                    x=tier_stats["ゲーム数"],
                    y=tier_stats.index,
                    orientation="h",
                    title="価格帯別ゲーム数比較",
                    labels={"x": "ゲーム数", "y": "価格帯"},
                    color=tier_stats["平均評価"],
                    color_continuous_scale="Viridis",
                )
                fig_compare.update_layout(height=400)
                st.plotly_chart(fig_compare, use_container_width=True)

            with col2:
                st.markdown("### 📊 価格帯別詳細統計")
                # 価格を円に変換して表示
                display_tier_stats = tier_stats.copy()
                for col in ["平均価格", "中央値価格", "最高価格", "最低価格"]:
                    display_tier_stats[col] = display_tier_stats[col].apply(
                        lambda x: f"¥{x*150:.0f}"
                    )
                display_tier_stats["平均評価"] = display_tier_stats["平均評価"].apply(
                    lambda x: f"{x:.2f}"
                )
                display_tier_stats["平均レビュー数"] = display_tier_stats[
                    "平均レビュー数"
                ].apply(lambda x: f"{x:,.0f}")
                st.dataframe(display_tier_stats, use_container_width=True)
        else:
            st.warning("分析に十分なデータがありません。")

    # 価格戦略インサイト
    st.markdown("### 💡 価格戦略インサイト")

    avg_price = filtered_df["price_usd"].mean()
    median_price = filtered_df["price_usd"].median()
    # 無料ゲーム比率の正確な計算（is_freeフラグのみ）
    free_games_count = len(filtered_df[filtered_df["is_free"] == True])
    free_ratio = (
        (free_games_count / len(filtered_df)) * 100 if len(filtered_df) > 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        avg_price_jpy = avg_price * 150 if not pd.isna(avg_price) else 0
        st.metric("平均価格", f"¥{avg_price_jpy:.0f}")

    with col2:
        median_price_jpy = median_price * 150 if not pd.isna(median_price) else 0
        st.metric("中央値価格", f"¥{median_price_jpy:.0f}")

    with col3:
        st.metric("無料ゲーム比率", f"{free_ratio:.1f}%")

    # 戦略提案
    st.markdown("### 🎯 価格戦略提案")

    if median_price <= 10:
        st.success(
            "💡 **低価格戦略**: 市場は低価格帯が主流。競争力のある価格設定が重要。"
        )
    elif median_price <= 25:
        st.info("💡 **中価格戦略**: バランス型価格設定。品質と価格のバランスが鍵。")
    else:
        st.warning("💡 **高価格戦略**: プレミアム市場。高品質・独自性が必須。")

    if free_ratio > 20:
        st.info(
            "🎮 **フリーミアム機会**: 無料ゲームが多い市場。フリーミアムモデルも検討可能。"
        )

    # AI価格戦略洞察
    if st.button("🤖 AI価格戦略洞察を生成", key="price_ai_insight"):
        if AI_INSIGHTS_AVAILABLE:
            with st.spinner("AI分析中..."):
                try:
                    ai_generator = AIInsightsGenerator()
                    
                    # 価格データサマリー作成
                    # 価格帯分類を動的に作成
                    filtered_df_temp = filtered_df.copy()
                    filtered_df_temp["price_tier"] = filtered_df_temp["price_usd"].apply(price_tier)
                    price_counts = filtered_df_temp['price_tier'].value_counts()
                    total = len(filtered_df)
                    
                    price_data = {
                        'free_percent': free_ratio,
                        'budget_percent': (price_counts.get('低価格帯 (¥0-750)', 0) / total * 100) if total > 0 else 0,
                        'mid_percent': (price_counts.get('中価格帯 (¥750-2,250)', 0) / total * 100) if total > 0 else 0,
                        'premium_percent': (price_counts.get('高価格帯 (¥2,250-4,500)', 0) / total * 100) if total > 0 else 0,
                        'luxury_percent': (price_counts.get('プレミアム (¥4,500+)', 0) / total * 100) if total > 0 else 0,
                        'avg_price': avg_price_jpy if avg_price_jpy > 0 else 0,
                        'price_rating_correlation': 'データ不足' if len(filtered_df[filtered_df['total_reviews'] > 0]) < 10 else '正の相関'
                    }
                    
                    # AI洞察生成
                    insight = ai_generator.generate_price_strategy_insight(price_data)
                    
                    # 洞察表示
                    st.markdown("### 🤖 AI価格戦略分析")
                    st.info(insight)
                    
                except Exception as e:
                    st.error(f"AI洞察生成エラー: {e}")
                    st.caption("💡 Gemini APIキーが設定されているか確認してください")
        else:
            # デモモード用AI洞察
            with st.spinner("デモAI分析中..."):
                time.sleep(1)
                st.markdown("### 🤖 AI価格戦略分析 (デモ)")
                demo_insight = generate_demo_insights("", "pricing")
                st.info(demo_insight)
                st.caption("💡 実際の環境では、Gemini APIによる詳細な分析が提供されます")


def display_insights_and_recommendations():
    """洞察と推奨事項の表示"""
    st.markdown("## 💡 市場洞察と推奨事項")

    # 洞察ボックス
    insights = [
        {
            "title": "🎯 市場構造",
            "content": "インディーゲームがSteam市場の主要セグメントを形成。多様な開発者による活発な競争市場。",
        },
        {
            "title": "💰 価格戦略",
            "content": "低価格戦略が主流だが、品質による差別化で高価格帯も成功可能。$5-15の価格帯が最も競争激化。",
        },
        {
            "title": "🖥️ プラットフォーム戦略",
            "content": "Windows対応は必須。Mac/Linux対応により差別化可能。マルチプラットフォーム対応が競争優位。",
        },
        {
            "title": "🎮 ジャンル動向",
            "content": "特定ジャンルの独占はなく、ニッチ分野での専門化が有効。新規参入の余地あり。",
        },
    ]

    for insight in insights:
        with st.container():
            st.markdown(
                f"""
            <div class="insight-box">
                <h4>{insight['title']}</h4>
                <p>{insight['content']}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # 推奨事項
    st.markdown("### 🚀 新規参入者への推奨事項")

    recommendations = [
        "**価格設定**: $5-15の価格帯での競争力確保",
        "**プラットフォーム**: Windows必須、Mac/Linux対応で差別化",
        "**ジャンル選択**: ニッチジャンルでの専門化による競争回避",
        "**品質重視**: ユーザーレビューと評価の重要性",
        "**コミュニティ**: 開発段階からのコミュニティ構築",
    ]

    for i, rec in enumerate(recommendations, 1):
        st.markdown(f"{i}. {rec}")

    # AI総合洞察セクション
    st.markdown("### 🤖 AI総合戦略洞察")
    
    if st.button("🤖 総合AI洞察を生成", key="comprehensive_ai_insight"):
        if AI_INSIGHTS_AVAILABLE:
            with st.spinner("包括的なAI分析を実行中..."):
                try:
                    ai_generator = AIInsightsGenerator()
                    
                    # 成功要因データの準備（例示データ）
                    success_data = {
                        'avg_reviews': 1500,
                        'avg_rating': 0.85,
                        'success_price_range': '¥750-2,250',
                        'success_genres': ['Action', 'Adventure', 'Puzzle'],
                        'platform_strategy': 'Windows + Mac対応'
                    }
                    
                    # AI成功要因洞察生成
                    insight = ai_generator.generate_success_factors_insight(success_data)
                    
                    # 洞察表示
                    st.info(insight)
                    
                except Exception as e:
                    st.error(f"AI洞察生成エラー: {e}")
                    st.caption("💡 Gemini APIキーが設定されているか確認してください")
        else:
            # デモモード用AI洞察
            with st.spinner("デモAI総合分析中..."):
                time.sleep(2)  # 総合分析のため少し長め
                st.info(generate_demo_insights("", "comprehensive"))
                st.caption("💡 実際の環境では、Gemini APIによる詳細な総合分析が提供されます")


def main():
    """メインアプリケーション（強化版）"""

    # ヘッダー
    st.markdown(
        '<h1 class="main-header">🎮 Steam インディーゲーム市場分析</h1>',
        unsafe_allow_html=True,
    )
    st.markdown("**データ駆動型のゲーム市場インサイト・プラットフォーム**")

    # プログレスバーでリアルタイム読み込み状況
    progress_bar = st.progress(0)
    status_text = st.empty()

    # データ読み込み
    status_text.text("データベースに接続中...")
    progress_bar.progress(20)

    with st.spinner("データを読み込み中..."):
        df = get_cached_data()

    progress_bar.progress(60)

    if df is None:
        st.error(
            "❌ データの読み込みに失敗しました。データベース接続を確認してください。"
        )
        st.info(
            "💡 **トラブルシューティング**: Docker Composeサービスが起動しているか確認してください。"
        )
        return

    status_text.text("データ処理中...")
    progress_bar.progress(80)

    # 初期データを保存（フィルター前の全データ）
    initial_df = df.copy()

    # データ読み込み完了
    progress_bar.progress(100)
    status_text.text("準備完了！")
    time.sleep(0.5)  # 完了メッセージを少し表示
    progress_bar.empty()
    status_text.empty()

    # サイドバー設定
    st.sidebar.title("🎮 Steam Analytics")
    st.sidebar.markdown("---")

    # キャッシュクリアボタン
    if st.sidebar.button("🔄 データ更新"):
        st.cache_data.clear()
        st.success("✅ キャッシュをクリアしました")
        st.rerun()

    # データ統計表示
    st.sidebar.success(f"✅ **{len(initial_df):,}件** のゲームデータを読み込み")
    
    st.sidebar.info(f"📅 最終更新: {datetime.now().strftime('%H:%M:%S')}")
    

    progress_bar.progress(100)
    status_text.text("✅ データ準備完了")
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()

    # データ要約
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 データ要約")
    st.sidebar.success(f"✅ **{len(initial_df):,}件** のインディーゲームを分析中")

    # メインコンテンツ
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 分析セクション")

    sections = {
        "市場概要": "overview",
        "ジャンル分析": "genre",
        "価格分析": "price",
        "洞察・推奨事項": "insights",
    }

    selected_section = st.sidebar.radio("表示する分析:", list(sections.keys()))

    # セクション表示
    if selected_section == "市場概要":
        display_market_overview(initial_df)
    elif selected_section == "ジャンル分析":
        display_genre_analysis(initial_df)
    elif selected_section == "価格分析":
        display_price_analysis(initial_df)
    elif selected_section == "洞察・推奨事項":
        display_insights_and_recommendations()

    # フッター
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 情報")
    st.sidebar.markdown(
        f"**更新日**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n"
        f"**インディーゲーム**: {len(initial_df):,}件  \n"
        f"**分析対象**: Steamの「Indie」ジャンル保有ゲーム  \n"
        f"**データソース**: Steam Web API"
    )


if __name__ == "__main__":
    main()
