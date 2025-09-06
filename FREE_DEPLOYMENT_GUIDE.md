# 🆓 無料デプロイメントガイド
## Steam Indie Analytics - ポートフォリオ用無料ホスティング

### 🎯 概要

ポートフォリオ目的で**完全無料**でSteam Indie Analyticsダッシュボードをデプロイする方法を3つ紹介します。

---

## 🌟 方法1: Streamlit Community Cloud（最推奨）

### ✅ メリット
- **完全無料**（制限なし）
- GitHub連携で自動デプロイ
- セットアップが簡単
- カスタムドメイン対応

### 📋 手順

#### 1. GitHubリポジトリの準備
```bash
# 必要ファイルをコミット
git add Dockerfile.cloudrun-free
git add requirements-cloudrun-free.txt  
git add src/dashboard/app_standalone.py
git add steam_indie_games_20250630_095737.json
git commit -m "Add Streamlit Cloud deployment files"
git push origin main
```

#### 2. Streamlit Community Cloudにデプロイ
1. [share.streamlit.io](https://share.streamlit.io) にアクセス
2. GitHubアカウントでログイン
3. "New app" をクリック
4. リポジトリ設定:
   - **Repository**: `your-username/steam-indie-analytics`
   - **Branch**: `main`
   - **Main file path**: `src/dashboard/app_standalone.py`
5. "Deploy!" をクリック

#### 3. アクセス
```
https://your-username-steam-indie-analytics-main-app-standalone-xxx.streamlit.app
```

### 💰 コスト
**$0/月** - 完全無料

---

## 🏗️ 方法2: Cloud Run無料枠

### ✅ メリット
- Google Cloudの信頼性
- 自動スケーリング
- Docker対応

### 📊 無料枠制限
- **リクエスト**: 200万回/月
- **CPU時間**: 36万vCPU秒/月  
- **メモリ時間**: 18万GiB秒/月
- **帯域**: 100GB送信/月

ポートフォリオ用途なら**十分無料範囲内**

### 📋 手順

#### 1. プロジェクト設定
```bash
# Google Cloud SDKセットアップ
gcloud auth login
gcloud projects create your-portfolio-project
gcloud config set project your-portfolio-project

# 必要APIの有効化
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

#### 2. デプロイ実行
```bash
# 無料版でビルド・デプロイ
gcloud builds submit --config=cloudbuild-free.yaml
```

#### 3. 手動デプロイ（Cloud Build不要）
```bash
# Dockerイメージビルド
docker build -f Dockerfile.cloudrun-free -t gcr.io/your-portfolio-project/steam-analytics .
docker push gcr.io/your-portfolio-project/steam-analytics

# Cloud Runデプロイ
gcloud run deploy steam-analytics \
    --image gcr.io/your-portfolio-project/steam-analytics \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 3 \
    --min-instances 0
```

### 💰 コスト
**$0/月** - 無料枠内なら課金なし

---

## 🚀 方法3: 他の無料ホスティングサービス

### 3-1. Render.com
```yaml
# render.yaml
services:
  - type: web
    name: steam-indie-analytics
    runtime: docker
    dockerfilePath: ./Dockerfile.cloudrun-free
    plan: free
    envVars:
      - key: DATA_SOURCE
        value: local_json
```

### 3-2. Railway
```dockerfile
# Railway は Dockerfile.cloudrun-free をそのまま使用可能
```

### 3-3. Fly.io
```bash
# Fly.ioでのデプロイ
fly launch --dockerfile Dockerfile.cloudrun-free
fly deploy
```

---

## 📊 比較表

| サービス | 無料枠 | 設定難易度 | 推奨度 |
|---------|--------|-----------|--------|
| **Streamlit Cloud** | 無制限 | ⭐ 簡単 | 🥇 **最推奨** |
| **Cloud Run** | 月200万req | ⭐⭐ 普通 | 🥈 技術アピール用 |
| **Render.com** | 750時間/月 | ⭐⭐ 普通 | 🥉 代替案 |
| **Railway** | $5クレジット/月 | ⭐⭐⭐ 難 | - |
| **Fly.io** | 制限あり | ⭐⭐⭐ 難 | - |

---

## 🛠️ 無料デプロイ用ファイル構成

```
📁 無料デプロイ用ファイル
├── Dockerfile.cloudrun-free          # 軽量Docker設定
├── requirements-cloudrun-free.txt    # 最小依存関係
├── src/dashboard/app_standalone.py   # スタンドアロン版アプリ
├── cloudbuild-free.yaml             # Cloud Run用CI/CD
├── steam_indie_games_*.json          # 静的データファイル
└── FREE_DEPLOYMENT_GUIDE.md         # このガイド
```

## 🎯 ポートフォリオ向け最適化

### 📱 アプリの特徴
- **データベース不要**: JSONファイルからデータ読み込み
- **軽量設計**: 最小限の依存関係
- **高速起動**: メモリ使用量最適化
- **レスポンシブ**: モバイル対応UI

### 📊 含まれる分析機能
- 価格分析・分布
- ジャンル別人気度
- レビュー評価分析  
- 成功要因分析
- トップゲーム一覧

### 🔗 ポートフォリオ価値
- **技術スタック**: Python, Streamlit, Plotly, Pandas
- **データ処理**: API→JSON→分析の一連の流れ
- **可視化**: インタラクティブグラフ・ダッシュボード
- **デプロイ**: クラウドサービス活用

---

## 🚨 注意事項・制限

### Streamlit Community Cloud
- GitHubパブリックリポジトリ必須
- 同時ユーザー数制限あり
- カスタムドメイン要設定

### Cloud Run無料枠
- 新規プロジェクト90日間$300クレジット有効活用
- リージョンはus-central1（無料枠対象）推奨
- 10分間アクセスがないとコールドスタート

### 共通制限
- 外部データベース接続なし（静的データのみ）
- 大容量ファイルアップロード不可
- 高負荷処理は制限される可能性

---

## ✅ デプロイ成功確認

### 1. アクセステスト
- ダッシュボードがエラーなく表示される
- グラフが正しく描画される
- フィルタ機能が動作する

### 2. パフォーマンステスト
- 初回ロード時間 < 10秒
- ページ切り替え < 3秒
- モバイル表示確認

### 3. ポートフォリオ確認
- GitHub・LinkedIn リンクが正しく動作
- 技術説明が適切に表示
- データ情報が正確

---

## 📞 トラブルシューティング

### よくある問題

#### 1. Streamlit Cloud
```
Problem: "Module not found"
Solution: requirements-cloudrun-free.txt の内容確認
```

#### 2. Cloud Run
```
Problem: "Memory exceeded"
Solution: メモリを512Mi→1Giに変更
gcloud run services update steam-analytics --memory 1Gi
```

#### 3. データ読み込みエラー
```
Problem: "Data file not found"  
Solution: steam_indie_games_*.json がリポジトリに含まれているか確認
```

---

## 🎉 まとめ

ポートフォリオ目的なら**Streamlit Community Cloud**が最も簡単で確実です。

技術的なアピールを重視するなら**Cloud Run**でのデプロイを推奨します。

どちらも**完全無料**で運用可能！