#!/usr/bin/env python3
"""
成功要因分析のテストスクリプト（同期版）
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 環境設定
load_dotenv()

def test_success_analysis():
    """成功要因分析のテスト実行"""
    
    print("🎯 Steam成功要因分析テスト開始")
    print("=" * 50)
    
    try:
        # データベース接続
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
        
        engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
        with engine.connect() as conn:
            # 価格別成功率分析
            price_success_query = text("""
                WITH game_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        price_final/100.0 as price_usd,
                        positive_reviews,
                        negative_reviews,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE 
                            WHEN positive_reviews >= 50 AND 
                                 CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.8 
                            THEN 1 ELSE 0 
                        END as is_successful
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 5
                      AND genres::text LIKE '%Indie%'
                )
                SELECT 
                    CASE 
                        WHEN price_usd = 0 THEN 'Free'
                        WHEN price_usd <= 5 THEN '$0-$5'
                        WHEN price_usd <= 10 THEN '$5-$10'
                        WHEN price_usd <= 20 THEN '$10-$20'
                        ELSE '$20+'
                    END as price_tier,
                    COUNT(*) as total_games,
                    SUM(is_successful) as successful_games,
                    CAST(SUM(is_successful) AS FLOAT) / COUNT(*) * 100 as success_rate,
                    AVG(rating) as avg_rating,
                    AVG(price_usd) as avg_price
                FROM game_metrics
                GROUP BY 
                    CASE 
                        WHEN price_usd = 0 THEN 'Free'
                        WHEN price_usd <= 5 THEN '$0-$5'
                        WHEN price_usd <= 10 THEN '$5-$10'
                        WHEN price_usd <= 20 THEN '$10-$20'
                        ELSE '$20+'
                    END
                ORDER BY success_rate DESC;
            """)
            
            result = conn.execute(price_success_query)
            price_data = [dict(row._mapping) for row in result]
            
            print("💰 価格別成功率分析:")
            for price in price_data:
                success_rate = round(price['success_rate'] or 0, 1)
                avg_rating = round(price['avg_rating'] or 0, 3)
                avg_price = round(price['avg_price'] or 0, 2)
                print(f"  {price['price_tier']:8s}: {success_rate:5.1f}% "
                      f"({price['successful_games']}/{price['total_games']}) "
                      f"平均評価{avg_rating:.3f} 平均${avg_price}")
            
            # ジャンル別成功率分析
            genre_success_query = text("""
                WITH game_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        genres,
                        price_final/100.0 as price_usd,
                        positive_reviews,
                        negative_reviews,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE 
                            WHEN positive_reviews >= 30 AND 
                                 CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.75 
                            THEN 1 ELSE 0 
                        END as is_successful
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 5
                      AND genres::text LIKE '%Indie%'
                      AND genres IS NOT NULL
                      AND array_length(genres, 1) > 0
                )
                SELECT 
                    UNNEST(genres) as genre,
                    COUNT(*) as total_games,
                    SUM(is_successful) as successful_games,
                    CAST(SUM(is_successful) AS FLOAT) / COUNT(*) * 100 as success_rate,
                    AVG(rating) as avg_rating,
                    AVG(price_usd) as avg_price
                FROM game_metrics
                GROUP BY UNNEST(genres)
                HAVING COUNT(*) >= 3
                ORDER BY success_rate DESC, total_games DESC
                LIMIT 10;
            """)
            
            result = conn.execute(genre_success_query)
            genre_data = [dict(row._mapping) for row in result]
            
            print("\n🏆 ジャンル別成功率 TOP10:")
            for i, genre in enumerate(genre_data, 1):
                success_rate = round(genre['success_rate'] or 0, 1)
                avg_rating = round(genre['avg_rating'] or 0, 3)
                avg_price = round(genre['avg_price'] or 0, 2)
                print(f"  {i:2d}. {genre['genre']:15s}: {success_rate:5.1f}% "
                      f"({genre['successful_games']}/{genre['total_games']}) "
                      f"評価{avg_rating:.3f} ${avg_price}")
            
            # プラットフォーム戦略別成功率
            platform_success_query = text("""
                WITH game_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        platforms_windows,
                        platforms_mac,
                        platforms_linux,
                        positive_reviews,
                        negative_reviews,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE 
                            WHEN positive_reviews >= 30 AND 
                                 CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.75 
                            THEN 1 ELSE 0 
                        END as is_successful,
                        (CASE WHEN platforms_windows THEN 1 ELSE 0 END +
                         CASE WHEN platforms_mac THEN 1 ELSE 0 END +
                         CASE WHEN platforms_linux THEN 1 ELSE 0 END) as platform_count
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 5
                      AND genres::text LIKE '%Indie%'
                )
                SELECT 
                    CASE 
                        WHEN platform_count = 1 THEN 'Single Platform'
                        WHEN platform_count = 2 THEN 'Dual Platform'
                        WHEN platform_count = 3 THEN 'Multi-Platform'
                        ELSE 'Other'
                    END as platform_strategy,
                    COUNT(*) as total_games,
                    SUM(is_successful) as successful_games,
                    CAST(SUM(is_successful) AS FLOAT) / COUNT(*) * 100 as success_rate,
                    AVG(rating) as avg_rating,
                    AVG(platform_count) as avg_platform_count
                FROM game_metrics
                GROUP BY 
                    CASE 
                        WHEN platform_count = 1 THEN 'Single Platform'
                        WHEN platform_count = 2 THEN 'Dual Platform'
                        WHEN platform_count = 3 THEN 'Multi-Platform'
                        ELSE 'Other'
                    END
                ORDER BY success_rate DESC;
            """)
            
            result = conn.execute(platform_success_query)
            platform_data = [dict(row._mapping) for row in result]
            
            print("\n🖥️ プラットフォーム戦略別成功率:")
            for platform in platform_data:
                success_rate = round(platform['success_rate'] or 0, 1)
                avg_rating = round(platform['avg_rating'] or 0, 3)
                avg_platforms = round(platform['avg_platform_count'] or 0, 1)
                print(f"  {platform['platform_strategy']:15s}: {success_rate:5.1f}% "
                      f"({platform['successful_games']}/{platform['total_games']}) "
                      f"評価{avg_rating:.3f} 平均{avg_platforms}プラットフォーム")
            
            # 戦略提案
            print("\n💡 データ駆動型戦略提案:")
            
            # 最高成功率の価格帯
            if price_data:
                best_price = max(price_data, key=lambda x: x['success_rate'])
                print(f"  1. 最適価格帯「{best_price['price_tier']}」で成功率{best_price['success_rate']:.1f}%を実現")
            
            # 最高成功率のジャンル
            if genre_data:
                best_genre = genre_data[0]
                print(f"  2. 高成功率ジャンル「{best_genre['genre']}」での特化戦略（成功率{best_genre['success_rate']:.1f}%）")
            
            # 最高成功率のプラットフォーム戦略
            if platform_data:
                best_platform = max(platform_data, key=lambda x: x['success_rate'])
                print(f"  3. 推奨プラットフォーム戦略「{best_platform['platform_strategy']}」で成功率{best_platform['success_rate']:.1f}%")
            
            print("  4. コミュニティ重視のマーケティングでレビュー数増加を図る")
            print("  5. 早期アクセスでユーザーフィードバックを活用した開発")
            
            print("\n✅ 成功要因分析テスト完了")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_success_analysis()