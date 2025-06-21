#!/usr/bin/env python3
"""
市場分析機能のテストスクリプト
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 環境設定
load_dotenv()

# データベース接続設定
def get_async_db_session():
    """非同期データベースセッション取得"""
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DB", "steam_analytics"),
        "user": os.getenv("POSTGRES_USER", "steam_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
    }
    
    async_engine = create_async_engine(
        f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    
    async_session_factory = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    return async_session_factory


async def test_market_analysis():
    """市場分析のテスト実行"""
    
    print("🎮 Steam市場分析テスト開始")
    print("=" * 50)
    
    try:
        session_factory = get_async_db_session()
        async with session_factory() as session:
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
            
            result = await session.execute(basic_stats_query)
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
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price
                FROM games 
                WHERE type = 'game' 
                  AND genres IS NOT NULL 
                  AND array_length(genres, 1) > 0
                GROUP BY UNNEST(genres)
                HAVING COUNT(*) >= 5
                ORDER BY game_count DESC
                LIMIT 5;
            """)
            
            result = await session.execute(genre_query)
            genres = [dict(row._mapping) for row in result]
            
            print("\n🏆 人気ジャンル TOP5:")
            for i, genre in enumerate(genres, 1):
                print(f"  {i}. {genre['genre']}: {genre['game_count']:,}件 (平均${genre['avg_price']:.2f})")
            
            # 価格帯分析
            price_query = text("""
                SELECT 
                    CASE 
                        WHEN price_final = 0 THEN 'Free'
                        WHEN price_final <= 500 THEN '$0-$5'
                        WHEN price_final <= 1000 THEN '$5-$10'
                        WHEN price_final <= 2000 THEN '$10-$20'
                        ELSE '$20+'
                    END as price_range,
                    COUNT(*) as game_count
                FROM games 
                WHERE type = 'game'
                GROUP BY 
                    CASE 
                        WHEN price_final = 0 THEN 'Free'
                        WHEN price_final <= 500 THEN '$0-$5'
                        WHEN price_final <= 1000 THEN '$5-$10'
                        WHEN price_final <= 2000 THEN '$10-$20'
                        ELSE '$20+'
                    END
                ORDER BY game_count DESC;
            """)
            
            result = await session.execute(price_query)
            prices = [dict(row._mapping) for row in result]
            
            print("\n💰 価格帯分布:")
            for price_range in prices:
                percentage = (price_range['game_count'] / stats['total_games']) * 100
                print(f"  {price_range['price_range']}: {price_range['game_count']:,}件 ({percentage:.1f}%)")
            
            # 市場洞察
            indie_ratio = (stats['indie_games'] / stats['total_games']) * 100
            free_ratio = (stats['free_games'] / stats['total_games']) * 100
            
            print("\n💡 市場洞察:")
            print(f"  • インディーゲーム比率{indie_ratio:.1f}%で市場に重要な影響")
            print(f"  • 無料ゲーム{free_ratio:.1f}%でフリーミアム戦略が普及")
            print(f"  • 最人気ジャンル「{genres[0]['genre']}」が市場を牽引")
            
            # 成功要因分析（簡易版）
            success_query = text("""
                SELECT 
                    CASE 
                        WHEN positive_reviews >= 100 AND 
                             CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.8 
                        THEN 'High Success'
                        WHEN positive_reviews >= 20 AND 
                             CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.7 
                        THEN 'Moderate Success'
                        ELSE 'Below Average'
                    END as success_level,
                    COUNT(*) as game_count,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price
                FROM games 
                WHERE type = 'game' 
                  AND positive_reviews + negative_reviews >= 10
                GROUP BY 
                    CASE 
                        WHEN positive_reviews >= 100 AND 
                             CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.8 
                        THEN 'High Success'
                        WHEN positive_reviews >= 20 AND 
                             CAST(positive_reviews AS FLOAT) / (positive_reviews + negative_reviews) >= 0.7 
                        THEN 'Moderate Success'
                        ELSE 'Below Average'
                    END
                ORDER BY 
                    CASE 
                        WHEN success_level = 'High Success' THEN 1
                        WHEN success_level = 'Moderate Success' THEN 2
                        ELSE 3
                    END;
            """)
            
            result = await session.execute(success_query)
            success_data = [dict(row._mapping) for row in result]
            
            print("\n🎯 成功要因分析:")
            for success in success_data:
                print(f"  {success['success_level']}: {success['game_count']:,}件 (平均${success['avg_price']:.2f})")
            
            print("\n✅ 市場分析テスト完了")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_market_analysis())