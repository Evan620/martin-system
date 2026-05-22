"""r6 buyer offtake matching tables

Revision ID: r6_buy3r_m4tch
Revises: r5_1nc0bat10n
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'r6_buy3r_m4tch'
down_revision = 'r5_1nc0bat10n'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE buyermatchstatus AS ENUM (
                'DETECTED', 'CONTACTED', 'INTERESTED', 'NEGOTIATING', 'COMMITTED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS buyers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            commodity_types JSONB,
            volume_mt_per_year FLOAT,
            contract_term_years INT,
            price_floor_usd FLOAT,
            geographic_focus JSONB,
            notes TEXT,
            deleted_at TIMESTAMP,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_buyer_matches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            buyer_id UUID NOT NULL REFERENCES buyers(id) ON DELETE CASCADE,
            match_score INT NOT NULL DEFAULT 0,
            status buyermatchstatus NOT NULL DEFAULT 'DETECTED',
            match_rationale TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_buyer_matches;")
    op.execute("DROP TABLE IF EXISTS buyers;")
    op.execute("DROP TYPE IF EXISTS buyermatchstatus;")
