"""
バッチ処理によるインディーゲームデータ継続収集スクリプト

大量データを効率的に収集するため、複数回に分けて実行する。
進捗保存機能付きで中断・再開が可能。
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any

from collect_indie_games import IndieGameCollector


class BatchCollector:
    """バッチ処理によるデータ収集管理"""

    def __init__(self, target_count: int = 1000, batch_size: int = 100):
        self.target_count = target_count
        self.batch_size = batch_size
        self.progress_file = "/workspace/data/collection_progress.json"
        self.log_file = "/workspace/data/collection_log.txt"
        
        # データディレクトリを作成
        os.makedirs("/workspace/data", exist_ok=True)
        
    def load_progress(self) -> Dict[str, Any]:
        """進捗情報を読み込み"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.log_message(f"進捗読み込みエラー: {e}")
        
        return {
            "total_processed": 0,
            "total_collected": 0,
            "completed_batches": [],
            "last_app_ids": [],
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
    
    def save_progress(self, progress: Dict[str, Any]) -> None:
        """進捗情報を保存"""
        try:
            progress["last_update"] = datetime.now().isoformat()
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_message(f"進捗保存エラー: {e}")
    
    def log_message(self, message: str) -> None:
        """ログメッセージを記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # ログファイル書き込みエラーは無視
    
    async def run_collection_batch(self, batch_num: int, progress: Dict[str, Any]) -> Dict[str, Any]:
        """単一バッチの収集実行"""
        
        self.log_message(f"📦 バッチ {batch_num} 開始 (目標: {self.batch_size}件)")
        
        batch_start_time = time.time()
        
        async with IndieGameCollector() as collector:
            # Steam APIから新しいゲームリストを取得
            # 前回の結果と重複しないように工夫
            app_ids = await collector.get_steam_game_list(self.batch_size * 3)  # 多めに取得
            
            # 既に処理済みのApp IDを除外
            processed_ids = set()
            for batch_ids in progress.get("completed_batches", []):
                processed_ids.update(batch_ids)
            
            new_app_ids = [app_id for app_id in app_ids if app_id not in processed_ids][:self.batch_size]
            
            if not new_app_ids:
                self.log_message("⚠️  新しいゲームIDが見つかりませんでした")
                return progress
            
            self.log_message(f"🎯 対象App ID数: {len(new_app_ids)}件")
            
            # データ収集実行
            indie_count = 0
            total_processed = 0
            collected_games = []
            
            for i, app_id in enumerate(new_app_ids):
                total_processed += 1
                
                # 進捗表示（10件ごと）
                if (i + 1) % 10 == 0:
                    self.log_message(f"  進捗: {i+1}/{len(new_app_ids)} - インディー収集済み: {indie_count}件")
                
                # 既存データをチェック
                if await collector.check_existing_game(app_id):
                    continue
                
                # ゲーム詳細情報を取得
                game_data = await collector.get_game_details(app_id)
                if not game_data:
                    continue
                
                # インディーゲーム判定
                is_indie = collector.is_indie_game(game_data)
                
                if is_indie:
                    indie_count += 1
                    
                    # レビューデータを取得
                    review_data = await collector.get_game_reviews(app_id)
                    
                    # データベースに保存
                    await collector.save_game_to_db(game_data, review_data)
                    
                    collected_games.append({
                        "app_id": app_id,
                        "name": game_data.get("name"),
                        "developers": game_data.get("developers"),
                        "genres": [g.get("description") for g in game_data.get("genres", [])],
                        "total_reviews": review_data.get("total_reviews", 0) if review_data else 0
                    })
                
                # レート制限対策
                await asyncio.sleep(0.3)
        
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time
        
        # 進捗を更新
        progress["total_processed"] += total_processed
        progress["total_collected"] += indie_count
        progress["completed_batches"].append(new_app_ids)
        progress["last_app_ids"] = new_app_ids
        
        self.log_message(f"✅ バッチ {batch_num} 完了:")
        self.log_message(f"   処理済み: {total_processed}件")
        self.log_message(f"   インディー収集: {indie_count}件")
        self.log_message(f"   実行時間: {batch_duration/60:.1f}分")
        self.log_message(f"   累計収集: {progress['total_collected']}件")
        
        # 進捗をファイルに保存
        self.save_progress(progress)
        
        return progress
    
    async def run_full_collection(self) -> None:
        """完全なデータ収集実行"""
        
        self.log_message("🚀 バッチ収集プロセス開始")
        self.log_message(f"🎯 目標: {self.target_count}件のインディーゲームデータ")
        self.log_message(f"📦 バッチサイズ: {self.batch_size}件")
        self.log_message("=" * 80)
        
        # 進捗を読み込み
        progress = self.load_progress()
        
        current_collected = progress.get("total_collected", 0)
        batch_num = len(progress.get("completed_batches", [])) + 1
        
        if current_collected > 0:
            self.log_message(f"📊 前回までの収集済み: {current_collected}件")
            self.log_message(f"📦 次回バッチ番号: {batch_num}")
        
        # 目標に達するまで繰り返し
        while current_collected < self.target_count:
            remaining = self.target_count - current_collected
            current_batch_size = min(self.batch_size, remaining)
            
            self.log_message(f"\n📦 バッチ {batch_num} / 残り目標: {remaining}件")
            
            try:
                # バッチ実行
                progress = await self.run_collection_batch(batch_num, progress)
                current_collected = progress.get("total_collected", 0)
                
                # 進捗レポート
                completion_rate = current_collected / self.target_count * 100
                self.log_message(f"📈 進捗率: {completion_rate:.1f}% ({current_collected}/{self.target_count})")
                
                batch_num += 1
                
                # バッチ間の休憩（API制限対策）
                if current_collected < self.target_count:
                    self.log_message("⏳ バッチ間休憩: 30秒")
                    await asyncio.sleep(30)
                
            except Exception as e:
                self.log_message(f"❌ バッチ {batch_num} エラー: {e}")
                self.log_message("⏳ エラー回復のため60秒待機")
                await asyncio.sleep(60)
                continue
        
        # 完了レポート
        self.log_message("\n" + "=" * 80)
        self.log_message("🎉 データ収集完了!")
        self.log_message(f"✅ 最終収集数: {current_collected}件")
        
        start_time = datetime.fromisoformat(progress.get("start_time", datetime.now().isoformat()))
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() / 3600
        
        self.log_message(f"⏱️  総実行時間: {total_duration:.1f}時間")
        self.log_message(f"📊 平均収集速度: {current_collected/total_duration:.1f}件/時間")


async def main():
    """メイン実行関数"""
    
    print("🎮 Steam インディーゲーム バッチ収集ツール")
    print("=" * 80)
    
    # バッチ収集実行（目標1000件、バッチサイズ50件）
    collector = BatchCollector(target_count=1000, batch_size=50)
    
    try:
        await collector.run_full_collection()
    except KeyboardInterrupt:
        print("\n⚠️  ユーザーによる中断")
        print("📄 進捗は保存されています。後で再開可能です。")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        print("📄 進捗は保存されています。")


if __name__ == "__main__":
    asyncio.run(main())