#!/usr/bin/env python3
"""
シンプルなStreamlitテストアプリ
ポート転送とダッシュボード動作の確認用
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="Steam Analytics - Connection Test",
    page_icon="🎮",
    layout="wide"
)

# メインタイトル
st.title("🎮 Steam Analytics - 接続テスト")
st.write(f"**現在時刻**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 接続状況確認
st.subheader("✅ 接続状況")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Streamlit", "正常", "🟢")

with col2:
    st.metric("Python", "3.9+", "🟢")

with col3:
    st.metric("ポート", "8080", "🟢")

# データベース接続テスト
st.subheader("🗄️ データベース接続テスト")

try:
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    
    load_dotenv()
    
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
    
    # 接続テスト
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as game_count FROM games;"))
        game_count = result.fetchone()[0]
        
    st.success(f"✅ データベース接続成功！収集済みゲーム数: {game_count:,}件")
    
    # 簡単な統計表示
    if game_count > 0:
        with engine.connect() as conn:
            # インディーゲーム統計
            indie_result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN genres::text LIKE '%Indie%' THEN 1 ELSE 0 END) as indie_games,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price
                FROM games 
                WHERE type = 'game';
            """))
            
            stats = indie_result.fetchone()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("総ゲーム数", f"{stats[0]:,}")
            
            with col2:
                st.metric("インディーゲーム数", f"{stats[1]:,}")
            
            with col3:
                st.metric("平均価格", f"${stats[2]:.2f}")
    
except Exception as e:
    st.error(f"❌ データベース接続エラー: {e}")

# サンプルグラフ
st.subheader("📊 サンプル可視化")

# ランダムデータでテスト
np.random.seed(42)
sample_data = pd.DataFrame({
    'Genre': ['Action', 'Adventure', 'Indie', 'Puzzle', 'Simulation'],
    'Count': np.random.randint(10, 100, 5),
    'Avg_Price': np.random.uniform(5, 30, 5)
})

col1, col2 = st.columns(2)

with col1:
    st.bar_chart(sample_data.set_index('Genre')['Count'])

with col2:
    st.line_chart(sample_data.set_index('Genre')['Avg_Price'])

# フィードバック
st.subheader("💬 動作確認")
st.info("""
**確認事項:**
- ✅ Streamlitが正常に表示されている
- ✅ リアルタイム時刻が更新されている  
- ✅ データベース統計が表示されている
- ✅ グラフが正常に描画されている

**次のステップ:**
このテストが成功したら、メインダッシュボード `src/dashboard/app.py` も同様に動作します。
""")

# 更新ボタン
if st.button("🔄 データ更新"):
    st.rerun()

st.write("---")
st.caption("Steam Analytics - Connection Test | Powered by Streamlit")