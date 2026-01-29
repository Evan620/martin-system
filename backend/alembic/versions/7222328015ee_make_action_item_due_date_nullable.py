"""make_action_item_due_date_nullable

Revision ID: 7222328015ee
Revises: c2fccf925338
Create Date: 2026-01-28 16:17:59.849548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7222328015ee'
down_revision: Union[str, Sequence[str], None] = 'c2fccf925338'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make due_date nullable in action_items table
    op.alter_column('action_items', 'due_date',
                    existing_type=sa.DateTime(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Make due_date non-nullable again (this might fail if there are NULL values)
    op.alter_column('action_items', 'due_date',
                    existing_type=sa.DateTime(),
                    nullable=False)
