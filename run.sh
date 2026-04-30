#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Cleanup Celery worker on exit
CELERY_PID=""
cleanup() {
    if [ -n "$CELERY_PID" ]; then
        info "Stopping Celery worker (PID: $CELERY_PID)..."
        kill "$CELERY_PID" 2>/dev/null || true
        wait "$CELERY_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

info "=== BoKe - Personal Research Portal ==="

# --- Python check ---
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found"
    exit 1
fi

PYTHON=python3
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_VER_FULL=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
info "Python version: $PY_VER_FULL"

# --- Virtual environment ---
# Markers used to detect venv corruption or version mismatch.
_VENV_OK=true

# 1) venv directory missing
if [ ! -d "venv" ]; then
    warn "Virtual environment not found."
    _VENV_OK=false
fi

# 2) activate script missing (partial/corrupt venv)
if $_VENV_OK && [ ! -f "venv/bin/activate" ]; then
    warn "venv/bin/activate missing — venv is corrupt."
    _VENV_OK=false
fi

# 3) Python version inside venv differs from system Python
if $_VENV_OK && [ -f "venv/pyvenv.cfg" ]; then
    _VENV_PY_VER=$(grep "^version" venv/pyvenv.cfg 2>/dev/null | cut -d' ' -f3 | cut -d. -f1,2)
    if [ -n "$_VENV_PY_VER" ] && [ "$_VENV_PY_VER" != "$PY_VER" ]; then
        warn "Python version mismatch: venv=$_VENV_PY_VER, system=$PY_VER"
        _VENV_OK=false
    fi
fi

# 4) pip broken inside venv
if $_VENV_OK && [ -x "venv/bin/pip" ]; then
    if ! venv/bin/pip --version &>/dev/null; then
        warn "pip inside venv is broken."
        _VENV_OK=false
    fi
elif $_VENV_OK && [ ! -x "venv/bin/pip" ]; then
    warn "pip not found inside venv."
    _VENV_OK=false
fi

# 5) critical dependency missing (fastapi import fails)
if $_VENV_OK && [ -x "venv/bin/python" ]; then
    if ! venv/bin/python -c "import fastapi" &>/dev/null; then
        warn "Critical dependency 'fastapi' not importable in venv."
        _VENV_OK=false
    fi
fi

# Rebuild if any check failed
if ! $_VENV_OK; then
    info "Rebuilding virtual environment..."
    rm -rf venv
    $PYTHON -m venv venv
    info "Virtual environment recreated."
fi

# Activate — if this fails, the venv is unusable
if ! source venv/bin/activate 2>/dev/null; then
    error "Failed to activate virtual environment. Recreating..."
    rm -rf venv
    $PYTHON -m venv venv
    source venv/bin/activate
fi

# --- Install dependencies ---
info "Installing Python dependencies..."
if ! pip install -q -r requirements.txt; then
    error "Failed to install dependencies. Check requirements.txt and network connectivity."
    exit 1
fi

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

# Security: warn if .env is world-readable
if [ "$(uname)" != "Darwin" ] || command -v stat &>/dev/null; then
    _ENV_PERMS=$(stat -c '%a' .env 2>/dev/null || stat -f '%Lp' .env 2>/dev/null || echo "")
    if [ -n "$_ENV_PERMS" ]; then
        # Check if group or other have any permissions (mask 077)
        _ENV_OTHER=${_ENV_PERMS: -2}
        if [ "$_ENV_OTHER" != "00" ]; then
            warn ".env file permissions are $_ENV_PERMS (recommended: 600)"
            warn "Fix with: chmod 600 .env"
        fi
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

# --- Redis / Celery ---
CELERY_ENABLED=false
if command -v redis-cli &>/dev/null; then
    if redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping 2>/dev/null | grep -q PONG; then
        info "Redis is available at ${REDIS_URL:-redis://localhost:6379/0}"
        CELERY_ENABLED=true
    else
        warn "Redis is not running. Document processing will use synchronous mode."
        warn "To enable async processing: start Redis server"
    fi
else
    warn "redis-cli not found. Install Redis for async document processing."
fi

if [ "$CELERY_ENABLED" = "true" ]; then
    info "Starting Celery worker in background..."
    venv/bin/celery -A backend.celery_app worker \
        --loglevel="${LOG_LEVEL:-info}" \
        --concurrency=1 \
        --pidfile=data/celery.pid \
        --logfile=data/celery.log &
    CELERY_PID=$!
    info "Celery worker started (PID: $CELERY_PID)"
fi

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
    uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
else
    uvicorn backend.main:app --host "$HOST" --port "$PORT"
fi
