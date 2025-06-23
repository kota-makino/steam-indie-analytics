#!/bin/bash

# Steam Indie Analytics - Security Hardening Script
# 本番環境のセキュリティ強化スクリプト

set -e

echo "🔐 Steam Indie Analytics セキュリティ強化スクリプト"
echo "=================================================="

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. システムセキュリティ設定
log_info "1. システムセキュリティ設定を開始..."

# ファイアウォール設定
if command -v ufw &> /dev/null; then
    log_info "UFWファイアウォールを設定中..."
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow 22/tcp comment 'SSH'
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'
    sudo ufw --force enable
    log_info "ファイアウォール設定完了"
else
    log_warn "UFWが見つかりません。手動でファイアウォールを設定してください。"
fi

# SSH設定強化
if [ -f /etc/ssh/sshd_config ]; then
    log_info "SSH設定を強化中..."
    sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    
    # SSH設定の強化
    sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sudo sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config
    
    # SSH再起動
    sudo systemctl restart ssh
    log_info "SSH設定強化完了"
fi

# 2. Docker セキュリティ設定
log_info "2. Docker セキュリティ設定を開始..."

# Docker daemon設定
sudo mkdir -p /etc/docker
cat <<EOF | sudo tee /etc/docker/daemon.json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "live-restore": true,
    "userland-proxy": false,
    "no-new-privileges": true
}
EOF

# Dockerサービス再起動
sudo systemctl restart docker
log_info "Docker設定完了"

# 3. 環境変数セキュリティチェック
log_info "3. 環境変数セキュリティチェックを開始..."

# 環境変数ファイル存在確認
if [ ! -f .env.production ]; then
    log_error ".env.productionファイルが見つかりません。"
    log_info ".env.production.exampleからコピーして設定してください："
    echo "cp .env.production.example .env.production"
    exit 1
fi

# 弱いパスワードチェック
check_password_strength() {
    local password=$1
    local field_name=$2
    
    if [ ${#password} -lt 16 ]; then
        log_warn "$field_name のパスワードが短すぎます（16文字以上推奨）"
    fi
    
    if [[ ! $password =~ [A-Z] ]] || [[ ! $password =~ [a-z] ]] || [[ ! $password =~ [0-9] ]]; then
        log_warn "$field_name のパスワードは大文字、小文字、数字を含む必要があります"
    fi
}

# パスワード強度チェック
if grep -q "YOUR_SECURE_PASSWORD_HERE" .env.production; then
    log_error "デフォルトパスワードが使用されています。強力なパスワードに変更してください。"
fi

if grep -q "your-" .env.production; then
    log_error "テンプレート値が残っています。実際の値に変更してください。"
fi

log_info "環境変数チェック完了"

# 4. SSL証明書設定
log_info "4. SSL証明書設定を確認中..."

# SSL証明書ディレクトリ作成
mkdir -p nginx/ssl

# 自己署名証明書生成（開発・テスト用）
if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    log_warn "SSL証明書が見つかりません。自己署名証明書を生成します（本番環境では適切な証明書を使用してください）"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Steam Analytics/CN=localhost"
    
    log_info "自己署名証明書を生成しました"
fi

# 証明書権限設定
chmod 600 nginx/ssl/key.pem
chmod 644 nginx/ssl/cert.pem

# 5. データベースセキュリティ設定
log_info "5. データベースセキュリティ設定を開始..."

# PostgreSQL設定ファイル作成
mkdir -p postgresql/conf.d
cat <<EOF > postgresql/conf.d/security.conf
# PostgreSQL セキュリティ設定
ssl = on
password_encryption = scram-sha-256
log_connections = on
log_disconnections = on
log_statement = 'mod'
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
shared_preload_libraries = 'pg_stat_statements'
EOF

log_info "PostgreSQLセキュリティ設定完了"

# 6. アプリケーションセキュリティ設定
log_info "6. アプリケーションセキュリティ設定を開始..."

# セキュリティヘッダー設定確認
if [ -f nginx/nginx.conf ]; then
    if grep -q "X-Frame-Options" nginx/nginx.conf; then
        log_info "セキュリティヘッダーが設定されています"
    else
        log_warn "nginx.confにセキュリティヘッダーが設定されていません"
    fi
fi

# 7. ログ設定
log_info "7. ログ設定を開始..."

# ログローテーション設定
sudo mkdir -p /etc/logrotate.d
cat <<EOF | sudo tee /etc/logrotate.d/steam-analytics
/var/log/steam-analytics/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

# ログディレクトリ作成
sudo mkdir -p /var/log/steam-analytics
sudo chown $USER:$USER /var/log/steam-analytics

log_info "ログ設定完了"

# 8. システム監視設定
log_info "8. システム監視設定を開始..."

# fail2ban インストール（オプション）
if command -v apt-get &> /dev/null; then
    if ! command -v fail2ban-server &> /dev/null; then
        log_info "fail2banをインストール中..."
        sudo apt-get update
        sudo apt-get install -y fail2ban
        
        # fail2ban設定
        cat <<EOF | sudo tee /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
EOF
        
        sudo systemctl enable fail2ban
        sudo systemctl start fail2ban
        log_info "fail2ban設定完了"
    fi
fi

# 9. バックアップスクリプト作成
log_info "9. バックアップスクリプトを作成中..."

cat <<'EOF' > backup_production.sh
#!/bin/bash

# Steam Indie Analytics バックアップスクリプト

BACKUP_DIR="/backup/steam-analytics"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# データベースバックアップ
docker-compose -f docker-compose.production.yml exec -T postgres pg_dump -U steam_user_prod steam_analytics_prod | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 設定ファイルバックアップ
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz .env.production nginx/ postgresql/

# 古いバックアップ削除（30日以上）
find $BACKUP_DIR -name "*backup_*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*backup_*.tar.gz" -mtime +30 -delete

echo "バックアップ完了: $BACKUP_DIR"
EOF

chmod +x backup_production.sh
log_info "バックアップスクリプト作成完了"

# 10. セキュリティチェックリスト出力
log_info "10. セキュリティチェックリストを作成中..."

cat <<EOF > SECURITY_CHECKLIST.md
# Steam Indie Analytics - セキュリティチェックリスト

## ✅ 完了済み項目

### システムセキュリティ
- [ ] ファイアウォール設定（UFW）
- [ ] SSH設定強化（パスワード認証無効、root無効）
- [ ] システム更新
- [ ] fail2ban設定（SSH、Nginx）

### Docker セキュリティ
- [ ] Docker daemon設定
- [ ] コンテナ権限制限
- [ ] ログ設定

### 環境変数・認証
- [ ] 強力なパスワード設定
- [ ] APIキー適切設定
- [ ] 環境変数ファイル権限設定（600）

### SSL/TLS
- [ ] SSL証明書設定
- [ ] Let's Encrypt または商用証明書
- [ ] HTTPS強制リダイレクト

### データベース
- [ ] PostgreSQL専用ユーザー作成
- [ ] 接続制限設定
- [ ] ログ設定
- [ ] 暗号化設定

### アプリケーション
- [ ] セキュリティヘッダー設定
- [ ] CORS設定
- [ ] レート制限設定
- [ ] エラーページ設定

### 監視・ログ
- [ ] ログローテーション設定
- [ ] システム監視
- [ ] アクセスログ分析
- [ ] 異常検知設定

### バックアップ・復旧
- [ ] 自動バックアップ設定
- [ ] バックアップ検証
- [ ] 復旧手順文書化
- [ ] 災害復旧計画

## 🔧 手動設定が必要な項目

1. **商用SSL証明書の設定**
   - Let's Encrypt または商用証明書の取得
   - 証明書の自動更新設定

2. **外部監視サービス**
   - UptimeRobot、DataDog等の設定
   - アラート通知設定

3. **バックアップ先設定**
   - AWS S3、Google Cloud Storage等
   - 暗号化バックアップ

4. **セキュリティスキャン**
   - 脆弱性スキャンの定期実行
   - ペネトレーションテスト

## 🚨 定期チェック項目

### 毎日
- [ ] システムリソース使用量
- [ ] エラーログ確認 
- [ ] バックアップ実行確認

### 毎週
- [ ] セキュリティアップデート確認
- [ ] SSL証明書期限確認
- [ ] ログ分析

### 毎月
- [ ] パスワード強度チェック
- [ ] アクセス権限監査
- [ ] バックアップ復旧テスト

EOF

log_info "セキュリティチェックリスト作成完了"

# 完了メッセージ
echo ""
echo "🎉 セキュリティ強化スクリプト実行完了！"
echo ""
echo "📋 次のステップ："
echo "1. .env.production ファイルの内容を確認・修正"
echo "2. SSL証明書を商用証明書に置換（推奨）"
echo "3. SECURITY_CHECKLIST.md の項目を確認"
echo "4. バックアップスクリプトをcronに追加"
echo ""
echo "🔐 セキュリティは継続的な取り組みです。定期的にチェックリストを確認してください。"