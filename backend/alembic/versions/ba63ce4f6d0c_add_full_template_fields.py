"""add_full_template_fields

Revision ID: ba63ce4f6d0c
Revises: b1c2d3e4f5a6
Create Date: 2026-05-13 14:31:11.767296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'ba63ce4f6d0c'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('key_contact_name', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('key_contact_email', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('technical_studies', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('permits_licences', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('financing_structure', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('investment_stage_label', sa.String(length=100), nullable=True))
    op.add_column('projects', sa.Column('macroeconomic_roi', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('ghg_avoided_target', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('jobs_construction', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('jobs_om', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('electricity_connections', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('digital_connections', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('smallholder_farmers_reached', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('submitted_by', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'submitted_by')
    op.drop_column('projects', 'smallholder_farmers_reached')
    op.drop_column('projects', 'digital_connections')
    op.drop_column('projects', 'electricity_connections')
    op.drop_column('projects', 'jobs_om')
    op.drop_column('projects', 'jobs_construction')
    op.drop_column('projects', 'ghg_avoided_target')
    op.drop_column('projects', 'macroeconomic_roi')
    op.drop_column('projects', 'investment_stage_label')
    op.drop_column('projects', 'financing_structure')
    op.drop_column('projects', 'permits_licences')
    op.drop_column('projects', 'technical_studies')
    op.drop_column('projects', 'key_contact_email')
    op.drop_column('projects', 'key_contact_name')
