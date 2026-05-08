"""add embedding_configs, rag_configs

Revision ID: 008
Revises: 007
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    # --- embedding_configs ---
    if not _table_exists("embedding_configs"):
        op.create_table(
            "embedding_configs",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("api_key", sa.String(500), nullable=True),
            sa.Column("base_url", sa.String(500), nullable=True),
            sa.Column("model_name", sa.String(100), nullable=True),
            sa.Column("vector_dimension", sa.Integer, server_default="1024"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )
        op.create_index(
            "idx_embedding_configs_user_id", "embedding_configs", ["user_id"]
        )
        op.create_index(
            "idx_embedding_configs_user_id_unique",
            "embedding_configs",
            ["user_id"],
            unique=True,
        )

    # --- rag_configs ---
    if not _table_exists("rag_configs"):
        op.create_table(
            "rag_configs",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chunk_size", sa.Integer, server_default="300"),
            sa.Column("chunk_overlap", sa.Integer, server_default="50"),
            sa.Column("top_k", sa.Integer, server_default="3"),
            sa.Column("threshold_dist", sa.Float, server_default="0.35"),
            sa.Column("query_buffer", sa.Integer, server_default="10"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )
        op.create_index("idx_rag_configs_user_id", "rag_configs", ["user_id"])
        op.create_index(
            "idx_rag_configs_user_id_unique", "rag_configs", ["user_id"], unique=True
        )


def downgrade() -> None:
    # Drop indexes and tables in reverse dependency order
    if _table_exists("rag_configs"):
        if _index_exists("rag_configs", "idx_rag_configs_user_id_unique"):
            op.drop_index("idx_rag_configs_user_id_unique", table_name="rag_configs")
        if _index_exists("rag_configs", "idx_rag_configs_user_id"):
            op.drop_index("idx_rag_configs_user_id", table_name="rag_configs")
        op.drop_table("rag_configs")

    if _table_exists("embedding_configs"):
        if _index_exists(
            "embedding_configs", "idx_embedding_configs_user_id_unique"
        ):
            op.drop_index(
                "idx_embedding_configs_user_id_unique",
                table_name="embedding_configs",
            )
        if _index_exists("embedding_configs", "idx_embedding_configs_user_id"):
            op.drop_index(
                "idx_embedding_configs_user_id", table_name="embedding_configs"
            )
        op.drop_table("embedding_configs")
