# Google Cloud Run デプロイメントガイド
## Steam Indie Analytics ダッシュボード

### 📋 概要

このガイドでは、Steam Indie Analytics ダッシュボードをGoogle Cloud Runにデプロイする手順を説明します。Cloud Runを使用することで、サーバーレスでスケーラブルなWebアプリケーションとして運用できます。

### 🏗️ アーキテクチャ構成

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cloud Build   │───▶│   Cloud Run      │───▶│  Cloud SQL      │
│   (CI/CD)       │    │ (Streamlit App)  │    │ (PostgreSQL)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │  Memory Store   │
                       │    (Redis)      │
                       └─────────────────┘
```

### 🚀 デプロイ手順

#### 1. 事前準備

##### 1.1 Google Cloud Projectの設定

```bash
# Google Cloud SDKのインストール（既にインストール済みの場合はスキップ）
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Google Cloudへのログイン
gcloud auth login

# プロジェクトの作成・選択
export PROJECT_ID="your-project-id"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# 必要なAPIの有効化
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    vpcaccess.googleapis.com \
    containerregistry.googleapis.com
```

##### 1.2 ネットワーク設定（VPC コネクター）

```bash
# VPCコネクターの作成（Cloud SQL・Memory Storeへのプライベート接続用）
gcloud compute networks vpc-access connectors create steam-analytics-vpc-connector \
    --region=asia-northeast1 \
    --subnet=default \
    --subnet-project=$PROJECT_ID \
    --min-instances=2 \
    --max-instances=3 \
    --machine-type=e2-micro
```

#### 2. データベース設定

##### 2.1 Cloud SQL PostgreSQL インスタンスの作成

```bash
# Cloud SQLインスタンスの作成
gcloud sql instances create steam-analytics-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=asia-northeast1 \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04

# データベースの作成
gcloud sql databases create steam_analytics \
    --instance=steam-analytics-db

# ユーザーの作成
gcloud sql users create steam_user \
    --instance=steam-analytics-db \
    --password=your_secure_password
```

##### 2.2 Memory Store Redis インスタンスの作成

```bash
# Memory Store Redisインスタンスの作成
gcloud redis instances create steam-analytics-redis \
    --size=1 \
    --region=asia-northeast1 \
    --redis-version=redis_7_0 \
    --tier=basic
```

#### 3. Secret Manager設定

```bash
# データベースURL
echo "postgresql://steam_user:your_secure_password@/steam_analytics?host=/cloudsql/$PROJECT_ID:asia-northeast1:steam-analytics-db" | \
    gcloud secrets create database-url --data-file=-

# Steam API Key
echo "your_steam_api_key" | \
    gcloud secrets create steam-api-key --data-file=-

# Redis Password（Memory Storeの認証情報）
gcloud redis instances describe steam-analytics-redis --region=asia-northeast1 --format="value(authString)" | \
    gcloud secrets create redis-password --data-file=-

# Gemini API Key
echo "your_gemini_api_key" | \
    gcloud secrets create gemini-api-key --data-file=-
```

#### 4. Cloud Build設定

##### 4.1 サービスアカウント権限の設定

```bash
# Cloud BuildサービスアカウントのメールアドレスUID取得
export CLOUD_BUILD_SA=$(gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="value(bindings.members)" | grep "cloudbuild.gserviceaccount.com")

# 必要な権限の付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=$CLOUD_BUILD_SA \
    --role=roles/run.developer

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=$CLOUD_BUILD_SA \
    --role=roles/secretmanager.secretAccessor

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=$CLOUD_BUILD_SA \
    --role=roles/compute.networkUser

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=$CLOUD_BUILD_SA \
    --role=roles/storage.admin
```

##### 4.2 ビルドの実行

```bash
# リポジトリのクローン（またはコードの配置）
git clone https://github.com/your-username/steam-indie-analytics.git
cd steam-indie-analytics

# Cloud Buildを使用したデプロイ
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_REGION=asia-northeast1
```

#### 5. 手動デプロイ（Cloud Buildを使わない場合）

```bash
# Dockerイメージのビルドとプッシュ
docker build -f Dockerfile.cloudrun -t gcr.io/$PROJECT_ID/steam-indie-analytics .
docker push gcr.io/$PROJECT_ID/steam-indie-analytics

# Cloud Runサービスのデプロイ
gcloud run deploy steam-indie-analytics \
    --image gcr.io/$PROJECT_ID/steam-indie-analytics \
    --region asia-northeast1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 1000m \
    --max-instances 10 \
    --min-instances 0 \
    --concurrency 80 \
    --timeout 900s \
    --set-env-vars ENVIRONMENT=production,PORT=8080 \
    --set-secrets /secrets/database-url=database-url:latest,/secrets/steam-api-key=steam-api-key:latest,/secrets/redis-password=redis-password:latest \
    --vpc-connector projects/$PROJECT_ID/locations/asia-northeast1/connectors/steam-analytics-vpc-connector
```

### 📊 設定パラメータ

#### Cloud Run設定

| パラメータ | 推奨値 | 説明 |
|-----------|--------|------|
| Memory | 2Gi | Streamlit + Pandas処理用 |
| CPU | 1000m | 1vCPU相当 |
| Max Instances | 10 | スケーリング上限 |
| Min Instances | 0 | コスト最適化（コールドスタート許容） |
| Concurrency | 80 | 同時リクエスト処理数 |
| Timeout | 900s | 15分（長時間処理対応） |

#### Cloud SQL設定

| パラメータ | 推奨値 | 説明 |
|-----------|--------|------|
| Tier | db-f1-micro | 開発・小規模運用用 |
| Storage | 10GB SSD | 高速アクセス用 |
| Backup | Daily 3:00 AM | 自動バックアップ |
| Maintenance | Sunday 4:00 AM | メンテナンス時間 |

### 🔒 セキュリティ設定

#### 1. IAM設定

```bash
# Cloud Runサービスアカウントの作成
gcloud iam service-accounts create steam-analytics-runner \
    --display-name="Steam Analytics Runner"

# Cloud SQL Client権限の付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:steam-analytics-runner@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Secret Manager権限の付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:steam-analytics-runner@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### 2. ファイアウォール設定

```bash
# VPC内部通信のみ許可（デフォルトで設定済み）
# インターネットからのアクセスはCloud Run経由のみ
```

### 🔍 モニタリング・ログ

#### 1. Cloud Monitoring設定

```bash
# アラートポリシーの作成（CPU使用率）
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

#### 2. ログの確認

```bash
# Cloud Runサービスログの表示
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=steam-indie-analytics" --limit=50

# Cloud Buildログの表示
gcloud builds list --limit=10
gcloud builds log [BUILD_ID]
```

### 🚨 トラブルシューティング

#### よくある問題と解決方法

##### 1. デプロイエラー

```bash
# 問題: "Cloud Build failed"
# 解決: ログを確認
gcloud builds log [BUILD_ID]

# 問題: "Image not found"
# 解決: Container Registryの確認
gcloud container images list --repository=gcr.io/$PROJECT_ID
```

##### 2. 接続エラー

```bash
# 問題: Cloud SQL接続エラー
# 解決: VPCコネクターとSecret Managerの確認
gcloud compute networks vpc-access connectors describe steam-analytics-vpc-connector --region=asia-northeast1
gcloud secrets versions access latest --secret=database-url
```

##### 3. パフォーマンス問題

```bash
# 問題: レスポンス速度が遅い
# 解決: リソース設定の調整
gcloud run services update steam-indie-analytics \
    --region asia-northeast1 \
    --memory 4Gi \
    --cpu 2000m
```

### 💰 コスト最適化

#### 推定月額費用（小規模運用）

| サービス | 設定 | 推定費用（月額） |
|----------|------|----------------|
| Cloud Run | 2Gi/1CPU, 月間100時間稼働 | ¥500-800 |
| Cloud SQL | db-f1-micro, 10GB SSD | ¥2,000-3,000 |
| Memory Store Redis | 1GB Basic | ¥1,500-2,000 |
| Cloud Build | 月10回ビルド | ¥100-200 |
| **合計** | | **¥4,100-6,000** |

#### コスト削減のヒント

1. **Min Instances = 0**: コールドスタートを許容してコスト削減
2. **Cloud SQL**: 開発時は停止、本番のみ稼働
3. **Memory Store**: Basicプランを選択
4. **Container Registry**: 古いイメージの定期削除

### 🔄 更新・運用

#### 継続的デプロイ

```bash
# GitHubリポジトリとの連携（Cloud Build Triggers）
gcloud builds triggers create github \
    --repo-name=steam-indie-analytics \
    --repo-owner=your-username \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

#### バックアップ・復旧

```bash
# データベースバックアップの確認
gcloud sql backups list --instance=steam-analytics-db

# 特定時点への復旧
gcloud sql backups restore [BACKUP_ID] --restore-instance=steam-analytics-db
```

### 📞 サポート・リソース

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

### ✅ デプロイ完了確認

デプロイが成功すると、以下のようなURLでアクセスできます：

```
https://steam-indie-analytics-[hash]-an.a.run.app
```

ダッシュボードが正常に動作し、Steam APIからのデータ取得とPostgreSQLへの保存が確認できれば、デプロイ完了です。