"""Make action_items.owner_id nullable

Revision ID: n0ll_0wn3r_id
Revises: r3n4m3_twg_n4m3s
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'n0ll_0wn3r_id'
down_revision: Union[str, Sequence[str], None] = 'r3n4m3_twg_n4m3s'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow action items to have no owner (unassigned)."""
    op.alter_column('action_items', 'owner_id', nullable=True)


def downgrade() -> None:
    """Revert owner_id to NOT NULL."""
    op.alter_column('action_items', 'owner_id', nullable=False)
