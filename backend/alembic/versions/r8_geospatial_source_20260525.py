"""r8 add source column to project_geospatial_data

Revision ID: r8_g30_5ource
Revises: r5_4rch1v3d
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'r8_g30_5ource'
down_revision = 'r5_4rch1v3d'
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
