import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        print(f"FATAL: environment variable {key} is required but not set.", file=sys.stderr)
        sys.exit(1)
    return val


def _get_int_env(key: str, default: int, min_val: int = 0, max_val: int | None = None) -> int:
    raw = _get_env(key, str(default))
    try:
        val = int(raw)
    except ValueError:
        print(f"FATAL: {key} must be an integer, got '{raw}'.", file=sys.stderr)
        sys.exit(1)
    if val < min_val:
        print(f"FATAL: {key} must be >= {min_val}, got {val}.", file=sys.stderr)
        sys.exit(1)
    if max_val is not None and val > max_val:
        print(f"FATAL: {key} must be <= {max_val}, got {val}.", file=sys.stderr)
        sys.exit(1)
    return val


# --- Database ---
DATABASE_URL = _get_env("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# --- JWT ---
JWT_SECRET_KEY = _get_env("JWT_SECRET_KEY", required=True)
JWT_ALGORITHM = _get_env("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 30, min_val=1)
REFRESH_TOKEN_EXPIRE_DAYS = _get_int_env("REFRESH_TOKEN_EXPIRE_DAYS", 7, min_val=1)

# Validate JWT secret key length
if len(JWT_SECRET_KEY) < 32:
    print("FATAL: JWT_SECRET_KEY must be at least 32 characters.", file=sys.stderr)
    sys.exit(1)

# --- Admin ---
ADMIN_USERNAME = _get_env("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _get_env("ADMIN_PASSWORD", required=True)

# --- Storage ---
STORAGE_PATH = Path(_get_env("STORAGE_PATH", str(BASE_DIR / "storage")))
STORAGE_PATH.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE_MB = _get_int_env("MAX_UPLOAD_SIZE_MB", 50, min_val=1)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = set(_get_env("ALLOWED_EXTENSIONS", "pdf,docx,md,png,jpg,jpeg").split(","))

# --- Image Upload (Profile) ---
IMAGE_MAX_UPLOAD_SIZE_MB = _get_int_env("IMAGE_MAX_UPLOAD_SIZE_MB", 2, min_val=1)
IMAGE_MAX_UPLOAD_SIZE_BYTES = IMAGE_MAX_UPLOAD_SIZE_MB * 1024 * 1024
IMAGE_ALLOWED_EXTENSIONS = set(_get_env("IMAGE_ALLOWED_EXTENSIONS", "png,jpg,jpeg,webp,gif").split(","))

# --- Logging ---
LOG_LEVEL = _get_env("LOG_LEVEL", "INFO").upper()

# --- CORS ---
CORS_ORIGINS = _get_env("CORS_ORIGINS", "http://localhost:5173").split(",")

# --- Celery / Redis ---
REDIS_URL = _get_env("REDIS_URL", "redis://localhost:6379/0")

# --- Rate Limiting ---
RATE_LIMIT_LOGIN = _get_int_env("RATE_LIMIT_LOGIN", 5, min_val=1)

# --- Chat ---
CHAT_MAX_TIMEOUT = _get_int_env("CHAT_MAX_TIMEOUT", 120, min_val=1)
CHAT_MAX_MESSAGE_LENGTH = _get_int_env("CHAT_MAX_MESSAGE_LENGTH", 8000, min_val=1)
CHAT_RATE_LIMIT_PER_MINUTE = _get_int_env("CHAT_RATE_LIMIT_PER_MINUTE", 20, min_val=1)

# --- LLM Provider Defaults ---
LLM_PROVIDER_DEFAULTS = {
    "siliconflow": "https://api.siliconflow.cn/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

# --- Registration ---
REGISTRATION_ENABLED = _get_env("REGISTRATION_ENABLED", "false").lower() == "true"
