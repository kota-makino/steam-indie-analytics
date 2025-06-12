FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# rootユーザーでシステムレベル設定
USER root

# システム更新と必要ツール
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Node.js 18 LTS インストール
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    node --version && \
    npm --version

# npm設定とClaude Code インストール
RUN npm config set prefix /usr/local && \
    npm install -g @anthropic-ai/claude-code && \
    npm list -g @anthropic-ai/claude-code

# vscodeユーザーに戻す
USER vscode
WORKDIR /workspace

# 環境変数とパス設定
ENV PATH="/usr/local/bin:$PATH"
ENV NODE_PATH="/usr/local/lib/node_modules"

# vscodeユーザーの.bashrcにエイリアス自動設定
RUN echo '# Claude Code エイリアス（自動設定）' >> ~/.bashrc && \
    echo 'alias claude-code="/usr/local/bin/claude"' >> ~/.bashrc && \
    echo 'alias claude="/usr/local/bin/claude"' >> ~/.bashrc && \
    echo '' >> ~/.bashrc && \
    echo '# 開発環境情報表示' >> ~/.bashrc && \
    echo 'echo "🚀 Dev Container Ready!"' >> ~/.bashrc && \
    echo 'echo "Claude Code: $(claude-code --version 2>/dev/null || echo \"Not available\")"' >> ~/.bashrc && \
    echo 'echo "Python: $(python --version)"' >> ~/.bashrc && \
    echo 'echo "Node.js: $(node --version)"' >> ~/.bashrc && \
    echo 'echo ""' >> ~/.bashrc
