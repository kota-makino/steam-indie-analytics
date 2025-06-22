# API Reference - Steam Indie Analytics

## 📡 Steam Web API Integration

### Core API Endpoints

#### 1. GetAppList API
```python
URL: https://api.steampowered.com/ISteamApps/GetAppList/v2/
Method: GET
Authentication: None required
Rate Limit: No specific limit
```

**Response Structure:**
```json
{
  "applist": {
    "apps": [
      {
        "appid": 413150,
        "name": "Stardew Valley"
      }
    ]
  }
}
```

#### 2. GetAppDetails API
```python
URL: https://store.steampowered.com/api/appdetails
Method: GET
Parameters:
  - appids: comma-separated app IDs
  - l: language (default: english)
  - cc: country code (default: us)
Rate Limit: ~200 requests per 5 minutes
```

**Response Structure:**
```json
{
  "413150": {
    "success": true,
    "data": {
      "steam_appid": 413150,
      "name": "Stardew Valley",
      "type": "game",
      "is_free": false,
      "developers": ["ConcernedApe"],
      "publishers": ["ConcernedApe"],
      "price_overview": {
        "currency": "USD",
        "initial": 1499,
        "final": 1499,
        "discount_percent": 0
      },
      "genres": [
        {
          "id": "23",
          "description": "Indie"
        }
      ]
    }
  }
}
```

#### 3. GetAppReviews API
```python
URL: https://store.steampowered.com/api/appreviews/{app_id}
Method: GET
Parameters:
  - json: 1
  - language: all
  - review_type: all
  - purchase_type: all
  - num_per_page: 0 (for summary only)
Rate Limit: ~200 requests per 5 minutes
```

**Response Structure:**
```json
{
  "success": 1,
  "query_summary": {
    "total_positive": 45123,
    "total_negative": 2341,
    "total_reviews": 47464,
    "review_score": 9,
    "review_score_desc": "Overwhelmingly Positive"
  }
}
```

### Rate Limiting Implementation

```python
# レート制限対応
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_game_details(app_id: int) -> Optional[Dict[str, Any]]:
    """指数バックオフによるリトライ機能付きAPI呼び出し"""
    # 実装詳細は collect_indie_games.py を参照
```

## 🗄️ Database API

### Database Schema

#### Primary Tables

##### games_normalized
```sql
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
```

##### Master Data Tables
```sql
-- ジャンルマスタ
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- 開発者マスタ
CREATE TABLE developers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) UNIQUE NOT NULL
);

-- パブリッシャーマスタ
CREATE TABLE publishers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) UNIQUE NOT NULL
);
```

##### Relationship Tables
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

### Analysis Views

#### game_analysis_view
```sql
CREATE VIEW game_analysis_view AS
SELECT 
    g.app_id,
    g.name,
    g.price_final / 100.0 AS price_usd,
    g.total_reviews,
    g.positive_reviews::float / NULLIF(g.total_reviews, 0) AS rating,
    g.is_indie,
    COALESCE(
        (SELECT genre.name FROM game_genres gg 
         JOIN genres genre ON gg.genre_id = genre.id 
         WHERE gg.game_id = g.app_id ORDER BY genre.name LIMIT 1), 
        'Unknown'
    ) AS primary_genre,
    CASE 
        WHEN g.price_final = 0 THEN '無料'
        WHEN g.price_final <= 500 THEN '低価格帯 (¥0-750)'
        WHEN g.price_final <= 1500 THEN '中価格帯 (¥750-2,250)'
        WHEN g.price_final <= 3000 THEN '高価格帯 (¥2,250-4,500)'
        ELSE 'プレミアム (¥4,500+)'
    END AS price_category
FROM games_normalized g;
```

## 🤖 AI Insights API

### Gemini AI Integration

#### Configuration
```python
import google.generativeai as genai

# API設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')
```

#### Insight Types

##### 1. Market Overview Insights
```python
def generate_market_insight(data_summary: str) -> str:
    """市場概要の分析洞察を生成"""
    prompt = f"""
    以下のSteamインディーゲーム市場データを分析し、
    市場動向と特徴について200文字以内で日本語で洞察を述べてください：
    
    {data_summary}
    """
```

##### 2. Genre Analysis Insights
```python
def generate_genre_insight(data_summary: str) -> str:
    """ジャンル分析の洞察を生成"""
    prompt = f"""
    以下のジャンル別データを分析し、各ジャンルの競争状況と
    開発者へのアドバイスを200文字以内で日本語で述べてください：
    
    {data_summary}
    """
```

##### 3. Price Strategy Insights
```python
def generate_price_insight(data_summary: str) -> str:
    """価格戦略の洞察を生成"""
    prompt = f"""
    以下の価格帯別データを分析し、最適な価格戦略について
    200文字以内で日本語で提案してください：
    
    {data_summary}
    """
```

##### 4. Strategic Recommendations
```python
def generate_strategy_insight(data_summary: str) -> str:
    """戦略的推奨事項の生成"""
    prompt = f"""
    以下の包括的データを基に、インディーゲーム開発者への
    戦略的アドバイスを200文字以内で日本語で提供してください：
    
    {data_summary}
    """
```

### Error Handling

```python
def generate_insight_with_fallback(prompt: str) -> str:
    """フォールバック機能付きAI洞察生成"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI分析は現在利用できません。データから手動で分析してください。(エラー: {str(e)[:50]}...)"
```

## 📊 Analytics API

### Market Analyzer

```python
class MarketAnalyzer:
    def get_market_overview(self) -> Dict[str, Any]:
        """市場概要データを取得"""
        return {
            'total_games': int,
            'avg_price': float,
            'price_distribution': Dict[str, int],
            'review_stats': Dict[str, float]
        }
```

### Success Analyzer

```python
class SuccessAnalyzer:
    def create_success_analysis_report(self) -> str:
        """成功要因分析レポートを生成"""
        # 高評価ゲームの特徴抽出
        # 成功パターンの識別
        # 推奨事項の生成
```

### Data Quality Checker

```python
class DataQualityChecker:
    def check_data_quality(self) -> Dict[str, Any]:
        """データ品質レポートを生成"""
        return {
            'completeness': Dict[str, float],
            'data_issues': List[str],
            'recommendations': List[str]
        }
```

## 🔧 Configuration

### Environment Variables

```bash
# Steam API (認証不要)
STEAM_API_KEY=your_steam_api_key  # オプション

# Gemini AI API
GEMINI_API_KEY=your_gemini_api_key

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=steam_analytics
POSTGRES_USER=steam_user
POSTGRES_PASSWORD=steam_password

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
```

### Database Connection

```python
# SQLAlchemy Engine
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(DATABASE_URL)

# Connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## 🚀 Usage Examples

### Data Collection

```python
# 基本的なデータ収集
async with IndieGameCollector() as collector:
    await collector.collect_indie_games(limit=100)
```

### AI Insights Generation

```python
# AI洞察生成
if AI_INSIGHTS_AVAILABLE:
    generator = AIInsightsGenerator()
    insight = generator.generate_market_insight(data_summary)
    st.info(insight)
```

### Dashboard Integration

```python
# Streamlitダッシュボード
@st.cache_data(ttl=600)
def load_data():
    """キャッシュ付きデータ読み込み"""
    return pd.read_sql_query(sql_query, engine)
```

## 🔒 Security & Best Practices

### API Rate Limiting
- Steam Store API: ~200 requests per 5 minutes
- Exponential backoff implementation
- Request timeout: 30 seconds

### Data Validation
- Pydantic models for type safety
- Input sanitization for SQL queries
- Error handling with graceful degradation

### Resource Management
- Connection pooling for database
- Async context managers for HTTP sessions
- Proper cleanup in finally blocks

---

このAPIリファレンスは、Steam Indie Analytics プロジェクトの技術的実装を理解し、拡張するためのガイドとして活用してください。