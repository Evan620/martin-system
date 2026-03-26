"""add timestamps to action_items

Revision ID: a1t1m3st4mps
Revises: rc2026mtg2702
Create Date: 2026-03-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1t1m3st4mps'
down_revision: Union[str, Sequence[str], None] = 'rc2026mtg2702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_at, updated_at, completed_at to action_items."""
    op.add_column('action_items', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    op.add_column('action_items', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('action_items', sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove timestamp columns from action_items."""
    op.drop_column('action_items', 'completed_at')
    op.drop_column('action_items', 'updated_at')
    op.drop_column('action_items', 'created_at')
