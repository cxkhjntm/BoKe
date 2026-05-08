"""Shared test fixtures for BoKe backend tests."""

import os

# Set required env vars BEFORE any backend imports (config.py reads them at import time)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-chars-long!!")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")
os.environ.setdefault("STORAGE_PATH", "./test_storage")

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.main import app
from backend.database import get_db
from backend.services.auth_service import init_admin
from backend.utils.security import create_access_token


# --- Database cleanup ---

@pytest.fixture(scope="session", autouse=True)
def _clean_test_db():
    """Remove leftover test database files before the test session starts."""
    db_path = Path("data/test.db")
    for suffix in ("", "-shm", "-wal"):
        p = db_path.parent / (db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()


# --- Database fixtures ---

@pytest.fixture(scope="session")
def tmp_storage(tmp_path_factory):
    """Session-scoped temporary storage directory."""
    return tmp_path_factory.mktemp("storage")


@pytest.fixture(scope="function")
def db_engine(tmp_path):
    """Create a fresh in-memory SQLite database per test."""
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode and foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a transactional database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session, tmp_storage):
    """FastAPI TestClient with overridden DB and storage."""
    from backend import config
    config.STORAGE_PATH = tmp_storage

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    _clear_rate_limits()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _clear_rate_limits():
    """Walk the ASGI middleware stack and clear any RateLimitMiddleware windows."""
    stack = app.middleware_stack
    seen = set()
    while stack is not None and id(stack) not in seen:
        seen.add(id(stack))
        if hasattr(stack, "_windows"):
            stack._windows.clear()
        stack = getattr(stack, "app", None)


@pytest.fixture
def admin_user(db_session):
    """Create and return an admin user."""
    from backend.models.user import User
    from backend.utils.security import hash_password

    user = User(
        username="testadmin",
        password_hash=hash_password("testpass123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(admin_user):
    """Authorization headers with a valid access token for the admin user."""
    token, _ = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal valid PDF file."""
    import fitz

    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Hello, test!")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_docx(tmp_path):
    """Create a minimal valid DOCX file."""
    from docx import Document

    docx_path = tmp_path / "test.docx"
    doc = Document()
    doc.add_paragraph("Hello, test!")
    doc.save(str(docx_path))
    return docx_path


@pytest.fixture
def sample_markdown(tmp_path):
    """Create a minimal Markdown file."""
    md_path = tmp_path / "test.md"
    md_path.write_text("# Hello\n\nThis is a test.", encoding="utf-8")
    return md_path


@pytest.fixture
def sample_image(tmp_path):
    """Create a minimal valid PNG image."""
    from PIL import Image

    img_path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(str(img_path))
    return img_path
