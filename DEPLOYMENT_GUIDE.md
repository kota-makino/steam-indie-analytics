# Steam Indie Analytics - デプロイメントガイド

## 📋 概要

このガイドでは、Steam Indie Analyticsプロジェクトを本番環境にデプロイする手順を説明します。

## 🚀 デプロイメント方法

### 1. Streamlit Cloud (推奨)

#### 前提条件
- GitHubアカウント
- Streamlit Cloudアカウント
- 外部データベース（PostgreSQL）
- 外部Redis（オプション）

#### 手順

1. **GitHubリポジトリの準備**
   ```bash
   # リポジトリをGitHubにプッシュ
   git add .
   git commit -m "Deploy to Streamlit Cloud"
   git push origin main
   ```

2. **Streamlit Cloudでのアプリ作成**
   - [Streamlit Cloud](https://share.streamlit.io/)にアクセス
   - 「New app」をクリック
   - GitHubリポジトリを選択
   - Main file path: `src/dashboard/app.py`
   - Python version: `3.11`

3. **環境変数設定**
   - Streamlit Cloudの「Settings」→「Secrets」で設定
   - `.streamlit/secrets.toml.example`を参考に設定

4. **外部データベース接続**
   - PostgreSQL: ElephantSQL、Heroku Postgres、AWS RDS等
   - Redis: Redis Cloud、Heroku Redis等

#### 設定例
```toml
# Streamlit Cloud Secrets
[database]
host = "your-elephantsql-host.com"
port = 5432
database = "your-database-name"
username = "your-username"
password = "your-password"

[api_keys]
steam_api_key = "your-steam-api-key"
gemini_api_key = "your-gemini-api-key"
```

### 2. Docker本番環境

#### 前提条件
- Docker & Docker Compose
- SSL証明書
- ドメイン名

#### 手順

1. **環境変数設定**
   ```bash
   # 本番用環境変数ファイル作成
   cp .env.production.example .env.production
   
   # 必要な値を設定
   nano .env.production
   ```

2. **SSL証明書配置**
   ```bash
   # SSL証明書配置
   mkdir -p nginx/ssl
   # cert.pem と key.pem を配置
   ```

3. **本番環境起動**
   ```bash
   # 本番環境起動
   docker-compose -f docker-compose.production.yml up -d
   
   # 起動確認
   docker-compose -f docker-compose.production.yml ps
   ```

4. **ヘルスチェック**
   ```bash
   # アプリケーション正常性確認
   curl -f http://localhost/health
   
   # データベース接続確認
   docker-compose -f docker-compose.production.yml exec postgres pg_isready
   ```

### 3. VPS/クラウドサーバー

#### 推奨サーバー
- **最小要件**: 2GB RAM, 2 vCPU, 20GB SSD
- **推奨**: 4GB RAM, 2 vCPU, 40GB SSD
- **OS**: Ubuntu 22.04 LTS

#### インストール手順

1. **サーバー初期設定**
   ```bash
   # システム更新
   sudo apt update && sudo apt upgrade -y
   
   # Docker インストール
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Docker Compose インストール
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **プロジェクトデプロイ**
   ```bash
   # プロジェクトクローン
   git clone https://github.com/yourusername/steam-indie-analytics.git
   cd steam-indie-analytics
   
   # 環境変数設定
   cp .env.production.example .env.production
   nano .env.production
   
   # 本番環境起動
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **ファイアウォール設定**
   ```bash
   # UFW設定
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

## 🔐 セキュリティ設定

### 1. 環境変数セキュリティ

#### 必須設定項目
```bash
# 強力なパスワード生成
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)

# APIキー設定
STEAM_API_KEY=your-steam-api-key
GEMINI_API_KEY=your-gemini-api-key
```

### 2. SSL/TLS設定

#### Let's Encrypt使用
```bash
# Certbot インストール
sudo apt install certbot python3-certbot-nginx

# SSL証明書取得
sudo certbot certonly --webroot -w /var/www/html -d yourdomain.com

# 証明書配置
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

### 3. データベースセキュリティ

#### PostgreSQL設定
```sql
-- 専用ユーザー作成
CREATE USER steam_user_prod WITH PASSWORD 'secure_password';
CREATE DATABASE steam_analytics_prod OWNER steam_user_prod;
GRANT ALL PRIVILEGES ON DATABASE steam_analytics_prod TO steam_user_prod;

-- 接続制限
ALTER USER steam_user_prod CONNECTION LIMIT 10;
```

## 📊 監視・メンテナンス

### 1. ログ監視

#### Docker Logs
```bash
# アプリケーションログ
docker-compose -f docker-compose.production.yml logs -f app

# データベースログ
docker-compose -f docker-compose.production.yml logs -f postgres

# Nginxログ
docker-compose -f docker-compose.production.yml logs -f nginx
```

### 2. バックアップ

#### データベースバックアップ
```bash
# 手動バックアップ
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U steam_user_prod steam_analytics_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 自動バックアップ（cron設定）
0 3 * * * /path/to/backup_script.sh
```

#### バックアップスクリプト例
```bash
#!/bin/bash
# backup_script.sh

BACKUP_DIR="/backup/postgres"
CONTAINER_NAME="steam_postgres_prod"
DB_NAME="steam_analytics_prod"
DB_USER="steam_user_prod"

# バックアップ実行
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 30日以上古いバックアップを削除
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

### 3. パフォーマンス監視

#### リソース使用量確認
```bash
# コンテナリソース使用量
docker stats

# システムリソース
htop
df -h
free -h
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. データベース接続エラー
```bash
# 接続確認
docker-compose -f docker-compose.production.yml exec postgres pg_isready

# ログ確認
docker-compose -f docker-compose.production.yml logs postgres
```

#### 2. Streamlitアプリ起動エラー
```bash
# アプリログ確認
docker-compose -f docker-compose.production.yml logs app

# コンテナ内部確認
docker-compose -f docker-compose.production.yml exec app bash
```

#### 3. SSL証明書エラー
```bash
# 証明書期限確認
openssl x509 -in nginx/ssl/cert.pem -text -noout | grep "Not After"

# 証明書更新
sudo certbot renew
```

### パフォーマンス最適化

#### 1. データベース最適化
```sql
-- インデックス作成
CREATE INDEX CONCURRENTLY idx_games_indie_score ON games(indie_score);
CREATE INDEX CONCURRENTLY idx_games_release_date ON games(release_date);

-- 統計情報更新
ANALYZE;
```

#### 2. Redis最適化
```bash
# Redis設定確認
docker-compose -f docker-compose.production.yml exec redis redis-cli CONFIG GET maxmemory

# メモリ使用量確認
docker-compose -f docker-compose.production.yml exec redis redis-cli INFO memory
```

## 📈 スケーリング

### 水平スケーリング

#### 1. ロードバランサー設定
```nginx
# nginx.conf
upstream streamlit_app {
    server app1:8501;
    server app2:8501;
    server app3:8501;
}
```

#### 2. データベース読み取り専用レプリカ
```yaml
# docker-compose.production.yml
services:
  postgres-replica:
    image: postgres:15-alpine
    environment:
      POSTGRES_REPLICA_MODE: slave
      POSTGRES_MASTER_SERVICE: postgres
```

### 垂直スケーリング

#### リソース増強
```yaml
# docker-compose.production.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## 🚀 CI/CD パイプライン

### GitHub Actions設定例

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/ssh-action@v0.1.5
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.KEY }}
          script: |
            cd /path/to/steam-indie-analytics
            git pull origin main
            docker-compose -f docker-compose.production.yml down
            docker-compose -f docker-compose.production.yml up -d --build
```

---

## 📞 サポート

デプロイメントで問題が発生した場合：

1. **ログの確認**: 各サービスのログを確認
2. **ヘルスチェック**: `/health`エンドポイントで正常性確認
3. **リソース確認**: CPU、メモリ、ディスク使用量を確認
4. **コンテナ状態確認**: `docker ps`でコンテナ状態を確認

成功したデプロイメントは転職活動でのアピールポイントとなります！