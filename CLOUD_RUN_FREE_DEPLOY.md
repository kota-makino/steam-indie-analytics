# Cloud Run 無料デプロイ手順
## 既存Dockerfileそのまま使用

### 🎯 Cloud Run無料枠での実行

既存の`Dockerfile.cloudrun`と`cloudbuild.yaml`をそのまま使って**完全無料**でデプロイできます。

## 📊 無料枠の範囲

| リソース | 無料枠 | あなたのアプリ使用量 | 評価 |
|---------|--------|------------------|------|
| リクエスト数 | 200万回/月 | 数百～数千回/月 | ✅ 十分 |
| CPU時間 | 36万vCPU秒/月 | 数千秒/月 | ✅ 十分 |
| メモリ時間 | 18万GiB秒/月 | 1万GiB秒/月程度 | ✅ 十分 |
| アウトバウンド | 100GB/月 | 数GB/月 | ✅ 十分 |

**ポートフォリオレベルなら確実に無料範囲内！**

## 🚀 簡単デプロイ手順

### 1. プロジェクト準備

```bash
# Google Cloud にログイン
gcloud auth login

# プロジェクト作成
export PROJECT_ID="steam-analytics-portfolio"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# 必要なAPIを有効化
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
```

### 2. 一発デプロイ（Cloud Build使用）

```bash
# 既存のcloudbuild.yamlを使用
gcloud builds submit --config=cloudbuild.yaml
```

### 3. 手動デプロイ（Cloud Build不使用）

```bash
# Dockerイメージビルド・プッシュ
docker build -f Dockerfile.cloudrun -t gcr.io/$PROJECT_ID/steam-indie-analytics .
docker push gcr.io/$PROJECT_ID/steam-indie-analytics

# Cloud Runにデプロイ（無料枠設定）
gcloud run deploy steam-indie-analytics \
    --image gcr.io/$PROJECT_ID/steam-indie-analytics \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 5 \
    --min-instances 0 \
    --concurrency 10 \
    --timeout 300s
```

## 🗄️ データベース問題の解決

### 問題: 外部データベースは有料
- Cloud SQL PostgreSQL: 月約$25～
- Memory Store Redis: 月約$15～

### 解決: 3つの選択肢

#### 選択肢1: デモ用静的データ（推奨）
既存のJSONファイル`steam_indie_games_20250630_095737.json`を使用

```bash
# 環境変数でJSONモードに切り替え
gcloud run services update steam-indie-analytics \
    --set-env-vars DATA_SOURCE=json,JSON_FILE_PATH=steam_indie_games_20250630_095737.json
```

#### 選択肢2: $300クレジット活用
- 新規Google Cloudアカウントなら90日間$300無料
- Cloud SQL + Memory Storeも無料で試用可能

#### 選択肢3: 無料データベース代替
- **Supabase**: PostgreSQL 500MB無料
- **PlanetScale**: MySQL 5GB無料
- **Firebase**: NoSQL 1GB無料

## 🔧 app.pyの自動対応

既存の`src/dashboard/app.py`を環境変数で切り替え対応に修正:

```python
import os

# データソースの判定
DATA_SOURCE = os.getenv('DATA_SOURCE', 'database')

if DATA_SOURCE == 'json':
    # JSONファイルからデータ読み込み
    df = load_json_data()
else:
    # データベースから読み込み（既存コード）
    df = load_database_data()
```

## 📋 実際のデプロイコマンド

### パターンA: データベース付き（$300クレジット使用）

```bash
# フルスペックデプロイ
gcloud builds submit --config=cloudbuild.yaml --substitutions=_REGION=us-central1
```

### パターンB: JSON版（完全無料）

```bash
# JSON版でデプロイ
gcloud run deploy steam-indie-analytics \
    --image gcr.io/$PROJECT_ID/steam-indie-analytics \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --set-env-vars DATA_SOURCE=json
```

## 💰 実際の課金額

### 想定利用シナリオ（ポートフォリオ）
- 面接官・採用担当者が月10回アクセス
- 各セッション3分程度の閲覧
- 月間合計30分稼働

### 計算結果
- **CPU時間**: 30分 × 1CPU = 1,800秒 ← 36万秒の0.5%
- **メモリ時間**: 30分 × 1GB = 0.5GiB時間 ← 18万GiB時間の0.0003%
- **リクエスト**: 月100リクエスト ← 200万リクエストの0.005%

**👉 完全無料範囲内で運用可能**

## ✅ デプロイ成功確認

```bash
# サービス状況確認
gcloud run services list

# URLを取得
gcloud run services describe steam-indie-analytics \
    --region us-central1 \
    --format "value(status.url)"
```

デプロイされたURLは:
```
https://steam-indie-analytics-xxxxx-uc.a.run.app
```

## 🎉 まとめ

- **Dockerfile.cloudrun**: そのまま使用可能
- **cloudbuild.yaml**: そのまま使用可能  
- **無料枠**: ポートフォリオ用途なら確実に無料
- **データベース**: JSON版なら完全無料、$300クレジットなら全機能利用可能

**今すぐデプロイできます！**