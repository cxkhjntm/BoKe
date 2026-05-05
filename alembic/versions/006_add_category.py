"""add document category

Revision ID: 006
Revises: 005
Create Date: 2026-05-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a SQLite table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    columns = [row[1] for row in result]
    return column in columns


def upgrade() -> None:
    # Only rebuild documents table if category column is missing
    if not _column_exists("documents", "category"):
        op.execute("""
            CREATE TABLE documents_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_type VARCHAR(20) NOT NULL,
                file_size INTEGER NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                thumbnail_path VARCHAR(500),
                content_text TEXT,
                status VARCHAR(20) DEFAULT 'queued',
                error_message TEXT,
                is_favorite BOOLEAN DEFAULT FALSE,
                category VARCHAR(20),
                view_count INTEGER DEFAULT 0,
                last_viewed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CHECK (file_type IN ('pdf','docx','md','png','jpg','jpeg')),
                CHECK (status IN ('queued','processing','ready','error')),
                CHECK (category IN ('sujian','shicui','manbi') OR category IS NULL)
            )
        """)

        op.execute("""
            INSERT INTO documents_new
                (id, user_id, title, original_filename, file_type, file_size,
                 file_path, thumbnail_path, content_text, status, error_message,
                 is_favorite, view_count, last_viewed_at, created_at, updated_at)
            SELECT
                id, user_id, title, original_filename, file_type, file_size,
                file_path, thumbnail_path, content_text, status, error_message,
                is_favorite, view_count, last_viewed_at, created_at, updated_at
            FROM documents
        """)

        # Drop old indexes
        op.execute("DROP INDEX IF EXISTS idx_documents_status")
        op.execute("DROP INDEX IF EXISTS idx_documents_user_id")
        op.execute("DROP INDEX IF EXISTS idx_documents_favorite")

        # Drop old table and rename new one
        op.execute("DROP TABLE documents")
        op.execute("ALTER TABLE documents_new RENAME TO documents")

        # Recreate indexes
        op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
        op.execute("CREATE INDEX idx_documents_status ON documents(status)")
        op.execute("CREATE INDEX idx_documents_favorite ON documents(user_id, is_favorite)")
    else:
        # Column already exists, just ensure indexes are correct
        pass

    # Create category index if not exists
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)")


def downgrade() -> None:
    # Drop category index
    op.execute("DROP INDEX IF EXISTS idx_documents_category")

    # Rebuild table without category column
    op.execute("""
        CREATE TABLE documents_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(20) NOT NULL,
            file_size INTEGER NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            thumbnail_path VARCHAR(500),
            content_text TEXT,
            status VARCHAR(20) DEFAULT 'queued',
            error_message TEXT,
            is_favorite BOOLEAN DEFAULT FALSE,
            view_count INTEGER DEFAULT 0,
            last_viewed_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CHECK (file_type IN ('pdf','docx','md','png','jpg','jpeg')),
            CHECK (status IN ('queued','processing','ready','error'))
        )
    """)

    op.execute("""
        INSERT INTO documents_old
            (id, user_id, title, original_filename, file_type, file_size,
             file_path, thumbnail_path, content_text, status, error_message,
             is_favorite, view_count, last_viewed_at, created_at, updated_at)
        SELECT
            id, user_id, title, original_filename, file_type, file_size,
            file_path, thumbnail_path, content_text, status, error_message,
            is_favorite, view_count, last_viewed_at, created_at, updated_at
        FROM documents
    """)

    # Drop old indexes
    op.execute("DROP INDEX IF EXISTS idx_documents_category")
    op.execute("DROP INDEX IF EXISTS idx_documents_favorite")
    op.execute("DROP INDEX IF EXISTS idx_documents_status")
    op.execute("DROP INDEX IF EXISTS idx_documents_user_id")

    # Drop old table and rename new one
    op.execute("DROP TABLE documents")
    op.execute("ALTER TABLE documents_old RENAME TO documents")

    # Recreate indexes
    op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
    op.execute("CREATE INDEX idx_documents_status ON documents(status)")
    op.execute("CREATE INDEX idx_documents_favorite ON documents(user_id, is_favorite)")
