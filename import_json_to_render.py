#!/usr/bin/env python3
'''
JSON形式データをRender環境にインポートするスクリプト
'''

import json
import os
import psycopg2
from urllib.parse import urlparse

def import_from_json():
    # DATABASE_URL取得
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URLが設定されていません")
        return False
    
    # 接続設定
    parsed_url = urlparse(database_url)
    db_config = {
        "host": parsed_url.hostname,
        "port": parsed_url.port or 5432,
        "database": parsed_url.path[1:],
        "user": parsed_url.username,
        "password": parsed_url.password,
    }
    
    try:
        # JSONデータ読み込み
        with open("steam_indie_games_20250630_095737.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        games = data["games"]
        print(f"📦 インポート対象: {len(games):,}件")
        
        # データベース接続
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # テーブル初期化
        print("🛠️ テーブル初期化...")
        cursor.execute("DELETE FROM games WHERE 'Indie' = ANY(genres)")
        
        # データインサート
        insert_sql = '''
        INSERT INTO games (
            app_id, name, type, is_free, short_description,
            developers, publishers, price_final,
            platforms_windows, platforms_mac, platforms_linux,
            genres, positive_reviews, negative_reviews, total_reviews
        ) VALUES (
            %(app_id)s, %(name)s, %(type)s, %(is_free)s, %(short_description)s,
            %(developers)s, %(publishers)s, %(price_final)s,
            %(platforms_windows)s, %(platforms_mac)s, %(platforms_linux)s,
            %(genres)s, %(positive_reviews)s, %(negative_reviews)s, %(total_reviews)s
        ) ON CONFLICT (app_id) DO NOTHING
        '''
        
        success_count = 0
        for game in games:
            try:
                cursor.execute(insert_sql, game)
                success_count += 1
                if success_count % 100 == 0:
                    print(f"   インポート進行中: {success_count}/{len(games)} ({success_count/len(games)*100:.1f}%)")
            except Exception as e:
                print(f"   スキップ: {game.get('name', 'Unknown')} - {e}")
        
        print(f"✅ インポート完了: {success_count:,}/{len(games):,}件")
        
        cursor.close()
        conn.close()
        
        # 正規化処理も実行
        print("🔄 正規化処理を実行中...")
        try:
            import subprocess
            result = subprocess.run(["python", "normalize_render_data.py"], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print("✅ 正規化処理完了")
            else:
                print(f"⚠️ 正規化処理エラー: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 正規化処理エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ インポートエラー: {e}")
        return False

if __name__ == "__main__":
    import_from_json()
