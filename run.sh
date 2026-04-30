#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

info "=== BoKe - Personal Research Portal ==="

# --- Python check ---
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found"
    exit 1
fi

PYTHON=python3
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PY_VER"

# --- Virtual environment ---
if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    $PYTHON -m venv venv
fi
source venv/bin/activate

# --- Install dependencies ---
info "Installing Python dependencies..."
pip install -q -r requirements.txt

# --- Environment variables ---
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn ".env created from .env.example — edit it before running!"
        echo ""
        echo "  Required variables:"
        echo "    JWT_SECRET_KEY  (>= 32 chars, generate: openssl rand -hex 32)"
        echo "    ADMIN_PASSWORD  (your admin password)"
        echo ""
        exit 1
    else
        error ".env file not found and no .env.example"
        exit 1
    fi
fi

set -a
source .env
set +a

# --- Validate required vars ---
if [ -z "${JWT_SECRET_KEY:-}" ] || [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    error "JWT_SECRET_KEY must be set and >= 32 characters"
    echo "  Generate with: openssl rand -hex 32"
    exit 1
fi

if [ -z "${ADMIN_PASSWORD:-}" ]; then
    error "ADMIN_PASSWORD must be set"
    exit 1
fi

# --- Create directories ---
mkdir -p data storage

# --- Database migrations ---
info "Running database migrations..."
alembic upgrade head 2>/dev/null || warn "Alembic migrations skipped (not configured)"

# --- Frontend ---
BUILD_FRONTEND="${BUILD_FRONTEND:-true}"
if [ "$BUILD_FRONTEND" = "true" ] && [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    if ! command -v node &>/dev/null; then
        warn "Node.js not found — skipping frontend build"
        warn "Install Node.js 18+ to build the frontend"
    else
        info "Building frontend..."
        cd frontend
        npm install --silent 2>/dev/null
        npm run build
        cd "$SCRIPT_DIR"
        info "Frontend built to frontend/dist/"
    fi
fi

# --- Start server ---
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"

echo ""
info "Starting BoKe on http://${HOST}:${PORT}"
info "API docs: http://${HOST}:${PORT}/docs"
echo ""

if [ "$RELOAD" = "true" ]; then
    exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
else
    exec uvicorn backend.main:app --host "$HOST" --port "$PORT"
fi
