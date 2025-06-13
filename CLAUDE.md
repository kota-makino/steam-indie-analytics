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
# ETLパイプライン実行
python scripts/run_etl.py

# ダッシュボード起動
streamlit run src/dashboard/app.py

# Jupyter Lab起動
jupyter lab notebooks/

# テスト実行
pytest --cov=src tests/

# コード品質チェック
black src/ tests/ && isort src/ tests/ && flake8 src/ tests/ && mypy src/
```

### 重要な設定情報

#### ポート番号
- **PostgreSQL**: localhost:5433（競合回避のため5432ではない）
- **Redis**: localhost:6380（競合回避のため6379ではない）
- **pgAdmin**: http://localhost:8081
- **Jupyter Lab**: http://localhost:8889
- **Streamlit**: http://localhost:8501

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

#### データベース接続テスト
```bash
# 手動で接続テスト実行
python tests/test_db_connection.py

# pytestで実行する場合
pytest tests/test_db_connection.py -v

# 期待される結果（正常時）
✅ PostgreSQL接続: OK
✅ Redis接続: OK  
✅ 環境変数設定: OK
```

#### 開発フロー
1. **Dev Container開起動**: 全サービス自動起動
2. **接続確認**: post-createスクリプトで自動テスト
3. **開発開始**: データベース環境が即座に利用可能
4. **サービス停止**: Dev Container終了で全サービス停止