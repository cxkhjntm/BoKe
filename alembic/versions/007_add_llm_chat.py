"""add llm_configs, chat_sessions, users.max_rounds

Revision ID: 007
Revises: 006
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    columns = [row[1] for row in result]
    return column in columns


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table},
    )
    return result.first() is not None


def _index_exists(table: str, index: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:name"),
        {"name": index},
    )
    return result.first() is not None


def upgrade() -> None:
    # --- llm_configs ---
    if not _table_exists("llm_configs"):
        op.create_table(
            "llm_configs",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("provider", sa.String(20), nullable=False),
            sa.Column("api_key", sa.String(500), nullable=False),
            sa.Column("base_url", sa.String(500), nullable=False),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )
        op.create_index("idx_llm_configs_user_id", "llm_configs", ["user_id"])
        op.create_index(
            "idx_llm_configs_user_id_unique", "llm_configs", ["user_id"], unique=True
        )

    # --- chat_sessions ---
    if not _table_exists("chat_sessions"):
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("session_id", sa.String(36), nullable=False, unique=True),
            sa.Column("title", sa.String(200), nullable=False, server_default="新会话"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )
        op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"])
        op.create_index(
            "idx_chat_sessions_updated_at", "chat_sessions", ["updated_at"]
        )

    # --- users.max_rounds ---
    if not _column_exists("users", "max_rounds"):
        op.execute("ALTER TABLE users ADD COLUMN max_rounds INTEGER DEFAULT 10")
        op.execute("UPDATE users SET max_rounds = 10 WHERE max_rounds IS NULL")

    # SQLite does not support ALTER TABLE ADD CHECK directly; rely on app-level validation.


def downgrade() -> None:
    # Drop indexes and tables in reverse dependency order
    if _table_exists("chat_sessions"):
        if _index_exists("chat_sessions", "idx_chat_sessions_updated_at"):
            op.drop_index("idx_chat_sessions_updated_at", table_name="chat_sessions")
        if _index_exists("chat_sessions", "idx_chat_sessions_user_id"):
            op.drop_index("idx_chat_sessions_user_id", table_name="chat_sessions")
        op.drop_table("chat_sessions")

    if _table_exists("llm_configs"):
        if _index_exists("llm_configs", "idx_llm_configs_user_id_unique"):
            op.drop_index(
                "idx_llm_configs_user_id_unique", table_name="llm_configs"
            )
        if _index_exists("llm_configs", "idx_llm_configs_user_id"):
            op.drop_index("idx_llm_configs_user_id", table_name="llm_configs")
        op.drop_table("llm_configs")

    # Note: we intentionally do NOT drop max_rounds from users to avoid data loss.
