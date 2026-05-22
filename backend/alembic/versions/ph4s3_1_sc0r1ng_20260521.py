"""Phase 1 scoring and classification columns

Revision ID: ph4s3_1_sc0r1ng
Revises: add_subgroups_20260520
Create Date: 2026-05-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'ph4s3_1_sc0r1ng'
down_revision: Union[str, Sequence[str], None] = 'add_subgroups_20260520'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on projects
    op.add_column('projects', sa.Column('value_chain_stages', sa.ARRAY(sa.Text()), nullable=True))
    op.add_column('projects', sa.Column('women_employment_pct', sa.Float(), nullable=True))
    op.add_column('projects', sa.Column('youth_employment_pct', sa.Float(), nullable=True))

    # Platform settings key/value table
    op.create_table(
        'platform_settings',
        sa.Column('key', sa.Text(), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    # Seed default thresholds
    op.execute("INSERT INTO platform_settings (key, value) VALUES ('gender_threshold_pct', '30')")
    op.execute("INSERT INTO platform_settings (key, value) VALUES ('youth_threshold_pct', '25')")


def downgrade() -> None:
    op.drop_table('platform_settings')
    op.drop_column('projects', 'youth_employment_pct')
    op.drop_column('projects', 'women_employment_pct')
    op.drop_column('projects', 'value_chain_stages')
