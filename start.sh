#!/bin/bash

# Cloud Run起動スクリプト - Steam Indie Analytics

echo "🚀 Steam Indie Analytics starting..."
echo "📊 Environment: $ENVIRONMENT"
echo "🔌 Port: ${PORT:-8080}"
echo "🗃️ Data Source: ${DATA_SOURCE:-json}"

# 必要なファイル存在確認
if [ "$DATA_SOURCE" = "json" ] && [ ! -f "steam_indie_games_20250630_095737.json" ]; then
    echo "⚠️ WARNING: JSON data file not found, switching to Firestore"
    export DATA_SOURCE=firestore
fi

# Firestoreの認証確認
if [ "$DATA_SOURCE" = "firestore" ]; then
    echo "🔥 Firestore mode - checking authentication..."
    python -c "
from google.cloud import firestore
try:
    db = firestore.Client()
    print('✅ Firestore authentication successful')
except Exception as e:
    print(f'❌ Firestore authentication failed: {e}')
    print('🔄 Falling back to demo data mode')
    exit(0)
"
fi

echo "🎮 Starting Streamlit dashboard..."

# ファイル存在確認
echo "📁 Current directory: $(pwd)"
echo "📋 Files in current directory:"
ls -la

echo "📋 Files in src/dashboard/:"
ls -la src/dashboard/ || echo "src/dashboard/ not found"

# Streamlit起動
exec streamlit run src/dashboard/app.py \
    --server.address=0.0.0.0 \
    --server.port=${PORT:-8080} \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false