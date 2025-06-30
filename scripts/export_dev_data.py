#!/usr/bin/env python3
"""
開発環境データのエクスポートスクリプト
PostgreSQLダンプを作成してRenderに移行可能な形式で出力
"""

import os
import subprocess
import sys
from datetime import datetime

def export_development_data():
    """開発環境のデータをエクスポート"""
    print("🚀 開発環境データエクスポート開始")
    print("=" * 50)
    
    # 開発環境の接続設定
    dev_config = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DB", "steam_analytics"),
        "user": os.getenv("POSTGRES_USER", "steam_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
    }
    
    print(f"🔗 エクスポート元: {dev_config['host']}:{dev_config['port']}/{dev_config['database']}")
    
    # エクスポートファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = f"steam_analytics_export_{timestamp}.sql"
    
    try:
        # pg_dumpコマンド実行
        print("📦 PostgreSQLダンプ作成中...")
        
        env = os.environ.copy()
        env["PGPASSWORD"] = dev_config["password"]
        
        # データのみエクスポート（スキーマは除外）
        cmd = [
            "pg_dump",
            "-h", dev_config["host"],
            "-p", str(dev_config["port"]),
            "-U", dev_config["user"],
            "-d", dev_config["database"],
            "--data-only",  # データのみ
            "--no-owner",   # オーナー情報除外
            "--no-privileges",  # 権限情報除外
            "-f", dump_file
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            # ファイルサイズ確認
            file_size = os.path.getsize(dump_file) / (1024 * 1024)  # MB
            print(f"✅ ダンプファイル作成完了: {dump_file}")
            print(f"📊 ファイルサイズ: {file_size:.1f} MB")
            
            # 簡易統計表示
            with open(dump_file, 'r') as f:
                content = f.read()
                insert_count = content.count('INSERT INTO')
                print(f"📈 推定レコード数: {insert_count:,}件")
            
            print(f"\n🎯 次のステップ:")
            print(f"1. {dump_file} をRender環境にアップロード")
            print(f"2. Renderで以下のコマンド実行:")
            print(f"   psql $DATABASE_URL < {dump_file}")
            
            return dump_file
            
        else:
            print(f"❌ ダンプ作成エラー: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ エクスポートエラー: {e}")
        return None

def create_render_import_script(dump_file):
    """Render用インポートスクリプト作成"""
    if not dump_file:
        return
        
    script_content = f"""#!/bin/bash
# Render環境データインポートスクリプト
# 使用方法: Renderのビルド時またはCron Jobで実行

echo "🚀 Steam Analytics データインポート開始"

# データベース接続確認
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URLが設定されていません"
    exit 1
fi

echo "🔗 データベース接続確認中..."
psql $DATABASE_URL -c "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ データベース接続失敗"
    exit 1
fi

echo "✅ データベース接続成功"

# テーブル初期化
echo "🛠️ テーブル初期化中..."
python init_render_db.py

# データインポート
echo "📦 データインポート実行中..."
psql $DATABASE_URL < {dump_file}

if [ $? -eq 0 ]; then
    echo "✅ データインポート完了"
    
    # 統計確認
    echo "📊 インポート結果確認:"
    psql $DATABASE_URL -c "SELECT COUNT(*) as total_games FROM games;"
    psql $DATABASE_URL -c "SELECT COUNT(*) as indie_games FROM games WHERE 'Indie' = ANY(genres);"
else
    echo "❌ データインポート失敗"
    exit 1
fi

echo "🎉 データ移行完了!"
"""
    
    script_file = "import_to_render.sh"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    # 実行権限付与
    os.chmod(script_file, 0o755)
    
    print(f"📝 Renderインポートスクリプト作成: {script_file}")

if __name__ == "__main__":
    dump_file = export_development_data()
    create_render_import_script(dump_file)