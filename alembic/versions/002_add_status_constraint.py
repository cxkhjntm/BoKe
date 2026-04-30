"""add status check constraint and queued state

Revision ID: 002
Revises: 001
Create Date: 2026-04-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER TABLE ADD CONSTRAINT.
    # Use table rebuild strategy: create new table, copy data, drop old, rename.

    # 1. Create new table with CHECK constraint
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
            status VARCHAR(20) DEFAULT 'processing',
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CHECK (file_type IN ('pdf','docx','md','png','jpg','jpeg')),
            CHECK (status IN ('queued','processing','ready','error'))
        )
    """)

    # 2. Copy data from old table
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

    # 3. Drop old table and indexes
    op.execute("DROP INDEX IF EXISTS idx_documents_status")
    op.execute("DROP INDEX IF EXISTS idx_documents_user_id")
    op.execute("DROP TABLE documents")

    # 4. Rename new table
    op.execute("ALTER TABLE documents_new RENAME TO documents")

    # 5. Recreate indexes
    op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
    op.execute("CREATE INDEX idx_documents_status ON documents(status)")


def downgrade() -> None:
    # Remove the CHECK constraint by rebuilding without it
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
            status VARCHAR(20) DEFAULT 'processing',
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CHECK (file_type IN ('pdf','docx','md','png','jpg','jpeg'))
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

    op.execute("DROP INDEX IF EXISTS idx_documents_status")
    op.execute("DROP INDEX IF EXISTS idx_documents_user_id")
    op.execute("DROP TABLE documents")
    op.execute("ALTER TABLE documents_old RENAME TO documents")
    op.execute("CREATE INDEX idx_documents_user_id ON documents(user_id)")
    op.execute("CREATE INDEX idx_documents_status ON documents(status)")
