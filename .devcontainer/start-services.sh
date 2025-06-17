#!/bin/bash
# Dev Container内で自動起動するサービス

echo "🚀 Steam Analytics サービス自動起動中..."

# JupyterLab起動
echo "📊 JupyterLab起動中..."
jupyter lab --ip=0.0.0.0 --port=8889 --no-browser --allow-root \
    --ServerApp.token='steam_analytics' \
    --ServerApp.allow_origin='*' \
    --ServerApp.allow_remote_access=True \
    > /tmp/jupyter.log 2>&1 &

sleep 3

# 起動確認
if curl -s http://localhost:8889 > /dev/null; then
    echo "✅ JupyterLab起動完了: http://localhost:8889 (token: steam_analytics)"
else
    echo "❌ JupyterLab起動失敗"
fi

echo "🎯 アクセス方法:"
echo "  JupyterLab: http://localhost:8889/?token=steam_analytics"
echo "  ダッシュボード: notebooks/interactive_dashboard.ipynb"

# バックグラウンドで実行継続
wait