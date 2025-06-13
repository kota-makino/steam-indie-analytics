#!/bin/bash

echo "🚀 Post-create script starting..."

# Python依存関係のインストール
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
else
    echo "📦 Installing basic Python packages..."
    pip install streamlit pandas numpy psycopg2-binary redis sqlalchemy requests beautifulsoup4 plotly seaborn scikit-learn
fi

# プロジェクト構造の作成
echo "📁 Creating project structure..."
mkdir -p src/{data_collection,analysis,models,api,utils}
mkdir -p notebooks/{exploration,analysis,reports}
mkdir -p data/{raw,processed,external}
mkdir -p sql/{migrations,queries,views}
mkdir -p tests/{unit,integration}
mkdir -p docs/{api,user_guide}

# .gitignore作成
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/settings.json
.idea/
*.swp
*.swo

# Data files
*.csv
*.json
*.xlsx
data/raw/*
data/processed/*
!data/raw/.gitkeep
!data/processed/.gitkeep

# Docker
docker_volumes/

# Claude Code
.claude/

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# API Keys
.env.local
.env.production
EOF
fi

# gitkeepファイルの作成
echo "📁 Creating .gitkeep files..."
touch data/raw/.gitkeep
touch data/processed/.gitkeep
touch data/external/.gitkeep

# Claude Code設定確認
echo "🤖 Checking Claude Code installation..."
if command -v claude &> /dev/null; then
    echo "✅ Claude Code is installed: $(claude --version)"
    echo "💡 Run 'claude auth login' to authenticate if needed"
else
    echo "❌ Claude Code not found in PATH"
fi

# 開発環境情報表示
echo ""
echo "🎉 Development environment setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Python: $(python --version)"
echo "🟢 Node.js: $(node --version)"
echo "📦 npm: $(npm --version)"
echo "🤖 Claude Code: $(claude --version 2>/dev/null || echo 'Not authenticated')"
echo "🐘 PostgreSQL: Available at localhost:5433"
echo "🔴 Redis: Available at localhost:6380"
echo "🔧 pgAdmin: http://localhost:8081"
echo "📊 Jupyter: http://localhost:8889"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Ready for development!"
echo "💡 Tip: Run 'claude auth login' to set up Claude Code"