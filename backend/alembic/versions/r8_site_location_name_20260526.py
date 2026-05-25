"""r8 add site_location_name to projects

Revision ID: r8_l0c_n4m3
Revises: r8_g30_5ource
Create Date: 2026-05-26
"""
from alembic import op


revision = 'r8_l0c_n4m3'
down_revision = 'r8_g30_5ource'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Human-readable place name set at intake or after auto-scout.
    # Nullable — legacy projects have no name; new projects can skip it.
    op.execute(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS site_location_name TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS site_location_name")
