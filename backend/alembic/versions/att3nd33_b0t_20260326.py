"""Add attendee_bot_id to meetings

Revision ID: att3nd33_b0t_id
Revises: n0ll_0wn3r_id
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'att3nd33_b0t_id'
down_revision: Union[str, Sequence[str], None] = 'n0ll_0wn3r_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add attendee_bot_id column to meetings table."""
    op.add_column('meetings', sa.Column('attendee_bot_id', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove attendee_bot_id column from meetings table."""
    op.drop_column('meetings', 'attendee_bot_id')
