FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    curl \
    git \
    postgresql-client \
    redis-tools \
    python3-pip \
    python3-venv \
    ffmpeg \
    portaudio19-dev \
    libsndfile1 \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash

USER vscode
