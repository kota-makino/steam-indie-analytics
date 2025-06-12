#!/bin/bash

echo "🚀 Setting up Indie Game Success Predictor with persistent Claude Code..."

# 権限設定
chmod +x .devcontainer/post-create.sh

# NPM設定の永続化
if [ ! -f ~/.npmrc ]; then
    npm config set prefix ~/.npm-global
    echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
fi

# Claude Codeインストール確認・インストール
if [ ! -f ~/.npm-global/bin/claude-code ]; then
    echo "📦 Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code
else
    echo "✅ Claude Code already installed"
fi

# パス設定
export PATH=~/.npm-global/bin:$PATH

# Python依存関係インストール
if [ -f requirements.txt ]; then
    echo "📦 Installing Python packages..."
    pip install -r requirements.txt
fi

# プロジェクト構造作成
echo "📁 Creating project structure..."
mkdir -p {src/{data_collectors,processors,analyzers,models,visualizers},notebooks,docs,tests,infrastructure}

# サンプルファイル作成（初回のみ）
if [ ! -f src/data_collectors/steam_collector.py ]; then
    echo "📝 Creating sample files..."
    
    cat > src/data_collectors/__init__.py << 'PYEOF'
"""Steam data collection modules."""
PYEOF

    cat > src/data_collectors/steam_collector.py << 'PYEOF'
"""
Steam API Data Collector for Indie Games Analysis
"""

import requests
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class GameData:
    """Steam game data structure"""
    appid: int
    name: str
    price: float
    genres: List[str]
    developers: List[str]
    publishers: List[str]
    release_date: str
    recommendations: int
    
class SteamDataCollector:
    """Collects game data from Steam Store API"""
    
    def __init__(self):
        self.base_url = "https://store.steampowered.com/api"
        self.session = requests.Session()
        
    def get_game_details(self, app_id: int) -> Optional[GameData]:
        """Fetch game details by app ID"""
        try:
            url = f"{self.base_url}/appdetails"
            params = {"appids": app_id}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if str(app_id) in data and data[str(app_id)]["success"]:
                game_info = data[str(app_id)]["data"]
                
                return GameData(
                    appid=app_id,
                    name=game_info.get("name", ""),
                    price=game_info.get("price_overview", {}).get("final", 0) / 100,
                    genres=[g["description"] for g in game_info.get("genres", [])],
                    developers=game_info.get("developers", []),
                    publishers=game_info.get("publishers", []),
                    release_date=game_info.get("release_date", {}).get("date", ""),
                    recommendations=game_info.get("recommendations", {}).get("total", 0)
                )
        except Exception as e:
            print(f"Error fetching game {app_id}: {e}")
            return None
            
        time.sleep(1)  # Rate limiting
        return None

# 使用例
if __name__ == "__main__":
    collector = SteamDataCollector()
    
    # Hollow Knight (人気インディーゲーム)
    game = collector.get_game_details(367520)
    if game:
        print(f"Game: {game.name}")
        print(f"Price: ${game.price}")
        print(f"Genres: {', '.join(game.genres)}")
        print(f"Developer: {', '.join(game.developers)}")
PYEOF

fi

# Git設定確認
if [ ! -f ~/.gitconfig ]; then
    echo "⚙️  Please configure Git:"
    echo "git config --global user.name 'Your Name'"
    echo "git config --global user.email 'your.email@example.com'"
fi

echo "✅ Development environment setup completed!"
echo ""
echo "🎮 Claude Code and Steam API collector ready!"
echo "Try: claude-code 'Create a function to analyze indie game success factors'"
