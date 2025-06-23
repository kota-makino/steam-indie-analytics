# Streamlit Cloud デプロイガイド - 簡単版

## 🚀 最速デプロイ手順

### 1. 必要なファイル準備

**requirements.txtを置き換え**
```bash
# 元のrequirements.txtをバックアップ
cp requirements.txt requirements-full.txt

# Streamlit Cloud用の軽量版を使用
cp requirements-streamlit.txt requirements.txt
```

### 2. Streamlit Cloud設定

**リポジトリ情報**
- Repository: `yourusername/steam-indie-analytics`
- Branch: `main`
- Main file path: `src/dashboard/app.py`

**環境変数（Secrets）**
```toml
# Streamlit Cloudの「Settings」→「Secrets」に追加

[database]
host = "your-external-postgres-host"
port = 5432
database = "your-database-name"
username = "your-username"
password = "your-password"

[api_keys]
gemini_api_key = "your-gemini-api-key"
```

### 3. エラー対処法

#### パッケージエラーが発生した場合
```bash
# さらに軽量なrequirements.txtを作成
cat > requirements.txt << 'EOF'
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.15.0
numpy>=1.24.0
google-generativeai>=0.8.0
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
EOF
```

#### データベース接続エラーの場合
- 外部PostgreSQLサービスを使用（ElephantSQL、Supabase等）
- または、CSVファイルでのデモモード実装

### 4. デモ用軽量版の作成

```python
# src/dashboard/app.py の先頭に追加
import os

# Streamlit Cloud環境検出
IS_STREAMLIT_CLOUD = os.getenv('STREAMLIT_SHARING') or 'streamlit.io' in os.getenv('HOSTNAME', '')

if IS_STREAMLIT_CLOUD:
    st.warning("🌟 デモモード: 本番環境では外部データベースに接続されます")
    # CSVファイルからデータ読み込み
    demo_data = pd.read_csv('demo_data.csv')
```

### 5. 成功のためのチェックリスト

- [ ] requirements.txtを軽量版に変更
- [ ] 外部データベース準備（または、デモデータ用意）
- [ ] Gemini API Key取得・設定
- [ ] .streamlit/config.tomlで設定確認
- [ ] エラーハンドリング強化

## 🎯 デプロイ成功のコツ

1. **段階的デプロイ**: 最小構成から開始
2. **依存関係最小化**: 必要最小限のパッケージのみ
3. **フォールバック機能**: DB接続失敗時のデモモード
4. **ログ確認**: Streamlit Cloudのログでエラー詳細確認

デプロイが成功したら、転職活動でライブデモとして強力なアピール材料になります！