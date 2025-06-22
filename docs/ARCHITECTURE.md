# アーキテクチャ設計書

## 🏗️ システム全体構成

### アーキテクチャ概要
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Steam Web API │────│  Data Pipeline  │────│   Analytics     │
│                 │    │                 │    │                 │
│ • Game Details  │    │ • Collection    │    │ • Dashboard     │
│ • Reviews       │    │ • Validation    │    │ • AI Insights   │
│ • Metadata      │    │ • Migration     │    │ • Reporting     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Data Storage  │
                       │                 │
                       │ • PostgreSQL    │
                       │ • Redis Cache   │
                       │ • Normalized DB │
                       └─────────────────┘
```

## 📊 データパイプライン

### 1. データ収集層 (Collection Layer)
```python
# collect_indie_games.py
class IndieGameCollector:
    async def collect_indie_games() -> None
    async def get_game_details() -> Dict
    async def run_data_migration() -> bool  # 自動連動
```

**特徴:**
- 非同期HTTP通信 (aiohttp)
- レート制限対応 (tenacity)
- 品質フィルタリング (ジャンル・開発者必須)
- 自動データ移行統合

### 2. データ処理層 (Processing Layer)
```python
# scripts/migrate_to_normalized_schema.py
class SchemaMigrator:
    def migrate_games() -> None
    def create_normalized_tables() -> None
    def migrate_master_data() -> None
```

**設計原則:**
- 正規化データベース設計 (3NF準拠)
- マスタデータ管理 (genres, developers, publishers)
- 中間テーブル活用 (多対多関係)

### 3. 分析層 (Analytics Layer)
```python
# src/analyzers/
market_analyzer.py      # 市場動向分析
success_analyzer.py     # 成功要因分析
ai_insights_generator.py # AI洞察生成
```

**AI統合:**
- Gemini API による自然言語生成
- コスト効率的実装 (無料枠活用)
- 4種類の分析洞察 (市場・ジャンル・価格・戦略)

## 🗄️ データベース設計

### 正規化スキーマ (3NF準拠)

#### 主要エンティティ
```sql
-- ゲーム基本情報
CREATE TABLE games_normalized (
    app_id INTEGER PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(50),
    is_free BOOLEAN DEFAULT FALSE,
    price_final INTEGER,
    is_indie BOOLEAN DEFAULT FALSE,
    total_reviews INTEGER,
    positive_reviews INTEGER,
    negative_reviews INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- マスタデータ
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE developers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) UNIQUE NOT NULL
);

CREATE TABLE publishers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) UNIQUE NOT NULL
);
```

#### 関係テーブル (多対多)
```sql
-- ゲーム-ジャンル関係
CREATE TABLE game_genres (
    game_id INTEGER REFERENCES games_normalized(app_id),
    genre_id INTEGER REFERENCES genres(id),
    PRIMARY KEY (game_id, genre_id)
);

-- ゲーム-開発者関係
CREATE TABLE game_developers (
    game_id INTEGER REFERENCES games_normalized(app_id),
    developer_id INTEGER REFERENCES developers(id),
    PRIMARY KEY (game_id, developer_id)
);
```

#### 分析ビュー
```sql
CREATE VIEW game_analysis_view AS
SELECT 
    g.app_id,
    g.name,
    g.price_final / 100.0 AS price_usd,
    g.total_reviews,
    g.positive_reviews::float / NULLIF(g.total_reviews, 0) AS rating,
    g.is_indie,
    -- 主要ジャンル（最初のジャンル）
    COALESCE(
        (SELECT genre.name FROM game_genres gg 
         JOIN genres genre ON gg.genre_id = genre.id 
         WHERE gg.game_id = g.app_id ORDER BY genre.name LIMIT 1), 
        'Unknown'
    ) AS primary_genre,
    -- 価格カテゴリ
    CASE 
        WHEN g.price_final = 0 THEN '無料'
        WHEN g.price_final <= 500 THEN '低価格帯 (¥0-750)'
        WHEN g.price_final <= 1500 THEN '中価格帯 (¥750-2,250)'
        WHEN g.price_final <= 3000 THEN '高価格帯 (¥2,250-4,500)'
        ELSE 'プレミアム (¥4,500+)'
    END AS price_category
FROM games_normalized g;
```

## 🎨 プレゼンテーション層

### Streamlit ダッシュボード構成
```python
# src/dashboard/app.py
def main():
    display_market_overview()     # 市場概要
    display_genre_analysis()      # ジャンル分析
    display_price_analysis()      # 価格分析
    display_insights_and_recommendations()  # 戦略洞察
```

**特徴:**
- インタラクティブ可視化 (Plotly)
- リアルタイムデータ更新
- AI洞察ボタン統合
- レスポンシブデザイン

### AI洞察統合
```python
# AI洞察生成フロー
def generate_ai_insight():
    1. データサマリー作成
    2. Gemini API呼び出し
    3. 構造化プロンプト送信
    4. 日本語分析コメント受信
    5. ダッシュボード表示
```

## 🔄 データフロー詳細

### 1. 収集フェーズ
```
Steam API → HTTP Request → JSON Response → Data Validation → PostgreSQL (games)
```

### 2. 移行フェーズ
```
games → Schema Migration → Normalized Tables → Master Data → Relations → Views
```

### 3. 分析フェーズ
```
Views → Streamlit → Interactive Charts → AI Insights → User Interface
```

## 🚀 パフォーマンス最適化

### キャッシュ戦略
```python
@st.cache_data(ttl=60)  # 1分キャッシュ
def load_data():
    # データベースクエリ結果をキャッシュ
```

### データベース最適化
```sql
-- インデックス設計
CREATE INDEX idx_games_genre ON games_normalized(is_indie);
CREATE INDEX idx_games_reviews ON games_normalized(total_reviews);
CREATE INDEX idx_game_genres_game ON game_genres(game_id);
CREATE INDEX idx_game_genres_genre ON game_genres(genre_id);
```

### 非同期処理
```python
# 並列データ取得
async with aiohttp.ClientSession() as session:
    tasks = [get_game_details(app_id) for app_id in app_ids]
    results = await asyncio.gather(*tasks)
```

## 🔒 セキュリティ・品質管理

### データ品質保証
```python
# フィルタリング条件
def is_indie_game(game_data):
    # 基本データ存在チェック
    if not game_data.get("name") or not game_data.get("steam_appid"):
        return False
    
    # ジャンル情報必須
    if not game_data.get("genres", []):
        return False
    
    # 開発者情報推奨
    if not game_data.get("developers", []):
        # 例外条件での許可
        if len(game_data.get("genres", [])) < 3:
            return False
```

### API制限対応
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_game_details(app_id):
    # 指数バックオフによるリトライ
    # レート制限 (200req/5min) 遵守
```

## 📈 スケーラビリティ設計

### 水平スケーリング対応
- ステートレスアプリケーション設計
- データベース正規化による効率化
- キャッシュ層分離 (Redis)

### 垂直スケーリング対応
- 非同期処理による並列化
- バッチ処理の最適化
- インデックス戦略

## 🛠️ 開発・運用

### 開発環境
```yaml
Environment: Dev Container + Docker Compose
Database: PostgreSQL 15 (port 5433)
Cache: Redis 7 (port 6380)
Dashboard: Streamlit (port 8501)
Admin: pgAdmin (port 8081)
Jupyter: JupyterLab (port 8889)
```

### 自動化
```bash
# 完全自動化パイプライン
python collect_indie_games.py
├── Steam API データ収集
├── インディーゲーム判定・フィルタリング
├── データベース保存
├── 自動データ移行実行
└── ダッシュボード反映準備完了
```

## 🎯 技術的な設計判断

### なぜこの技術選択？

**PostgreSQL**: 
- 複雑なリレーション対応
- JSON型サポート
- 本格的なデータウェアハウス構築

**Streamlit**: 
- 迅速なプロトタイピング
- インタラクティブ機能
- Pythonネイティブ

**Gemini API**: 
- コスト効率 (無料枠100万トークン/月)
- 日本語対応品質
- 簡単な統合

**非同期処理**: 
- Steam API の大量呼び出し対応
- レスポンス時間短縮
- リソース効率化

---

この設計により、**スケーラブル・保守性・拡張性**を備えた現代的なデータ分析プラットフォームを実現しています。