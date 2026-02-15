"""add group_type column to twgs table

Revision ID: g1h2i3j4k5l6
Revises: fe5cd4954a45
Create Date: 2026-02-16 00:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
down_revision = '7222328015ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('twgs', sa.Column('group_type', sa.String(50), server_default='twg', nullable=False))


def downgrade() -> None:
    op.drop_column('twgs', 'group_type')
