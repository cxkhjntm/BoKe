#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Personal Research Manager ==="

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Copying from .env.example..."
    echo "Please edit .env and set JWT_SECRET_KEY and ADMIN_PASSWORD."
    cp .env.example .env
    exit 1
fi

# Source .env
set -a
source .env
set +a

# Validate required variables
if [ -z "${JWT_SECRET_KEY:-}" ] || [ "$JWT_SECRET_KEY" = "change-me-to-a-random-64-char-hex-string-at-least-32-chars" ]; then
    echo "ERROR: JWT_SECRET_KEY must be set to a secure value."
    echo "Generate one with: openssl rand -hex 32"
    exit 1
fi

if [ -z "${ADMIN_PASSWORD:-}" ] || [ "$ADMIN_PASSWORD" = "change-me-to-a-strong-password" ]; then
    echo "ERROR: ADMIN_PASSWORD must be set to a secure value."
    exit 1
fi

# Create directories
mkdir -p data storage

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head 2>/dev/null || {
    echo "Alembic not configured yet, using direct table creation..."
}

# Start server
echo ""
echo "Starting server on http://0.0.0.0:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
