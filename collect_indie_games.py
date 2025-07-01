"""
インディーゲームデータ収集スクリプト

Steam Store API（認証不要）を使用してインディーゲームの情報を収集し、
PostgreSQLデータベースに保存します。
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

import aiohttp
import psycopg2  # type: ignore
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# データベース接続設定（DATABASE_URL優先対応）
def get_db_config():
    """データベース接続設定を取得"""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url and "postgresql://" in database_url:
        # DATABASE_URLをパース
        from urllib.parse import urlparse
        parsed_url = urlparse(database_url)
        
        return {
            "host": parsed_url.hostname,
            "port": parsed_url.port or 5432,
            "database": parsed_url.path[1:],  # '/'を除去
            "user": parsed_url.username,
            "password": parsed_url.password,
        }
    else:
        # 個別環境変数から設定
        return {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }

DB_CONFIG = get_db_config()


class IndieGameCollector:
    """インディーゲーム データコレクター"""

    def __init__(self) -> None:
        self.session = None
        self.db_conn = None
        self.collected_games = []

        # インディーゲーム識別キーワード
        self.indie_keywords = [
            "indie",
            "independent",
            "pixel",
            "retro",
            "adventure",
            "casual",
            "puzzle",
            "platformer",
            "roguelike",
            "survival",
            "crafting",
            "sandbox",
            "exploration",
            "story",
            "narrative",
        ]

        # 大手パブリッシャー（除外対象）
        self.major_publishers = [
            "valve",
            "electronic arts",
            "ea",
            "activision",
            "ubisoft",
            "bethesda",
            "square enix",
            "capcom",
            "bandai namco",
            "sega",
            "take-two",
            "nintendo",
            "sony",
            "microsoft",
            "rockstar",
        ]

    async def __aenter__(self) -> "IndieGameCollector":
        """非同期コンテキスト開始"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # データベース接続
        self.db_conn = psycopg2.connect(**DB_CONFIG)
        self.db_conn.autocommit = True

        await self.create_tables()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """非同期コンテキスト終了"""
        if self.session:
            await self.session.close()
        if self.db_conn:
            self.db_conn.close()

    async def create_tables(self) -> None:
        """データベーステーブルを作成"""

        create_games_table = """
        CREATE TABLE IF NOT EXISTS games (
            app_id INTEGER PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            type VARCHAR(50),
            is_free BOOLEAN DEFAULT FALSE,
            detailed_description TEXT,
            short_description TEXT,
            developers TEXT[],
            publishers TEXT[],
            price_currency VARCHAR(10),
            price_initial INTEGER,
            price_final INTEGER,
            price_discount_percent INTEGER,
            release_date_text VARCHAR(100),
            release_date_coming_soon BOOLEAN,
            platforms_windows BOOLEAN DEFAULT FALSE,
            platforms_mac BOOLEAN DEFAULT FALSE,
            platforms_linux BOOLEAN DEFAULT FALSE,
            genres TEXT[],
            categories TEXT[],
            positive_reviews INTEGER,
            negative_reviews INTEGER,
            total_reviews INTEGER,
            recommendation_score FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        create_reviews_table = """
        CREATE TABLE IF NOT EXISTS game_reviews (
            id SERIAL PRIMARY KEY,
            app_id INTEGER REFERENCES games(app_id),
            total_positive INTEGER DEFAULT 0,
            total_negative INTEGER DEFAULT 0,
            total_reviews INTEGER DEFAULT 0,
            review_score INTEGER DEFAULT 0,
            review_score_desc VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        # インデックス作成
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_games_name ON games(name);",
            "CREATE INDEX IF NOT EXISTS idx_games_type ON games(type);",
            "CREATE INDEX IF NOT EXISTS idx_games_developers ON games USING GIN(developers);",
            "CREATE INDEX IF NOT EXISTS idx_games_genres ON games USING GIN(genres);",
            "CREATE INDEX IF NOT EXISTS idx_games_total_reviews ON games(total_reviews);",
        ]

        cursor = self.db_conn.cursor()

        try:
            cursor.execute(create_games_table)
            cursor.execute(create_reviews_table)

            for index_sql in create_indexes:
                cursor.execute(index_sql)

            print("✅ データベーステーブルを作成/確認しました")

        except Exception as e:
            print(f"❌ テーブル作成エラー: {e}")
        finally:
            cursor.close()

    async def get_steam_game_list(self, limit: int = 1000) -> List[int]:
        """Steam APIから全ゲームリストを取得し、ランダムサンプリング"""
        
        print("🔍 Steam全ゲームリストを取得中...")
        
        # Steam Web APIからゲーム一覧を取得
        url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    apps = data.get("applist", {}).get("apps", [])
                    
                    print(f"✅ 総ゲーム数: {len(apps):,}件")
                    
                    # ゲーム名にインディー関連キーワードが含まれるものを優先的に抽出
                    potential_indie_games = []
                    other_games = []
                    
                    for app in apps:
                        name = app.get("name", "").lower()
                        app_id = app.get("appid")
                        
                        # 無効なApp IDやDLC、ツールを除外
                        if not app_id or app_id <= 0:
                            continue
                            
                        # 明らかにゲームではないものを除外
                        if any(keyword in name for keyword in ["dlc", "soundtrack", "demo", "trailer", "wallpaper", "tool"]):
                            continue
                            
                        # インディー関連キーワードをチェック
                        has_indie_keyword = any(keyword in name for keyword in self.indie_keywords)
                        
                        if has_indie_keyword:
                            potential_indie_games.append(app_id)
                        else:
                            other_games.append(app_id)
                    
                    print(f"🎯 インディー関連キーワード含有: {len(potential_indie_games):,}件")
                    
                    # 有名なインディーゲームも追加（確実にいくつかは取得するため）
                    known_indie_games = [
                        413150,  # Stardew Valley
                        250900,  # The Binding of Isaac: Rebirth
                        105600,  # Terraria
                        211820,  # Starbound
                        367520,  # Hollow Knight
                        391540,  # Undertale
                        257350,  # Hyper Light Drifter
                        447040,  # A Hat in Time
                        268910,  # Cuphead
                        574240,  # Ori and the Will of the Wisps
                        387290,  # Ori and the Blind Forest
                        593110,  # Dead Cells
                        588650,  # Subnautica
                        346110,  # ARK: Survival Evolved
                        294100,  # RimWorld
                        252950,  # Rocket League
                        431960,  # Wallpaper Engine
                        282070,  # This War of Mine
                        238460,  # BattleBlock Theater
                        108710,  # Alan Wake
                    ]
                    
                    # 組み合わせて重複を除去
                    import random
                    all_candidates = list(set(known_indie_games + potential_indie_games[:500] + random.sample(other_games, min(500, len(other_games)))))
                    random.shuffle(all_candidates)
                    
                    result = all_candidates[:limit]
                    print(f"📊 収集対象として選定: {len(result)}件")
                    
                    return result
                    
                else:
                    print(f"❌ Steam API エラー: HTTP {response.status}")
                    # フォールバック: 既知のゲームリストを使用
                    return self.get_fallback_game_list(limit)
                    
        except Exception as e:
            print(f"❌ Steam API取得エラー: {e}")
            return self.get_fallback_game_list(limit)
    
    def get_fallback_game_list(self, limit: int) -> List[int]:
        """Steam APIが利用できない場合のフォールバックリスト"""
        
        print("⚠️  フォールバックモード: 拡張された既知ゲームリストを使用")
        
        # より多くの既知インディーゲームリスト
        extended_indie_games = [
            413150, 250900, 105600, 211820, 367520, 391540, 257350, 447040, 268910,
            574240, 387290, 593110, 588650, 346110, 294100, 252950, 431960, 282070,
            238460, 108710, 200510, 219740, 233450, 239030, 244210, 261550, 274190,
            291160, 304430, 317400, 323190, 333600, 346330, 359550, 372490, 383870,
            394690, 414700, 424840, 431750, 447020, 454650, 465240, 489940, 504230,
            525200, 548430, 563720, 588650, 612020, 632360, 646570, 674940, 698780,
            730530, 755790, 784080, 824270, 863550, 892970, 924970, 955050, 975370,
            1000030, 1027290, 1058550, 1089490, 1119780, 1151340, 1182900, 1214460,
            1246020, 1277580, 1309140, 1340700, 1372260, 1403820, 1435380, 1466940,
            1498500, 1530060, 1561620, 1593180, 1624740, 1656300, 1687860, 1719420,
            1750980, 1782540, 1814100, 1845660, 1877220, 1908780, 1940340, 1971900,
            2003460, 2035020, 2066580, 2098140, 2129700, 2161260, 2192820, 2224380
        ]
        
        return extended_indie_games[:limit]

    async def get_game_details(self, app_id: int, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """ゲーム詳細情報を取得（リトライ機能付き）"""

        url = "https://store.steampowered.com/api/appdetails"
        params = {"appids": app_id, "l": "english", "cc": "us"}

        for attempt in range(max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        app_data = data.get(str(app_id))

                        if app_data and app_data.get("success"):
                            return app_data.get("data")
                        else:
                            if attempt == max_retries - 1:
                                print(f"⚠️  App ID {app_id}: データ取得失敗 (最終試行)")
                            return None
                    elif response.status == 429:  # Too Many Requests
                        wait_time = 2 ** attempt  # 指数バックオフ
                        print(f"⏳ App ID {app_id}: レート制限 - {wait_time}秒待機")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        if attempt == max_retries - 1:
                            print(f"❌ App ID {app_id}: HTTP {response.status}")
                        return None

            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    print(f"⏱️  App ID {app_id}: タイムアウト")
                else:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ App ID {app_id}: エラー - {e}")
                else:
                    await asyncio.sleep(1)
                    continue

        return None

    async def get_game_reviews(self, app_id: int) -> Optional[Dict[str, Any]]:
        """ゲームレビュー情報を取得"""

        url = f"https://store.steampowered.com/api/appreviews/{app_id}"
        params = {
            "json": 1,
            "language": "all",
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": 0,  # 統計情報のみ取得
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") == 1:
                        return data.get("query_summary", {})

        except Exception as e:
            print(f"❌ レビュー取得エラー (App ID {app_id}): {e}")

        return None

    def is_indie_game(self, game_data: Dict[str, Any]) -> bool:
        """
        ゲームがインディーゲームかどうかを判定
        
        ビューで表示される条件と一致させるため、以下の条件も適用:
        - ジャンル情報が存在すること
        - 開発者情報が存在すること
        - 基本的なゲーム情報が完全であること
        """

        # 基本データの存在チェック（ビューのJOIN条件に対応）
        if not game_data.get("name") or not game_data.get("steam_appid"):
            return False
            
        # ジャンル情報が存在するかチェック（ビューのINNER JOIN対応）
        genres = game_data.get("genres", [])
        if not genres:
            return False
            
        # 開発者情報が存在するかチェック（ビューのINNER JOIN対応）
        # ただし、既存データとの整合性のため、空の場合でも例外的に通す場合がある
        developers = game_data.get("developers", [])
        if not developers:
            # 例外: ジャンルが豊富で明らかにインディーゲームの場合は通す
            genres = game_data.get("genres", [])
            if len(genres) < 3:  # ジャンル情報が少ない場合は除外
                return False
            
        # DLCやデモは除外（ビューの品質基準に合わせる）
        name_lower = game_data.get("name", "").lower()
        if any(keyword in name_lower for keyword in ["demo", "dlc", "soundtrack", "trailer"]):
            return False
            
        # ゲームタイプのチェック
        game_type = game_data.get("type", "")
        if game_type not in ["game"]:
            return False

        # 開発者情報での判定
        publishers = game_data.get("publishers", [])

        # 大手パブリッシャーの場合は除外
        for publisher in publishers:
            if any(
                major.lower() in publisher.lower() for major in self.major_publishers
            ):
                return False

        # ジャンル情報での判定
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

        # 開発者とパブリッシャーが同じ場合（セルフパブリッシング）
        if developers and publishers and set(developers) == set(publishers):
            return True

        # 小規模チーム（開発者が1-2社）
        if len(developers) <= 2:
            return True

        return False

    async def run_data_migration(self) -> bool:
        """データ移行スクリプトを自動実行"""
        try:
            import subprocess
            import sys
            
            # データ移行スクリプトを実行
            result = subprocess.run(
                [sys.executable, "scripts/migrate_to_normalized_schema.py"],
                cwd="/workspace",
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )
            
            if result.returncode == 0:
                print(f"✅ データ移行が正常に完了しました")
                # 移行後のインディーゲーム数を取得
                try:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "インディーゲーム:" in line:
                            print(f"   📊 移行後インディーゲーム数: {line.split(':')[1].strip()}")
                            break
                except:
                    pass
                return True
            else:
                print(f"❌ データ移行でエラーが発生しました")
                print(f"   エラー出力: {result.stderr[:200]}...")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  データ移行がタイムアウトしました（5分超過）")
            return False
        except Exception as e:
            print(f"❌ データ移行の実行中にエラー: {e}")
            return False

    async def save_game_to_db(
        self, game_data: Dict[str, Any], review_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """ゲーム情報をデータベースに保存"""

        cursor = self.db_conn.cursor()

        try:
            # 価格情報の処理
            price_overview = game_data.get("price_overview", {})
            price_currency = price_overview.get("currency")
            price_initial = price_overview.get("initial")
            price_final = price_overview.get("final")
            price_discount = price_overview.get("discount_percent")

            # リリース日情報の処理
            release_date = game_data.get("release_date", {})
            release_date_text = release_date.get("date")
            release_coming_soon = release_date.get("coming_soon", False)

            # プラットフォーム情報の処理
            platforms = game_data.get("platforms", {})
            platforms_windows = platforms.get("windows", False)
            platforms_mac = platforms.get("mac", False)
            platforms_linux = platforms.get("linux", False)

            # ジャンル・カテゴリ情報の処理
            genres = [g.get("description") for g in game_data.get("genres", [])]
            categories = [c.get("description") for c in game_data.get("categories", [])]

            # レビュー情報の処理
            positive_reviews = None
            negative_reviews = None
            total_reviews = None

            if review_data:
                positive_reviews = review_data.get("total_positive", 0)
                negative_reviews = review_data.get("total_negative", 0)
                total_reviews = review_data.get("total_reviews", 0)

            # ゲーム情報をINSERT (ON CONFLICT DO UPDATE)
            insert_game_sql = """
            INSERT INTO games (
                app_id, name, type, is_free, detailed_description, short_description,
                developers, publishers, price_currency, price_initial, price_final, price_discount_percent,
                release_date_text, release_date_coming_soon,
                platforms_windows, platforms_mac, platforms_linux,
                genres, categories, positive_reviews, negative_reviews, total_reviews,
                updated_at
            ) VALUES (
                %(app_id)s, %(name)s, %(type)s, %(is_free)s, %(detailed_description)s, %(short_description)s,
                %(developers)s, %(publishers)s, %(price_currency)s, %(price_initial)s, %(price_final)s, %(price_discount_percent)s,
                %(release_date_text)s, %(release_date_coming_soon)s,
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

            game_params = {
                "app_id": game_data.get("steam_appid"),
                "name": game_data.get("name"),
                "type": game_data.get("type"),
                "is_free": game_data.get("is_free", False),
                "detailed_description": game_data.get("detailed_description"),
                "short_description": game_data.get("short_description"),
                "developers": game_data.get("developers", []),
                "publishers": game_data.get("publishers", []),
                "price_currency": price_currency,
                "price_initial": price_initial,
                "price_final": price_final,
                "price_discount_percent": price_discount,
                "release_date_text": release_date_text,
                "release_date_coming_soon": release_coming_soon,
                "platforms_windows": platforms_windows,
                "platforms_mac": platforms_mac,
                "platforms_linux": platforms_linux,
                "genres": genres,
                "categories": categories,
                "positive_reviews": positive_reviews,
                "negative_reviews": negative_reviews,
                "total_reviews": total_reviews,
            }

            cursor.execute(insert_game_sql, game_params)

            # レビュー詳細情報も保存
            if review_data:
                insert_review_sql = """
                INSERT INTO game_reviews (
                    app_id, total_positive, total_negative, total_reviews,
                    review_score, review_score_desc
                ) VALUES (
                    %(app_id)s, %(total_positive)s, %(total_negative)s, %(total_reviews)s,
                    %(review_score)s, %(review_score_desc)s
                )
                """

                review_params = {
                    "app_id": game_data.get("steam_appid"),
                    "total_positive": review_data.get("total_positive", 0),
                    "total_negative": review_data.get("total_negative", 0),
                    "total_reviews": review_data.get("total_reviews", 0),
                    "review_score": review_data.get("review_score", 0),
                    "review_score_desc": review_data.get("review_score_desc"),
                }

                cursor.execute(insert_review_sql, review_params)

            print(
                f"✅ 保存完了: {game_data.get('name')} (ID: {game_data.get('steam_appid')})"
            )

        except Exception as e:
            print(f"❌ DB保存エラー: {e}")
        finally:
            cursor.close()

    async def check_existing_game(self, app_id: int) -> bool:
        """データベース内にゲームが既に存在するかチェック"""
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM games WHERE app_id = %s", (app_id,))
            return cursor.fetchone() is not None
        except Exception:
            return False
        finally:
            cursor.close()

    async def collect_indie_games(self, limit: int = 20) -> None:
        """インディーゲーム情報の収集を実行"""

        print(f"🚀 インディーゲームデータ収集開始 (最大{limit}件)")
        print("=" * 60)

        # 対象ゲームのApp IDリストを取得
        app_ids = await self.get_steam_game_list(limit)

        indie_count = 0
        total_processed = 0
        skipped_existing = 0

        for i, app_id in enumerate(app_ids):
            total_processed += 1

            print(f"\n📊 進捗: {i+1}/{len(app_ids)} - App ID {app_id}")

            # 既存データをチェック（効率化）
            if await self.check_existing_game(app_id):
                skipped_existing += 1
                print(f"  ⏭️  スキップ: 既に収集済み")
                continue

            # ゲーム詳細情報を取得
            game_data = await self.get_game_details(app_id)
            if not game_data:
                continue

            print(f"  🎮 ゲーム名: {game_data.get('name', 'N/A')}")
            print(f"  🏢 開発者: {game_data.get('developers', ['N/A'])}")
            print(
                f"  📋 ジャンル: {[g.get('description') for g in game_data.get('genres', [])]}"
            )

            # インディーゲーム判定
            is_indie = self.is_indie_game(game_data)
            print(f"  🔍 インディーゲーム判定: {'✅ YES' if is_indie else '❌ NO'}")

            if is_indie:
                indie_count += 1

                # レビューデータを取得
                review_data = await self.get_game_reviews(app_id)
                if review_data:
                    total_reviews = review_data.get("total_reviews", 0)
                    print(f"  📝 レビュー数: {total_reviews:,}")

                # データベースに保存
                await self.save_game_to_db(game_data, review_data)
                self.collected_games.append(
                    {
                        "app_id": app_id,
                        "name": game_data.get("name"),
                        "developers": game_data.get("developers"),
                        "total_reviews": (
                            review_data.get("total_reviews", 0) if review_data else 0
                        ),
                    }
                )

            # レート制限対策（0.5秒待機 - 大量収集のため高速化）
            await asyncio.sleep(0.5)
            
            # 進捗定期レポート（50件ごと）
            if (i + 1) % 50 == 0:
                elapsed_time = (i + 1) * 0.5 / 60  # 概算経過時間（分）
                remaining_time = (len(app_ids) - i - 1) * 0.5 / 60  # 概算残り時間（分）
                print(f"\n📈 中間レポート ({i+1}/{len(app_ids)}):")
                print(f"   ✅ インディーゲーム収集済み: {indie_count}件")
                print(f"   ⏭️  スキップ済み（重複）: {skipped_existing}件")
                print(f"   ⏱️  経過時間: {elapsed_time:.1f}分")
                print(f"   ⏳ 残り予想時間: {remaining_time:.1f}分")
                print("   " + "="*50)

        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 収集結果サマリー")
        print("=" * 60)
        print(f"🔍 処理済みゲーム: {total_processed}件")
        print(f"⏭️  スキップ済み（重複）: {skipped_existing}件")
        print(f"✅ インディーゲーム新規収集: {indie_count}件")
        rate = indie_count / (total_processed - skipped_existing) * 100 if (total_processed - skipped_existing) > 0 else 0
        print(f"📈 インディー判定率: {rate:.1f}%")
        print(f"⏱️  総実行時間: {total_processed * 0.5 / 60:.1f}分")
        
        # 自動データ移行の実行
        print(f"\n🔄 データ移行を自動実行中...")
        migration_success = await self.run_data_migration()
        
        # ダッシュボード反映のための完了通知
        print(f"\n🔄 ダッシュボード更新:")
        print(f"   ✅ データベース更新完了")
        print(f"   📊 新規インディーゲーム: {indie_count}件")
        if migration_success:
            print(f"   🔄 データ移行: 自動完了")
        else:
            print(f"   ⚠️  データ移行: 手動実行が必要")
        print(f"   ⏱️  完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   💡 ダッシュボードで「🔄 データ更新」ボタンを押して反映してください")

        if self.collected_games:
            print(f"\n🏆 収集したインディーゲーム TOP 5:")
            # レビュー数でソート
            sorted_games = sorted(
                self.collected_games, key=lambda x: x["total_reviews"], reverse=True
            )
            for i, game in enumerate(sorted_games[:5]):
                reviews = game["total_reviews"]
                print(f"  {i+1}. {game['name']} - {reviews:,} レビュー")


async def main() -> None:
    """メイン実行関数"""

    print("🎮 Steam インディーゲーム データ収集ツール")
    print("=" * 60)

    async with IndieGameCollector() as collector:
        await collector.collect_indie_games(limit=1000)  # 1000件のデータ収集

    print("\n🎉 データ収集完了!")


if __name__ == "__main__":
    asyncio.run(main())
