#!/usr/bin/env python3
"""
カスタムWebサーバー版ダッシュボード
Flask + HTML/CSS/JavaScript を使用してStreamlitの問題を完全に回避
"""

from flask import Flask, render_template_string, jsonify, request
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import threading
import time

# Flask アプリ設定
app = Flask(__name__)
load_dotenv()

# データベース接続設定
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "steam_analytics"),
    "user": os.getenv("POSTGRES_USER", "steam_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
}

engine = create_engine(
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

def load_game_data():
    """データベースからゲームデータを読み込み"""
    query = text("""
        SELECT 
            app_id, name, type, is_free, developers, publishers,
            price_final, genres, categories, positive_reviews,
            negative_reviews, total_reviews, platforms_windows,
            platforms_mac, platforms_linux, created_at
        FROM games
        WHERE type = 'game'
        ORDER BY created_at DESC
        LIMIT 1000;
    """)
    
    df = pd.read_sql_query(query, engine)
    
    # データ前処理
    df['price_usd'] = df['price_final'] / 100
    df.loc[df['is_free'] == True, 'price_usd'] = 0
    
    # インディーゲーム判定
    df['is_indie'] = df['genres'].apply(
        lambda x: bool(x and any('Indie' in str(genre) for genre in x if genre))
    )
    
    # その他の前処理
    df['platform_count'] = (
        df['platforms_windows'].astype(int) + 
        df['platforms_mac'].astype(int) + 
        df['platforms_linux'].astype(int)
    )
    
    df['primary_genre'] = df['genres'].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'Other'
    )
    
    def price_category(price):
        if price == 0:
            return 'Free'
        elif price < 5:
            return 'Budget ($0-5)'
        elif price < 15:
            return 'Mid-range ($5-15)'
        elif price < 30:
            return 'Premium ($15-30)'
        else:
            return 'AAA ($30+)'
    
    df['price_category'] = df['price_usd'].apply(price_category)
    
    return df

# グローバルデータ
game_data = None

def refresh_data():
    """データを更新"""
    global game_data
    try:
        game_data = load_game_data()
        print(f"✅ データ更新完了: {len(game_data):,}件")
    except Exception as e:
        print(f"❌ データ更新エラー: {e}")

# 初回データロード
refresh_data()

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 Steam インディーゲーム市場分析ダッシュボード</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: #333;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .controls {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .control-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .control-group label {
            font-weight: bold;
            color: #555;
        }
        
        .control-group input, .control-group select {
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #ff6b6b, #ff8e8e);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-card:nth-child(2) {
            background: linear-gradient(135deg, #4ecdc4, #7dd3c0);
        }
        
        .metric-card:nth-child(3) {
            background: linear-gradient(135deg, #45b7d1, #6cc4e6);
        }
        
        .metric-card:nth-child(4) {
            background: linear-gradient(135deg, #f9ca24, #f0932b);
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 20px;
            color: #333;
            text-align: center;
        }
        
        .insights {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-top: 30px;
        }
        
        .insights h2 {
            margin-bottom: 20px;
            text-align: center;
        }
        
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .insight-card {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .insight-card h3 {
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .update-info {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: transform 0.2s ease;
        }
        
        .btn:hover {
            transform: scale(1.05);
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            
            .controls {
                flex-direction: column;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Steam インディーゲーム市場分析</h1>
            <p>データ駆動型の市場洞察ダッシュボード</p>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label>
                    <input type="checkbox" id="indieOnly" checked> インディーゲームのみ表示
                </label>
            </div>
            
            <div class="control-group">
                <label for="maxPrice">最大価格 ($)</label>
                <input type="range" id="maxPrice" min="0" max="100" value="50" step="5">
                <span id="maxPriceValue">$50</span>
            </div>
            
            <div class="control-group">
                <button class="btn" onclick="refreshData()">🔄 データ更新</button>
            </div>
        </div>
        
        <div class="metrics-grid" id="metricsGrid">
            <!-- メトリクスはJavaScriptで動的に生成 -->
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">人気ジャンル TOP 10</div>
                <canvas id="genreChart"></canvas>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">価格帯分布</div>
                <canvas id="priceChart"></canvas>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">プラットフォーム対応率</div>
                <canvas id="platformChart"></canvas>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">月別リリース動向</div>
                <canvas id="trendChart"></canvas>
            </div>
        </div>
        
        <div class="insights">
            <h2>💡 市場洞察</h2>
            <div class="insights-grid" id="insightsGrid">
                <!-- 洞察はJavaScriptで動的に生成 -->
            </div>
        </div>
        
        <div class="update-info">
            <p>最終更新: <span id="lastUpdate"></span> | データソース: Steam Web API</p>
        </div>
    </div>
    
    <script>
        let gameData = null;
        let charts = {};
        
        // 初期化
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
            
            // イベントリスナー設定
            document.getElementById('indieOnly').addEventListener('change', updateDashboard);
            document.getElementById('maxPrice').addEventListener('input', function() {
                document.getElementById('maxPriceValue').textContent = '$' + this.value;
                updateDashboard();
            });
        });
        
        // データ読み込み
        async function loadData() {
            try {
                const response = await fetch('/api/data');
                gameData = await response.json();
                updateDashboard();
                updateTimestamp();
            } catch (error) {
                console.error('データ読み込みエラー:', error);
            }
        }
        
        // データ更新
        async function refreshData() {
            try {
                const response = await fetch('/api/refresh', { method: 'POST' });
                gameData = await response.json();
                updateDashboard();
                updateTimestamp();
                alert('データを更新しました！');
            } catch (error) {
                console.error('データ更新エラー:', error);
                alert('データ更新に失敗しました。');
            }
        }
        
        // ダッシュボード更新
        function updateDashboard() {
            if (!gameData) return;
            
            // フィルタリング
            const indieOnly = document.getElementById('indieOnly').checked;
            const maxPrice = parseFloat(document.getElementById('maxPrice').value);
            
            let filteredData = gameData.filter(game => {
                if (indieOnly && !game.is_indie) return false;
                if (game.price_usd > maxPrice) return false;
                return true;
            });
            
            updateMetrics(filteredData);
            updateCharts(filteredData);
            updateInsights(filteredData);
        }
        
        // メトリクス更新
        function updateMetrics(data) {
            const totalGames = data.length;
            const indieGames = data.filter(g => g.is_indie).length;
            const avgPrice = data.filter(g => g.price_usd > 0).reduce((sum, g) => sum + g.price_usd, 0) / data.filter(g => g.price_usd > 0).length || 0;
            const freeGames = data.filter(g => g.price_usd === 0).length;
            
            const metricsHtml = `
                <div class="metric-card">
                    <div class="metric-value">${totalGames.toLocaleString()}</div>
                    <div class="metric-label">総ゲーム数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${indieGames.toLocaleString()}</div>
                    <div class="metric-label">インディーゲーム (${(indieGames/totalGames*100).toFixed(1)}%)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">$${avgPrice.toFixed(2)}</div>
                    <div class="metric-label">平均価格</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${freeGames.toLocaleString()}</div>
                    <div class="metric-label">無料ゲーム</div>
                </div>
            `;
            
            document.getElementById('metricsGrid').innerHTML = metricsHtml;
        }
        
        // チャート更新
        function updateCharts(data) {
            updateGenreChart(data);
            updatePriceChart(data);
            updatePlatformChart(data);
            updateTrendChart(data);
        }
        
        // ジャンルチャート
        function updateGenreChart(data) {
            const genreCounts = {};
            data.forEach(game => {
                const genre = game.primary_genre || 'Other';
                genreCounts[genre] = (genreCounts[genre] || 0) + 1;
            });
            
            const sortedGenres = Object.entries(genreCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);
            
            const ctx = document.getElementById('genreChart').getContext('2d');
            
            if (charts.genre) charts.genre.destroy();
            
            charts.genre = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: sortedGenres.map(g => g[0]),
                    datasets: [{
                        data: sortedGenres.map(g => g[1]),
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // 価格チャート
        function updatePriceChart(data) {
            const priceCounts = {};
            data.forEach(game => {
                const category = game.price_category || 'Other';
                priceCounts[category] = (priceCounts[category] || 0) + 1;
            });
            
            const ctx = document.getElementById('priceChart').getContext('2d');
            
            if (charts.price) charts.price.destroy();
            
            charts.price = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(priceCounts),
                    datasets: [{
                        data: Object.values(priceCounts),
                        backgroundColor: [
                            '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#ff9ff3'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
        
        // プラットフォームチャート
        function updatePlatformChart(data) {
            const platformStats = {
                'Windows': data.filter(g => g.platforms_windows).length / data.length * 100,
                'Mac': data.filter(g => g.platforms_mac).length / data.length * 100,
                'Linux': data.filter(g => g.platforms_linux).length / data.length * 100
            };
            
            const ctx = document.getElementById('platformChart').getContext('2d');
            
            if (charts.platform) charts.platform.destroy();
            
            charts.platform = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Object.keys(platformStats),
                    datasets: [{
                        data: Object.values(platformStats),
                        backgroundColor: ['#0078d4', '#ff6b35', '#f7931e']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // トレンドチャート（ダミーデータ）
        function updateTrendChart(data) {
            const ctx = document.getElementById('trendChart').getContext('2d');
            
            if (charts.trend) charts.trend.destroy();
            
            // 簡易的な月別集計
            const months = ['1月', '2月', '3月', '4月', '5月', '6月'];
            const values = [45, 52, 38, 61, 47, 55]; // ダミーデータ
            
            charts.trend = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: months,
                    datasets: [{
                        label: 'リリース数',
                        data: values,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // 洞察更新
        function updateInsights(data) {
            const indieRatio = data.filter(g => g.is_indie).length / data.length * 100;
            const avgPrice = data.filter(g => g.price_usd > 0).reduce((sum, g) => sum + g.price_usd, 0) / data.filter(g => g.price_usd > 0).length || 0;
            
            const insightsHtml = `
                <div class="insight-card">
                    <h3>🎯 市場構造</h3>
                    <p>インディーゲームが市場の${indieRatio.toFixed(1)}%を占め、主要セグメントを形成。</p>
                </div>
                <div class="insight-card">
                    <h3>💰 価格戦略</h3>
                    <p>平均価格$${avgPrice.toFixed(2)}。低価格戦略が主流だが、品質による差別化も重要。</p>
                </div>
                <div class="insight-card">
                    <h3>🖥️ プラットフォーム</h3>
                    <p>Windows対応は必須。Mac/Linux対応により差別化可能。</p>
                </div>
                <div class="insight-card">
                    <h3>📈 成長機会</h3>
                    <p>ニッチジャンルでの専門化と、マルチプラットフォーム対応が鍵。</p>
                </div>
            `;
            
            document.getElementById('insightsGrid').innerHTML = insightsHtml;
        }
        
        // タイムスタンプ更新
        function updateTimestamp() {
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString('ja-JP');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """メインダッシュボードページ"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    """ゲームデータをJSON形式で返す"""
    if game_data is None:
        return jsonify([])
    
    # DataFrameをJSONに変換
    return jsonify(game_data.to_dict('records'))

@app.route('/api/refresh', methods=['POST'])
def refresh_data_api():
    """データを更新してJSON形式で返す"""
    refresh_data()
    
    if game_data is None:
        return jsonify([])
    
    return jsonify(game_data.to_dict('records'))

if __name__ == '__main__':
    print("🎮 Steam Analytics ダッシュボードサーバー起動中...")
    print("📊 アクセス URL: http://localhost:8501")
    print("🔄 Ctrl+C で停止")
    
    # デバッグモードで起動
    app.run(host='0.0.0.0', port=8501, debug=True)