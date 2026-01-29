"""add_action_items_snapshot_to_minutes_versions

Revision ID: c2fccf925338
Revises: e00bcb856c06
Create Date: 2026-01-28 14:34:34.233694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2fccf925338'
down_revision: Union[str, Sequence[str], None] = 'e00bcb856c06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('minutes_versions', sa.Column('action_items_snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('minutes_versions', 'action_items_snapshot')
