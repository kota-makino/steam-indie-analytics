#!/usr/bin/env python3
"""
静的HTMLダッシュボード生成スクリプト
StreamlitのUI問題を回避するため
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from datetime import datetime
import json

def generate_static_dashboard():
    """静的HTMLダッシュボードを生成"""
    
    load_dotenv()
    
    # データベース接続
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DB", "steam_analytics"),
        "user": os.getenv("POSTGRES_USER", "steam_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
    }
    
    engine = create_engine(
        f"postgresql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    
    try:
        # データ取得
        with engine.connect() as conn:
            # 基本統計
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN genres::text LIKE '%Indie%' THEN 1 ELSE 0 END) as indie_games,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price,
                    COUNT(CASE WHEN is_free THEN 1 END) as free_games
                FROM games 
                WHERE type = 'game';
            """)
            
            result = conn.execute(stats_query)
            stats = result.fetchone()
            
            # ジャンル別統計
            genre_query = text("""
                SELECT 
                    UNNEST(genres) as genre,
                    COUNT(*) as count,
                    AVG(CASE WHEN price_final > 0 THEN price_final/100.0 ELSE 0 END) as avg_price
                FROM games 
                WHERE type = 'game' AND genres IS NOT NULL
                GROUP BY UNNEST(genres)
                ORDER BY count DESC
                LIMIT 10;
            """)
            
            genre_result = conn.execute(genre_query)
            genres = [dict(row._mapping) for row in genre_result]
        
        # HTML生成
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steam インディーゲーム市場分析</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            color: #1f77b4;
            margin-bottom: 30px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #1f77b4;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #1f77b4;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .section {{
            margin: 30px 0;
        }}
        .genre-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .genre-table th, .genre-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .genre-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .update-time {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Steam インディーゲーム市場分析</h1>
            <p>データ駆動型の市場洞察ダッシュボード</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{stats[0]:,}</div>
                <div class="metric-label">総ゲーム数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{stats[1]:,}</div>
                <div class="metric-label">インディーゲーム数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${stats[2]:.2f}</div>
                <div class="metric-label">平均価格</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{stats[3]:,}</div>
                <div class="metric-label">無料ゲーム数</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 人気ジャンル TOP 10</h2>
            <table class="genre-table">
                <thead>
                    <tr>
                        <th>ジャンル</th>
                        <th>ゲーム数</th>
                        <th>平均価格</th>
                        <th>市場シェア</th>
                    </tr>
                </thead>
                <tbody>"""
        
        for i, genre in enumerate(genres[:10], 1):
            share = genre['count'] / stats[0] * 100
            html_content += f"""
                    <tr>
                        <td>{genre['genre']}</td>
                        <td>{genre['count']:,}</td>
                        <td>${genre['avg_price']:.2f}</td>
                        <td>{share:.1f}%</td>
                    </tr>"""
        
        html_content += f"""
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>💡 市場洞察</h2>
            <div style="background: #e8f4f8; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8;">
                <h3>主要な発見:</h3>
                <ul>
                    <li><strong>インディーゲーム比率:</strong> {stats[1]/stats[0]*100:.1f}% - Steam市場で重要な位置</li>
                    <li><strong>価格戦略:</strong> 平均${stats[2]:.2f}の価格設定</li>
                    <li><strong>無料ゲーム:</strong> {stats[3]/stats[0]*100:.1f}%が無料提供</li>
                    <li><strong>最人気ジャンル:</strong> {genres[0]['genre'] if genres else 'N/A'} ({genres[0]['count'] if genres else 0}件)</li>
                </ul>
                
                <h3>推奨戦略:</h3>
                <ul>
                    <li>🎯 ニッチジャンルでの専門化</li>
                    <li>💰 競争力のある価格設定 ($5-15範囲)</li>
                    <li>🖥️ マルチプラットフォーム対応</li>
                    <li>📈 コミュニティ重視の開発</li>
                </ul>
            </div>
        </div>
        
        <div class="update-time">
            最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            データソース: Steam Web API | 
            Steam Analytics Dashboard
        </div>
    </div>
</body>
</html>"""
        
        # HTMLファイル保存
        with open('/workspace/static_dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("✅ 静的ダッシュボードを生成しました: static_dashboard.html")
        print(f"📊 統計: {stats[0]:,}ゲーム, {stats[1]:,}インディー, ${stats[2]:.2f}平均価格")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    generate_static_dashboard()