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
    # Idempotent: prod has historically had columns added via metadata.create_all
    # or hand-rolled SQL hotfixes, so the column may already exist when this runs.
    op.execute(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS sector_details JSONB"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS sector_details")
