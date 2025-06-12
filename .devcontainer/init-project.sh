#!/bin/bash

echo "🚀 Initializing Indie Game Analysis Project..."

# package.json作成（存在しない場合のみ）
if [ ! -f package.json ]; then
    npm init -y
    npm pkg set devDependencies.@anthropic-ai/claude-code="^1.0.19"
    npm pkg set scripts.claude="claude-code"
    npm pkg set scripts.dev="streamlit run src/app.py"
    echo "✅ package.json created"
fi

# プロジェクト構造作成
mkdir -p {src/{data_collectors,processors,analyzers,models,visualizers},notebooks,docs,tests}

# サンプルファイル作成（存在しない場合のみ）
if [ ! -f src/data_collectors/steam_collector.py ]; then
    cat > src/data_collectors/__init__.py << 'PYEOF'
"""Steam data collection modules."""
PYEOF

    echo "📝 Basic project structure created"
fi

# .gitignore作成（存在しない場合のみ）
if [ ! -f .gitignore ]; then
    cat > .gitignore << 'GITEOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv
.env

# Data files
data/
*.csv
*.json
*.xlsx

# Jupyter Notebook
.ipynb_checkpoints

# VS Code
.vscode/

# OS
.DS_Store
Thumbs.db

# Project specific
logs/
temp/
GITEOF
    echo "✅ .gitignore created"
fi

# Git初期化（存在しない場合のみ）
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit with automated Dev Container setup"
    echo "✅ Git repository initialized"
fi

echo ""
echo "🎮 Indie Game Success Predictor - Ready for Development!"
echo "Try: claude-code 'Create a Steam API data collector'"
echo ""
