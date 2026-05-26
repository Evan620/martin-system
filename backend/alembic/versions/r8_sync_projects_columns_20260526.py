"""r8 sync projects table columns added via Base.metadata.create_all

Revision ID: r8_sync_proj
Revises: r8_cr34t3_t4bl
Create Date: 2026-05-26

Backfill columns that were added to the Project SQLAlchemy model over time
but never had explicit ALTER TABLE migrations. Local dev was running
Base.metadata.create_all(), so the schema kept up; prod (alembic-only)
fell behind silently. Symptom on prod:
    UndefinedColumnError: column projects.certifications_held does not exist

All ADDs use IF NOT EXISTS so this is safe to re-run on any environment.
"""
from alembic import op


revision = 'r8_sync_proj'
down_revision = 'r8_cr34t3_t4bl'
branch_labels = None
depends_on = None


_COLUMNS = [
    # R2 — gender & youth flags
    ("gender_intentional", "BOOLEAN"),
    ("gender_justification", "TEXT"),
    ("youth_focused", "BOOLEAN"),
    ("youth_justification", "TEXT"),
    # Phase 1 classification
    ("value_chain_stages", "TEXT[]"),
    ("women_employment_pct", "DOUBLE PRECISION"),
    ("youth_employment_pct", "DOUBLE PRECISION"),
    # R6 — buyer/offtake certifications
    ("certifications_held", "JSON"),
    # R8 — site coordinates + place name
    ("site_lat", "DOUBLE PRECISION"),
    ("site_lon", "DOUBLE PRECISION"),
    ("site_location_name", "TEXT"),
    # Investment template
    ("subsector", "VARCHAR(255)"),
    ("project_sponsor", "VARCHAR(255)"),
    ("is_cross_border", "BOOLEAN DEFAULT FALSE"),
    ("key_contact_name", "VARCHAR(255)"),
    ("key_contact_email", "VARCHAR(255)"),
    ("technical_studies", "TEXT"),
    ("permits_licences", "TEXT"),
    ("land_status", "TEXT"),
    ("financing_structure", "TEXT"),
    ("investment_stage_label", "VARCHAR(100)"),
    ("revenue_model", "TEXT"),
    ("macroeconomic_roi", "TEXT"),
    ("climate_impact", "TEXT"),
    ("esg_compliance", "TEXT"),
    ("ghg_avoided_target", "TEXT"),
    ("jobs_construction", "TEXT"),
    ("jobs_om", "TEXT"),
    ("electricity_connections", "TEXT"),
    ("digital_connections", "TEXT"),
    ("smallholder_farmers_reached", "TEXT"),
    ("submitted_by", "VARCHAR(255)"),
]


def upgrade() -> None:
    for col_name, col_type in _COLUMNS:
        op.execute(f"ALTER TABLE projects ADD COLUMN IF NOT EXISTS {col_name} {col_type}")


def downgrade() -> None:
    # Project columns added by this migration mostly carry application-meaningful
    # data; dropping them would lose user content. Treat as one-way.
    pass
