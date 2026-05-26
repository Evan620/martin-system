"""r8/r9 create project_geospatial_data and impact_log_entries tables

Revision ID: r8_cr34t3_t4bl
Revises: r7_dfi_w1nd0ws
Create Date: 2026-05-26

These two tables were originally introduced via SQLAlchemy
Base.metadata.create_all() in local dev and never had a CREATE TABLE
Alembic migration. On prod (alembic-only) the tables never existed,
so the subsequent r8_g30_5ource ALTER fails. This migration creates
both tables idempotently before the ALTER runs.

We use raw SQL with IF NOT EXISTS so re-running on environments that
already created the tables manually (e.g. via metadata.create_all)
stays safe.
"""
from alembic import op


revision = 'r8_cr34t3_t4bl'
down_revision = 'r7_dfi_w1nd0ws'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # R8: per-project geospatial cache
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_geospatial_data (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
            ndvi DOUBLE PRECISION NOT NULL,
            water_proximity_km DOUBLE PRECISION NOT NULL,
            land_use_description TEXT NOT NULL,
            land_use_smallholder_pct DOUBLE PRECISION NOT NULL,
            deforestation_risk TEXT NOT NULL,
            geo_score_boost INTEGER NOT NULL,
            is_demo BOOLEAN NOT NULL DEFAULT TRUE,
            analysed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
            raw_response JSONB
        )
        """
    )

    # R9: post-commitment quarterly impact actuals
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS impact_log_entries (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            period_label TEXT NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            jobs_created INTEGER,
            ghg_avoided_tco2 DOUBLE PRECISION,
            smallholders_reached INTEGER,
            women_jobs_actual INTEGER,
            youth_jobs_actual INTEGER,
            investment_deployed_usd NUMERIC(15, 2),
            notes TEXT,
            logged_by_id UUID NOT NULL REFERENCES users(id),
            logged_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_impact_log_entries_project_id "
        "ON impact_log_entries (project_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS impact_log_entries")
    op.execute("DROP TABLE IF EXISTS project_geospatial_data")
