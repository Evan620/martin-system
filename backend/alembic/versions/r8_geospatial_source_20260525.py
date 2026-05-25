"""r8 add source column to project_geospatial_data

Revision ID: r8_g30_5ource
Revises: r7_dfi_w1nd0ws
Create Date: 2026-05-25

Note: originally chained from r5_4rch1v3d (a local-only R5 archive-status
migration that was never committed to main). Re-pointed to r7_dfi_w1nd0ws
so the chain is valid on prod. The R5 archive migration can land in a
separate commit when that work is ready.
"""
from alembic import op
import sqlalchemy as sa

revision = 'r8_g30_5ource'
down_revision = 'r7_dfi_w1nd0ws'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GeospatialService writes one of: 'copernicus', 'fixture', 'stub'.
    # Default 'stub' is the safest pre-existing-row value — it matches the
    # previous behaviour where every row was synthetic.
    op.execute(
        "ALTER TABLE project_geospatial_data "
        "ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'stub'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE project_geospatial_data DROP COLUMN IF EXISTS source")
