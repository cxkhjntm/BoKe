"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("is_admin", sa.Boolean, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("login_failures", sa.Integer, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("thumbnail_path", sa.String(500), nullable=True),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="processing"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_documents_user_id", "documents", ["user_id"])
    op.create_index("idx_documents_status", "documents", ["status"])

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])

    # Refresh Tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("jti", sa.String(36), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_jti", "refresh_tokens", ["jti"])

    # FTS5 virtual table and triggers
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            title,
            content_text,
            content='documents',
            content_rowid='id'
        )
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, title, content_text)
            VALUES (new.id, new.title, new.content_text);
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, title, content_text)
            VALUES ('delete', old.id, old.title, old.content_text);
        END
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, title, content_text)
            VALUES ('delete', old.id, old.title, old.content_text);
            INSERT INTO documents_fts(rowid, title, content_text)
            VALUES (new.id, new.title, new.content_text);
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS documents_au")
    op.execute("DROP TRIGGER IF EXISTS documents_ad")
    op.execute("DROP TRIGGER IF EXISTS documents_ai")
    op.execute("DROP TABLE IF EXISTS documents_fts")
    op.drop_table("refresh_tokens")
    op.drop_table("api_keys")
    op.drop_index("idx_documents_status", "documents")
    op.drop_index("idx_documents_user_id", "documents")
    op.drop_table("documents")
    op.drop_table("users")
