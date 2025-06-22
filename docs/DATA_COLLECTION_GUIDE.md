# Data Collection Guide - Steam Indie Analytics

## 🎯 データ収集戦略

### 収集対象とスコープ

#### ターゲットデータ
- **ゲーム基本情報**: 名前、タイプ、価格、開発者、パブリッシャー
- **メタデータ**: ジャンル、カテゴリ、プラットフォーム対応
- **レビューデータ**: 総レビュー数、ポジティブ/ネガティブ比率
- **リリース情報**: リリース日、Early Access状況

#### インディーゲーム判定基準
```python
def is_indie_game(game_data: Dict[str, Any]) -> bool:
    """
    インディーゲーム判定ロジック
    
    判定基準:
    1. ジャンルに「Indie」が含まれる
    2. 開発者とパブリッシャーが同一（セルフパブリッシング）
    3. 小規模チーム（開発者1-2社）
    4. 大手パブリッシャーでない
    5. 基本的なデータ品質を満たす
    """
```

#### データ品質基準
- **必須フィールド**: name, steam_appid, type="game"
- **推奨フィールド**: genres, developers, price_overview
- **除外対象**: DLC, デモ, サウンドトラック, ツール類

## 🔌 Steam Web API活用

### API概要

#### 認証不要API（メイン使用）
```python
# GetAppList API - ゲーム一覧取得
URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"

# GetAppDetails API - ゲーム詳細取得  
URL = "https://store.steampowered.com/api/appdetails"

# GetAppReviews API - レビュー情報取得
URL = "https://store.steampowered.com/api/appreviews/{app_id}"
```

#### レート制限対応
```python
# 制限: 約200リクエスト/5分
# 戦略: 指数バックオフ + 0.5秒間隔

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_game_details(app_id: int) -> Optional[Dict[str, Any]]:
    """レート制限対応のAPI呼び出し"""
    # リトライ機能付き実装
```

### データ収集フロー

#### 1. ゲーム一覧取得
```python
async def get_steam_game_list(self, limit: int = 1000) -> List[int]:
    """
    Steam全ゲームリストから候補を抽出
    
    抽出戦略:
    1. インディー関連キーワードを含むゲームを優先
    2. 既知の人気インディーゲームを必ず含める
    3. ランダムサンプリングで多様性を確保
    4. DLC・デモ・ツール類は事前除外
    """
    
    # インディー関連キーワード
    indie_keywords = [
        "indie", "independent", "pixel", "retro", "adventure",
        "casual", "puzzle", "platformer", "roguelike", "survival"
    ]
    
    # 既知の人気インディーゲーム
    known_indie_games = [
        413150,  # Stardew Valley
        250900,  # The Binding of Isaac: Rebirth
        367520,  # Hollow Knight
        391540,  # Undertale
        # ... 他約20タイトル
    ]
```

#### 2. ゲーム詳細取得
```python
async def get_game_details(self, app_id: int) -> Optional[Dict[str, Any]]:
    """
    ゲーム詳細情報の取得
    
    取得情報:
    - 基本情報（名前、タイプ、説明）
    - 価格情報（通貨、初期価格、最終価格、割引率）
    - 開発・パブリッシング情報
    - ジャンル・カテゴリ情報
    - プラットフォーム対応情報
    - リリース日情報
    """
    
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": app_id, "l": "english", "cc": "us"}
```

#### 3. レビューデータ取得
```python
async def get_game_reviews(self, app_id: int) -> Optional[Dict[str, Any]]:
    """
    レビュー統計情報の取得
    
    取得データ:
    - total_positive: ポジティブレビュー数
    - total_negative: ネガティブレビュー数  
    - total_reviews: 総レビュー数
    - review_score: レビュースコア (0-10)
    - review_score_desc: スコア説明文
    """
    
    url = f"https://store.steampowered.com/api/appreviews/{app_id}"
    params = {
        "json": 1,
        "language": "all",
        "review_type": "all", 
        "purchase_type": "all",
        "num_per_page": 0  # 統計情報のみ取得
    }
```

## 🔍 インディーゲーム判定ロジック

### 判定アルゴリズム

```python
def is_indie_game(self, game_data: Dict[str, Any]) -> bool:
    """
    多段階インディーゲーム判定
    
    Phase 1: 基本データ品質チェック
    Phase 2: 大手パブリッシャー除外
    Phase 3: インディー特徴識別
    Phase 4: ビューとの整合性確保
    """
    
    # Phase 1: 基本データ存在チェック
    if not self._validate_basic_data(game_data):
        return False
        
    # Phase 2: 大手パブリッシャー除外
    if self._is_major_publisher(game_data):
        return False
        
    # Phase 3: インディー特徴チェック
    if self._has_indie_characteristics(game_data):
        return True
        
    # Phase 4: 小規模開発チーム判定
    return self._is_small_team(game_data)

def _validate_basic_data(self, game_data: Dict[str, Any]) -> bool:
    """基本データ品質チェック（ビューのJOIN条件対応）"""
    # 必須: ゲーム名、App ID
    if not game_data.get("name") or not game_data.get("steam_appid"):
        return False
        
    # 必須: ジャンル情報（game_genres テーブル用）
    if not game_data.get("genres", []):
        return False
        
    # 推奨: 開発者情報（game_developers テーブル用）
    developers = game_data.get("developers", [])
    if not developers:
        # 例外: ジャンル情報が豊富な場合は許可
        genres = game_data.get("genres", [])
        if len(genres) < 3:
            return False
            
    # タイプチェック
    if game_data.get("type") != "game":
        return False
        
    # 除外対象チェック
    name_lower = game_data.get("name", "").lower()
    excluded_keywords = ["demo", "dlc", "soundtrack", "trailer"]
    if any(keyword in name_lower for keyword in excluded_keywords):
        return False
        
    return True

def _is_major_publisher(self, game_data: Dict[str, Any]) -> bool:
    """大手パブリッシャー判定"""
    major_publishers = [
        "valve", "electronic arts", "ea", "activision", "ubisoft",
        "bethesda", "square enix", "capcom", "bandai namco", "sega",
        "take-two", "nintendo", "sony", "microsoft", "rockstar"
    ]
    
    publishers = game_data.get("publishers", [])
    for publisher in publishers:
        for major in major_publishers:
            if major.lower() in publisher.lower():
                return True
    return False

def _has_indie_characteristics(self, game_data: Dict[str, Any]) -> bool:
    """インディー特徴識別"""
    # ジャンルでの判定
    genres = game_data.get("genres", [])
    for genre in genres:
        genre_desc = genre.get("description", "").lower()
        if "indie" in genre_desc or "independent" in genre_desc:
            return True
            
    # カテゴリでの判定
    categories = game_data.get("categories", [])
    for category in categories:
        cat_desc = category.get("description", "").lower()
        if "indie" in cat_desc:
            return True
            
    return False

def _is_small_team(self, game_data: Dict[str, Any]) -> bool:
    """小規模チーム判定"""
    developers = game_data.get("developers", [])
    publishers = game_data.get("publishers", [])
    
    # セルフパブリッシング（開発者=パブリッシャー）
    if developers and publishers and set(developers) == set(publishers):
        return True
        
    # 小規模チーム（開発者1-2社）
    if len(developers) <= 2:
        return True
        
    return False
```

## 📊 データ処理パイプライン

### ETL プロセス

#### Extract（抽出）
```python
async def collect_indie_games(self, limit: int = 1000) -> None:
    """
    データ抽出メインプロセス
    
    処理フロー:
    1. Steam APIからゲームリスト取得
    2. 並列でゲーム詳細情報取得
    3. インディーゲーム判定実行
    4. レビューデータ補完
    5. データベース保存
    """
    
    # 対象ゲーム選定
    app_ids = await self.get_steam_game_list(limit)
    
    # 進捗管理
    indie_count = 0
    total_processed = 0
    
    for app_id in app_ids:
        # 重複チェック
        if await self.check_existing_game(app_id):
            continue
            
        # ゲーム詳細取得
        game_data = await self.get_game_details(app_id)
        if not game_data:
            continue
            
        # インディーゲーム判定
        if self.is_indie_game(game_data):
            # レビューデータ取得
            review_data = await self.get_game_reviews(app_id)
            
            # データベース保存
            await self.save_game_to_db(game_data, review_data)
            indie_count += 1
            
        # レート制限対応
        await asyncio.sleep(0.5)
```

#### Transform（変換）
```python
async def save_game_to_db(self, game_data: Dict[str, Any], review_data: Optional[Dict[str, Any]]) -> None:
    """
    データ変換・正規化処理
    
    変換処理:
    1. 価格情報の正規化（セント→ドル変換）
    2. 配列データの PostgreSQL配列形式変換
    3. ブール値の統一
    4. 日付フォーマット統一
    5. NULL値の適切な処理
    """
    
    # 価格情報の処理
    price_overview = game_data.get("price_overview", {})
    price_currency = price_overview.get("currency")
    price_initial = price_overview.get("initial")  # セント単位
    price_final = price_overview.get("final")      # セント単位
    
    # プラットフォーム情報の処理
    platforms = game_data.get("platforms", {})
    platforms_windows = platforms.get("windows", False)
    platforms_mac = platforms.get("mac", False)
    platforms_linux = platforms.get("linux", False)
    
    # 配列データの処理
    genres = [g.get("description") for g in game_data.get("genres", [])]
    categories = [c.get("description") for c in game_data.get("categories", [])]
    developers = game_data.get("developers", [])
    publishers = game_data.get("publishers", [])
```

#### Load（格納）
```python
# 原始データテーブル（games）への保存
insert_game_sql = """
INSERT INTO games (
    app_id, name, type, is_free, detailed_description, short_description,
    developers, publishers, price_currency, price_initial, price_final,
    price_discount_percent, release_date_text, release_date_coming_soon,
    platforms_windows, platforms_mac, platforms_linux,
    genres, categories, positive_reviews, negative_reviews, total_reviews,
    updated_at
) VALUES (
    %(app_id)s, %(name)s, %(type)s, %(is_free)s, %(detailed_description)s, %(short_description)s,
    %(developers)s, %(publishers)s, %(price_currency)s, %(price_initial)s, %(price_final)s,
    %(price_discount_percent)s, %(release_date_text)s, %(release_date_coming_soon)s,
    %(platforms_windows)s, %(platforms_mac)s, %(platforms_linux)s,
    %(genres)s, %(categories)s, %(positive_reviews)s, %(negative_reviews)s, %(total_reviews)s,
    CURRENT_TIMESTAMP
)
ON CONFLICT (app_id) DO UPDATE SET
    name = EXCLUDED.name,
    detailed_description = EXCLUDED.detailed_description,
    short_description = EXCLUDED.short_description,
    positive_reviews = EXCLUDED.positive_reviews,
    negative_reviews = EXCLUDED.negative_reviews,
    total_reviews = EXCLUDED.total_reviews,
    updated_at = CURRENT_TIMESTAMP
"""
```

## 🔄 データ移行・正規化

### 正規化プロセス

```python
# scripts/migrate_to_normalized_schema.py

class SchemaMigrator:
    """データ正規化移行クラス"""
    
    def migrate_games(self) -> None:
        """ゲーム基本情報の移行"""
        migration_sql = """
        INSERT INTO games_normalized (
            app_id, name, type, is_free, price_final, is_indie,
            total_reviews, positive_reviews, negative_reviews
        )
        SELECT DISTINCT
            app_id,
            name,
            type,
            is_free,
            price_final,
            true as is_indie,  -- 収集時点でインディー判定済み
            total_reviews,
            positive_reviews,
            negative_reviews
        FROM games
        WHERE app_id IS NOT NULL AND name IS NOT NULL
        ON CONFLICT (app_id) DO UPDATE SET
            name = EXCLUDED.name,
            total_reviews = EXCLUDED.total_reviews,
            positive_reviews = EXCLUDED.positive_reviews,
            negative_reviews = EXCLUDED.negative_reviews,
            updated_at = CURRENT_TIMESTAMP;
        """
    
    def migrate_master_data(self) -> None:
        """マスタデータの作成・移行"""
        
        # ジャンルマスタ作成
        genres_sql = """
        INSERT INTO genres (name)
        SELECT DISTINCT unnest(genres) as genre_name
        FROM games
        WHERE genres IS NOT NULL AND array_length(genres, 1) > 0
        ON CONFLICT (name) DO NOTHING;
        """
        
        # 開発者マスタ作成
        developers_sql = """
        INSERT INTO developers (name)
        SELECT DISTINCT unnest(developers) as developer_name
        FROM games
        WHERE developers IS NOT NULL AND array_length(developers, 1) > 0
        ON CONFLICT (name) DO NOTHING;
        """
        
        # 中間テーブル作成
        game_genres_sql = """
        INSERT INTO game_genres (game_id, genre_id)
        SELECT DISTINCT
            g.app_id,
            genre.id
        FROM games g
        CROSS JOIN unnest(g.genres) as genre_name
        JOIN genres genre ON genre.name = genre_name
        WHERE g.app_id IN (SELECT app_id FROM games_normalized)
        ON CONFLICT (game_id, genre_id) DO NOTHING;
        """
```

### 自動データ移行

```python
async def run_data_migration(self) -> bool:
    """
    収集後の自動データ移行
    
    実行タイミング:
    - データ収集完了後
    - 手動でのデータ更新時
    - 定期バッチ処理時
    """
    try:
        import subprocess
        import sys
        
        # データ移行スクリプト実行
        result = subprocess.run(
            [sys.executable, "scripts/migrate_to_normalized_schema.py"],
            cwd="/workspace",
            capture_output=True,
            text=True,
            timeout=300  # 5分タイムアウト
        )
        
        if result.returncode == 0:
            print("✅ データ移行が正常に完了しました")
            # 移行結果レポート表示
            self._parse_migration_report(result.stdout)
            return True
        else:
            print("❌ データ移行でエラーが発生しました")
            print(f"エラー出力: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️ データ移行がタイムアウトしました（5分超過）")
        return False
    except Exception as e:
        print(f"❌ データ移行の実行中にエラー: {e}")
        return False
```

## 📈 データ品質管理

### 品質チェック項目

```python
# src/analyzers/data_quality_checker.py

class DataQualityChecker:
    """データ品質監視クラス"""
    
    def check_data_completeness(self) -> Dict[str, float]:
        """データ完全性チェック"""
        completeness_sql = """
        SELECT 
            COUNT(*) as total_games,
            COUNT(name) as has_name,
            COUNT(CASE WHEN array_length(genres, 1) > 0 THEN 1 END) as has_genres,
            COUNT(CASE WHEN array_length(developers, 1) > 0 THEN 1 END) as has_developers,
            COUNT(price_final) as has_price,
            COUNT(total_reviews) as has_reviews
        FROM games;
        """
        
    def identify_data_issues(self) -> List[str]:
        """データ品質問題の識別"""
        issues = []
        
        # 重複データチェック
        duplicates = self._check_duplicates()
        if duplicates > 0:
            issues.append(f"重複ゲームデータ: {duplicates}件")
            
        # 不整合データチェック  
        inconsistencies = self._check_inconsistencies()
        issues.extend(inconsistencies)
        
        # 外れ値チェック
        outliers = self._check_outliers()
        issues.extend(outliers)
        
        return issues
    
    def _check_duplicates(self) -> int:
        """重複データ検出"""
        duplicate_sql = """
        SELECT COUNT(*) - COUNT(DISTINCT app_id)
        FROM games;
        """
        
    def _check_inconsistencies(self) -> List[str]:
        """データ不整合検出"""
        issues = []
        
        # 価格データ不整合
        price_issues_sql = """
        SELECT COUNT(*) 
        FROM games 
        WHERE price_final < 0 OR price_initial < price_final;
        """
        
        # レビューデータ不整合
        review_issues_sql = """
        SELECT COUNT(*)
        FROM games
        WHERE total_reviews < (positive_reviews + negative_reviews);
        """
        
        return issues
```

### 監視・アラート

```python
def generate_quality_report(self) -> str:
    """データ品質レポート生成"""
    report = []
    
    # 基本統計
    basic_stats = self.get_basic_statistics()
    report.append(f"📊 総ゲーム数: {basic_stats['total_games']:,}件")
    report.append(f"📊 インディーゲーム: {basic_stats['indie_games']:,}件")
    
    # 完全性スコア
    completeness = self.check_data_completeness()
    avg_completeness = sum(completeness.values()) / len(completeness) * 100
    report.append(f"📈 データ完全性: {avg_completeness:.1f}%")
    
    # 問題検出
    issues = self.identify_data_issues()
    if issues:
        report.append("⚠️ 検出された問題:")
        for issue in issues:
            report.append(f"  - {issue}")
    else:
        report.append("✅ データ品質: 問題なし")
    
    return "\n".join(report)
```

## 🚀 実行・運用

### 基本的な収集実行

```bash
# 標準的な収集実行（1000件）
python collect_indie_games.py

# 少量テスト実行（20件）  
python /tmp/quick_batch_test.py

# 大量収集実行（3000件）
python -c "
import asyncio
from collect_indie_games import IndieGameCollector

async def large_collection():
    async with IndieGameCollector() as collector:
        await collector.collect_indie_games(limit=3000)

asyncio.run(large_collection())
"
```

### 定期実行設定

```bash
# crontab設定例
# 毎日午前2時に新規データ収集
0 2 * * * cd /workspace && python collect_indie_games.py >> /var/log/steam-collection.log 2>&1

# 毎週日曜日午前3時に大量データ更新
0 3 * * 0 cd /workspace && python collect_indie_games.py --limit=5000 >> /var/log/steam-weekly.log 2>&1
```

### パフォーマンス最適化

```python
# 並列処理最適化
async def optimized_collection(self, app_ids: List[int]) -> None:
    """並列処理による高速データ収集"""
    
    # セマフォで同時接続数制御
    semaphore = asyncio.Semaphore(10)  # 最大10並列
    
    async def fetch_with_semaphore(app_id: int):
        async with semaphore:
            return await self.get_game_details(app_id)
    
    # バッチ処理で効率化
    batch_size = 50
    for i in range(0, len(app_ids), batch_size):
        batch = app_ids[i:i + batch_size]
        tasks = [fetch_with_semaphore(app_id) for app_id in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果処理
        for app_id, result in zip(batch, results):
            if not isinstance(result, Exception) and result:
                if self.is_indie_game(result):
                    await self.save_game_to_db(result)
```

---

このデータ収集ガイドを参考に、効率的で品質の高いデータ収集システムを構築・運用してください。Steam APIの制限を遵守しながら、包括的なインディーゲームデータベースの構築が可能です。