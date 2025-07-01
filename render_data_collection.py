#!/usr/bin/env python3
"""
Render環境用データ収集実行スクリプト
開発環境同等のデータ量確保のための専用スクリプト
"""

import os
import subprocess
import time
from datetime import datetime

def main():
    """Render環境でのデータ収集実行"""
    print("🚀 Render環境 - Steam データ収集開始")
    print("=" * 60)
    
    # 環境確認
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URLが設定されていません")
        return False
    
    print(f"🔗 データベース接続確認済み")
    print(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Steam インディーゲームデータ収集実行
        print("\n🎮 Steam インディーゲームデータ収集開始...")
        print("💡 この処理には10-15分程度かかります")
        
        start_time = time.time()
        
        # collect_indie_games.py実行
        result = subprocess.run(
            ["python", "collect_indie_games.py"],
            capture_output=True,
            text=True,
            timeout=1800  # 30分タイムアウト
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print("✅ データ収集完了")
            print(f"⏱️ 実行時間: {duration/60:.1f}分")
            
            # 結果表示
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-10:]:  # 最後の10行を表示
                    if any(keyword in line for keyword in ['✅', '📊', '🎮', '完了']):
                        print(f"   {line}")
            
            print("\n🎉 Render環境データ収集完了！")
            print("📊 ダッシュボードで豊富なデータを確認できます")
            return True
            
        else:
            print("❌ データ収集中にエラーが発生しました")
            if result.stderr:
                print("エラー詳細:")
                print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ データ収集がタイムアウトしました（30分制限）")
        print("💡 Render環境では処理時間に制限があります")
        return False
        
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)