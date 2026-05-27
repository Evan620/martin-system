"""add sector_details to projects

Revision ID: r8_s3ct0r_d3t
Revises: r8_4rchiv3d
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'r8_s3ct0r_d3t'
down_revision = 'r8_4rchiv3d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("sector_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "sector_details")
