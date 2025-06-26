"""
Render環境用Steam APIデータ収集スクリプト
バックグラウンドでの大量データ収集に最適化
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# パス設定
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from collect_indie_games import IndieGameCollector


class RenderDataCollector:
    """Render環境用データ収集クラス"""

    def __init__(self):
        self.is_render = os.getenv('RENDER') == 'true'
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        print(f"🌐 実行環境: {'Render' if self.is_render else 'Local'}")
        print(f"📊 環境設定: {self.environment}")

    async def collect_full_dataset(self, target_games: int = 500):
        """本格的なデータセット収集"""
        print(f"🚀 フルデータセット収集開始 (目標: {target_games}件)")
        print("=" * 60)
        
        start_time = datetime.now()
        
        async with IndieGameCollector() as collector:
            # より大量のデータ収集を実行
            await collector.collect_indie_games(limit=target_games * 3)  # 3倍収集してフィルタリング
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 データ収集完了!")
        print(f"⏱️  実行時間: {duration}")
        print(f"📊 完了時刻: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    async def verify_database_connection(self):
        """データベース接続確認"""
        try:
            import psycopg2
            
            db_config = {
                "host": os.getenv("POSTGRES_HOST"),
                "port": int(os.getenv("POSTGRES_PORT", 5432)),
                "database": os.getenv("POSTGRES_DB"),
                "user": os.getenv("POSTGRES_USER"),
                "password": os.getenv("POSTGRES_PASSWORD"),
            }
            
            print("🔗 データベース接続テスト中...")
            
            # 接続設定チェック
            missing_vars = [k for k, v in db_config.items() if v is None]
            if missing_vars:
                print(f"❌ 未設定の環境変数: {missing_vars}")
                return False
            
            # 接続テスト
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # 基本クエリ実行
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ PostgreSQL接続成功: {version[:50]}...")
            
            # ゲーム数確認
            cursor.execute("SELECT COUNT(*) FROM games WHERE 1=1")
            game_count = cursor.fetchone()[0]
            print(f"📊 現在のゲーム数: {game_count}件")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            return False

    async def run_migration_if_needed(self):
        """必要に応じてデータ移行実行"""
        try:
            import subprocess
            
            print("🔄 データ移行チェック...")
            
            # 移行スクリプトの存在確認
            migration_script = project_root / "scripts" / "migrate_to_normalized_schema.py"
            
            if migration_script.exists():
                print("📋 データ移行スクリプト実行中...")
                
                result = subprocess.run(
                    [sys.executable, str(migration_script)],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=600  # 10分タイムアウト
                )
                
                if result.returncode == 0:
                    print("✅ データ移行完了")
                    print(f"📊 移行結果:\n{result.stdout[-200:]}")  # 最後の200文字
                else:
                    print(f"⚠️  データ移行警告: {result.stderr[:100]}...")
                    
            else:
                print("⏭️  データ移行スクリプトが見つかりません（スキップ）")
                
        except subprocess.TimeoutExpired:
            print("⏱️  データ移行がタイムアウトしました")
        except Exception as e:
            print(f"❌ データ移行エラー: {e}")

    async def run_full_pipeline(self):
        """完全なデータパイプライン実行"""
        print("🔄 Steam Analytics データパイプライン実行")
        print("=" * 60)
        
        # 1. データベース接続確認
        if not await self.verify_database_connection():
            print("❌ データベース接続に失敗しました")
            return False
        
        # 2. データ収集実行
        if self.is_render:
            # Render環境: 本格データ収集
            await self.collect_full_dataset(target_games=1000)
        else:
            # ローカル環境: 限定データ収集
            await self.collect_full_dataset(target_games=200)
        
        # 3. データ移行実行
        await self.run_migration_if_needed()
        
        print("\n🎉 全データパイプライン完了!")
        return True


async def main():
    """メイン実行関数"""
    try:
        collector = RenderDataCollector()
        success = await collector.run_full_pipeline()
        
        if success:
            print("\n✅ Steam Analytics データ収集成功")
            exit(0)
        else:
            print("\n❌ データ収集に失敗しました")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  ユーザーによる中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        exit(1)


if __name__ == "__main__":
    # Render環境での非同期実行
    asyncio.run(main())