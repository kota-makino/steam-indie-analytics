FROM mcr.microsoft.com/devcontainers/python:3.11

# システム更新と基本ツール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    vim \
    htop \
    tree \
    jq \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /workspace

# ユーザー切り替え
USER vscode

# 環境変数
ENV PYTHONPATH=/workspace/src
ENV NODE_ENV=development
