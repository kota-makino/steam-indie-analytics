"""
データベース状態確認スクリプト

収集済みデータの状況を確認し、今後のデータ収集戦略を決定する。
"""

import os
import psycopg2  # type: ignore
from dotenv import load_dotenv
from typing import Dict, Any

# 環境変数の読み込み
load_dotenv()

# データベース接続設定
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "steam_analytics"),
    "user": os.getenv("POSTGRES_USER", "steam_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
}


def check_database_status() -> Dict[str, Any]:
    """データベースの現在の状態をチェック"""
    
    print("🔍 データベース状態確認開始")
    print("=" * 60)
    
    try:
        # データベース接続
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        status = {}
        
        # 1. 総ゲーム数
        cursor.execute("SELECT COUNT(*) FROM games;")
        total_games = cursor.fetchone()[0]
        status["total_games"] = total_games
        print(f"📊 総収集ゲーム数: {total_games:,}件")
        
        # 2. インディーゲーム数（ジャンルベース）
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE 'Indie' = ANY(genres) OR 'indie' = ANY(genres);
        """)
        indie_by_genre = cursor.fetchone()[0]
        status["indie_by_genre"] = indie_by_genre
        print(f"🎯 インディージャンル明記: {indie_by_genre:,}件")
        
        # 3. ゲームタイプ別統計
        cursor.execute("""
            SELECT type, COUNT(*) as count 
            FROM games 
            WHERE type IS NOT NULL 
            GROUP BY type 
            ORDER BY count DESC;
        """)
        game_types = cursor.fetchall()
        print(f"\n📋 ゲームタイプ別統計:")
        for game_type, count in game_types:
            print(f"  {game_type}: {count:,}件")
        status["game_types"] = dict(game_types)
        
        # 4. レビュー数統計
        cursor.execute("""
            SELECT 
                COUNT(*) as games_with_reviews,
                AVG(total_reviews) as avg_reviews,
                MAX(total_reviews) as max_reviews,
                MIN(total_reviews) as min_reviews
            FROM games 
            WHERE total_reviews IS NOT NULL AND total_reviews > 0;
        """)
        review_stats = cursor.fetchone()
        games_with_reviews, avg_reviews, max_reviews, min_reviews = review_stats
        print(f"\n📝 レビュー統計:")
        print(f"  レビューあり: {games_with_reviews:,}件")
        
        if avg_reviews is not None:
            print(f"  平均レビュー数: {avg_reviews:.1f}")
            print(f"  最大レビュー数: {max_reviews:,}")
            print(f"  最小レビュー数: {min_reviews}")
        else:
            print("  レビューデータなし")
        
        status["review_stats"] = {
            "games_with_reviews": games_with_reviews,
            "avg_reviews": float(avg_reviews) if avg_reviews else 0,
            "max_reviews": max_reviews if max_reviews else 0,
            "min_reviews": min_reviews if min_reviews else 0
        }
        
        # 5. 人気上位ゲーム（レビュー数順）
        cursor.execute("""
            SELECT name, developers[1], total_reviews, genres
            FROM games 
            WHERE total_reviews IS NOT NULL 
            ORDER BY total_reviews DESC 
            LIMIT 10;
        """)
        top_games = cursor.fetchall()
        print(f"\n🏆 人気ゲーム TOP 10 (レビュー数順):")
        for i, (name, developer, reviews, genres) in enumerate(top_games, 1):
            genre_str = ", ".join(genres[:3]) if genres else "N/A"
            print(f"  {i:2d}. {name[:40]:<40} | {developer[:20]:<20} | {reviews:>8,} | {genre_str}")
        
        # 6. 最近追加されたゲーム
        cursor.execute("""
            SELECT name, developers[1], created_at::date
            FROM games 
            ORDER BY created_at DESC 
            LIMIT 5;
        """)
        recent_games = cursor.fetchall()
        print(f"\n📅 最近追加されたゲーム:")
        for name, developer, date in recent_games:
            print(f"  {name[:50]:<50} | {developer[:20]:<20} | {date}")
        
        # 7. 開発者別統計（上位10社）
        cursor.execute("""
            SELECT 
                developer,
                COUNT(*) as game_count,
                AVG(total_reviews) as avg_reviews
            FROM (
                SELECT UNNEST(developers) as developer, total_reviews
                FROM games 
                WHERE developers IS NOT NULL AND array_length(developers, 1) > 0
            ) dev_games
            GROUP BY developer
            HAVING COUNT(*) >= 2
            ORDER BY game_count DESC, avg_reviews DESC
            LIMIT 10;
        """)
        top_developers = cursor.fetchall()
        print(f"\n🏢 活発な開発者 TOP 10:")
        for developer, game_count, avg_reviews in top_developers:
            avg_rev = avg_reviews if avg_reviews else 0
            print(f"  {developer[:30]:<30} | {game_count:>3}ゲーム | 平均{avg_rev:>6.0f}レビュー")
        
        # 8. 価格統計
        cursor.execute("""
            SELECT 
                COUNT(*) as paid_games,
                AVG(price_final::float / 100) as avg_price,
                MAX(price_final::float / 100) as max_price,
                MIN(price_final::float / 100) as min_price
            FROM games 
            WHERE price_final IS NOT NULL AND price_final > 0;
        """)
        price_stats = cursor.fetchone()
        if price_stats[0] > 0:
            paid_games, avg_price, max_price, min_price = price_stats
            print(f"\n💰 価格統計:")
            print(f"  有料ゲーム: {paid_games:,}件")
            print(f"  平均価格: ${avg_price:.2f}")
            print(f"  最高価格: ${max_price:.2f}")
            print(f"  最低価格: ${min_price:.2f}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ データベース状態確認完了")
        
        return status
        
    except Exception as e:
        print(f"❌ データベース確認エラー: {e}")
        return {}


def recommend_next_steps(status: Dict[str, Any]) -> None:
    """収集状況に基づく次のステップ推奨"""
    
    print("\n🎯 次のステップ推奨")
    print("=" * 60)
    
    total_games = status.get("total_games", 0)
    indie_games = status.get("indie_by_genre", 0)
    
    if total_games < 100:
        print("📈 状況: 初期段階 - より多くのデータが必要")
        print("🎯 推奨アクション:")
        print("  1. データ収集スクリプトを継続実行")
        print("  2. 目標: 500-1000件のゲームデータ収集")
        print("  3. 多様なジャンルのゲームをバランス良く収集")
        
    elif total_games < 500:
        print("📈 状況: 成長段階 - 分析準備中")
        print("🎯 推奨アクション:")
        print("  1. インディーゲーム比率を向上（目標: 50%以上）")
        print("  2. レビューデータの充実化")
        print("  3. 基本的な分析開始の準備")
        
    elif total_games < 1000:
        print("📈 状況: 分析可能段階 - 本格分析開始可能")
        print("🎯 推奨アクション:")
        print("  1. Jupyter Notebookでの探索的データ分析開始")
        print("  2. Streamlitダッシュボード構築開始")
        print("  3. 市場トレンド分析の実装")
        
    else:
        print("📈 状況: 成熟段階 - 高度な分析が可能")
        print("🎯 推奨アクション:")
        print("  1. 機械学習モデルによる成功予測")
        print("  2. 詳細な競合分析レポート")
        print("  3. 本格的なダッシュボード完成")
    
    print(f"\n📊 現在の進捗:")
    print(f"  総ゲーム数: {total_games:,}件 / 目標1000件")
    progress = min(100, total_games / 10)  # 1000件で100%
    print(f"  進捗率: {progress:.1f}%")
    
    if indie_games > 0:
        indie_ratio = indie_games / total_games * 100
        print(f"  インディーゲーム比率: {indie_ratio:.1f}%")


if __name__ == "__main__":
    status = check_database_status()
    recommend_next_steps(status)