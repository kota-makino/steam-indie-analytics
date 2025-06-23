# Steam Indie Analytics - 技術スタック詳細

## 📋 プロジェクト基本情報

| 項目 | 内容 |
|------|------|
| **プロジェクト名** | Steam Indie Analytics |
| **開発期間** | 11日間（2025年6月12日〜6月23日） |
| **開発者** | 個人開発 |
| **目的** | データエンジニア転職ポートフォリオ |
| **対象企業** | 生成AI活用企業 |

## 🛠️ 技術スタック一覧

### プログラミング言語
- **Python 3.11+** - メイン開発言語
- **SQL (PostgreSQL)** - データベース操作
- **HTML/CSS/JavaScript** - フロントエンド（Streamlit内）
- **YAML** - 設定ファイル（Docker Compose等）
- **Bash** - 運用スクリプト

### フレームワーク・ライブラリ

#### データ処理・分析
```python
pandas==2.1.4                 # データ操作・変換
polars==0.20.2                # 高速データ処理
numpy==1.24.3                 # 数値計算
scipy==1.11.4                 # 統計処理
scikit-learn==1.3.2           # 機械学習（将来拡張用）
```

#### データベース・ORM
```python
sqlalchemy==2.0.23            # ORM・データベース操作
psycopg2-binary==2.9.9        # PostgreSQL接続ドライバ
alembic==1.13.1               # データベースマイグレーション
```

#### Web開発・UI
```python
streamlit==1.29.0             # ダッシュボード・Webアプリ
plotly==5.17.0                # インタラクティブ可視化
seaborn==0.13.0               # 統計可視化
matplotlib==3.8.2             # 基本グラフ作成
```

#### API・非同期処理
```python
aiohttp==3.9.1                # 非同期HTTPリクエスト
requests==2.31.0              # HTTP リクエスト
tenacity==8.2.3               # リトライ機能（レート制限対応）
aiofiles==23.2.1              # 非同期ファイルI/O
```

#### AI・LLM統合
```python
google-generativeai==0.8.5    # Gemini API（分析コメント生成）
```

### インフラストラクチャ

#### データベース
- **PostgreSQL 15** - メインデータベース
- **Redis 7** - キャッシュ・セッション管理

#### コンテナ化・オーケストレーション
- **Docker** - アプリケーションコンテナ化
- **Docker Compose** - 開発環境オーケストレーション
- **Nginx** - リバースプロキシ・ロードバランサー

#### 開発・運用ツール
```python
pytest==7.4.3                 # テストフレームワーク
pytest-cov==4.1.0             # カバレッジ測定
pytest-asyncio==0.21.1        # 非同期テスト
black==23.11.0                # コードフォーマッター
flake8==6.1.0                 # コードリンター
```

## 🏗️ アーキテクチャ構成

### システム構成図
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Steam Web API │────│  Data Collector  │────│   PostgreSQL    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         │
                       ┌──────────────────┐               │
                       │   Data Processor │───────────────┘
                       └──────────────────┘               │
                                │                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Gemini AI API │────│   AI Insights    │    │      Redis      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         │
                       ┌──────────────────┐               │
                       │  Streamlit UI    │───────────────┘
                       └──────────────────┘
                                │
                       ┌──────────────────┐
                       │      Users       │
                       └──────────────────┘
```

### データフロー
1. **データ収集**: Steam Web API → データコレクター
2. **データ処理**: ETLパイプライン → PostgreSQL
3. **AI分析**: Gemini API → 洞察生成
4. **可視化**: Streamlit Dashboard → ユーザー

## 📊 実装詳細と技術的特徴

### 1. データ収集システム

#### API連携アーキテクチャ
```python
# Steam APIレート制限対応
class SteamAPICollector:
    def __init__(self):
        self.rate_limiter = RateLimiter(max_calls=200, period=300)  # 200/5分
        self.session = aiohttp.ClientSession()
    
    @retry(stop=stop_after_attempt(3))
    async def fetch_game_data(self, app_id: int) -> dict:
        async with self.rate_limiter:
            # 指数バックオフリトライでAPI呼び出し
            pass
```

**技術的特徴:**
- 非同期処理による高速データ収集
- 指数バックオフによる堅牢なエラーハンドリング
- APIレート制限の適切な管理

### 2. データベース設計

#### 正規化スキーマ
```sql
-- ゲーム基本情報
CREATE TABLE games (
    app_id INTEGER PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    indie_score FLOAT,
    release_date DATE,
    price DECIMAL(10,2)
);

-- ジャンル正規化
CREATE TABLE genres (
    genre_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- 多対多関係テーブル
CREATE TABLE game_genres (
    game_id INTEGER REFERENCES games(app_id),
    genre_id INTEGER REFERENCES genres(genre_id),
    PRIMARY KEY (game_id, genre_id)
);
```

**技術的特徴:**
- 第3正規形に基づく設計
- パフォーマンス最適化インデックス
- 外部キー制約による整合性保証

### 3. 分析エンジン

#### データ分析パイプライン
```python
class MarketAnalyzer:
    def analyze_market_trends(self, df: pd.DataFrame) -> dict:
        # 価格帯別成功率分析
        price_analysis = df.groupby(
            pd.cut(df['price'], bins=[0, 5, 15, 30, float('inf')])
        ).agg({
            'positive_percentage': 'mean',
            'review_count': 'median',
            'indie_score': 'mean'
        })
        
        return {
            'price_effectiveness': price_analysis,
            'optimal_price_range': self._find_optimal_price(price_analysis),
            'market_insights': self._generate_insights(price_analysis)
        }
```

**技術的特徴:**
- pandas/polarsによる高速データ処理
- 統計的手法による市場分析
- ビジネス価値の高い洞察抽出

### 4. AI統合システム

#### Gemini API活用
```python
class AIInsightsGenerator:
    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_market_insights(self, data: pd.DataFrame) -> str:
        prompt = self._create_analysis_prompt(data)
        response = self.model.generate_content(prompt)
        return self._format_response(response.text)
```

**技術的特徴:**
- 生成AI APIの実践的活用
- プロンプトエンジニアリング
- ビジネス価値向上への貢献

## 🔧 開発・運用プロセス

### 開発環境
```yaml
# Docker開発環境
services:
  app:
    build: .devcontainer/
    volumes:
      - .:/workspace:cached
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: steam_analytics
  
  redis:
    image: redis:7-alpine
```

### 品質保証プロセス
```bash
# 開発時品質チェック
black src/ tests/                          # コードフォーマット
isort src/ tests/                          # import整理
flake8 src/ tests/ --max-line-length=88    # リンター
mypy src/                                  # 型チェック
pytest --cov=src tests/                    # テスト実行
```

### テスト戦略
- **ユニットテスト**: 個別関数・クラステスト
- **統合テスト**: データベース・API連携テスト
- **システムテスト**: エンドツーエンド機能テスト
- **非同期テスト**: pytest-asyncioによる非同期処理テスト

## 📈 パフォーマンス・スケーラビリティ

### 現在の性能指標
| メトリクス | 値 |
|-----------|-----|
| データ収集速度 | 100件/分 |
| ダッシュボード読み込み | < 3秒 |
| データベースクエリ | < 500ms |
| API成功率 | 95%以上 |

### スケーラビリティ対応
```python
# 非同期並列処理
async def collect_games_parallel(app_ids: List[int]) -> List[dict]:
    semaphore = asyncio.Semaphore(10)  # 同時接続数制限
    tasks = [
        self._fetch_with_semaphore(semaphore, app_id) 
        for app_id in app_ids
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## 🔐 セキュリティ・運用考慮

### セキュリティ対策
- **環境変数管理**: python-dotenvによる秘密情報分離
- **SQLインジェクション対策**: SQLAlchemy ORMの活用
- **API認証**: 適切なAPIキー管理
- **HTTPS対応**: SSL/TLS証明書設定

### 運用・監視
```python
# 構造化ログ
from loguru import logger

logger.info(
    "Data collection completed",
    games_collected=len(games),
    success_rate=success_rate,
    duration=duration
)
```

## 🚀 デプロイメント戦略

### 対応デプロイ環境
1. **Streamlit Cloud** - 最速デプロイ
2. **Docker本番環境** - フルコントロール
3. **VPS/クラウドサーバー** - スケーラブル運用

### CI/CDパイプライン準備
```yaml
# GitHub Actions (準備済み)
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest --cov=src
```

## 💡 技術選択の理由

### なぜPythonエコシステム？
1. **データ分析の標準**: pandas, numpy, scipyの豊富な機能
2. **AI/LLM統合**: 生成AI APIとの親和性
3. **実務採用率**: データエンジニアリング分野での標準
4. **学習効率**: 統一言語によるフルスタック開発

### なぜStreamlit？
1. **開発速度**: Pythonのみでの迅速なWebアプリ開発
2. **データ親和性**: データサイエンス向け設計
3. **デプロイ簡易性**: Streamlit Cloudでの即座公開
4. **プロトタイピング**: 分析結果の即座可視化

### なぜPostgreSQL？
1. **スケーラビリティ**: 大規模データ処理対応
2. **JSON対応**: 柔軟なデータ構造対応
3. **実務標準**: エンタープライズ環境での採用実績
4. **拡張性**: 将来的な機能追加への対応

## 📊 学習成果・習得技術

### 新規習得技術 (11日間で)
- **Streamlit**: Webアプリケーション開発
- **SQLAlchemy 2.0**: 現代的ORM活用
- **非同期Python**: aiohttp, asyncioの実践的活用
- **Docker**: コンテナ化・オーケストレーション
- **生成AI API**: Gemini API統合

### 向上した技術
- **pandas**: 高度なデータ操作・分析
- **PostgreSQL**: データベース設計・最適化
- **pytest**: 包括的テスト設計
- **Git/GitHub**: バージョン管理・協働開発

## 🎯 転職市場での技術価値

### データエンジニア必須スキル
✅ **Python**: データ処理・分析の主力言語  
✅ **SQL**: データベース操作・最適化  
✅ **Docker**: 環境統一・デプロイメント  
✅ **API連携**: 外部データソース統合  
✅ **テスト**: 品質保証・保守性向上  

### 生成AI企業での付加価値
✅ **LLM API統合**: 実務レベル活用経験  
✅ **プロンプトエンジニアリング**: 効果的AI活用  
✅ **最新技術適応**: 迅速な技術キャッチアップ  
✅ **ビジネス価値創出**: AI活用での付加価値提供  

### 実務即戦力要素
✅ **本番環境対応**: セキュリティ・監視・バックアップ  
✅ **スケーラビリティ**: 成長対応設計  
✅ **品質管理**: テスト・コード品質保証  
✅ **ドキュメント**: 保守性・継承性確保  

---

## 📋 技術習熟度自己評価

| 技術領域 | レベル | 経験期間 | 実践レベル |
|---------|--------|----------|------------|
| **Python** | 中級+ | 1年+ | 実務適用可能 |
| **SQL/PostgreSQL** | 中級 | 6ヶ月 | 基本設計・最適化 |
| **Docker** | 初級+ | 11日間 | 開発環境構築 |
| **Web開発(Streamlit)** | 初級+ | 11日間 | 基本アプリ開発 |
| **API統合** | 中級 | 11日間 | レート制限・エラー処理 |
| **生成AI活用** | 初級+ | 11日間 | 基本的な統合・活用 |
| **テスト設計** | 中級 | 11日間 | 包括的テストスイート |

**総合評価**: データエンジニア新人〜1年目レベルの技術力を実証

このプロジェクトにより、現代的なデータエンジニアリング技術スタックの実務レベル習得を証明できます。