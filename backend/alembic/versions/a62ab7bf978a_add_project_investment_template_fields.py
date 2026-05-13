"""add_project_investment_template_fields

Revision ID: a62ab7bf978a
Revises: att3nd33_b0t_id
Create Date: 2026-05-13 12:21:38.562123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a62ab7bf978a'
down_revision: Union[str, Sequence[str], None] = 'att3nd33_b0t_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add investment template fields to projects table."""
    op.add_column('projects', sa.Column('subsector', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('project_sponsor', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('is_cross_border', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('projects', sa.Column('land_status', sa.String(100), nullable=True))
    op.add_column('projects', sa.Column('revenue_model', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('climate_impact', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('esg_compliance', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove investment template fields from projects table."""
    op.drop_column('projects', 'esg_compliance')
    op.drop_column('projects', 'climate_impact')
    op.drop_column('projects', 'revenue_model')
    op.drop_column('projects', 'land_status')
    op.drop_column('projects', 'is_cross_border')
    op.drop_column('projects', 'project_sponsor')
    op.drop_column('projects', 'subsector')
