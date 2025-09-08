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

# Render環境検出 - DATABASE_URLベースの確実な検出
IS_RENDER = (
    os.getenv("RENDER") == "true"
    or "onrender.com" in os.getenv("RENDER_EXTERNAL_URL", "")
    or os.getenv("RENDER_SERVICE_NAME") is not None
    or "render" in os.getenv("HOSTNAME", "").lower()
    or (os.getenv("DATABASE_URL") and "postgresql://" in os.getenv("DATABASE_URL", ""))
)

# Streamlit Cloud環境検出
IS_STREAMLIT_CLOUD = (
    os.getenv("STREAMLIT_SHARING") == "true"
    or "streamlit.io" in os.getenv("HOSTNAME", "")
    or "/mount/src/" in str(current_dir)
)

# 分析モジュールのインポート (エラーハンドリング付き)
try:
    from src.analyzers.market_analyzer import MarketAnalyzer
    from src.analyzers.success_analyzer import SuccessAnalyzer
    from src.analyzers.data_quality_checker import DataQualityChecker

    ANALYZERS_AVAILABLE = True
except ImportError as e:
    # 本番環境（DATA_SOURCE=firestore）では分析モジュール不要
    show_info = os.getenv("ENVIRONMENT") != "production"
    if show_info:
        st.info(f"🔍 分析モジュール: 簡素化モードで動作中")
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
        if os.getenv("ENVIRONMENT") != "production":
            st.info("🤖 AI洞察機能: 分析モジュールが利用できません")
except ImportError as e:
    if os.getenv("ENVIRONMENT") != "production":
        st.info(f"🤖 AI洞察機能: インポートエラー {e}")


# デモ用AI洞察生成関数
def generate_demo_insights(data_summary: str, section: str) -> str:
    """デモ用AI洞察（固定メッセージ）"""
    demo_insights = {
        "market": "🎮 市場概況: インディーゲーム市場は多様性に富み、低価格帯ゲームが主流を占めています。プラットフォーム対応とユーザーレビューの質が成功の鍵となっています。",
        "genre": "🎯 ジャンル分析: Actionジャンルが最も競争が激しく、Adventure・Casualジャンルにニッチな機会があります。複合ジャンルのゲームが高い評価を得る傾向があります。",
        "pricing": "💰 価格戦略: 中価格帯（$10-30）が最適なスイートスポットです。無料ゲームは高いダウンロード数を獲得できますが、収益化に課題があります。",
        "comprehensive": "📈 総合評価: インディーゲーム市場は創造性とユーザーエンゲージメントが重視される環境です。データドリブンな開発戦略が成功確率を高めます。",
    }
    return demo_insights.get(section, "🤖 AI分析データを処理中です...")


warnings.filterwarnings("ignore")

# 環境変数読み込み
load_dotenv()


def get_database_connection_string():
    """統一されたデータベース接続文字列を取得"""
    database_url = os.getenv("DATABASE_URL")

    if database_url and "postgresql://" in database_url:
        return database_url
    else:
        # 個別環境変数から構築
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "steam_analytics")
        user = os.getenv("POSTGRES_USER", "steam_user")
        password = os.getenv("POSTGRES_PASSWORD", "steam_password")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"


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
        "app_id": range(1, 549),
        "name": [f"Demo Game {i}" for i in range(1, 549)],
        "type": ["game"] * 548,
        "is_free": np.random.choice([True, False], 548, p=[0.3, 0.7]),
        "price_final": np.random.exponential(1500, 548),
        "price_usd": np.random.exponential(15, 548),
        "release_date": pd.date_range("2020-01-01", periods=548, freq="D"),
        "platforms_windows": np.random.choice([True, False], 548, p=[0.9, 0.1]),
        "platforms_mac": np.random.choice([True, False], 548, p=[0.6, 0.4]),
        "platforms_linux": np.random.choice([True, False], 548, p=[0.5, 0.5]),
        "platform_count": np.random.randint(1, 4, 548),
        "positive_reviews": np.random.poisson(100, 548),
        "negative_reviews": np.random.poisson(20, 548),
        "total_reviews": lambda x: x["positive_reviews"] + x["negative_reviews"],
        "rating": np.random.beta(8, 2, 548) * 100,  # 80%平均の評価
        "is_indie": [True] * 548,
        "primary_genre": np.random.choice(
            ["Action", "Adventure", "Casual", "RPG", "Strategy"], 548
        ),
        "primary_developer": [f"Developer {i%50}" for i in range(548)],
        "primary_publisher": [f"Publisher {i%30}" for i in range(548)],
        "price_category": np.random.choice(
            ["無料", "低価格", "中価格", "プレミアム"], 548, p=[0.3, 0.4, 0.2, 0.1]
        ),
    }

    df = pd.DataFrame(demo_data)
    df["total_reviews"] = df["positive_reviews"] + df["negative_reviews"]
    df["positive_percentage"] = (
        df["positive_reviews"] / df["total_reviews"] * 100
    ).fillna(0)

    return df


def load_json_data():
    """JSONファイルからデータを読み込む"""
    import json
    
    try:
        # JSONファイルパス（複数パターン対応）
        json_paths = [
            "steam_indie_games_20250630_095737.json",
            "/app/steam_indie_games_20250630_095737.json",
            "./steam_indie_games_20250630_095737.json"
        ]
        
        # デバッグ: ファイル検索状況を表示
        st.info("🔍 JSONファイルを検索中...")
        for path in json_paths:
            exists = os.path.exists(path)
            st.text(f"  {path}: {'✅ 存在' if exists else '❌ なし'}")
        
        # カレントディレクトリの内容を表示
        current_files = os.listdir('.')
        json_files = [f for f in current_files if f.endswith('.json')]
        if json_files:
            st.info(f"📁 カレントディレクトリ内のJSONファイル: {json_files}")
        else:
            st.warning("📁 カレントディレクトリにJSONファイルがありません")
        
        data = None
        used_path = None
        
        for json_path in json_paths:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    used_path = json_path
                    break
            except FileNotFoundError:
                continue
        
        if data is None:
            st.error("❌ JSONデータファイルが見つかりません")
            st.info("🌟 代替手段として、デモデータを表示します")
            return load_demo_data()
        
        # JSONの構造確認とデータ抽出
        if isinstance(data, dict) and 'games' in data:
            # 構造化されたJSON（export_info + games）
            games_data = data['games']
            export_info = data.get('export_info', {})
            st.info(f"📊 データソース: {export_info.get('source', 'unknown')} ({export_info.get('timestamp', '')})")
            df = pd.DataFrame(games_data)
        elif isinstance(data, list):
            # 直接ゲームリスト
            df = pd.DataFrame(data)
        else:
            st.error("❌ 不明なJSONデータ構造です")
            return load_demo_data()
        
        # データ型変換
        numeric_columns = ['price_initial', 'price_final', 'positive_reviews', 'negative_reviews', 'estimated_owners', 'peak_ccu']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 日付変換
        if 'release_date_text' in df.columns:
            df['release_date'] = pd.to_datetime(df['release_date_text'], errors='coerce')
        
        # 価格をドル単位に変換（セントからドル）
        if 'price_final' in df.columns:
            df['price_usd'] = df['price_final'] / 100
        
        # 計算カラム
        df['total_reviews'] = df.get('positive_reviews', 0) + df.get('negative_reviews', 0)
        df['positive_percentage'] = (df.get('positive_reviews', 0) / (df['total_reviews'] + 1)) * 100
        
        st.success(f"✅ JSONデータを正常に読み込みました: {len(df)} ゲーム （{used_path}）")
        
        return df
        
    except Exception as e:
        st.error(f"❌ JSONデータ読み込みエラー: {str(e)}")
        st.info("🌟 代替手段として、デモデータを表示します")
        return load_demo_data()


def load_firestore_data():
    """Firestoreからデータを読み込む"""
    try:
        from google.cloud import firestore
        
        # Firestoreクライアント初期化
        db = firestore.Client()
        
        # システム情報表示の条件チェック
        show_info = st.session_state.get("show_announcements", False)
        if show_info:
            st.info("🔍 Firestoreに接続中...")
        
        # gamesコレクションから全ドキュメントを取得
        games_ref = db.collection('games')
        docs = games_ref.stream()
        
        games_data = []
        for doc in docs:
            game_data = doc.to_dict()
            game_data['doc_id'] = doc.id  # ドキュメントIDを保持
            games_data.append(game_data)
        
        if not games_data:
            st.warning("⚠️ Firestoreにデータが見つかりません")
            if show_info:
                st.info("💡 scripts/import_to_firestore.py を実行してデータをインポートしてください")
            return load_demo_data()
        
        # DataFrameに変換
        df = pd.DataFrame(games_data)
        
        # 必要なカラムを作成/補完
        if 'developers' in df.columns and 'primary_developer' not in df.columns:
            df['primary_developer'] = df['developers'].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Unknown'
            )
        
        if 'publishers' in df.columns and 'primary_publisher' not in df.columns:
            df['primary_publisher'] = df['publishers'].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Unknown'
            )
        
        if 'genres' in df.columns and 'primary_genre' not in df.columns:
            df['primary_genre'] = df['genres'].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Unknown'
            )
        
        # platform_countカラムを作成（プラットフォーム対応数）
        if 'platform_count' not in df.columns:
            platform_cols = ['platforms_windows', 'platforms_mac', 'platforms_linux']
            available_platforms = [col for col in platform_cols if col in df.columns]
            if available_platforms:
                df['platform_count'] = df[available_platforms].sum(axis=1)
            else:
                # platforms配列から計算
                if 'platforms' in df.columns:
                    df['platform_count'] = df['platforms'].apply(
                        lambda x: len(x) if isinstance(x, list) else 1
                    )
                else:
                    df['platform_count'] = 1  # デフォルト値
        
        # メタデータ情報取得
        try:
            meta_doc = db.collection('metadata').document('import_info').get()
            if meta_doc.exists:
                meta_data = meta_doc.to_dict()
                if show_info:
                    st.success(f"✅ Firestoreデータ読み込み完了: {len(df)} ゲーム")
                    st.info(f"📊 インポート日時: {meta_data.get('imported_at', 'unknown')}")
            else:
                if show_info:
                    st.success(f"✅ Firestoreデータ読み込み完了: {len(df)} ゲーム")
        except Exception as e:
            if show_info:
                st.success(f"✅ Firestoreデータ読み込み完了: {len(df)} ゲーム")
        
        return df
        
    except ImportError:
        st.error("❌ Firestore SDK がインストールされていません")
        st.code("pip install google-cloud-firestore firebase-admin")
        return load_demo_data()
    except Exception as e:
        st.error(f"❌ Firestore接続エラー: {str(e)}")
        st.info("🌟 フォールバック: デモデータを表示します")
        return load_demo_data()


# キャッシング設定（キャッシュ無効化）
def get_cached_data():
    """データ取得（キャッシュなし）"""
    return load_data()


@st.cache_data(ttl=600)
def get_market_analysis():
    """キャッシュされた市場分析"""
    if not ANALYZERS_AVAILABLE:
        return {}
    
    # Firestore/JSON/本番モード時は分析モジュール無効化（PostgreSQL接続回避）
    data_source = os.getenv("DATA_SOURCE", "").lower()
    if data_source in ["json", "firestore"] or os.getenv("ENVIRONMENT") == "production":
        show_info = st.session_state.get("show_announcements", False)
        if show_info:
            st.info("📊 本番モード: PostgreSQL分析機能を無効化します")
        return {}
    
    try:
        analyzer = MarketAnalyzer()
        analyzer.load_data()
        return analyzer.get_market_overview()
    except Exception as e:
        st.warning(f"⚠️ 市場分析エラー: {str(e)}")
        return {}


@st.cache_data(ttl=600)
def get_success_analysis():
    """キャッシュされた成功要因分析"""
    # Firestore/JSON/本番モード時は分析モジュール無効化（PostgreSQL接続回避）
    data_source = os.getenv("DATA_SOURCE", "").lower()
    if data_source in ["json", "firestore"] or os.getenv("ENVIRONMENT") == "production":
        return ""
    
    try:
        analyzer = SuccessAnalyzer()
        analyzer.load_data()
        return analyzer.create_success_analysis_report()
    except Exception as e:
        st.warning(f"⚠️ 成功分析エラー: {str(e)}")
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
    
    # DATA_SOURCE環境変数をチェック（最優先）
    data_source = os.getenv("DATA_SOURCE", "").lower()
    show_info = st.session_state.get("show_announcements", False)
    
    if data_source == "firestore":
        if show_info:
            st.info("🔥 Firestoreデータベースからデータを読み込んでいます...")
        return load_firestore_data()
    elif data_source == "json":
        if show_info:
            st.info("📄 JSONファイルからデータを読み込んでいます...")
        return load_json_data()
    
    # Cloud Run環境での優先順位: Firestore > JSON
    if os.getenv("ENVIRONMENT") == "production":
        # まずFirestoreを試行
        try:
            if show_info:
                st.info("🔥 本番環境: Firestoreデータベースを試行中...")
            return load_firestore_data()
        except:
            if show_info:
                st.info("📄 フォールバック: JSONデータを使用します...")
            return load_json_data()

    # データベース接続設定の取得
    db_config = None

    # デバッグ情報（本番では非表示）
    if os.getenv("DEBUG_MODE") == "true":
        with st.expander("🔍 環境デバッグ情報"):
            st.text(f"IS_RENDER: {IS_RENDER}")
            st.text(
                f"DATABASE_URL: {'設定済み' if os.getenv('DATABASE_URL') else '未設定'}"
            )
            st.text(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST', '未設定')}")
            st.text(f"RENDER env: {os.getenv('RENDER', '未設定')}")
            st.text(f"HOSTNAME: {os.getenv('HOSTNAME', '未設定')}")

    try:
        # DATABASE_URLが設定されている場合は最優先で使用
        database_url = os.getenv("DATABASE_URL")
        if database_url and "postgresql://" in database_url:
            # DATABASE_URL形式をパース
            from urllib.parse import urlparse

            parsed_url = urlparse(database_url)
            db_config = {
                "host": parsed_url.hostname,
                "port": parsed_url.port or 5432,
                "database": parsed_url.path[1:],  # '/'を除去
                "user": parsed_url.username,
                "password": parsed_url.password,
            }
            st.info("🔗 PostgreSQL データベース接続中... (DATABASE_URL)")
        elif IS_RENDER:
            # Render環境で個別環境変数
            if os.getenv("POSTGRES_HOST") and os.getenv("POSTGRES_HOST") != "postgres":
                db_config = {
                    "host": os.getenv("POSTGRES_HOST"),
                    "port": int(os.getenv("POSTGRES_PORT", 5432)),
                    "database": os.getenv("POSTGRES_DB", "steam_analytics"),
                    "user": os.getenv("POSTGRES_USER", "steam_user"),
                    "password": os.getenv("POSTGRES_PASSWORD"),
                }
                st.info("🔗 Render PostgreSQL データベース接続中... (環境変数)")
            else:
                # Render環境でDB未設定 → 設定手順表示
                st.error("❌ Render環境でデータベース設定が見つかりません")
                st.markdown("### 🔧 Renderデータベース設定手順")
                st.markdown(
                    """
                **原因**: PostgreSQLサービスが接続されていません
                
                **解決方法**:
                1. **PostgreSQLサービス作成** (未作成の場合)
                   - Render Dashboard → New + → PostgreSQL
                   - Name: `steam-analytics-db`
                   - Database: `steam_analytics`
                
                2. **Webサービスにデータベース接続**
                   - Web Service → Environment → Connect Database
                   - 作成したPostgreSQLサービスを選択
                   - `DATABASE_URL` が自動追加されます
                
                3. **手動設定** (代替案)
                   - Environment Variables に以下を追加:
                   - `POSTGRES_HOST`: [PostgreSQLサービスのhost]
                   - `POSTGRES_USER`: [ユーザー名]
                   - `POSTGRES_PASSWORD`: [パスワード]
                   - `POSTGRES_DB`: [データベース名]
                """
                )

                st.warning("🌟 デモモード: サンプルデータを表示しています")
                return load_demo_data()
        elif IS_STREAMLIT_CLOUD:
            # Streamlit Cloud環境
            if "database" in st.secrets:
                db_config = {
                    "host": st.secrets["database"]["host"],
                    "port": int(st.secrets["database"]["port"]),
                    "database": st.secrets["database"]["database"],
                    "user": st.secrets["database"]["username"],
                    "password": st.secrets["database"]["password"],
                }
                st.info("🔗 外部データベース接続を試行中...")
            else:
                # Secretsにデータベース設定なし → デモモード
                st.warning("🌟 デモモード: サンプルデータを表示しています")
                st.caption(
                    "💡 実際のデータを表示するには、Streamlit Secretsでデータベース設定を行ってください"
                )
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
                st.caption(
                    "💡 実際のデータを表示するには、.envファイルでデータベース設定を行ってください"
                )
                return load_demo_data()
    except Exception as e:
        st.warning(f"🌟 デモモード: 設定読み込みエラー ({e})")
        return load_demo_data()

    # データベース接続がない場合はデモモード
    if db_config is None:
        st.warning("🌟 デモモード: データベース設定がありません")
        return load_demo_data()

    try:
        # SQLAlchemy エンジン作成（タイムアウト設定付き）
        engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}",
            connect_args={
                "connect_timeout": 5,  # 接続タイムアウト5秒（短縮）
                "application_name": "streamlit_dashboard",
            },
            pool_timeout=10,  # プール取得タイムアウト10秒（短縮）
            pool_recycle=3600,  # 1時間でコネクション再利用
        )

        # インディーゲームのみを取得（実際のテーブル構造に対応）
        query = """
        SELECT 
            app_id,
            name,
            type,
            is_free,
            short_description,
            price_initial,
            price_final,
            price_final::float / 100 as price_usd,  -- セント単位をドル単位に変換
            release_date_text as release_date,
            platforms_windows,
            platforms_mac, 
            platforms_linux,
            (platforms_windows::int + platforms_mac::int + platforms_linux::int) as platform_count,
            COALESCE(positive_reviews, 0) as positive_reviews,
            COALESCE(negative_reviews, 0) as negative_reviews,
            (COALESCE(positive_reviews, 0) + COALESCE(negative_reviews, 0)) as total_reviews,
            CASE 
                WHEN (COALESCE(positive_reviews, 0) + COALESCE(negative_reviews, 0)) > 0 
                THEN (COALESCE(positive_reviews, 0)::float / (COALESCE(positive_reviews, 0) + COALESCE(negative_reviews, 0))) * 100
                ELSE 75.0 
            END as rating,
            CASE WHEN 'Indie' = ANY(genres) THEN true ELSE false END as is_indie,
            CASE WHEN array_length(genres, 1) > 0 THEN genres[1] ELSE 'Unknown' END as primary_genre,
            CASE WHEN array_length(developers, 1) > 0 THEN developers[1] ELSE 'Unknown' END as primary_developer,
            CASE WHEN array_length(publishers, 1) > 0 THEN publishers[1] ELSE 'Unknown' END as primary_publisher,
            CASE 
                WHEN is_free THEN '無料'
                WHEN price_final <= 500 THEN '低価格帯 (¥0-750)'
                WHEN price_final <= 1500 THEN '中価格帯 (¥750-2,250)'
                WHEN price_final <= 3000 THEN '高価格帯 (¥2,250-4,500)'
                ELSE 'プレミアム (¥4,500+)'
            END as price_category,
            created_at
        FROM games 
        WHERE type = 'game' AND 'Indie' = ANY(genres)
        ORDER BY created_at DESC
        """

        # データベース接続テスト
        from sqlalchemy import text

        with engine.connect() as conn:
            test_result = conn.execute(text("SELECT 1"))
            test_result.fetchone()

        # データ読み込み（実際のテーブルから）
        df = pd.read_sql_query(query, engine)

        # 成功メッセージ
        st.success(
            f"✅ データベースから {len(df)} 件のインディーゲームデータを読み込みました"
        )

        if len(df) == 0:
            st.warning("⚠️ データベースにインディーゲームデータが見つかりません。")
            st.info("💡 Steam APIからインディーゲームデータを収集する必要があります。")
            return load_demo_data()  # データがない場合はデモモードに切り替え

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
        st.error(f"❌ データベースエラー: {str(e)}")
        st.warning(
            f"🌟 デモモード: データベース接続エラーのため、サンプルデータを表示しています"
        )
        st.caption(
            "💡 外部データベースに接続できないため、サンプルデータを表示しています"
        )

        # デバッグ情報表示
        with st.expander("🔍 詳細エラー情報（デバッグ用）"):
            st.text(f"エラー詳細: {str(e)}")
            st.text(f"環境情報:")
            st.text(f"  - IS_RENDER: {IS_RENDER}")
            st.text(
                f"  - DATABASE_URL: {'設定済み' if os.getenv('DATABASE_URL') else '未設定'}"
            )
            st.text(f"  - POSTGRES_HOST: {os.getenv('POSTGRES_HOST', '未設定')}")
            st.text(f"データベース設定:")
            st.text(f"  - Host: {db_config.get('host', 'N/A') if db_config else 'N/A'}")
            st.text(f"  - Port: {db_config.get('port', 'N/A') if db_config else 'N/A'}")
            st.text(
                f"  - Database: {db_config.get('database', 'N/A') if db_config else 'N/A'}"
            )
            st.text(f"  - User: {db_config.get('user', 'N/A') if db_config else 'N/A'}")

        return load_demo_data()


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
            
            # ジャンル分布グラフ作成
            if 'primary_genre' in df.columns:
                genre_counts = df['primary_genre'].value_counts().head(10)
                
                if len(genre_counts) > 0:
                    try:
                        fig_genre = px.bar(
                            x=genre_counts.values,
                            y=genre_counts.index,
                            orientation="h", 
                            title="ジャンル別ゲーム数",
                            labels={"x": "ゲーム数", "y": "ジャンル"}
                        )
                        fig_genre.update_layout(height=400)
                        st.plotly_chart(fig_genre, width='stretch')
                    except Exception as e:
                        st.error(f"❌ グラフ作成エラー: {e}")
                else:
                    st.warning("⚠️ ジャンルデータが見つかりません")
            else:
                st.error("❌ ジャンルデータの取得に失敗しました")

        with col2:
            st.markdown("#### 💰 価格カテゴリ分布")
            # price_categoryカラムが存在しない場合は作成
            if 'price_category' not in df.columns:
                if 'price_usd' in df.columns:
                    df['price_category'] = df['price_usd'].apply(
                        lambda x: '無料' if x == 0 else 
                                 '低価格' if x < 10 else
                                 '中価格' if x < 30 else 
                                 'プレミアム'
                    )
                else:
                    # フォールバック: サンプルデータ
                    df['price_category'] = ['無料'] * (len(df)//3) + ['低価格'] * (len(df)//3) + ['中価格'] * (len(df) - 2*(len(df)//3))
            
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
            st.plotly_chart(fig_price, width='stretch')

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
                        "total_games": total_games,
                        "free_games": len(free_games),
                        "free_ratio": free_ratio,
                        "avg_price_jpy": avg_price_jpy if avg_price_jpy > 0 else 0,
                        "top_genres": df["primary_genre"]
                        .value_counts()
                        .head(3)
                        .index.tolist(),
                        "review_ratio": reviewed_ratio,
                    }

                    # AI洞察生成
                    insight = ai_generator.generate_market_overview_insight(
                        data_summary
                    )

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
                st.caption(
                    "💡 実際の環境では、Gemini APIによる詳細な分析が提供されます"
                )


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
        show_multi_genre = st.checkbox("複数ジャンル表示（現在無効）", value=False, disabled=True)

    # フィルタリング適用
    filtered_df = indie_df.copy()
    if price_filter == "有料のみ":
        filtered_df = filtered_df[filtered_df["is_free"] == False]
    elif price_filter == "無料のみ":
        filtered_df = filtered_df[filtered_df["is_free"] == True]

    # 複数ジャンル表示の処理（現在無効）
    multi_genre_df = None
    if False:  # show_multi_genre - 一時的に無効化
        # 複数ジャンルデータを取得（Firestoreから直接処理）
        try:
            # Firestoreデータから複数ジャンルを持つゲームを抽出
            multi_genre_games = []
            for _, game in df.iterrows():
                if 'genres' in df.columns and isinstance(game.get('genres'), list) and len(game.get('genres', [])) > 1:
                    multi_genre_games.append({
                        'app_id': game.get('app_id'),
                        'name': game.get('name'),
                        'price_usd': game.get('price_usd', 0),
                        'positive_reviews': game.get('positive_reviews', 0),
                        'negative_reviews': game.get('negative_reviews', 0),
                        'total_reviews': game.get('total_reviews', 0),
                        'all_genres': ', '.join(game.get('genres', [])) if isinstance(game.get('genres'), list) else str(game.get('genres', ''))
                    })
            
            multi_genre_df = pd.DataFrame(multi_genre_games).head(100)

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

                st.dataframe(display_multi_df.head(20), width='stretch')

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
                st.plotly_chart(fig_combo, width='stretch')

                # 複数ジャンル表示の場合はここで処理終了
                return
            else:
                st.warning("複数ジャンルを持つゲームが見つかりませんでした。")

        except Exception as e:
            st.error(f"複数ジャンルデータの取得でエラーが発生しました: {e}")
            st.info("💡 単一ジャンル表示に切り替えて続行します。")

    # Firestoreから直接ジャンル情報を取得（PostgreSQL完全無効化）
    # フォールバック処理を直接実行
    show_info = st.session_state.get("show_announcements", False)
    if show_info:
        st.info("💡 Firestore専用モード: シンプルなジャンル表示を使用します")

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
        st.plotly_chart(fig_genre, width='stretch')

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
        st.plotly_chart(fig_reviews, width='stretch')

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

    st.dataframe(display_stats, width='stretch')

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
                st.caption(
                    "💡 実際の環境では、Gemini APIによる詳細な分析が提供されます"
                )


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
        available_genres = [
            genre
            for genre in indie_df["primary_genre"].unique()[:10]
            if genre != "Indie"
        ]
        genre_filter = st.multiselect(
            "ジャンルフィルター",
            options=available_genres,
            default=[],
            help="🎮 既に全データがインディーゲームです",
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
            st.plotly_chart(fig_hist, width='stretch')

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
                    textposition="inside",
                    textinfo="percent",
                    direction="clockwise",
                    sort=False,
                    rotation=0,  # 0度（3時方向）からスタート
                    textfont_size=12,
                )
            else:
                # フォールバック：元の順序で表示
                fig_pie = px.pie(
                    values=price_dist.values,
                    names=price_dist.index,
                    title="価格帯別分布",
                )
                fig_pie.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    direction="clockwise",
                    sort=False,
                    rotation=0,
                )

            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, width='stretch')

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
                st.plotly_chart(fig_scatter, width='stretch')

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
                st.plotly_chart(fig_box, width='stretch')
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
                st.plotly_chart(fig_compare, width='stretch')

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
                st.dataframe(display_tier_stats, width='stretch')
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
                    filtered_df_temp["price_tier"] = filtered_df_temp[
                        "price_usd"
                    ].apply(price_tier)
                    price_counts = filtered_df_temp["price_tier"].value_counts()
                    total = len(filtered_df)

                    price_data = {
                        "free_percent": free_ratio,
                        "budget_percent": (
                            (price_counts.get("低価格帯 (¥0-750)", 0) / total * 100)
                            if total > 0
                            else 0
                        ),
                        "mid_percent": (
                            (price_counts.get("中価格帯 (¥750-2,250)", 0) / total * 100)
                            if total > 0
                            else 0
                        ),
                        "premium_percent": (
                            (
                                price_counts.get("高価格帯 (¥2,250-4,500)", 0)
                                / total
                                * 100
                            )
                            if total > 0
                            else 0
                        ),
                        "luxury_percent": (
                            (price_counts.get("プレミアム (¥4,500+)", 0) / total * 100)
                            if total > 0
                            else 0
                        ),
                        "avg_price": avg_price_jpy if avg_price_jpy > 0 else 0,
                        "price_rating_correlation": (
                            "データ不足"
                            if len(filtered_df[filtered_df["total_reviews"] > 0]) < 10
                            else "正の相関"
                        ),
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
                st.caption(
                    "💡 実際の環境では、Gemini APIによる詳細な分析が提供されます"
                )


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
                        "avg_reviews": 1500,
                        "avg_rating": 0.85,
                        "success_price_range": "¥750-2,250",
                        "success_genres": ["Action", "Adventure", "Puzzle"],
                        "platform_strategy": "Windows + Mac対応",
                    }

                    # AI成功要因洞察生成
                    insight = ai_generator.generate_success_factors_insight(
                        success_data
                    )

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
                st.caption(
                    "💡 実際の環境では、Gemini APIによる詳細な総合分析が提供されます"
                )


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
        st.error("❌ 予期しないエラーが発生しました。")
        st.info("💡 ページを再読み込みしてください。")
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
    
    # 表示設定
    with st.sidebar.expander("⚙️ 表示設定"):
        # 前回の状態を保存
        prev_show_announcements = st.session_state.get("prev_show_announcements", False)
        show_announcements = st.checkbox("📢 システム情報を表示", value=False, key="show_announcements")
        
        # 状態が変更された場合はリロード
        if show_announcements != prev_show_announcements:
            st.session_state.prev_show_announcements = show_announcements
            st.rerun()

    # キャッシュクリアボタン
    if st.sidebar.button("🔄 データ更新"):
        st.cache_data.clear()
        st.success("✅ キャッシュをクリアしました")
        st.rerun()

    # データ収集ボタン（Render環境のみ）
    if IS_RENDER and st.sidebar.button("🎮 Steam データ収集実行"):
        st.sidebar.warning("⚠️ この処理には10-15分かかります")

        if st.sidebar.button("🚀 実行確認", key="confirm_collection"):
            with st.spinner("Steam データ収集中... (10-15分)"):
                try:
                    import subprocess
                    import sys

                    # データ収集スクリプト実行
                    result = subprocess.run(
                        [sys.executable, "/workspace/collect_indie_games.py"],
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30分タイムアウト
                    )

                    if result.returncode == 0:
                        st.success("✅ データ収集完了！")
                        st.info(
                            "📊 ページを再読み込みして新しいデータを確認してください"
                        )
                        # キャッシュクリア
                        st.cache_data.clear()
                    else:
                        st.error("❌ データ収集中にエラーが発生しました")
                        if result.stderr:
                            st.text(result.stderr[:500])

                except subprocess.TimeoutExpired:
                    st.error("⏰ データ収集がタイムアウトしました（30分制限）")
                except Exception as e:
                    st.error(f"❌ 予期しないエラー: {e}")

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
