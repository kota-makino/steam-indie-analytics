-- Steam Analytics - 正規化データベーススキーマ
-- 配列型を使わず、適切な関係テーブル設計に変更

-- ジャンルマスタテーブル
CREATE TABLE IF NOT EXISTS genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 開発者マスタテーブル
CREATE TABLE IF NOT EXISTS developers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    country VARCHAR(100),
    founded_year INTEGER,
    is_indie BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- パブリッシャーマスタテーブル
CREATE TABLE IF NOT EXISTS publishers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    country VARCHAR(100),
    founded_year INTEGER,
    is_major BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- カテゴリマスタテーブル
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ゲームテーブル（正規化版）
CREATE TABLE IF NOT EXISTS games_normalized (
    app_id INTEGER PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(50) DEFAULT 'game',
    is_free BOOLEAN DEFAULT FALSE,
    short_description TEXT,
    detailed_description TEXT,
    
    -- 価格情報
    price_currency VARCHAR(10) DEFAULT 'USD',
    price_initial INTEGER, -- セント単位
    price_final INTEGER,   -- セント単位
    price_discount_percent INTEGER DEFAULT 0,
    
    -- リリース情報
    release_date_text VARCHAR(50),
    release_date_coming_soon BOOLEAN DEFAULT FALSE,
    release_date DATE,
    
    -- プラットフォーム対応
    platforms_windows BOOLEAN DEFAULT FALSE,
    platforms_mac BOOLEAN DEFAULT FALSE,
    platforms_linux BOOLEAN DEFAULT FALSE,
    
    -- レビュー情報
    positive_reviews INTEGER DEFAULT 0,
    negative_reviews INTEGER DEFAULT 0,
    total_reviews INTEGER DEFAULT 0,
    
    -- メタデータ
    header_image_url TEXT,
    website_url TEXT,
    support_url TEXT,
    
    -- インディーゲーム判定
    is_indie BOOLEAN DEFAULT FALSE,
    
    -- タイムスタンプ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ゲーム-ジャンル中間テーブル
CREATE TABLE IF NOT EXISTS game_genres (
    game_id INTEGER REFERENCES games_normalized(app_id) ON DELETE CASCADE,
    genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE, -- 主要ジャンルかどうか
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_id, genre_id)
);

-- ゲーム-開発者中間テーブル
CREATE TABLE IF NOT EXISTS game_developers (
    game_id INTEGER REFERENCES games_normalized(app_id) ON DELETE CASCADE,
    developer_id INTEGER REFERENCES developers(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE, -- 主要開発者かどうか
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_id, developer_id)
);

-- ゲーム-パブリッシャー中間テーブル
CREATE TABLE IF NOT EXISTS game_publishers (
    game_id INTEGER REFERENCES games_normalized(app_id) ON DELETE CASCADE,
    publisher_id INTEGER REFERENCES publishers(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE, -- 主要パブリッシャーかどうか
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_id, publisher_id)
);

-- ゲーム-カテゴリ中間テーブル
CREATE TABLE IF NOT EXISTS game_categories (
    game_id INTEGER REFERENCES games_normalized(app_id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_id, category_id)
);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_games_normalized_type ON games_normalized(type);
CREATE INDEX IF NOT EXISTS idx_games_normalized_is_free ON games_normalized(is_free);
CREATE INDEX IF NOT EXISTS idx_games_normalized_is_indie ON games_normalized(is_indie);
CREATE INDEX IF NOT EXISTS idx_games_normalized_price_final ON games_normalized(price_final);
CREATE INDEX IF NOT EXISTS idx_games_normalized_total_reviews ON games_normalized(total_reviews);
CREATE INDEX IF NOT EXISTS idx_games_normalized_release_date ON games_normalized(release_date);

CREATE INDEX IF NOT EXISTS idx_game_genres_game_id ON game_genres(game_id);
CREATE INDEX IF NOT EXISTS idx_game_genres_genre_id ON game_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_game_genres_is_primary ON game_genres(is_primary);

CREATE INDEX IF NOT EXISTS idx_game_developers_game_id ON game_developers(game_id);
CREATE INDEX IF NOT EXISTS idx_game_developers_developer_id ON game_developers(developer_id);
CREATE INDEX IF NOT EXISTS idx_game_developers_is_primary ON game_developers(is_primary);

CREATE INDEX IF NOT EXISTS idx_game_publishers_game_id ON game_publishers(game_id);
CREATE INDEX IF NOT EXISTS idx_game_publishers_publisher_id ON game_publishers(publisher_id);

CREATE INDEX IF NOT EXISTS idx_game_categories_game_id ON game_categories(game_id);
CREATE INDEX IF NOT EXISTS idx_game_categories_category_id ON game_categories(category_id);

-- 分析用ビュー作成
CREATE OR REPLACE VIEW game_analysis_view AS
SELECT 
    g.app_id,
    g.name,
    g.type,
    g.is_free,
    g.short_description,
    g.price_final,
    g.price_final / 100.0 AS price_usd,
    g.release_date,
    g.platforms_windows,
    g.platforms_mac,
    g.platforms_linux,
    (g.platforms_windows::int + g.platforms_mac::int + g.platforms_linux::int) AS platform_count,
    g.positive_reviews,
    g.negative_reviews,
    g.total_reviews,
    CASE 
        WHEN g.total_reviews > 0 THEN g.positive_reviews::float / g.total_reviews
        ELSE NULL 
    END AS rating,
    g.is_indie,
    
    -- 主要ジャンル
    pg.name AS primary_genre,
    
    -- 主要開発者
    pd.name AS primary_developer,
    pd.is_indie AS developer_is_indie,
    
    -- 主要パブリッシャー
    pp.name AS primary_publisher,
    
    -- 価格カテゴリ
    CASE 
        WHEN g.is_free THEN '無料'
        WHEN g.price_final < 500 THEN '低価格帯 (¥0-750)'
        WHEN g.price_final < 1500 THEN '中価格帯 (¥750-2,250)'
        WHEN g.price_final < 3000 THEN '高価格帯 (¥2,250-4,500)'
        ELSE 'プレミアム (¥4,500+)'
    END AS price_category,
    
    g.created_at,
    g.updated_at
    
FROM games_normalized g

-- 主要ジャンル
LEFT JOIN game_genres gg_primary ON g.app_id = gg_primary.game_id AND gg_primary.is_primary = true
LEFT JOIN genres pg ON gg_primary.genre_id = pg.id

-- 主要開発者
LEFT JOIN game_developers gd_primary ON g.app_id = gd_primary.game_id AND gd_primary.is_primary = true
LEFT JOIN developers pd ON gd_primary.developer_id = pd.id

-- 主要パブリッシャー
LEFT JOIN game_publishers gp_primary ON g.app_id = gp_primary.game_id AND gp_primary.is_primary = true
LEFT JOIN publishers pp ON gp_primary.publisher_id = pp.id

WHERE g.type = 'game';

-- 統計用ビュー
CREATE OR REPLACE VIEW market_stats_view AS
SELECT 
    COUNT(*) as total_games,
    COUNT(*) FILTER (WHERE is_indie = true) as indie_games,
    COUNT(*) FILTER (WHERE is_free = true) as free_games,
    AVG(price_final / 100.0) FILTER (WHERE is_free = false) as avg_price,
    AVG(total_reviews) as avg_reviews,
    AVG(rating) FILTER (WHERE rating IS NOT NULL) as avg_rating
FROM game_analysis_view;

-- ジャンル統計ビュー
CREATE OR REPLACE VIEW genre_stats_view AS
SELECT 
    g.name as genre_name,
    COUNT(gg.game_id) as game_count,
    COUNT(gg.game_id) FILTER (WHERE ga.is_indie = true) as indie_count,
    AVG(ga.price_usd) FILTER (WHERE ga.is_free = false) as avg_price,
    AVG(ga.rating) FILTER (WHERE ga.rating IS NOT NULL) as avg_rating,
    AVG(ga.total_reviews) as avg_reviews
FROM genres g
LEFT JOIN game_genres gg ON g.id = gg.genre_id
LEFT JOIN game_analysis_view ga ON gg.game_id = ga.app_id
GROUP BY g.id, g.name
HAVING COUNT(gg.game_id) > 0
ORDER BY game_count DESC;

COMMENT ON TABLE games_normalized IS '正規化されたゲーム情報テーブル';
COMMENT ON TABLE genres IS 'ジャンルマスタテーブル';
COMMENT ON TABLE developers IS '開発者マスタテーブル';
COMMENT ON TABLE publishers IS 'パブリッシャーマスタテーブル';
COMMENT ON TABLE categories IS 'カテゴリマスタテーブル';
COMMENT ON VIEW game_analysis_view IS 'ダッシュボード用の統合分析ビュー';