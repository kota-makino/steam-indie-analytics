from sqlalchemy import create_engine, text
import pandas as pd
import os

# データベース接続
host = os.getenv('POSTGRES_HOST', 'postgres')
port = int(os.getenv('POSTGRES_PORT', 5432))
database = os.getenv('POSTGRES_DB', 'steam_analytics')
user = os.getenv('POSTGRES_USER', 'steam_user')
password = os.getenv('POSTGRES_PASSWORD', 'steam_password')

try:
    engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')
    
    # 修正したクエリをテスト
    query = """
    SELECT 
        app_id,
        name,
        type,
        is_free,
        price_initial,
        price_final,
        price_final::float / 100 as price_usd,
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
    LIMIT 5
    """
    
    df = pd.read_sql_query(query, engine)
    print(f'✅ クエリ成功: {len(df)}件のデータを取得')
    print()
    print('📊 取得したデータの概要:')
    print(f'ゲーム名例: {df["name"].iloc[0]}')
    print(f'価格例: ${df["price_usd"].iloc[0]:.2f}')
    print(f'プラットフォーム数例: {df["platform_count"].iloc[0]}')
    print(f'評価例: {df["rating"].iloc[0]:.1f}%')
    print()
    print('🎯 このデータでStreamlitが正常動作するはずです！')
    
except Exception as e:
    print(f'❌ エラー: {e}')