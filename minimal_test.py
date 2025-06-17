#!/usr/bin/env python3
"""
最小限のStreamlitテストアプリ
"""

import streamlit as st

# 基本的な表示
st.title("🟢 Streamlit 動作確認")
st.write("このメッセージが見えていれば、Streamlitは正常に動作しています。")

# 現在時刻
from datetime import datetime
st.write(f"現在時刻: {datetime.now()}")

# シンプルなボタン
if st.button("クリックして確認"):
    st.success("✅ ボタンが正常に動作しています！")

# 基本的なメトリクス
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("テスト1", "OK", "✅")
with col2:
    st.metric("テスト2", "正常", "🟢")
with col3:
    st.metric("テスト3", "動作中", "🔄")

st.write("---")
st.write("もしこの画面が表示されていれば、Streamlitの基本機能は動作しています。")