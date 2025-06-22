# Deployment Guide - Steam Indie Analytics

## 🚀 デプロイメントオプション

### 1. Streamlit Cloud (推奨)

最も簡単で費用効果的なデプロイ方法です。

#### 前提条件
- GitHubリポジトリの公開
- Streamlit Cloud アカウント
- 必要なAPIキーの準備

#### デプロイ手順

1. **リポジトリ準備**
```bash
# requirements.txtの確認
cat requirements.txt

# .streamlit/config.tomlの作成
mkdir -p .streamlit
cat > .streamlit/config.toml << 'EOF'
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
EOF
```

2. **Streamlit Cloud設定**
- https://share.streamlit.io/ にアクセス
- GitHubアカウントでサインアップ
- "New app" → リポジトリ選択
- Main file path: `src/dashboard/app.py`

3. **環境変数設定**
```
GEMINI_API_KEY=your_gemini_api_key_here
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_DB=steam_analytics
POSTGRES_USER=steam_user
POSTGRES_PASSWORD=your_password
```

4. **データベース設定**
- 外部PostgreSQLサービス（ElephantSQL、Heroku Postgres等）
- または、SQLiteへのマイグレーション

#### SQLite変換スクリプト
```python
# scripts/convert_to_sqlite.py
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

def migrate_to_sqlite():
    """PostgreSQLデータをSQLiteに移行"""
    # PostgreSQLから読み取り
    pg_engine = create_engine("postgresql://...")
    
    # SQLiteに書き込み
    sqlite_engine = create_engine("sqlite:///data/steam_analytics.db")
    
    # テーブル移行
    tables = ['games_normalized', 'genres', 'developers', 'publishers', 
              'game_genres', 'game_developers', 'game_publishers']
    
    for table in tables:
        df = pd.read_sql_table(table, pg_engine)
        df.to_sql(table, sqlite_engine, if_exists='replace', index=False)
```

### 2. Heroku Deployment

#### 必要ファイル

**Procfile**
```
web: streamlit run src/dashboard/app.py --server.port=$PORT --server.address=0.0.0.0
```

**runtime.txt**
```
python-3.11.0
```

**app.json**
```json
{
  "name": "Steam Indie Analytics",
  "description": "Steam インディーゲーム市場分析ダッシュボード",
  "repository": "https://github.com/yourusername/steam-indie-analytics",
  "env": {
    "GEMINI_API_KEY": {
      "description": "Google Gemini API Key for AI insights"
    }
  },
  "addons": [
    "heroku-postgresql:mini"
  ],
  "buildpacks": [
    {
      "url": "heroku/python"
    }
  ]
}
```

#### デプロイ手順
```bash
# Heroku CLI インストール後
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
heroku config:set GEMINI_API_KEY=your_key_here
git push heroku main
```

### 3. Docker Production Deployment

#### Production Dockerfile
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY . .

# 非rootユーザー作成
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard/app.py", "--server.address=0.0.0.0"]
```

#### Docker Compose (Production)
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8501:8501"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=steam_analytics
      - POSTGRES_USER=steam_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=steam_analytics
      - POSTGRES_USER=steam_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/:/docker-entrypoint-initdb.d/
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U steam_user -d steam_analytics"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

#### Nginx設定
```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream streamlit {
        server app:8501;
    }

    server {
        listen 80;
        server_name your-domain.com;
        
        # HTTPS リダイレクト
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://streamlit;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        # 静的ファイルキャッシュ
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### 4. AWS Deployment

#### EC2 + RDS構成

**EC2インスタンス設定**
```bash
# Amazon Linux 2
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Docker Compose インストール
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**RDS PostgreSQL設定**
- Engine: PostgreSQL 15
- Instance class: db.t3.micro (無料枠)
- Storage: 20 GB gp2
- Multi-AZ: No
- Public accessibility: No

**環境変数設定**
```bash
# EC2上で
cat > .env << 'EOF'
POSTGRES_HOST=your-rds-endpoint.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=steam_analytics
POSTGRES_USER=steam_user
POSTGRES_PASSWORD=your_secure_password
GEMINI_API_KEY=your_gemini_api_key
EOF
```

#### ECS Fargate構成

**task-definition.json**
```json
{
  "family": "steam-indie-analytics",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "streamlit-app",
      "image": "your-account.dkr.ecr.region.amazonaws.com/steam-indie-analytics:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "POSTGRES_HOST",
          "value": "your-rds-endpoint.amazonaws.com"
        }
      ],
      "secrets": [
        {
          "name": "GEMINI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:gemini-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/steam-indie-analytics",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 5. GCP Deployment

#### Cloud Run設定

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: steam-indie-analytics
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 4
      containers:
      - image: gcr.io/your-project/steam-indie-analytics
        ports:
        - containerPort: 8501
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
        env:
        - name: POSTGRES_HOST
          value: "your-cloud-sql-ip"
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: gemini-api-key
              key: key
```

**デプロイコマンド**
```bash
# Cloud SQL作成
gcloud sql instances create steam-analytics \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1

# データベース作成
gcloud sql databases create steam_analytics \
    --instance=steam-analytics

# アプリデプロイ
gcloud run deploy steam-indie-analytics \
    --image gcr.io/your-project/steam-indie-analytics \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

## 📊 データ移行・初期化

### 本番データベース初期化

```bash
# 1. スキーマ作成
psql $DATABASE_URL -f sql/create_tables.sql

# 2. インデックス作成
psql $DATABASE_URL -f sql/create_indexes.sql

# 3. データ移行
python scripts/migrate_to_normalized_schema.py

# 4. 初期データ投入
python collect_indie_games.py
```

### データバックアップ戦略

```bash
# 日次バックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL | gzip > backup_${DATE}.sql.gz

# S3へアップロード（AWS CLI設定済み）
aws s3 cp backup_${DATE}.sql.gz s3://your-backup-bucket/steam-analytics/
```

## 🔧 運用・監視

### ヘルスチェック

```python
# health_check.py
import requests
import sys

def health_check():
    try:
        response = requests.get("http://localhost:8501/_stcore/health", timeout=10)
        if response.status_code == 200:
            print("✅ Application is healthy")
            return 0
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return 1
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(health_check())
```

### ログ設定

```python
# logging_config.py
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/var/log/steam-analytics.log')
        ]
    )
```

### 監視アラート

```yaml
# prometheus/alerts.yml
groups:
- name: steam-analytics
  rules:
  - alert: AppDown
    expr: up{job="steam-analytics"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Steam Analytics app is down"
      
  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage detected"
```

## 🔐 セキュリティ設定

### SSL/TLS設定

```bash
# Let's Encrypt証明書取得
sudo certbot --nginx -d your-domain.com

# 自動更新設定
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### 環境変数管理

```bash
# AWS Systems Manager Parameter Store
aws ssm put-parameter \
    --name "/steam-analytics/gemini-api-key" \
    --value "your-api-key" \
    --type "SecureString"
```

### ファイアウォール設定

```bash
# UFW設定
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 📈 パフォーマンス最適化

### データベース最適化

```sql
-- インデックス最適化
ANALYZE games_normalized;
ANALYZE game_genres;
ANALYZE game_developers;

-- クエリ計画確認
EXPLAIN ANALYZE SELECT * FROM game_analysis_view LIMIT 100;
```

### Streamlitキャッシュ最適化

```python
# キャッシュ設定の調整
@st.cache_data(ttl=3600, max_entries=1000)
def load_heavy_data():
    # 重いデータ処理
    pass
```

### CDN設定

```yaml
# CloudFlare設定例
Page Rules:
- Pattern: your-domain.com/*
  Settings:
    - Cache Level: Standard
    - Browser Cache TTL: 1 hour
    - Security Level: Medium
```

---

このデプロイメントガイドを参考に、用途と予算に応じて最適なデプロイ方法を選択してください。開発フェーズではStreamlit Cloud、本格運用ではAWS/GCPの利用を推奨します。