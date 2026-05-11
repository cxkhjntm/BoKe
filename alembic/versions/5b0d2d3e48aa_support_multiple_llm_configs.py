"""support_multiple_llm_configs

Revision ID: 5b0d2d3e48aa
Revises: 008
Create Date: 2026-05-10 21:51:44.310532
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b0d2d3e48aa'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('llm_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Integer(), nullable=False, server_default='0'))
        batch_op.drop_index('idx_llm_configs_user_id_unique')
        batch_op.create_unique_constraint('uq_user_provider', ['user_id', 'provider'])


def downgrade() -> None:
    with op.batch_alter_table('llm_configs', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_provider', type_='unique')
        batch_op.create_index('idx_llm_configs_user_id_unique', ['user_id'], unique=True)
        batch_op.drop_column('is_active')
