# BoKe — Personal Research Portal

A lightweight, secure personal knowledge management system for researchers.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Nginx (80)                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│   │  Static   │  │  /api/*  │  │  /storage/*  │  │
│   │  (Vue3)   │  │  proxy → │  │  proxy →     │  │
│   └──────────┘  └────┬─────┘  └──────┬───────┘  │
│                       │               │          │
└───────────────────────┼───────────────┼──────────┘
                        │               │
               ┌────────▼───────────────▼────────┐
               │      FastAPI Backend (8000)      │
               │  ┌──────────┐  ┌──────────────┐ │
               │  │   JWT    │  │  API Key     │ │
               │  │   Auth   │  │  Auth        │ │
               │  └──────────┘  └──────────────┘ │
               │  ┌──────────┐  ┌──────────────┐ │
               │  │ Document │  │  Processing  │ │
               │  │  CRUD    │  │  Pipeline    │ │
               │  └──────────┘  └──────────────┘ │
               │  ┌──────────┐  ┌──────────────┐ │
               │  │  FTS5    │  │   File       │ │
               │  │  Search  │  │   Storage    │ │
               │  └──────────┘  └──────────────┘ │
               └───────────────┬─────────────────┘
                               │
               ┌───────────────▼─────────────────┐
               │       SQLite + Alembic           │
               │  (WAL mode, foreign keys ON)     │
               └──────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend build)

### 1. Clone and configure

```bash
git clone https://github.com/cxkhjntm/claude_code.git
cd claude_code

# Create .env from template
cp .env.example .env

# Edit .env — set at minimum:
#   JWT_SECRET_KEY=<openssl rand -hex 32>
#   ADMIN_PASSWORD=<your-password>
```

### 2. One-click start

```bash
bash run.sh
```

This will:
- Create Python virtual environment
- Install all dependencies
- Run database migrations
- Build the Vue3 frontend
- Start the FastAPI server

### 3. Access

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login (returns JWT) |
| POST | `/api/v1/auth/refresh` | Refresh tokens |
| POST | `/api/v1/auth/logout` | Revoke refresh token |

Supports both JWT Bearer tokens and API Keys (`sk-xxx`).

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents` | Upload document |
| GET | `/api/v1/documents` | List documents |
| GET | `/api/v1/documents/{id}` | Get document |
| PATCH | `/api/v1/documents/{id}` | Update title |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/documents/{id}/retry` | Retry failed processing |
| GET | `/api/v1/documents/search?q=` | Full-text search |

### Files (authenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/files/{id}/original` | Download original file |
| GET | `/api/v1/files/{id}/thumbnail` | Get thumbnail |

### API Keys

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/api-keys` | List keys |
| POST | `/api/v1/api-keys` | Create key |
| DELETE | `/api/v1/api-keys/{id}` | Delete key |

### Reserved (not yet implemented)

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/api/v1/chat/` | `{"code": 5010, "message": "LLM integration is not available yet."}` |
| GET | `/api/v1/milvus/status` | `{"code": 0, "data": {"status": "not_configured"}}` |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Vite, Pinia, Vue Router |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite (WAL mode) |
| Migrations | Alembic |
| Auth | JWT (HS256) + API Key (SHA256) |
| File Processing | PyMuPDF (PDF), python-docx (DOCX), Pillow (images) |
| Search | SQLite FTS5 |

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Environment config
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   ├── middleware/           # Auth, rate limiting
│   ├── utils/               # JWT, logging, response helpers
│   └── exceptions/          # Error handling
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios HTTP client
│   │   ├── stores/          # Pinia state
│   │   ├── router/          # Vue Router
│   │   ├── views/           # Page components
│   │   └── components/      # Shared components
│   └── vite.config.js
├── alembic/                 # DB migrations
├── docs/DEVELOPMENT.md      # Technical spec
├── nginx.conf               # Production config
├── requirements.txt
└── run.sh                   # One-click start
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes | — | JWT signing key (>= 32 chars) |
| `ADMIN_PASSWORD` | Yes | — | Initial admin password |
| `DATABASE_URL` | No | `sqlite:///./data/app.db` | Database URL |
| `ADMIN_USERNAME` | No | `admin` | Admin username |
| `STORAGE_PATH` | No | `./storage` | File storage root |
| `MAX_UPLOAD_SIZE_MB` | No | `50` | Max upload size (MB) |
| `LOG_LEVEL` | No | `INFO` | Log level |
| `CORS_ORIGINS` | No | `http://localhost:5173` | CORS origins |
| `RATE_LIMIT_LOGIN` | No | `5` | Login rate limit/min/IP |

## Deployment

### Development

```bash
# Terminal 1: Backend
bash run.sh

# Terminal 2: Frontend (hot reload)
cd frontend && npm run dev
```

### Production (with Nginx)

```bash
# Build and start
bash run.sh

# Configure Nginx
sudo cp nginx.conf /etc/nginx/sites-available/boke
sudo ln -s /etc/nginx/sites-available/boke /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## License

MIT
