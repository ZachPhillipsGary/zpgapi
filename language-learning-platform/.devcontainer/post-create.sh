#!/bin/bash
set -e

echo "🚀 Setting up Language Learning Platform development environment..."

# Install uv for Python package management
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Install Bun
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"

# Install Python dependencies for all services
echo "📦 Installing Python dependencies..."
cd /workspace/services/django-backend && uv pip install -r requirements.txt
cd /workspace/services/pipecat-service && uv pip install -r requirements.txt
cd /workspace/services/ai-worker && uv pip install -r requirements.txt

# Install Bun dependencies
echo "📦 Installing Bun dependencies..."
cd /workspace/services/bun-api && bun install
cd /workspace/apps/web && bun install
cd /workspace/packages/shared-types && bun install

# Set up pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
cd /workspace
pip install pre-commit
pre-commit install

echo "✅ Development environment ready!"
