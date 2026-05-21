"""add gender_intentional and youth_focused binary flags

Revision ID: g3nd3r_yn_fl4gs
Revises: ph4s3_1_sc0r1ng
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'g3nd3r_yn_fl4gs'
down_revision = 'ph4s3_1_sc0r1ng'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('gender_intentional', sa.Boolean(), nullable=True))
    op.add_column('projects', sa.Column('gender_justification', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('youth_focused', sa.Boolean(), nullable=True))
    op.add_column('projects', sa.Column('youth_justification', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('projects', 'youth_justification')
    op.drop_column('projects', 'youth_focused')
    op.drop_column('projects', 'gender_justification')
    op.drop_column('projects', 'gender_intentional')
