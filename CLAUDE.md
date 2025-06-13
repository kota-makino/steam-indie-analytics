# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Steam Indie Analytics - データエンジニア転職ポートフォリオ

## プロジェクト概要

### 目的
Steam APIを活用してインディーゲーム市場の分析を行い、データエンジニアリング・データ分析のスキルセットを実証するポートフォリオプロジェクト。生成AI活用企業への転職を目指し、実務レベルのデータパイプライン構築から可視化まで一貫して実装する。

### ターゲット
- データエンジニア職（特に生成AI活用企業）
- 開発期間：1ヶ月以内
- 既存経験：Java SE経験、Python初級〜中級、業務効率化ツール開発経験

## 技術構成

### Core Stack（必須実装）
```yaml
Language: Python 3.9+
Database: PostgreSQL 15+
Container: Docker & Docker Compose
Version Control: Git & GitHub
Environment: Windows 11 + WSL2
```

### Data Engineering Stack
```yaml
Data Collection:
  - requests (Steam API連携)
  - schedule (定期実行)
  - python-dotenv (環境変数管理)

Data Processing:
  - pandas (データ変換・集計)
  - sqlalchemy (ORM・DB操作)
  - pydantic (データバリデーション)

Infrastructure:
  - Docker Compose (ローカル環境)
  - PostgreSQL (データウェアハウス)
  - Redis (キャッシュ・セッション管理)
```

### Analytics & Visualization Stack
```yaml
Analysis:
  - jupyter (探索的データ分析)
  - numpy (数値計算)
  - scipy (統計処理)

Visualization:
  - streamlit (ダッシュボード)
  - plotly (インタラクティブグラフ)
  - seaborn (統計可視化)

Quality Assurance:
  - pytest (テスト)
  - black (コードフォーマット)
  - flake8 (リンター)
```

## データ分析設計

### 1. データ収集戦略
```yaml
Steam Web API使用:
  - GetAppList: ゲーム一覧取得
  - GetAppDetails: 詳細情報取得
  - GetReviews: レビューデータ取得
  - GetSteamSpy: 売上・プレイヤー数推定

収集対象:
  - インディーゲーム全般（タグベースフィルタリング）
  - リリース日：2020年以降
  - データ更新頻度：週次バッチ処理

API制限対策:
  - レート制限遵守（200req/5min）
  - 指数バックオフ再試行
  - データキャッシュ戦略
```

### 2. 分析テーマ
```yaml
Market Trend Analysis:
  - インディーゲーム市場の成長推移
  - ジャンル別成功率・売上分析
  - 価格帯別パフォーマンス比較
  - 季節性・リリースタイミング分析

Success Factor Analysis:
  - 高評価ゲームの特徴抽出
  - タグ組み合わせ効果分析
  - 開発者規模と成功率相関
  - レビュー傾向と売上の関係

Business Intelligence:
  - 競合分析ダッシュボード
  - 市場ポジショニング可視化
  - トレンド予測レポート
```

### 3. データモデル設計
```sql
-- Primary Tables
games: ゲーム基本情報
developers: 開発者情報
genres_tags: ジャンル・タグマスタ
reviews: レビューデータ
sales_metrics: 売上・プレイヤー数推定

-- Analysis Views
market_trends: 市場トレンド集計
success_metrics: 成功指標計算
competitive_analysis: 競合分析用
```

## プロジェクト構成

```
steam-indie-analytics/
├── README.md                    # プロジェクト説明・セットアップ
├── claude.md                    # 本仕様書
├── requirements.txt             # Python依存関係
├── docker-compose.yml           # 開発環境設定
├── .env.example                 # 環境変数テンプレート
├── .github/workflows/           # CI/CD設定
│
├── src/
│   ├── __init__.py
│   ├── config/                  # 設定管理
│   │   ├── settings.py
│   │   └── database.py
│   ├── collectors/              # データ収集
│   │   ├── steam_api.py
│   │   ├── rate_limiter.py
│   │   └── data_validator.py
│   ├── processors/              # ETL処理
│   │   ├── etl_pipeline.py
│   │   ├── data_cleaner.py
│   │   └── feature_engineer.py
│   ├── models/                  # データモデル
│   │   ├── database_models.py
│   │   └── pydantic_models.py
│   ├── analyzers/               # 分析ロジック
│   │   ├── market_analyzer.py
│   │   ├── success_analyzer.py
│   │   └── trend_analyzer.py
│   └── dashboard/               # Streamlit UI
│       ├── app.py
│       ├── pages/
│       └── components/
│
├── notebooks/                   # 探索的データ分析
│   ├── 01_data_exploration.ipynb
│   ├── 02_market_analysis.ipynb
│   ├── 03_success_factors.ipynb
│   └── 04_visualization_prototypes.ipynb
│
├── tests/                       # テストコード
│   ├── test_collectors.py
│   ├── test_processors.py
│   └── test_analyzers.py
│
├── docs/                        # ドキュメント
│   ├── architecture.md
│   ├── api_documentation.md
│   └── deployment_guide.md
│
├── scripts/                     # 運用スクリプト
│   ├── setup_database.py
│   ├── run_etl.py
│   └── backup_data.py
│
└── sql/                         # SQLスクリプト
    ├── create_tables.sql
    ├── create_indexes.sql
    └── analysis_views.sql
```

## 実装フェーズ

### Phase 1: 基盤構築（1週目）
```yaml
Priority: High
Tasks:
  - Steam Web API Key取得・テスト
  - Docker環境構築
  - PostgreSQL設定・接続確認
  - 基本的なETLパイプライン実装
  - ログ・エラーハンドリング実装

Deliverables:
  - 動作するデータ収集スクリプト
  - データベーススキーマ
  - 基本的なCI/CD設定
```

### Phase 2: データ分析（2週目）
```yaml
Priority: High
Tasks:
  - Jupyter Notebookでの探索的データ分析
  - 市場トレンド分析実装
  - 成功要因分析実装
  - データ品質チェック・改善

Deliverables:
  - 分析結果ノートブック
  - 洞察レポート
  - データ品質レポート
```

### Phase 3: 可視化・ダッシュボード（3週目）
```yaml
Priority: High
Tasks:
  - Streamlitダッシュボード開発
  - インタラクティブ可視化実装
  - ユーザビリティ改善
  - パフォーマンス最適化

Deliverables:
  - 完成したダッシュボード
  - デプロイ可能なアプリケーション
```

### Phase 4: 仕上げ・ドキュメント（4週目）
```yaml
Priority: Medium
Tasks:
  - README・ドキュメント整備
  - コードリファクタリング
  - テストカバレッジ向上
  - デプロイ・運用準備

Deliverables:
  - 完成したポートフォリオ
  - 技術ドキュメント
  - 面接用プレゼン資料
```

## 面接アピール戦略

### データエンジニアリング観点
```yaml
Technical Skills:
  - "APIレート制限を考慮した堅牢なデータ収集パイプライン設計"
  - "PostgreSQL + Docker構成での実務想定環境構築"
  - "データ品質管理・異常値検知の自動化実装"
  - "バッチ処理でのスケーラビリティ考慮"

Process & Quality:
  - "要件定義から運用まで一人称での実装経験"
  - "テスト駆動開発によるコード品質確保"
  - "Git/GitHub を使った開発フロー実践"
```

### ビジネス価値創出
```yaml
Problem Solving:
  - "インディーゲーム市場の不透明な成功要因を数値化"
  - "開発者向け意思決定支援ツールとしての価値提供"
  - "データドリブンな市場分析による新規参入支援"

Communication:
  - "非技術者でも理解しやすい可視化設計"
  - "ビジネス課題から技術選択までの論理的説明"
```

### 生成AI企業への適合性
```yaml
Learning Ability:
  - "1ヶ月という短期間での新技術スタック習得"
  - "未経験領域への積極的な取り組み姿勢"
  - "自律的な問題解決・学習プロセス"

Technology Adoption:
  - "Claude Code活用による効率的な開発プロセス"
  - "AI支援を活用した高速プロトタイピング"
  - "技術進歩に対する柔軟な適応力"
```

## 成功指標

### 技術的成果物
- [ ] 安定動作するETLパイプライン
- [ ] 1000件以上のゲームデータ収集・分析
- [ ] インタラクティブダッシュボード完成
- [ ] テストカバレッジ70%以上

### 面接での訴求力
- [ ] 技術選択理由の明確な説明
- [ ] 実務を想定した設計思想の提示
- [ ] ビジネス価値創出の具体例提示
- [ ] 継続的改善・拡張の提案

## コーディングルール

### Cursor IDEエラー対応
```yaml
コードスタイル:
  - 型ヒント必須（Pythonのmypyに準拠）
  - import文は自動整理（isort準拠）
  - PEP8準拠のコードフォーマット（black準拠）
  - 未使用変数・未使用import文の排除

Lintツール設定:
  - flake8: コードリンター（E203, W503は無視設定）
  - mypy: 型チェック（strict設定）
  - black: コードフォーマッター（88文字幅）
  - isort: import文自動整理

エラー回避:
  - function annotations: すべての関数に型ヒント
  - variable annotations: 複雑な変数に型ヒント
  - try-except: 例外処理の明示的な型指定
  - Optional/Union: None許可時の明示的な型宣言
```

### 依存関係管理
```yaml
新規ライブラリ追加ルール:
  1. requirements.txtに必ず追記
  2. バージョン固定（セキュリティ確保）
  3. 日本語コメントで用途説明
  4. カテゴリ別に整理（既存パターンに従う）

追記フォーマット:
  library-name==x.x.x         # 用途説明（日本語）

禁止事項:
  - 手動pip installでの一時的インストール
  - バージョン未固定でのrequirementsへの記載
  - 本番環境に不要な開発用ライブラリの混在
  
コンテナ起動時の自動化:
  - requirements.txtの変更は即座にコンテナに反映
  - 手動でのライブラリインストール作業を撲滅
  - Dev Container環境での一元管理
```

## 開発・学習方針

### コード品質・可読性
```yaml
Documentation Language: 日本語
- コメント：すべて日本語で記述
- README：日本語での詳細説明
- 変数名・関数名：英語（業界標準に準拠）
- ドキュメント：日本語での技術解説

Code Comments Policy:
- 学習目的のため、コードの意図・動作を詳細にコメント
- 初心者が理解できるレベルでの説明を心がける
- なぜそのロジックを選択したかの理由も記載
- 技術選択の背景・トレードオフも説明

Example Comment Style:
"""
Steam APIからゲームデータを取得する関数

Args:
    app_id (int): Steamアプリケーションのユニークな識別子
    retry_count (int): API呼び出し失敗時の再試行回数（デフォルト: 3）
    
Returns:
    dict: ゲーム詳細情報のJSON形式データ
    None: API呼び出し失敗時
    
Note:
    - Steam APIのレート制限（200req/5min）を考慮してsleep処理を実装
    - pydanticモデルでデータバリデーションを行い、型安全性を確保
    - 実務では外部API呼び出しの例外処理が重要なため、詳細なエラーハンドリングを実装
"""
```

### 学習支援コメント
```python
# 【学習ポイント】なぜsqlalchemyのORM（Object-Relational Mapping）を使うのか？
# 1. SQLインジェクション攻撃の防止（セキュリティ）
# 2. データベース種別の差異を吸収（ポータビリティ）
# 3. Pythonオブジェクトとして直感的に操作可能（開発効率）
# 4. 実務でよく使われる技術のため転職活動でアピール可能

# 【実務Tips】with文を使う理由
# データベース接続は必ずwith文でリソース管理を行う
# 処理が成功/失敗にかかわらず、確実にコネクションが閉じられる
with get_db_session() as session:
    # この中でDB操作を行う
    pass  # 自動的にコネクションが閉じられる
```

### README構成方針
```yaml
Target Audience: 
  - 採用担当者（技術背景なし）
  - エンジニア（技術レビュー）
  - 自分自身（学習記録・振り返り）

Content Structure:
1. プロジェクト概要（30秒で理解できる要約）
2. デモ・スクリーンショット（視覚的な成果物）
3. 技術選択理由（なぜその技術を選んだか）
4. 実装で学んだこと（学習成果の言語化）
5. 課題と改善案（次のステップへの思考）
6. セットアップ手順（再現可能な環境構築）

Japanese Technical Writing:
- 専門用語は英語＋日本語説明併記
- 図表を活用した分かりやすい説明
- 実務での応用方法も言及
```

このプロジェクトを通じて、データエンジニアとしての基礎力と、生成AI時代に求められる学習力・適応力を実証し、転職成功につなげていきます。

---

## Claude Code 作業ガイド

### 開発コマンド

#### 環境セットアップ
```bash
# Docker環境起動（開発用サービス含む）
docker-compose --profile dev up -d

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envを編集してSTEAM_API_KEYを設定

# データベース初期化
python scripts/setup_database.py
```

#### 日常的な開発作業
```bash
# シンプル接続テスト（Steam API & DB確認）
python tests/test_steam_simple.py

# データベース接続テスト
python tests/test_db_connection.py

# ETLパイプライン実行
python scripts/run_etl.py

# インディーゲーム収集スクリプト（直接実行）
python collect_indie_games.py

# ダッシュボード起動
streamlit run src/dashboard/app.py

# Jupyter Lab起動 (コンテナが起動していれば http://localhost:8889)
jupyter lab notebooks/

# テスト実行
pytest --cov=src tests/

# 特定テスト実行
pytest tests/test_steam_simple.py -v
pytest tests/test_db_connection.py -v

# コード品質チェック（個別実行）
black src/ tests/                          # コードフォーマット
isort src/ tests/                          # import文整理
flake8 src/ tests/ --max-line-length=88    # リンター
mypy src/                                  # 型チェック

# コード品質チェック（一括実行）
black src/ tests/ && isort src/ tests/ && flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503 && mypy src/
```

### 重要な設定情報

#### ポート番号
- **PostgreSQL**: localhost:5433（競合回避のため5432ではない）
- **Redis**: localhost:6380（競合回避のため6379ではない）
- **pgAdmin**: http://localhost:8081 (admin@steam-analytics.local / admin123)
- **Jupyter Lab**: http://localhost:8889 (token: steam_analytics)
- **Streamlit**: http://localhost:8501

#### 現在のプロジェクト状況
- `collect_indie_games.py`: プロジェクトルートにあるメインスクリプト
- `tests/test_steam_simple.py`: Steam API & DB接続のシンプルテスト
- `tests/test_db_connection.py`: データベース接続専用テスト
- `src/collectors/`: Steam API収集ロジック実装済み
- `scripts/`: 各種運用スクリプト（一部未実装の可能性）

#### API制限
- **Steam API**: 200リクエスト/5分の制限
- `src/collectors/`でレート制限とリトライ処理を実装済み
- 指数バックオフによる再試行ロジック

#### データベース構成
- **接続**: SQLAlchemy 2.0 + psycopg2-binary
- **ORM**: 非同期対応のSQLAlchemyモデル
- **マイグレーション**: Alembicを使用

### トラブルシューティング

#### よくある問題
1. **PostgreSQL接続エラー**
   - ポート5433が使用可能か確認
   - Docker Composeサービスが起動しているか確認
   - `.env`ファイルの設定値を確認

2. **Steam API制限エラー**
   - API Keyが有効か確認
   - レート制限に達していないか確認
   - `tenacity`による自動リトライが動作しているか確認

3. **Docker権限問題**
   - `docker_volumes/`ディレクトリの権限確認
   - WSL2環境でのファイル権限設定

#### デバッグ手順
```bash
# Docker Composeサービス状態確認
docker-compose ps

# PostgreSQL接続テスト
docker-compose exec postgres pg_isready -U steam_user -d steam_analytics

# Redis接続テスト
docker-compose exec redis redis-cli ping

# ログ確認
docker-compose logs postgres
docker-compose logs redis
```

### コード作業時の注意点

#### コードスタイル
- **コメント**: 日本語で詳細に記述（学習目的）
- **変数・関数名**: 英語（Python標準）
- **型ヒント**: 必須（mypy対応）
- **docstring**: 日本語で詳細な説明

#### ファイル配置規約
- **テストコード**: 必ず`tests/`ディレクトリ内に配置
- **テストファイル名**: `test_*.py`または`*_test.py`形式
- **テスト実行**: `pytest`コマンドを使用
- **設定ファイル**: プロジェクトルートに配置（`.env`, `requirements.txt`等）
- **一時的なテストファイル**: プロジェクトルートではなく`tests/`または`/tmp/`に配置

```bash
# 正しいテストファイル配置例
tests/
├── __init__.py
├── test_db_connection.py      # データベース接続テスト
├── test_collectors.py         # Steam APIコレクターテスト
├── test_processors.py         # データ処理テスト
└── test_analyzers.py          # 分析ロジックテスト

# テスト実行
pytest tests/                  # 全テスト実行
pytest tests/test_db_connection.py -v  # 特定テスト実行
pytest --cov=src tests/        # カバレッジ付きテスト実行
```

#### テスト戦略
- 外部API呼び出しはmock化
- データベーステストはトランザクション分離
- カバレッジ70%以上を目標

#### 実装パターン
```python
# データベース操作の基本パターン
async def get_game_data(session: AsyncSession, app_id: int) -> Optional[Game]:
    """Steam APIからゲームデータを取得し、DBに保存する
    
    Args:
        session: データベースセッション
        app_id: SteamアプリケーションID
        
    Returns:
        ゲームデータまたはNone（エラー時）
    """
    # 実装...

# API呼び出しの基本パターン（レート制限対応）
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def fetch_steam_api(url: str) -> dict:
    """Steam APIを呼び出す（リトライ機能付き）"""
    # 実装...
```

### コードフォーマット自動化

#### 事前設定
```bash
# 開発時にrequirements.txtから自動インストール
pip install -r requirements.txt

# 設定ファイルの確認
# .flake8, pyproject.toml, .isort.cfg などの設定ファイルが有効
```

#### 全ファイル一括フォーマット
```bash
# 1. 全Pythonファイルの自動フォーマット実行
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" | xargs black --line-length=88
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" | xargs isort

# 2. リンターによるエラーチェック
flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503,F401

# 3. 型チェック実行
mypy src/ --ignore-missing-imports
```

#### Claude Code生成ファイルの自動適用
```yaml
コード生成時の必須適用事項:
  - 生成された全PythonファイルはBLACK準拠フォーマット（88文字）を自動適用
  - すべての関数・メソッドに型ヒント（Type Hints）を必須で付与
  - Import文はISORT準拠で自動整理・アルファベット順
  - FLAKE8リンター準拠でコード品質チェック通過状態で生成
  - 未使用import・変数の除去を自動実行
  - PEP8準拠のコードスタイルを保持

生成ファイルの品質保証:
  - 生成後に手動でのフォーマット作業が不要な状態で提供
  - requirements.txtへの依存関係自動追記
  - 日本語コメントでの学習用詳細説明付与
  - エラーハンドリング・ログ出力の適切な実装

禁止事項:
  - フォーマット未適用でのファイル生成
  - 型ヒント不足でのコード提供
  - Import文の手動整理が必要な状態での納品
  - Lint警告が残存した状態でのファイル生成
```

#### VS Code/Cursor IDE設定
```json
// settings.json に追加推奨設定
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.sortImports.args": ["--profile", "black"],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": [
        "--max-line-length=88",
        "--extend-ignore=E203,W503"
    ],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### Pre-commit Hook設定（推奨）
```bash
# pre-commitのインストールと設定
pip install pre-commit
pre-commit install

# .pre-commit-config.yaml が自動実行される
# 各コミット前に自動でフォーマットとリンターが実行
```

### Dev Container環境設定

#### Docker Compose連携
プロジェクトはDev ContainerとDocker Composeを連携させて動作します：

```yaml
# .devcontainer/devcontainer.json の重要設定
{
  "dockerComposeFile": ["../docker-compose.yml"],
  "service": "app",
  "forwardPorts": [8501, 8080, 5433, 6380, 8081, 8889],
  "postCreateCommand": ".devcontainer/post-create.sh"
}
```

#### 自動起動されるサービス
Dev Container起動時に以下のサービスが自動的に起動：

1. **app**: アプリケーションコンテナ（Claude Code実行環境）
2. **postgres**: PostgreSQL 15（ポート5433）
3. **redis**: Redis 7（ポート6380）  
4. **pgadmin**: PostgreSQL管理ツール（ポート8081）
5. **jupyter**: Jupyter Lab（ポート8889）

#### 環境変数設定
`.env`ファイルでコンテナ間接続を設定：

```bash
# Docker Compose環境用設定
POSTGRES_HOST=postgres      # コンテナ名で接続
POSTGRES_PORT=5432          # コンテナ内ポート
REDIS_HOST=redis           # コンテナ名で接続  
REDIS_PORT=6379            # コンテナ内ポート
```

#### 初回セットアップ
Dev Container起動時に`.devcontainer/post-create.sh`が自動実行：

```bash
# 実行される処理
1. Python依存関係インストール
2. .envファイル作成（存在しない場合）
3. データベース起動待機
4. 接続テスト実行
5. 環境確認レポート表示
```


#### 開発フロー
1. **Dev Container開起動**: 全サービス自動起動
2. **接続確認**: post-createスクリプトで自動テスト
3. **開発開始**: データベース環境が即座に利用可能
4. **サービス停止**: Dev Container終了で全サービス停止