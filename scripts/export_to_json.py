#!/usr/bin/env python3
"""
開発環境データをJSON形式でエクスポート
軽量で扱いやすい形式でデータ移行
"""

import os
import sys
import json
from datetime import datetime
from urllib.parse import urlparse

sys.path.append('/workspace')

def export_to_json():
    """開発環境データをJSONでエクスポート"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # DATABASE_URL優先の接続設定
        database_url = os.getenv("DATABASE_URL")
        
        if database_url and "postgresql://" in database_url:
            parsed_url = urlparse(database_url)
            db_config = {
                "host": parsed_url.hostname,
                "port": parsed_url.port or 5432,
                "database": parsed_url.path[1:],
                "user": parsed_url.username,
                "password": parsed_url.password,
            }
        else:
            db_config = {
                "host": os.getenv("POSTGRES_HOST", "postgres"),
                "port": int(os.getenv("POSTGRES_PORT", 5432)),
                "database": os.getenv("POSTGRES_DB", "steam_analytics"),
                "user": os.getenv("POSTGRES_USER", "steam_user"),
                "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
            }
        
        print("🚀 JSON形式エクスポート開始")
        print(f"🔗 接続先: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # インディーゲームデータ取得
        cursor.execute("""
            SELECT 
                app_id, name, type, is_free, short_description,
                developers, publishers, price_final,
                platforms_windows, platforms_mac, platforms_linux,
                genres, positive_reviews, negative_reviews, total_reviews,
                created_at::text as created_at
            FROM games 
            WHERE type = 'game' AND 'Indie' = ANY(genres)
            ORDER BY total_reviews DESC NULLS LAST
            LIMIT 1000
        """)
        
        games_data = cursor.fetchall()
        
        # JSONシリアライズ可能な形式に変換
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "count": len(games_data),
                "source": "development_environment"
            },
            "games": []
        }
        
        for game in games_data:
            game_dict = dict(game)
            # datetime型をstring型に変換
            if game_dict.get('created_at'):
                game_dict['created_at'] = str(game_dict['created_at'])
            export_data["games"].append(game_dict)
        
        # JSONファイル作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"steam_indie_games_{timestamp}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        file_size = os.path.getsize(json_file) / (1024 * 1024)
        print(f"✅ JSONファイル作成完了: {json_file}")
        print(f"📦 ファイルサイズ: {file_size:.1f} MB")
        print(f"🎮 エクスポート件数: {len(games_data):,}件")
        
        cursor.close()
        conn.close()
        
        # インポートスクリプトも作成
        create_json_importer(json_file)
        
        return json_file
        
    except Exception as e:
        print(f"❌ エクスポートエラー: {e}")
        return None

def create_json_importer(json_file):
    """JSON用インポートスクリプト作成"""
    importer_script = f"""#!/usr/bin/env python3
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
    db_config = {{
        "host": parsed_url.hostname,
        "port": parsed_url.port or 5432,
        "database": parsed_url.path[1:],
        "user": parsed_url.username,
        "password": parsed_url.password,
    }}
    
    try:
        # JSONデータ読み込み
        with open("{json_file}", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        games = data["games"]
        print(f"📦 インポート対象: {{len(games):,}}件")
        
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
                    print(f"   インポート進行中: {{success_count}}/{{len(games)}} ({{success_count/len(games)*100:.1f}}%)")
            except Exception as e:
                print(f"   スキップ: {{game.get('name', 'Unknown')}} - {{e}}")
        
        print(f"✅ インポート完了: {{success_count:,}}/{{len(games):,}}件")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ インポートエラー: {{e}}")
        return False

if __name__ == "__main__":
    import_from_json()
"""
    
    importer_file = f"import_json_to_render.py"
    with open(importer_file, 'w') as f:
        f.write(importer_script)
    
    print(f"📝 インポートスクリプト作成: {importer_file}")

if __name__ == "__main__":
    export_to_json()