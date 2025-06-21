#!/usr/bin/env python3
"""
市場分析機能のテストスクリプト（同期版）
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

# 環境設定
load_dotenv()

# データベース接続設定
def get_db_engine():
    """データベースエンジン取得"""
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
    
    return engine


def test_market_analysis():
    """市場分析のテスト実行"""
    
    print("🎮 Steam市場分析テスト開始")
    print("=" * 50)
    
    try:
        engine = get_db_engine()
        
        with engine.connect() as conn:
            # 基本統計クエリ
            basic_stats_query = text("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN genres::text LIKE '%Indie%' THEN 1 END) as indie_games,
                    COUNT(CASE WHEN is_free THEN 1 END) as free_games,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price
                FROM games 
                WHERE type = 'game';
            """)
            
            result = conn.execute(basic_stats_query)
            stats = dict(result.fetchone()._mapping)
            
            # 基本統計表示
            print("📊 基本統計:")
            print(f"  総ゲーム数: {stats['total_games']:,}")
            print(f"  インディーゲーム: {stats['indie_games']:,}")
            print(f"  無料ゲーム: {stats['free_games']:,}")
            print(f"  平均価格: ${stats['avg_price']:.2f}")
            
            # ジャンル別TOP5
            genre_query = text("""
                SELECT 
                    UNNEST(genres) as genre,
                    COUNT(*) as game_count,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price,
                    AVG(CASE WHEN positive_reviews > 0 THEN 
                        CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) 
                        ELSE 0 END) as avg_rating
                FROM games 
                WHERE type = 'game' 
                  AND genres IS NOT NULL 
                  AND array_length(genres, 1) > 0
                GROUP BY UNNEST(genres)
                HAVING COUNT(*) >= 5
                ORDER BY game_count DESC
                LIMIT 10;
            """)
            
            result = conn.execute(genre_query)
            genres = [dict(row._mapping) for row in result]
            
            print("\n🏆 人気ジャンル TOP10:")
            for i, genre in enumerate(genres, 1):
                rating = f"評価{genre['avg_rating']:.3f}" if genre['avg_rating'] else "評価なし"
                print(f"  {i:2d}. {genre['genre']:15s}: {genre['game_count']:4,}件 (平均${genre['avg_price']:5.2f}, {rating})")
            
            # 価格帯分析
            price_query = text("""
                SELECT 
                    CASE 
                        WHEN price_final = 0 THEN 'Free'
                        WHEN price_final <= 500 THEN '$0-$5'
                        WHEN price_final <= 1000 THEN '$5-$10'
                        WHEN price_final <= 2000 THEN '$10-$20'
                        WHEN price_final <= 3000 THEN '$20-$30'
                        ELSE '$30+'
                    END as price_range,
                    COUNT(*) as game_count,
                    COUNT(CASE WHEN genres::text LIKE '%Indie%' THEN 1 END) as indie_count
                FROM games 
                WHERE type = 'game'
                GROUP BY 
                    CASE 
                        WHEN price_final = 0 THEN 'Free'
                        WHEN price_final <= 500 THEN '$0-$5'
                        WHEN price_final <= 1000 THEN '$5-$10'
                        WHEN price_final <= 2000 THEN '$10-$20'
                        WHEN price_final <= 3000 THEN '$20-$30'
                        ELSE '$30+'
                    END
                ORDER BY 
                    CASE 
                        WHEN price_final = 0 THEN 0
                        WHEN price_final <= 500 THEN 1
                        WHEN price_final <= 1000 THEN 2
                        WHEN price_final <= 2000 THEN 3
                        WHEN price_final <= 3000 THEN 4
                        ELSE 5
                    END;
            """)
            
            result = conn.execute(price_query)
            prices = [dict(row._mapping) for row in result]
            
            print("\n💰 価格帯分布:")
            for price_range in prices:
                percentage = (price_range['game_count'] / stats['total_games']) * 100
                indie_ratio = (price_range['indie_count'] / price_range['game_count']) * 100
                print(f"  {price_range['price_range']:8s}: {price_range['game_count']:4,}件 ({percentage:4.1f}%, インディー{indie_ratio:4.1f}%)")
            
            # 成功要因分析
            success_query = text("""
                WITH success_metrics AS (
                    SELECT 
                        app_id,
                        name,
                        price_final/100.0 as price_usd,
                        positive_reviews,
                        negative_reviews,
                        CASE WHEN positive_reviews + negative_reviews > 0 
                             THEN CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews)
                             ELSE 0 END as rating,
                        CASE WHEN genres::text LIKE '%Indie%' THEN 1 ELSE 0 END as is_indie
                    FROM games 
                    WHERE type = 'game' 
                      AND positive_reviews + negative_reviews >= 10
                )
                SELECT 
                    CASE 
                        WHEN rating >= 0.9 AND positive_reviews >= 100 THEN 'Highly Successful'
                        WHEN rating >= 0.8 AND positive_reviews >= 50 THEN 'Successful'
                        WHEN rating >= 0.7 AND positive_reviews >= 20 THEN 'Moderately Successful'
                        ELSE 'Below Average'
                    END as success_tier,
                    COUNT(*) as game_count,
                    AVG(price_usd) as avg_price,
                    AVG(is_indie) * 100 as indie_ratio,
                    AVG(rating) as avg_rating
                FROM success_metrics
                GROUP BY 
                    CASE 
                        WHEN rating >= 0.9 AND positive_reviews >= 100 THEN 'Highly Successful'
                        WHEN rating >= 0.8 AND positive_reviews >= 50 THEN 'Successful'
                        WHEN rating >= 0.7 AND positive_reviews >= 20 THEN 'Moderately Successful'
                        ELSE 'Below Average'
                    END
                ORDER BY 
                    CASE 
                        WHEN success_tier = 'Highly Successful' THEN 1
                        WHEN success_tier = 'Successful' THEN 2
                        WHEN success_tier = 'Moderately Successful' THEN 3
                        ELSE 4
                    END;
            """)
            
            result = conn.execute(success_query)
            success_data = [dict(row._mapping) for row in result]
            
            print("\n🎯 成功要因分析:")
            for success in success_data:
                print(f"  {success['success_tier']:20s}: {success['game_count']:4,}件 "
                      f"(平均${success['avg_price']:5.2f}, インディー{success['indie_ratio']:4.1f}%, "
                      f"評価{success['avg_rating']:.3f})")
            
            # 市場洞察
            indie_ratio = (stats['indie_games'] / stats['total_games']) * 100
            free_ratio = (stats['free_games'] / stats['total_games']) * 100
            
            print("\n💡 市場洞察:")
            print(f"  • インディーゲーム比率{indie_ratio:.1f}%で市場に重要な影響")
            print(f"  • 無料ゲーム{free_ratio:.1f}%でフリーミアム戦略が普及")
            print(f"  • 最人気ジャンル「{genres[0]['genre']}」が{genres[0]['game_count']:,}件で市場を牽引")
            
            # 成功ゲームの価格戦略
            successful_games = [s for s in success_data if s['success_tier'] in ['Highly Successful', 'Successful']]
            if successful_games:
                avg_success_price = sum(s['avg_price'] for s in successful_games) / len(successful_games)
                print(f"  • 成功ゲームの平均価格${avg_success_price:.2f}で最適価格帯が判明")
            
            print("\n✅ 市場分析テスト完了")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_market_analysis()