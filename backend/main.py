from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder

from backend.config import CORS_ORIGINS, RATE_LIMIT_LOGIN, CHAT_RATE_LIMIT_PER_MINUTE
from backend.database import engine, SessionLocal, Base
from backend.utils.logger import setup_logger, get_logger
from backend.utils.response import fail
from backend.exceptions.handlers import AppException, app_exception_handler, global_exception_handler
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.middleware.logging import RequestLoggingMiddleware
from backend.services.auth_service import init_admin

from backend.routers import auth, documents, search, files, chat, milvus, api_keys, health, admin, dashboard, profile, llm_config, chat_sessions

setup_logger()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")

    # Run Alembic migrations to bring existing databases up to date
    _run_migrations()

    # Create tables (handles brand-new databases)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # Create FTS5 virtual table and triggers
    _setup_fts5()

    # Initialize admin user
    db = SessionLocal()
    try:
        init_admin(db)
    finally:
        db.close()

    logger.info("Application started successfully.")
    yield

    # Shutdown
    logger.info("Application shutting down.")


def _run_migrations():
    """Run Alembic migrations to upgrade the database schema."""
    from alembic.config import Config
    from alembic import command

    project_root = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.warning("Migration check failed (may be first run): %s", e)


def _setup_fts5():
    """Create FTS5 virtual table and triggers if they don't exist."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # Create FTS5 virtual table
        db.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title,
                content_text,
                content='documents',
                content_rowid='id'
            )
        """))

        # Create triggers (ignore if already exist)
        triggers = [
            """
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, title, content_text)
                VALUES (new.id, new.title, new.content_text);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content_text)
                VALUES ('delete', old.id, old.title, old.content_text);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content_text)
                VALUES ('delete', old.id, old.title, old.content_text);
                INSERT INTO documents_fts(rowid, title, content_text)
                VALUES (new.id, new.title, new.content_text);
            END
            """,
        ]

        for trigger_sql in triggers:
            db.execute(text(trigger_sql))

        db.commit()
        logger.info("FTS5 virtual table and triggers verified.")
    except Exception as e:
        logger.error("Failed to setup FTS5: %s", e)
        db.rollback()
    finally:
        db.close()


app = FastAPI(
    title="Personal Research Manager",
    version="0.1.0",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 4000, "message": "Validation error", "data": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    # Normalize HTTPException detail to unified response format
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        content = {"code": exc.status_code * 10 + 1, "message": str(exc.detail), "data": None}
    return JSONResponse(status_code=exc.status_code, content=content)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    rules={
        "/api/v1/auth/login": (RATE_LIMIT_LOGIN, 60),
        "/api/v1/auth/refresh": (10, 60),
        "/api/v1/chat/messages/": (CHAT_RATE_LIMIT_PER_MINUTE, 60),
    },
)

# Request logging (outermost middleware after CORS)
app.add_middleware(RequestLoggingMiddleware)

# Routers (search before documents to avoid /search matching /{doc_id})
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(documents.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(milvus.router)
app.include_router(api_keys.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(profile.router)
app.include_router(llm_config.router)
app.include_router(chat_sessions.router)

# Serve Vue3 frontend (built static files)
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """SPA fallback: serve static files or index.html for client-side routing.
        Skips /api/ paths to preserve proper 404 responses."""
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"code": 4004, "message": "Not found", "data": None})
        file_path = (_FRONTEND_DIST / path).resolve()
        if not file_path.is_relative_to(_FRONTEND_DIST.resolve()):
            return JSONResponse(status_code=400, content={"code": 4000, "message": "Invalid path", "data": None})
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_FRONTEND_DIST / "index.html")
