"""
app.pyのload_data関数をデバッグ
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

# 環境変数読み込み
print('=== 環境変数 ===')
print(f'POSTGRES_HOST: {os.getenv("POSTGRES_HOST")}')
print(f'POSTGRES_PORT: {os.getenv("POSTGRES_PORT")}')
print(f'POSTGRES_DB: {os.getenv("POSTGRES_DB")}')
print(f'POSTGRES_USER: {os.getenv("POSTGRES_USER")}')
print(f'POSTGRES_PASSWORD: {os.getenv("POSTGRES_PASSWORD") and "***設定済み***" or "未設定"}')

# パス設定
current_dir = Path(__file__).parent
project_root = current_dir

# 環境検出
IS_RENDER = (
    os.getenv('RENDER') == 'true' or 
    'onrender.com' in os.getenv('RENDER_EXTERNAL_URL', '') or
    os.getenv('RENDER_SERVICE_NAME') is not None or
    'render' in os.getenv('HOSTNAME', '').lower()
)

IS_STREAMLIT_CLOUD = (
    os.getenv('STREAMLIT_SHARING') == 'true' or 
    'streamlit.io' in os.getenv('HOSTNAME', '') or
    '/mount/src/' in str(current_dir)
)

print(f'\n=== 環境検出 ===')
print(f'IS_RENDER: {IS_RENDER}')
print(f'IS_STREAMLIT_CLOUD: {IS_STREAMLIT_CLOUD}')
print(f'ローカル環境: {not IS_RENDER and not IS_STREAMLIT_CLOUD}')

# データベース接続設定の取得
db_config = None

try:
    if IS_RENDER:
        print('\n=== Render環境 ===')
        if os.getenv("POSTGRES_HOST"):
            db_config = {
                "host": os.getenv("POSTGRES_HOST"),
                "port": int(os.getenv("POSTGRES_PORT", 5432)),
                "database": os.getenv("POSTGRES_DB", "steam_analytics"),
                "user": os.getenv("POSTGRES_USER", "steam_user"),
                "password": os.getenv("POSTGRES_PASSWORD"),
            }
            print("✅ Render PostgreSQL 設定取得")
        else:
            print("❌ Render環境でDB未設定")
    elif IS_STREAMLIT_CLOUD:
        print('\n=== Streamlit Cloud環境 ===')
        print("❌ Secrets未実装（この環境では動作しません）")
    else:
        print('\n=== ローカル環境 ===')
        if os.getenv("POSTGRES_HOST"):
            db_config = {
                "host": os.getenv("POSTGRES_HOST", "postgres"),
                "port": int(os.getenv("POSTGRES_PORT", 5432)),
                "database": os.getenv("POSTGRES_DB", "steam_analytics"),
                "user": os.getenv("POSTGRES_USER", "steam_user"),
                "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
            }
            print("✅ ローカル環境変数から設定取得")
        else:
            print("❌ 環境変数なし")

except Exception as e:
    print(f"❌ 設定読み込みエラー: {e}")

# データベース接続がない場合
if db_config is None:
    print("\n❌ データベース設定がありません → デモモード")
    exit()

print(f'\n=== データベース接続テスト ===')
print(f'接続先: {db_config["user"]}@{db_config["host"]}:{db_config["port"]}/{db_config["database"]}')

try:
    # SQLAlchemy エンジン作成
    engine = create_engine(
        f"postgresql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}",
        connect_args={
            "connect_timeout": 5,
            "application_name": "debug_test",
        },
        pool_timeout=10,
        pool_recycle=3600,
    )

    # データベース接続テスト
    with engine.connect() as conn:
        test_result = conn.execute(text("SELECT 1"))
        test_result.fetchone()
        print("✅ データベース接続成功")

    # app.pyと同じクエリを実行
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

    print("\n=== SQLクエリ実行 ===")
    df = pd.read_sql_query(query, engine)
    
    print(f"✅ データ読み込み成功: {len(df)} 件のインディーゲームデータ")
    
    if len(df) == 0:
        print("⚠️ インディーゲームデータが見つかりません")
    else:
        print(f"サンプル: {df['name'].iloc[0]} (${df['price_usd'].iloc[0]:.2f})")
        print("\n🎯 app.pyが正常に動作するはずです！")

except Exception as e:
    print(f"❌ エラー: {e}")
    print("→ デモモードに切り替わります")