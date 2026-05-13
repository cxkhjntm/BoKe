# BoKe — Personal Research Portal

中文版本请查看 [README_CN.md](./README_CN.md)

A self-hosted research material management system. Upload documents, search across your entire library, and interact with your knowledge base through an LLM-powered chat interface. Runs on a single machine with minimal setup.

## Highlights

- Document upload with automatic text extraction (PDF, DOCX, Markdown, images)
- SQLite FTS5 full-text search across all documents
- RAG pipeline with ChromaDB vector storage for context-aware chat
- Dual authentication: JWT sessions and long-lived API keys
- Async file processing via Celery with graceful degradation when Redis is unavailable
- OpenAI-compatible LLM integration (bring your own API key)
- Responsive Vue 3 SPA with a clean, distraction-free interface

## Architecture

```
┌──────────────────────────────────────────────────┐
│                    Nginx (80)                     │
│   ┌───────────┐  ┌───────────┐  ┌─────────────┐ │
│   │  Static    │  │  /api/*   │  │  /storage/* │ │
│   │  (Vue 3)   │  │  proxy →  │  │  proxy →    │ │
│   └───────────┘  └─────┬─────┘  └──────┬──────┘ │
│                         │               │        │
└─────────────────────────┼───────────────┼────────┘
                          │               │
                 ┌────────▼───────────────▼────────┐
                 │      FastAPI Backend (:8000)     │
                 │                                  │
                 │  ┌─────────┐    ┌─────────────┐ │
                 │  │  JWT +   │    │   Document  │ │
                 │  │  API Key │    │   CRUD      │ │
                 │  └─────────┘    └─────────────┘ │
                 │  ┌─────────┐    ┌─────────────┐ │
                 │  │  FTS5    │    │  File Proc  │ │
                 │  │  Search  │    │  Pipeline   │ │
                 │  └─────────┘    └─────────────┘ │
                 │  ┌─────────┐    ┌─────────────┐ │
                 │  │  RAG +   │    │  Celery     │ │
                 │  │  LLM     │    │  Tasks      │ │
                 │  └─────────┘    └─────────────┘ │
                 └────────────────┬─────────────────┘
                                 │
                 ┌───────────────▼─────────────────┐
                 │   SQLite (WAL) + Alembic         │
                 │   ChromaDB (vectors)             │
                 │   Redis (optional task queue)    │
                 └──────────────────────────────────┘
```

## Tech Stack

| Layer            | Technology                                          |
| ---------------- | --------------------------------------------------- |
| Frontend         | Vue 3, Vite, Pinia, Vue Router                      |
| Backend          | Python 3.11+, FastAPI, SQLAlchemy, Pydantic         |
| Database         | SQLite with WAL mode                                |
| Migrations       | Alembic                                             |
| Auth             | JWT (HS256) + API Key (SHA256)                      |
| File Processing  | PyMuPDF (PDF), python-docx (DOCX), Pillow (images)  |
| Task Queue       | Celery + Redis (optional)                           |
| Search           | SQLite FTS5                                         |
| RAG              | ChromaDB + langchain-text-splitters                 |
| LLM Integration  | OpenAI-compatible API                               |

## Environment Requirements

| Requirement | Version | Required | Notes |
|-------------|---------|----------|-------|
| Python | 3.11+ | Yes | Backend runtime |
| Node.js | 18+ | Yes | Frontend build |
| Redis | 6.0+ | No | Optional, for async task queue (Celery) |
| Nginx | 1.18+ | No | Recommended for production deployment |
| SQLite | 3.35+ | Yes | Bundled with Python, WAL mode support required |

**System Dependencies (Linux):**
- `build-essential` (Ubuntu) or `gcc gcc-c++ make` (CentOS)
- `libmagic-dev` (Ubuntu) or `file-devel` (CentOS) for file type detection
- `curl`, `wget`, `git` for installation

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Redis, if you want async task processing

### Install

```bash
git clone https://github.com/cxkhjntm/BoKe.git
cd BoKe

# Create environment file
cp .env.example .env

# Generate a secret key and set your admin password
# Edit .env:
#   JWT_SECRET_KEY=<openssl rand -hex 32>
#   ADMIN_PASSWORD=<your-password>
```

### Run

```bash
bash run.sh
```

This script creates a Python virtual environment, installs all dependencies, runs database migrations, builds the frontend, and starts the server.

### Access

| Service      | URL                             |
| ------------ | ------------------------------- |
| Web UI       | http://localhost:8000           |
| API Docs     | http://localhost:8000/docs      |
| Health Check | http://localhost:8000/api/v1/health |

## Environment Variables

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `JWT_SECRET_KEY` | Yes | *none* | Signing key for JWT tokens. Minimum 32 characters. |
| `ADMIN_PASSWORD` | Yes | *none* | Password for the initial admin account. |
| `ADMIN_USERNAME` | No | `admin` | Username for the initial admin account. |
| `DATABASE_URL` | No | `sqlite:///./data/app.db` | SQLAlchemy database connection string. |
| `STORAGE_PATH` | No | `./storage` | Root directory for uploaded files. |
| `MAX_UPLOAD_SIZE_MB` | No | `50` | Maximum document upload size in MB. |
| `ALLOWED_EXTENSIONS` | No | `pdf,docx,md,png,jpg,jpeg` | Comma-separated list of allowed document extensions. |
| `IMAGE_MAX_UPLOAD_SIZE_MB` | No | `2` | Maximum image upload size in MB. |
| `IMAGE_ALLOWED_EXTENSIONS` | No | `png,jpg,jpeg,webp,gif` | Comma-separated list of allowed image extensions. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed CORS origins (comma-separated for multiple). |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL for Celery task queue. |
| `RATE_LIMIT_LOGIN` | No | `5` | Max login attempts per minute per IP. |
| `LOG_LEVEL` | No | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR). |
| `REGISTRATION_ENABLED` | No | `false` | Whether to allow new user registration. |
| `CHAT_MAX_TIMEOUT` | No | `120` | Max seconds to wait for an LLM response. |
| `CHAT_MAX_MESSAGE_LENGTH` | No | `8000` | Max character length for a single chat message. |
| `CHAT_RATE_LIMIT_PER_MINUTE` | No | `20` | Max chat requests per minute per user. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | JWT refresh token lifetime in days. |

## API Reference

All endpoints are prefixed with `/api/v1`. Authentication uses either a JWT Bearer token or an API key (`sk-xxx`) in the `Authorization` header.

### Auth

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/v1/auth/login` | Login with username/password. Returns access and refresh tokens. |
| POST | `/api/v1/auth/refresh` | Exchange a refresh token for a new access token. |
| POST | `/api/v1/auth/logout` | Revoke the current refresh token. |

### Documents

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/v1/documents` | Upload a document (multipart/form-data). |
| GET | `/api/v1/documents` | List all documents with pagination. |
| GET | `/api/v1/documents/{id}` | Get a single document by ID. |
| PATCH | `/api/v1/documents/{id}` | Update a document's title. |
| DELETE | `/api/v1/documents/{id}` | Delete a document and its files. |
| POST | `/api/v1/documents/{id}/retry` | Retry processing for a failed document. |
| GET | `/api/v1/documents/search?q=` | Full-text search across document content. |

### Files

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/v1/files/{id}/original` | Download the original uploaded file. |
| GET | `/api/v1/files/{id}/thumbnail` | Get the document thumbnail image. |

### API Keys

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/v1/api-keys` | List all API keys for the current user. |
| POST | `/api/v1/api-keys` | Create a new API key. Returns the key once. |
| DELETE | `/api/v1/api-keys/{id}` | Delete an API key. |

### Admin

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/v1/health` | Health check. Returns service status. |

### Dashboard

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/v1/dashboard/stats` | Aggregate statistics (document count, storage used, etc.). |
| GET | `/api/v1/dashboard/recent` | Most recently uploaded documents. |
| GET | `/api/v1/dashboard/top` | Most viewed or accessed documents. |

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment variable loading
│   ├── database.py          # SQLAlchemy engine and session
│   ├── celery_app.py        # Celery task queue configuration
│   ├── tasks.py             # Async task definitions
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # API endpoint definitions
│   ├── services/            # Business logic layer
│   ├── middleware/           # Auth, rate limiting, logging
│   ├── utils/               # JWT helpers, logging, response formatting
│   └── exceptions/          # Custom error classes and handlers
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios HTTP client and interceptors
│   │   ├── stores/          # Pinia state management
│   │   ├── router/          # Vue Router configuration
│   │   ├── views/           # Page-level components
│   │   └── components/      # Reusable UI components
│   └── vite.config.js
├── alembic/                 # Database migration scripts
├── tests/                   # Test suite
├── docs/                    # Additional documentation
├── nginx.conf               # Production Nginx configuration
├── requirements.txt         # Python dependencies
└── run.sh                   # One-click start script
```

## Deployment

### Development

Run the backend and frontend separately for hot-reload during development.

```bash
# Terminal 1: Backend with auto-reload
bash run.sh

# Terminal 2: Frontend dev server (hot reload on port 5173)
cd frontend && npm run dev
```

### Production Deployment

For production deployment, we recommend following the detailed deployment guide:

📖 **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete step-by-step deployment manual

The deployment guide covers:
- Server environment preparation (Ubuntu/CentOS/Debian)
- Python 3.11+ installation from source
- Node.js 18+ installation
- Redis installation and configuration
- Nginx reverse proxy setup
- Systemd service management
- Firewall configuration
- SSL/HTTPS setup (optional)

**Quick Production Setup:**

```bash
# Build everything and start the backend
bash run.sh

# Set up Nginx
sudo cp nginx.conf /etc/nginx/sites-available/boke
sudo ln -s /etc/nginx/sites-available/boke /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

The Nginx config serves the Vue 3 static build, proxies `/api/*` requests to the FastAPI backend on port 8000, and serves uploaded files from `/storage/*`.

## Updates

### One-Click Update

The project includes an update script for quick updates:

```bash
cd ~/BoKe
chmod +x update.sh
bash update.sh
```

The script automatically handles:
- Stopping services
- Database backup
- Pulling latest code
- Updating Python dependencies
- Running database migrations
- Building frontend
- Restarting services
- Health check verification

### Manual Update

If the update script fails or you need more control, see:

📖 **[UPDATE.md](./UPDATE.md)** - Detailed manual update guide

The update guide covers:
- Pre-update preparation and backup
- Step-by-step manual update process
- Version-specific migration notes
- Post-update verification
- Rollback procedures
- Troubleshooting common issues

## Development Guide

### Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run the full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=term-missing
```

### Database Migrations

Alembic manages schema migrations. After changing models in `backend/models/`, generate and apply a migration:

```bash
# Generate a new migration
alembic revision --autogenerate -m "describe your change"

# Apply pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

### Adding a New API Endpoint

1. Define the Pydantic schema in `backend/schemas/`
2. Add the ORM model (if needed) in `backend/models/`
3. Write the business logic in `backend/services/`
4. Create the route in `backend/routers/`
5. Register the router in `backend/main.py`

## License

MIT
