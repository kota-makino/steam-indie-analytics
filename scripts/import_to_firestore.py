#!/usr/bin/env python3
"""
JSONデータをFirestoreにインポートするスクリプト
Steam Indie Analytics - Firebase/Firestore連携
"""

import json
import os
from datetime import datetime
from google.cloud import firestore
from google.cloud.firestore import Client

def initialize_firestore() -> Client:
    """Firestoreクライアントを初期化"""
    # Google Cloud認証（Cloud Shell/Cloud Run環境では自動）
    db = firestore.Client()
    return db

def import_games_to_firestore(json_file_path: str):
    """JSONファイルからFirestoreにゲームデータをインポート"""
    
    print(f"🔥 Firestoreへのデータインポートを開始...")
    print(f"📄 ファイル: {json_file_path}")
    
    # Firestoreクライアント初期化
    db = initialize_firestore()
    
    # JSONファイル読み込み
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ エラー: ファイル {json_file_path} が見つかりません")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}")
        return False
    
    # データ構造確認
    if isinstance(data, dict) and 'games' in data:
        games_data = data['games']
        export_info = data.get('export_info', {})
        print(f"📊 エクスポート情報: {export_info}")
    elif isinstance(data, list):
        games_data = data
    else:
        print("❌ 不明なJSONデータ構造")
        return False
    
    print(f"📈 インポート対象: {len(games_data)} ゲーム")
    
    # バッチ書き込みでFirestoreにデータ投入
    batch = db.batch()
    batch_count = 0
    total_count = 0
    
    for game in games_data:
        # ドキュメントID（app_idを使用）
        doc_id = str(game.get('app_id', f'game_{total_count}'))
        
        # ゲームドキュメント作成
        game_ref = db.collection('games').document(doc_id)
        
        # データクリーニング（Firestoreに適した形式に変換）
        cleaned_game = clean_game_data(game)
        
        batch.set(game_ref, cleaned_game)
        batch_count += 1
        total_count += 1
        
        # バッチサイズ上限（Firestoreは500ドキュメント/バッチ）
        if batch_count >= 450:
            try:
                batch.commit()
                print(f"✅ バッチコミット完了: {total_count} / {len(games_data)}")
                batch = db.batch()
                batch_count = 0
            except Exception as e:
                print(f"❌ バッチコミットエラー: {e}")
                return False
    
    # 残りのドキュメントをコミット
    if batch_count > 0:
        try:
            batch.commit()
            print(f"✅ 最終バッチコミット完了")
        except Exception as e:
            print(f"❌ 最終バッチエラー: {e}")
            return False
    
    # インポート情報をメタデータとして保存
    meta_ref = db.collection('metadata').document('import_info')
    meta_ref.set({
        'imported_at': firestore.SERVER_TIMESTAMP,
        'total_games': len(games_data),
        'source_file': json_file_path,
        'export_info': export_info
    })
    
    print(f"🎉 Firestoreインポート完了: {total_count} ゲーム")
    return True

def clean_game_data(game: dict) -> dict:
    """ゲームデータをFirestore用にクリーニング"""
    cleaned = {}
    
    # 基本情報
    cleaned['app_id'] = game.get('app_id')
    cleaned['name'] = game.get('name', '')
    cleaned['type'] = game.get('type', 'game')
    cleaned['is_free'] = game.get('is_free', False)
    cleaned['short_description'] = game.get('short_description', '')
    
    # 価格情報（整数値）
    cleaned['price_initial'] = int(game.get('price_initial', 0))
    cleaned['price_final'] = int(game.get('price_final', 0))
    cleaned['price_usd'] = round(game.get('price_final', 0) / 100, 2)  # セントからドル
    
    # レビュー情報
    cleaned['positive_reviews'] = int(game.get('positive_reviews', 0))
    cleaned['negative_reviews'] = int(game.get('negative_reviews', 0))
    cleaned['total_reviews'] = cleaned['positive_reviews'] + cleaned['negative_reviews']
    
    if cleaned['total_reviews'] > 0:
        cleaned['positive_percentage'] = round((cleaned['positive_reviews'] / cleaned['total_reviews']) * 100, 1)
    else:
        cleaned['positive_percentage'] = 0.0
    
    # リリース日
    if game.get('release_date_text'):
        cleaned['release_date'] = game.get('release_date_text')
    
    # 開発者・パブリッシャー（配列として保持）
    cleaned['developers'] = game.get('developers', [])
    cleaned['publishers'] = game.get('publishers', [])
    
    # ジャンル・タグ
    cleaned['genres'] = game.get('genres', [])
    cleaned['tags'] = game.get('tags', [])
    
    # プラットフォーム
    platforms = []
    if game.get('platforms_windows'): platforms.append('Windows')
    if game.get('platforms_mac'): platforms.append('Mac')
    if game.get('platforms_linux'): platforms.append('Linux')
    cleaned['platforms'] = platforms
    
    # その他の数値データ
    cleaned['estimated_owners'] = int(game.get('estimated_owners', 0))
    cleaned['peak_ccu'] = int(game.get('peak_ccu', 0))
    
    # Firestore用タイムスタンプ
    cleaned['created_at'] = firestore.SERVER_TIMESTAMP
    
    return cleaned

if __name__ == "__main__":
    # JSONファイルパス
    json_file = "steam_indie_games_20250630_095737.json"
    
    if not os.path.exists(json_file):
        print(f"❌ ファイル {json_file} が見つかりません")
        print("💡 スクリプトをプロジェクトルートで実行してください")
        exit(1)
    
    # インポート実行
    success = import_games_to_firestore(json_file)
    
    if success:
        print("✅ Firestoreセットアップ完了！")
        print("🎮 Cloud RunダッシュボードからFirestoreデータにアクセスできます")
    else:
        print("❌ インポート失敗")
        exit(1)