#!/bin/bash

echo "🚀 Steam Indie Analytics プロジェクト構築開始"
echo "既存のDev Container + Claude Code環境を活用します"

echo ""
echo "=== Step 1: プロジェクト構造作成 ==="

# メインプロジェクトディレクトリ構造
mkdir -p src/{config,collectors,processors,models,analyzers,dashboard}
mkdir -p src/dashboard/{pages,components}
mkdir -p {notebooks,tests,docs,scripts,sql}
mkdir -p .github/workflows

# __init__.py ファイル作成
touch src/__init__.py
touch src/config/__init__.py
touch src/collectors/__init__.py
touch src/processors/__init__.py
touch src/models/__init__.py
touch src/analyzers/__init__.py
touch src/dashboard/__init__.py
touch tests/__init__.py

echo "✅ ディレクトリ構造作成完了"

echo ""
echo "=== Step 2: 設定ファイル更新 ==="

# requirements.txt を仕様書版に更新
echo "📦 requirements.txt を更新中..."

# .gitignore作成
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
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment Variables
.env
.env.local

# Jupyter Notebook
.ipynb_checkpoints

# Database
*.db
*.sqlite3

# Docker
docker-compose.override.yml

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Data files
data/
*.csv
*.json
*.parquet

# Cache
.cache/
.pytest_cache/
EOF

# .env.example作成
cat > .env.example << 'EOF'
# Steam Web API
STEAM_API_KEY=your_steam_api_key_here

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=steam_analytics
POSTGRES_USER=steam_user
POSTGRES_PASSWORD=your_password_here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=0

# Application
DEBUG=True
LOG_LEVEL=INFO

# API Rate Limiting
STEAM_API_RATE_LIMIT=200  # requests per 5 minutes
API_RETRY_ATTEMPTS=3
API_BACKOFF_FACTOR=2
EOF

echo "✅ 設定ファイル作成完了"

echo ""
echo "=== Step 3: README更新 ==="

cat > README.md << 'EOF'
# Steam Indie Analytics - データエンジニア転職ポートフォリオ

## 🎯 プロジェクト概要

Steam APIを活用してインディーゲーム市場の分析を行い、データエンジニアリング・データ分析のスキルセットを実証するポートフォリオプロジェクト。

### 主な機能
- Steam APIからのゲームデータ自動収集
- PostgreSQLを使用したデータウェアハウス構築
- インディーゲーム市場トレンド分析
- Streamlitによるインタラクティブダッシュボード

## 🛠️ 技術スタック

- **言語**: Python 3.11
- **データベース**: PostgreSQL 15+
- **コンテナ**: Docker & Docker Compose
- **データ処理**: pandas, SQLAlchemy, pydantic
- **可視化**: Streamlit, Plotly, Seaborn
- **分析**: Jupyter, NumPy, SciPy
- **開発環境**: VS Code Dev Container + Claude Code

## 🚀 開発環境セットアップ

### 前提条件
- Docker & Docker Compose
- VS Code + Dev Containers extension
- Steam Web API Key

### セットアップ手順

1. **Dev Container起動** (既に完了)
```bash
# VS Code Dev Container内で作業
```

2. **Docker Compose環境起動**
```bash
docker-compose up -d
```

3. **環境変数設定**
```bash
cp .env.example .env
# .envファイルを編集してSteam API Keyを設定
```

4. **依存関係インストール**
```bash
pip install -r requirements.txt
```

5. **データベース初期化**
```bash
python scripts/setup_database.py
```

## 📊 使用方法

### データ収集
```bash
python scripts/run_etl.py
```

### ダッシュボード起動
```bash
streamlit run src/dashboard/app.py
```

### 分析ノートブック
```bash
jupyter lab notebooks/
```

## 🏗️ プロジェクト構造

```
steam-indie-analytics/
├── src/                     # メインソースコード
│   ├── config/             # 設定管理
│   ├── collectors/         # データ収集
│   ├── processors/         # ETL処理
│   ├── models/             # データモデル
│   ├── analyzers/          # 分析ロジック
│   └── dashboard/          # Streamlit UI
├── notebooks/              # Jupyter分析ノートブック
├── tests/                  # テストコード
├── sql/                    # SQLスクリプト
└── scripts/                # 運用スクリプト
```

## 📈 分析内容

- インディーゲーム市場の成長推移
- ジャンル別成功率・売上分析
- 価格帯別パフォーマンス比較
- 高評価ゲームの特徴抽出

## 🔧 開発ツール

- **pgAdmin**: http://localhost:8081
- **Jupyter Lab**: http://localhost:8889
- **Streamlit**: http://localhost:8501

## 🎯 転職アピールポイント

### データエンジニアリング
- APIレート制限を考慮した堅牢なデータ収集パイプライン
- PostgreSQL + Docker構成での実務想定環境
- データ品質管理・異常値検知の自動化

### ビジネス価値創出
- インディーゲーム市場の成功要因を数値化
- 開発者向け意思決定支援ツールとしての価値提供
- データドリブンな市場分析

### 技術力・学習力
- 1ヶ月での新技術スタック習得
- Claude Code活用による効率的な開発
- 自律的な問題解決プロセス

## 📝 学習ログ

開発過程での学習内容や技術選択の理由については、`docs/` ディレクトリ内のドキュメントを参照。

## 📄 ライセンス

MIT License
EOF

echo "✅ README更新完了"

echo ""
echo "=== Step 4: 次のアクション ==="
echo "1. Steam Web API Key取得: https://steamcommunity.com/dev/apikey"
echo "2. requirements.txt更新 (新しい依存関係)"
echo "3. devcontainer.json更新 (ポート設定など)"
echo "4. docker-compose.yml追加 (PostgreSQL + Redis)"
echo "5. Dev Container再ビルド"

echo ""
echo "🎉 基本構造セットアップ完了！"
echo "次は Steam API Key を取得して、Phase 1: 基盤構築 に進みましょう。"