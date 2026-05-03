"""add user profile columns

Revision ID: 004
Revises: 003
Create Date: 2026-05-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a SQLite table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    columns = [row[1] for row in result]
    return column in columns


def upgrade() -> None:
    if not _column_exists("users", "avatar_path"):
        op.execute("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(500)")
    if not _column_exists("users", "background_path"):
        op.execute("ALTER TABLE users ADD COLUMN background_path VARCHAR(500)")
    if not _column_exists("users", "background_opacity"):
        op.execute("ALTER TABLE users ADD COLUMN background_opacity FLOAT DEFAULT 0.3")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN avatar_path")
    op.execute("ALTER TABLE users DROP COLUMN background_path")
    op.execute("ALTER TABLE users DROP COLUMN background_opacity")
