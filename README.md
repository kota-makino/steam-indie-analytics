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
