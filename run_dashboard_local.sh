#!/bin/bash
# ローカル環境でStreamlitダッシュボードを実行するスクリプト

echo "🎮 Steam Analytics ダッシュボード起動スクリプト"
echo "================================================"

# 環境確認
echo "📋 環境確認中..."

# Python確認
if command -v python3 &> /dev/null; then
    echo "✅ Python3: $(python3 --version)"
else
    echo "❌ Python3 が見つかりません"
    exit 1
fi

# pip確認
if command -v pip3 &> /dev/null; then
    echo "✅ pip3: 利用可能"
else
    echo "❌ pip3 が見つかりません"
    exit 1
fi

# 必要なライブラリインストール
echo "📦 依存関係インストール中..."
pip3 install streamlit pandas sqlalchemy psycopg2-binary python-dotenv

# 環境変数設定確認
echo "🔧 環境変数確認中..."
if [ ! -f ".env" ]; then
    echo "⚠️  .envファイルが見つかりません。.env.exampleからコピーしてください。"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env.exampleから.envを作成しました。編集してください。"
    fi
fi

# データベース接続確認
echo "🗄️  データベース接続確認中..."
python3 -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

try:
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5433)),
        'database': os.getenv('POSTGRES_DB', 'steam_analytics'),
        'user': os.getenv('POSTGRES_USER', 'steam_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'steam_password'),
    }
    
    engine = create_engine(
        f\"postgresql://{db_config['user']}:{db_config['password']}@\"
        f\"{db_config['host']}:{db_config['port']}/{db_config['database']}\"
    )
    
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM games;'))
        count = result.fetchone()[0]
        print(f'✅ データベース接続成功: {count:,}件のゲームデータ')

except Exception as e:
    print(f'❌ データベース接続エラー: {e}')
    print('⚠️  Docker Composeでデータベースが起動しているか確認してください。')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ データベース接続に失敗しました。"
    exit 1
fi

# Streamlit起動
echo "🚀 Streamlitダッシュボード起動中..."
echo "📖 アクセス方法:"
echo "   ブラウザで http://localhost:8501 を開いてください"
echo "   停止するには Ctrl+C を押してください"
echo ""

# 使用するダッシュボードを選択
if [ -f "lightweight_dashboard.py" ]; then
    echo "🔧 軽量版ダッシュボードを起動します..."
    streamlit run lightweight_dashboard.py --server.port 8501 --server.address 0.0.0.0
elif [ -f "src/dashboard/app.py" ]; then
    echo "🎯 メインダッシュボードを起動します..."
    streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
else
    echo "❌ ダッシュボードファイルが見つかりません。"
    exit 1
fi