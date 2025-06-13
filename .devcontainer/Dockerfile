FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# 基本的なシステムツールのみ
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# vscodeユーザーで基本的なPython依存関係
USER vscode
RUN pip install --user \
    streamlit \
    pandas \
    numpy \
    psycopg2-binary \
    redis \
    sqlalchemy \
    requests \
    beautifulsoup4