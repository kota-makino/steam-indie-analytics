#!/usr/bin/env python3
"""
開発環境データをSQL INSERT文形式でエクスポート
Docker環境に依存せずにPythonでデータ移行用ファイルを作成
"""

import os
import sys
import json
from datetime import datetime
from urllib.parse import urlparse

# プロジェクトルートをパスに追加
sys.path.append('/workspace')

try:
    from src.config.database import get_sync_session
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)

def get_db_connection():
    """データベース接続を取得"""
    # DATABASE_URL優先
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
        # 個別環境変数
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
    
    return psycopg2.connect(**db_config)

def export_games_data():
    """gamesテーブルのデータをエクスポート"""
    print("🚀 開発環境データエクスポート開始")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # データ件数確認
        cursor.execute("SELECT COUNT(*) FROM games")
        total_count = cursor.fetchone()[0]
        print(f"📊 総ゲーム数: {total_count:,}件")
        
        # インディーゲームのみエクスポート
        cursor.execute("""
            SELECT * FROM games 
            WHERE type = 'game' AND 'Indie' = ANY(genres)
            ORDER BY created_at DESC
        """)
        
        games_data = cursor.fetchall()
        indie_count = len(games_data)
        print(f"🎮 インディーゲーム: {indie_count:,}件")
        
        if indie_count == 0:
            print("❌ エクスポートするデータがありません")
            return None
        
        # SQLファイル作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sql_file = f"render_import_{timestamp}.sql"
        
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("-- Steam Analytics データインポート用SQL\n")
            f.write(f"-- 作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- エクスポート件数: {indie_count:,}件\n\n")
            
            f.write("-- 既存データクリア（オプション）\n")
            f.write("-- DELETE FROM games WHERE 'Indie' = ANY(genres);\n\n")
            
            # INSERT文生成
            for game in games_data:
                # NULL値とエスケープ処理
                values = []
                for key, value in game.items():
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, str):
                        # シングルクォートエスケープ
                        escaped = value.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(value, bool):
                        values.append("TRUE" if value else "FALSE")
                    elif isinstance(value, list):
                        # PostgreSQL配列形式
                        if value:
                            array_items = [f"'{item.replace("'", "''")}'" for item in value]
                            values.append("ARRAY[" + ",".join(array_items) + "]")
                        else:
                            values.append("ARRAY[]::text[]")
                    else:
                        values.append(str(value))
                
                columns = list(game.keys())
                f.write(f"INSERT INTO games ({', '.join(columns)}) VALUES ({', '.join(values)}) ON CONFLICT (app_id) DO NOTHING;\n")
        
        # ファイル情報表示
        file_size = os.path.getsize(sql_file) / (1024 * 1024)
        print(f"✅ SQLファイル作成完了: {sql_file}")
        print(f"📦 ファイルサイズ: {file_size:.1f} MB")
        
        cursor.close()
        conn.close()
        
        return sql_file
        
    except Exception as e:
        print(f"❌ エクスポートエラー: {e}")
        return None

def create_render_instructions(sql_file):
    """Render環境での実行手順を作成"""
    if not sql_file:
        return
    
    instructions = f"""
🎯 Render環境でのデータインポート手順

1. 📁 ファイルアップロード:
   {sql_file} をRenderプロジェクトにアップロード

2. 🔧 Build Commandに追加:
   pip install -r requirements.txt && python init_render_db.py && psql $DATABASE_URL < {sql_file}

3. 🚀 代替案 - GitHub Actions:
   .github/workflows/import-data.yml を作成して自動実行

4. ✅ 確認方法:
   ダッシュボードで「🔄 データ更新」→ 1000+件のデータが表示される

注意: {sql_file} は約{os.path.getsize(sql_file) / (1024 * 1024):.1f}MBです
"""
    
    with open("RENDER_IMPORT_INSTRUCTIONS.md", "w") as f:
        f.write(instructions)
    
    print(instructions)

if __name__ == "__main__":
    sql_file = export_games_data()
    create_render_instructions(sql_file)