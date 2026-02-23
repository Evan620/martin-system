"""Add invite tracking fields to users

Revision ID: a1b2c3d4e5f6
Revises: g1h2i3j4k5l6
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('invite_sent_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('invite_accepted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_reset_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_reset_at')
    op.drop_column('users', 'invite_accepted_at')
    op.drop_column('users', 'invite_sent_at')
