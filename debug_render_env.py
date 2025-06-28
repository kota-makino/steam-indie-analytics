#!/usr/bin/env python3
"""
Render環境デバッグ用スクリプト
環境変数と設定を確認するためのStreamlitアプリ
"""

import streamlit as st
import os
from pathlib import Path

st.set_page_config(page_title="Render環境デバッグ", page_icon="🔍")

st.title("🔍 Render環境デバッグツール")

# 環境検出ロジック（同じコードを使用）
current_dir = Path(__file__).parent
IS_RENDER = (
    os.getenv("RENDER") == "true"
    or "onrender.com" in os.getenv("RENDER_EXTERNAL_URL", "")
    or os.getenv("RENDER_SERVICE_NAME") is not None
    or "render" in os.getenv("HOSTNAME", "").lower()
)

st.markdown("## 🌐 環境検出結果")

# 環境検出の詳細
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔍 検出条件")
    st.write(f"**IS_RENDER**: {IS_RENDER}")
    
    st.markdown("#### 個別条件:")
    render_env = os.getenv("RENDER")
    st.write(f"1. RENDER == 'true': {render_env == 'true'} (値: {render_env})")
    
    render_url = os.getenv("RENDER_EXTERNAL_URL", "")
    st.write(f"2. 'onrender.com' in RENDER_EXTERNAL_URL: {'onrender.com' in render_url} (値: {render_url})")
    
    render_service = os.getenv("RENDER_SERVICE_NAME")
    st.write(f"3. RENDER_SERVICE_NAME is not None: {render_service is not None} (値: {render_service})")
    
    hostname = os.getenv("HOSTNAME", "")
    st.write(f"4. 'render' in HOSTNAME.lower(): {'render' in hostname.lower()} (値: {hostname})")

with col2:
    st.markdown("### 📊 データベース環境変数")
    
    database_url = os.getenv("DATABASE_URL")
    st.write(f"**DATABASE_URL**: {'✅ 設定済み' if database_url else '❌ 未設定'}")
    
    if database_url:
        # DATABASE_URLの詳細表示（パスワード部分は隠す）
        from urllib.parse import urlparse
        try:
            parsed_url = urlparse(database_url)
            st.markdown("#### DATABASE_URL詳細:")
            st.write(f"- Host: {parsed_url.hostname}")
            st.write(f"- Port: {parsed_url.port or 5432}")
            st.write(f"- Database: {parsed_url.path[1:] if parsed_url.path else 'N/A'}")
            st.write(f"- User: {parsed_url.username}")
            st.write(f"- Password: {'***' if parsed_url.password else 'None'}")
        except Exception as e:
            st.error(f"DATABASE_URL解析エラー: {e}")
            st.code(database_url)
    
    st.markdown("#### 個別変数:")
    postgres_vars = [
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", 
        "POSTGRES_USER", "POSTGRES_PASSWORD"
    ]
    for var in postgres_vars:
        value = os.getenv(var)
        status = "✅ 設定済み" if value else "❌ 未設定"
        display_value = "***" if "PASSWORD" in var and value else (value or "未設定")
        st.write(f"- {var}: {status} ({display_value})")

st.markdown("## 🔧 全環境変数")

# 関連する環境変数のみ表示
relevant_vars = [var for var in os.environ.keys() if any(keyword in var.upper() for keyword in 
    ["RENDER", "DATABASE", "POSTGRES", "DB", "HOST", "PORT", "USER", "PASSWORD", "URL"])]

if relevant_vars:
    st.markdown("### 📋 関連環境変数一覧")
    for var in sorted(relevant_vars):
        value = os.getenv(var)
        # パスワード系は隠す
        if any(secret in var.upper() for secret in ["PASSWORD", "SECRET", "KEY"]):
            display_value = "***" if value else "未設定"
        else:
            display_value = value or "未設定"
        st.write(f"**{var}**: {display_value}")

st.markdown("## 💡 診断結果")

if IS_RENDER:
    if database_url:
        st.success("✅ Render環境を正しく検出し、DATABASE_URLが設定されています。")
        st.info("🔧 この状況でデモモードになっている場合、データベース接続エラーまたはデータが空の可能性があります。")
    else:
        st.error("❌ Render環境ですが、DATABASE_URLが設定されていません。")
        st.info("💡 Renderダッシュボードでデータベースサービスとの接続を確認してください。")
else:
    st.warning("⚠️ Render環境として検出されていません。")
    st.info("💡 環境変数 RENDER=true または RENDER_SERVICE_NAME を設定してください。")

# 接続テストボタン
if st.button("🔗 データベース接続テスト"):
    if database_url:
        try:
            from sqlalchemy import create_engine, text
            
            with st.spinner("データベースに接続中..."):
                engine = create_engine(
                    database_url,
                    connect_args={
                        "connect_timeout": 10,
                        "application_name": "render_debug"
                    }
                )
                
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    test_result = result.fetchone()
                    
                if test_result and test_result[0] == 1:
                    st.success("✅ データベース接続成功！")
                    
                    # テーブル確認
                    try:
                        with engine.connect() as conn:
                            tables_result = conn.execute(text("""
                                SELECT table_name 
                                FROM information_schema.tables 
                                WHERE table_schema = 'public'
                                ORDER BY table_name
                            """))
                            tables = [row[0] for row in tables_result.fetchall()]
                            
                        st.info(f"📋 利用可能なテーブル: {', '.join(tables) if tables else 'なし'}")
                        
                        # gamesテーブルのデータ確認
                        if 'games' in tables:
                            try:
                                with engine.connect() as conn:
                                    count_result = conn.execute(text("SELECT COUNT(*) FROM games"))
                                    game_count = count_result.scalar()
                                    
                                    indie_result = conn.execute(text("""
                                        SELECT COUNT(*) FROM games 
                                        WHERE type = 'game' AND 'Indie' = ANY(genres)
                                    """))
                                    indie_count = indie_result.scalar()
                                    
                                st.success(f"🎮 ゲームデータ: 総数 {game_count:,}件、インディーゲーム {indie_count:,}件")
                                
                            except Exception as e:
                                st.warning(f"⚠️ ゲームデータ確認エラー: {e}")
                    except Exception as e:
                        st.warning(f"⚠️ テーブル確認エラー: {e}")
                else:
                    st.error("❌ 接続テスト失敗")
                    
        except Exception as e:
            st.error(f"❌ データベース接続エラー: {str(e)}")
            
            # エラー詳細
            with st.expander("🔍 エラー詳細"):
                st.code(str(e))
    else:
        st.error("❌ DATABASE_URLが設定されていないため、接続テストできません。")