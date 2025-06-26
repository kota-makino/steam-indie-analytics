# 🚀 Render完全デプロイガイド - 実データ版

開発環境と同等の本格的なSteam Analyticsシステムを渡るRenderでデプロイする手順です。

## 📋 概要

**デプロイ内容:**
- PostgreSQL 15 データベース（実データ用）
- Streamlitダッシュボード（フル機能版）
- Steam API自動データ収集
- AI分析機能（Gemini API）
- 正規化データベーススキーマ

**開発環境との差分:**
- Redis/pgAdminなし（Render制限）
- バックグラウンドデータ収集対応
- 本番用セキュリティ設定

## 🔧 事前準備

### 1. GitHubリポジトリ準備
```bash
# 全ファイルをcommit & push
git add .
git commit -m "Render本番デプロイ設定完了"
git push origin main
```

### 2. 必要なAPIキー
- **Gemini API Key**: AIサービス利用（必須）
  - 取得場所: https://makersuite.google.com/app/apikey
  - 現在の値: `AIzaSyDI5iFYRhPzgJZKC3Jom0-TqypovOWOlVY`

## 🌐 Renderでのデプロイ手順

### Step 1: Renderアカウント作成・設定

1. **Renderアカウント作成**
   ```
   https://render.com
   → Sign Up with GitHub
   → リポジトリ連携許可
   ```

2. **GitHubリポジトリ接続**
   ```
   Dashboard → Connect GitHub
   → steam-indie-analytics リポジトリ選択
   ```

### Step 2: PostgreSQLデータベース作成

1. **データベースサービス作成**
   ```
   New + → PostgreSQL
   ```

2. **設定値**
   ```yaml
   Name: steam-analytics-db
   Database Name: steam_analytics
   User: steam_user
   Region: Oregon (US West)
   PostgreSQL Version: 15
   Plan: Free ($0/month, 1GB storage)
   ```

3. **作成完了を待機**
   - 作成には3-5分かかります
   - Statusが"Available"になるまで待機

### Step 3: Webサービス作成

1. **Webサービス作成**
   ```
   New + → Web Service
   → Connect Repository: steam-indie-analytics
   ```

2. **基本設定**
   ```yaml
   Name: steam-indie-analytics
   Runtime: Python 3
   Region: Oregon (US West)
   Branch: main
   Plan: Free ($0/month)
   ```

3. **ビルド設定**
   ```yaml
   Build Command: 
   pip install -r requirements-render.txt
   python scripts/setup_database_render.py

   Start Command:
   streamlit run src/dashboard/app_render.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
   ```

### Step 4: 環境変数設定

**Environment Variables:**
```yaml
# Python設定
PYTHON_VERSION: 3.11.0
ENVIRONMENT: production
DEBUG: false
RENDER: true

# AI API設定
GEMINI_API_KEY: AIzaSyDI5iFYRhPzgJZKC3Jom0-TqypovOWOlVY

# データベース接続（自動設定）
POSTGRES_HOST: [自動設定 - データベースサービスから]
POSTGRES_PORT: [自動設定 - データベースサービスから]
POSTGRES_DB: [自動設定 - データベースサービスから]
POSTGRES_USER: [自動設定 - データベースサービスから]
POSTGRES_PASSWORD: [自動設定 - データベースサービスから]
```

**データベース接続の自動設定:**
```yaml
# この設定によりRenderが自動的にDB情報を注入
- key: POSTGRES_HOST
  fromDatabase:
    name: steam-analytics-db
    property: host
```

### Step 5: 自動デプロイ実行

1. **初回デプロイ**
   - Webサービス作成後、自動的にデプロイ開始
   - Build Logsで進捗確認

2. **デプロイ完了確認**
   ```
   Dashboard → steam-indie-analytics
   → Status: "Live" になるまで待機（10-15分）
   ```

## 📊 デプロイ後の初期設定

### 1. データベース初期化確認

アプリケーションURL（例: `https://steam-indie-analytics.onrender.com`）にアクセス:

```
✅ 期待する結果:
- サンプルデータが表示される（3件のゲーム）
- AI分析ボタンが動作する
- "📊 新しいデータを収集"ボタンが表示される
```

### 2. 実データ収集の開始

1. **ダッシュボードから収集開始**
   ```
   🤖 AI市場分析セクション
   → "📊 新しいデータを収集" ボタンクリック
   → バックグラウンド収集開始
   ```

2. **収集進捗の確認**
   - 初回収集: 10-15分で完了
   - 収集目標: 1000件のインディーゲーム
   - ページ更新で新しいデータ確認

### 3. データ品質確認

収集完了後の確認項目:
```bash
✅ ゲーム数: 500-1000件
✅ ジャンル分析データ: 複数カテゴリ
✅ AI洞察: 実データ基づく分析
✅ 価格分析: 実際の価格データ
✅ レビュー分析: 実際のSteamレビュー
```

## 🔧 高度な設定・運用

### 定期データ更新

**手動更新:**
- ダッシュボードの「📊 新しいデータを収集」ボタン使用
- 1日1回程度の更新推奨

**API制限対策:**
- Steam API: 200リクエスト/5分制限
- 自動リトライ・指数バックオフ実装済み
- 収集間隔: 0.5秒（最適化済み）

### 監視・ログ確認

**Renderダッシュボード:**
```
steam-indie-analytics サービス
→ Logs タブ
→ リアルタイムログ監視
```

**よくあるログメッセージ:**
```
✅ 正常: "✅ PostgreSQL接続成功"
✅ 正常: "✅ インディーゲーム新規収集: N件"
⚠️  注意: "🌟 デモモード" (一時的なDB接続問題)
❌ エラー: "❌ Steam API エラー" (API制限)
```

### パフォーマンス最適化

**Render Free Plan制限:**
- RAM: 512MB
- CPU: 共有
- Storage: 1GB（PostgreSQL）
- Monthly Hours: 750時間
- Sleep: 15分非アクティブで自動スリープ

**最適化設定:**
- Streamlitキャッシング有効
- PostgreSQL接続プール
- AI API呼び出しの効率化

## 🚨 トラブルシューティング

### よくある問題と解決法

#### 1. ビルドエラー
```bash
# 原因: requirements.txtの依存関係エラー
# 解決: ログ確認し、問題のあるパッケージを特定

# よくある問題:
- psycopg2 → psycopg2-binary に変更済み
- バージョン競合 → requirements-render.txt で解決済み
```

#### 2. データベース接続エラー
```bash
# 原因: データベース起動前にアプリが起動
# 解決: Renderが自動リトライ、数分待機

# デバッグ手順:
1. Logs確認: "❌ データベース接続エラー"
2. データベースStatus確認: "Available"になっているか
3. 環境変数確認: POSTGRES_* が正しく設定されているか
```

#### 3. Steam API制限
```bash
# 症状: "❌ Steam API エラー: HTTP 429"
# 対策: 自動リトライ実装済み、少し待つ

# 制限詳細:
- 200リクエスト/5分
- 自動指数バックオフ
- 失敗時のフォールバック機能
```

#### 4. AI機能エラー
```bash
# 原因: GEMINI_API_KEY未設定または無効
# 解決手順:
1. Environment Variables確認
2. APIキーの有効性確認
3. デモモードでの動作確認
```

### 緊急時の対応

**サービス停止:**
```
Dashboard → steam-indie-analytics
→ Settings → Suspend Service
```

**データバックアップ:**
```bash
# PostgreSQL接続情報でpg_dumpを使用
# External Connectionsタブで接続情報取得可能
```

**ロールバック:**
```bash
# GitHubで前のコミットにreset
git reset --hard HEAD~1
git push --force-with-lease origin main
# 自動的に再デプロイ実行
```

## 📈 成功指標

デプロイ成功の確認項目:

### ✅ 基本機能
- [ ] アプリケーションが正常に起動
- [ ] データベース接続成功
- [ ] サンプルデータ表示
- [ ] AI分析機能動作

### ✅ データ収集
- [ ] Steam APIからデータ取得
- [ ] インディーゲーム判定機能
- [ ] データベース保存機能
- [ ] 500件以上のゲーム収集

### ✅ 分析機能
- [ ] 価格分析グラフ表示
- [ ] ジャンル分析機能
- [ ] レビュー分析機能
- [ ] AI洞察生成

### ✅ 運用面
- [ ] 15分以内の自動復帰（sleep解除）
- [ ] ログ出力・監視可能
- [ ] エラー時の適切なフォールバック
- [ ] バックグラウンドタスク実行

## 🎯 完了

このガイドに従ってデプロイすることで、開発環境と同等の機能を持つSteam Analytics システムがRender上で稼働します。

**アクセスURL例:**
`https://steam-indie-analytics.onrender.com`

**主な機能:**
- 実際のSteamデータによる市場分析
- AI powered インサイト生成
- インタラクティブなデータ可視化
- リアルタイムデータ更新機能

これで本格的なデータエンジニアリングポートフォリオがクラウド環境で稼働開始です！