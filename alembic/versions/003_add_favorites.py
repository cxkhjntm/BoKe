"""add favorites and dashboard columns

Revision ID: 003
Revises: 002
Create Date: 2026-04-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite table rebuild: add is_favorite, view_count, last_viewed_at
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
            view_count INTEGER DEFAULT 0,
            last_viewed_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CHECK (file_type IN ('pdf','docx','md','png','jpg','jpeg')),
            CHECK (status IN ('queued','processing','ready','error'))
        )
    """)

    op.execute("""
        INSERT INTO documents_new
            (id, user_id, title, original_filename, file_type, file_size,
             file_path, thumbnail_path, content_text, status, error_message,
             created_at, updated_at)
        SELECT
            id, user_id, title, original_filename, file_type, file_size,
            file_path, thumbnail_path, content_text, status, error_message,
            created_at, updated_at
        FROM documents
    """)

    op.execute("DROP INDEX IF EXISTS idx_documents_status")
    op.execute("DROP INDEX IF EXISTS idx_documents_user_id")
    op.execute("DROP TABLE documents")
    op.execute("ALTER TABLE documents_new RENAME TO documents")

    op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
    op.execute("CREATE INDEX idx_documents_status ON documents(status)")
    op.execute("CREATE INDEX idx_documents_favorite ON documents(user_id, is_favorite)")

    # Activity log table
    op.execute("""
        CREATE TABLE activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
            action VARCHAR(20) NOT NULL,
            metadata_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX idx_activity_user_id ON activity_log(user_id)")
    op.execute("CREATE INDEX idx_activity_created_at ON activity_log(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activity_log")

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
             created_at, updated_at)
        SELECT
            id, user_id, title, original_filename, file_type, file_size,
            file_path, thumbnail_path, content_text, status, error_message,
            created_at, updated_at
        FROM documents
    """)

    op.execute("DROP INDEX IF EXISTS idx_documents_favorite")
    op.execute("DROP INDEX IF EXISTS idx_documents_status")
    op.execute("DROP INDEX IF EXISTS idx_documents_user_id")
    op.execute("DROP TABLE documents")
    op.execute("ALTER TABLE documents_old RENAME TO documents")
    op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
    op.execute("CREATE INDEX idx_documents_status ON documents(status)")
