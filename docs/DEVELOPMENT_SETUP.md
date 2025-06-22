# Development Setup Guide - Steam Indie Analytics

## 🛠️ 開発環境セットアップ

### 前提条件

#### 必要なソフトウェア
- **Windows 11** + **WSL2** (Ubuntu 20.04以降)
- **Docker Desktop** (WSL2バックエンド)
- **Visual Studio Code** + Dev Container Extension
- **Git** for Windows
- **Python 3.11+** (コンテナ内で管理)

#### 推奨スペック
- RAM: 8GB以上 (16GB推奨)
- Storage: 10GB以上の空き容量
- CPU: マルチコア (Docker並列処理用)

### 🚀 クイックスタート

#### 1. リポジトリクローン
```bash
# WSL2ターミナルで実行
cd /mnt/c/Users/YourName/Projects/  # または任意のディレクトリ
git clone https://github.com/yourusername/steam-indie-analytics.git
cd steam-indie-analytics
```

#### 2. Dev Container起動
```bash
# VS Code起動
code .

# Command Palette (Ctrl+Shift+P) で:
# "Dev Containers: Reopen in Container"を実行
```

#### 3. 環境変数設定
```bash
# .envファイル作成
cp .env.example .env

# エディタで編集
nano .env
```

```env
# .env設定例
STEAM_API_KEY=your_steam_api_key_here  # オプション
GEMINI_API_KEY=your_gemini_api_key_here

# Database (Dev Container自動設定)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=steam_analytics
POSTGRES_USER=steam_user
POSTGRES_PASSWORD=steam_password

# Redis (Dev Container自動設定)
REDIS_HOST=redis
REDIS_PORT=6379
```

#### 4. サービス起動確認
```bash
# 全サービス起動状態確認
docker-compose ps

# 結果例:
# postgres    running   0.0.0.0:5433->5432/tcp
# redis       running   0.0.0.0:6380->6379/tcp
# pgadmin     running   0.0.0.0:8081->80/tcp
# jupyter     running   0.0.0.0:8889->8888/tcp
```

#### 5. 接続テスト
```bash
# データベース接続テスト
python tests/test_db_connection.py

# Steam API接続テスト
python tests/test_steam_simple.py
```

### 📊 開発サービス一覧

| サービス | ポート | URL | 用途 |
|---------|--------|-----|------|
| **PostgreSQL** | 5433 | localhost:5433 | メインデータベース |
| **Redis** | 6380 | localhost:6380 | キャッシュ・セッション |
| **pgAdmin** | 8081 | http://localhost:8081 | DB管理ツール |
| **Jupyter Lab** | 8889 | http://localhost:8889 | データ分析ノートブック |
| **Streamlit** | 8501 | http://localhost:8501 | ダッシュボード |

### 🔧 詳細セットアップ

#### Dev Container構成
```json
// .devcontainer/devcontainer.json
{
  "name": "Steam Indie Analytics",
  "dockerComposeFile": ["../docker-compose.yml"],
  "service": "app",
  "workspaceFolder": "/workspace",
  
  // VS Code設定
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-python.flake8",
        "ms-python.mypy-type-checker",
        "ms-vscode.vscode-json"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.formatting.provider": "black",
        "python.linting.enabled": true,
        "python.linting.flake8Enabled": true,
        "editor.formatOnSave": true
      }
    }
  },
  
  // 転送ポート
  "forwardPorts": [8501, 8080, 5433, 6380, 8081, 8889],
  
  // 初期化スクリプト
  "postCreateCommand": ".devcontainer/post-create.sh",
  
  // コンテナユーザー
  "remoteUser": "vscode"
}
```

#### Docker Compose構成
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - .:/workspace:cached
      - vscode-server:/home/vscode/.vscode-server
    command: /bin/sh -c "while sleep 1000; do :; done"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    networks:
      - dev-network

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: steam_analytics
      POSTGRES_USER: steam_user
      POSTGRES_PASSWORD: steam_password
    ports:
      - "5433:5432"  # 競合回避
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/:/docker-entrypoint-initdb.d/
    networks:
      - dev-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6380:6379"  # 競合回避
    volumes:
      - redis_data:/data
    networks:
      - dev-network

  pgadmin:
    image: dpage/pgadmin4:latest
    restart: unless-stopped
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@steam-analytics.local
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "8081:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    networks:
      - dev-network

  jupyter:
    image: jupyter/scipy-notebook:latest
    restart: unless-stopped
    environment:
      JUPYTER_ENABLE_LAB: "yes"
      JUPYTER_TOKEN: "steam_analytics"
    ports:
      - "8889:8888"
    volumes:
      - ./notebooks:/home/jovyan/work
    networks:
      - dev-network

volumes:
  postgres_data:
  redis_data:
  pgadmin_data:
  vscode-server:

networks:
  dev-network:
    driver: bridge
```

### 🐍 Python開発環境

#### 仮想環境管理
```bash
# pipenvを使用（Dev Container内で自動設定）
pipenv install --dev

# または通常のvenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 依存関係管理
```python
# requirements.txt
# Data Engineering
pandas>=2.0.0
numpy>=1.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
redis>=4.5.0
pydantic>=2.0.0

# Web Scraping & API
aiohttp>=3.8.0
requests>=2.28.0
tenacity>=8.2.0

# Visualization
streamlit>=1.28.0
plotly>=5.15.0
seaborn>=0.12.0
matplotlib>=3.7.0

# AI Integration
google-generativeai>=0.3.0

# Development Tools
pytest>=7.4.0
black>=23.7.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.5.0

# Environment Management
python-dotenv>=1.0.0
```

#### コード品質ツール設定

**pyproject.toml**
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["src"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "plotly.*",
    "streamlit.*",
    "google.generativeai.*"
]
ignore_missing_imports = true
```

**.flake8**
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, F401
exclude = 
    .git,
    __pycache__,
    .venv,
    venv,
    .eggs,
    *.egg,
    build,
    dist
```

### 🧪 テスト環境

#### pytest設定
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=70
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

#### テスト実行
```bash
# 全テスト実行
pytest

# 特定テスト実行
pytest tests/test_db_connection.py -v

# カバレッジ付きテスト
pytest --cov=src tests/

# インテグレーションテストのみ
pytest -m integration

# 高速テストのみ
pytest -m "not slow"
```

### 🗄️ データベース開発

#### 接続確認
```bash
# Docker経由でPostgreSQL接続
docker-compose exec postgres psql -U steam_user -d steam_analytics

# または、外部から直接接続
psql -h localhost -p 5433 -U steam_user -d steam_analytics
```

#### よく使うクエリ
```sql
-- テーブル一覧
\dt

-- データ件数確認
SELECT 
    'games' as table_name, COUNT(*) as count FROM games
UNION ALL
SELECT 
    'games_normalized', COUNT(*) FROM games_normalized
UNION ALL
SELECT 
    'genres', COUNT(*) FROM genres;

-- インディーゲーム統計
SELECT 
    primary_genre,
    COUNT(*) as game_count,
    AVG(rating) as avg_rating,
    AVG(price_usd) as avg_price
FROM game_analysis_view 
WHERE rating IS NOT NULL
GROUP BY primary_genre
ORDER BY game_count DESC
LIMIT 10;
```

#### スキーマ管理
```bash
# スキーマエクスポート
pg_dump -h localhost -p 5433 -U steam_user -d steam_analytics -s > schema.sql

# データエクスポート
pg_dump -h localhost -p 5433 -U steam_user -d steam_analytics > backup.sql

# データインポート
psql -h localhost -p 5433 -U steam_user -d steam_analytics < backup.sql
```

### 🚀 Streamlit開発

#### 開発サーバー起動
```bash
# 基本起動
streamlit run src/dashboard/app.py

# デバッグモード（自動リロード）
streamlit run src/dashboard/app.py --logger.level=debug

# 外部アクセス許可
streamlit run src/dashboard/app.py --server.address=0.0.0.0
```

#### ホットリロード設定
```python
# .streamlit/config.toml
[server]
runOnSave = true
allowRunOnSave = true

[logger]
level = "debug"

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### 📊 Jupyter開発

#### アクセス方法
```bash
# 起動確認
docker-compose logs jupyter

# ブラウザでアクセス
# URL: http://localhost:8889
# Token: steam_analytics
```

#### よく使うノートブック
```python
# データ読み込みテンプレート
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import create_engine
import os

# データベース接続
DATABASE_URL = "postgresql://steam_user:steam_password@postgres:5432/steam_analytics"
engine = create_engine(DATABASE_URL)

# データ読み込み
df = pd.read_sql_query("""
    SELECT * FROM game_analysis_view 
    LIMIT 1000
""", engine)

# 基本統計
df.describe()
```

### 🔄 開発ワークフロー

#### 日常的な開発サイクル

1. **朝の環境確認**
```bash
# サービス起動確認
docker-compose ps

# 最新データ確認
python tests/test_db_connection.py

# ブランチ同期
git pull origin main
```

2. **機能開発**
```bash
# 新機能ブランチ作成
git checkout -b feature/new-analysis

# 開発・テスト
python -m pytest tests/test_new_feature.py

# コード品質チェック
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

3. **データ更新**
```bash
# 新規データ収集
python collect_indie_games.py

# データ移行
python scripts/migrate_to_normalized_schema.py

# ダッシュボード確認
streamlit run src/dashboard/app.py
```

4. **コミット・プッシュ**
```bash
# 変更ステージング
git add .

# コミット
git commit -m "Add: 新しい分析機能を実装"

# プッシュ
git push origin feature/new-analysis
```

### 🔧 トラブルシューティング

#### よくある問題と解決法

**Docker接続エラー**
```bash
# Docker Desktop起動確認
docker --version

# WSL2統合確認
docker context ls

# サービス再起動
docker-compose down && docker-compose up -d
```

**PostgreSQL接続エラー**
```bash
# コンテナ状態確認
docker-compose logs postgres

# ポート競合確認
netstat -an | grep 5433

# データベース再初期化
docker-compose down -v
docker-compose up -d postgres
```

**Python Import エラー**
```bash
# パス確認
echo $PYTHONPATH

# モジュール再インストール
pip install -r requirements.txt --force-reinstall

# キャッシュクリア
find . -type d -name __pycache__ -delete
```

**Streamlit動作不良**
```bash
# キャッシュクリア
streamlit cache clear

# 設定確認
streamlit config show

# デバッグモード起動
streamlit run src/dashboard/app.py --logger.level=debug
```

### 📚 学習リソース

#### 推奨ドキュメント
- [Streamlit Documentation](https://docs.streamlit.io/)
- [SQLAlchemy 2.0 Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

#### 実践的な学習アプローチ
1. **小さな機能から開始**: 単一グラフの追加
2. **段階的な複雑化**: データ処理→可視化→AI統合
3. **実際のデータで試行**: Steam APIデータでの実験
4. **ドキュメント化**: 実装した機能の記録

---

この開発セットアップガイドを使って、効率的な開発環境を構築し、スムーズな開発体験を実現してください。