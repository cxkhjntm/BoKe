"""add user_backgrounds table and carousel_interval

Revision ID: 005
Revises: 004
Create Date: 2026-05-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    columns = [row[1] for row in result]
    return column in columns


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table})
    return result.first() is not None


def upgrade() -> None:
    # Add carousel_interval to users
    if not _column_exists("users", "carousel_interval"):
        op.execute("ALTER TABLE users ADD COLUMN carousel_interval INTEGER DEFAULT 5")

    # Create user_backgrounds table
    if not _table_exists("user_backgrounds"):
        op.create_table(
            "user_backgrounds",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("image_path", sa.String(500), nullable=False),
            sa.Column("position", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("ix_user_backgrounds_user_id", "user_backgrounds", ["user_id"])

    # Migrate existing background_path data
    conn = op.get_bind()
    users_with_bg = conn.execute(sa.text("SELECT id, background_path FROM users WHERE background_path IS NOT NULL"))
    for row in users_with_bg:
        user_id, bg_path = row
        # Check if already migrated
        existing = conn.execute(
            sa.text("SELECT id FROM user_backgrounds WHERE user_id=:uid AND image_path=:path"),
            {"uid": user_id, "path": bg_path},
        ).first()
        if not existing:
            conn.execute(
                sa.text("INSERT INTO user_backgrounds (user_id, image_path, position) VALUES (:uid, :path, 0)"),
                {"uid": user_id, "path": bg_path},
            )


def downgrade() -> None:
    op.drop_index("ix_user_backgrounds_user_id", table_name="user_backgrounds")
    op.drop_table("user_backgrounds")
    # Note: we don't drop carousel_interval from users to avoid data loss
