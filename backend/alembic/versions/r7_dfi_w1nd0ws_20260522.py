"""r7 blended finance — dfi windows + project_dfi_matches

Revision ID: r7_dfi_w1nd0ws
Revises: r6_buy3r_m4tch
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'r7_dfi_w1nd0ws'
down_revision = 'r6_buy3r_m4tch'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dfimatchstatus AS ENUM (
                'IDENTIFIED', 'APPROACHED', 'IN_REVIEW', 'SUBMITTED', 'APPROVED', 'REJECTED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dfiinstrumenttype AS ENUM (
                'GRANT', 'CONCESSIONAL_LOAN', 'EQUITY', 'BLENDED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dfi_windows (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            institution TEXT NOT NULL,
            instrument_type dfiinstrumenttype NOT NULL DEFAULT 'BLENDED',
            sectors JSONB,
            geographies JSONB,
            min_size_usd FLOAT,
            max_size_usd FLOAT,
            eligible_stages JSONB,
            gender_focus BOOLEAN DEFAULT FALSE,
            climate_focus BOOLEAN DEFAULT FALSE,
            description TEXT,
            url TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_dfi_matches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            dfi_window_id UUID NOT NULL REFERENCES dfi_windows(id) ON DELETE CASCADE,
            fit_score INT NOT NULL DEFAULT 0,
            fit_rationale TEXT,
            status dfimatchstatus NOT NULL DEFAULT 'IDENTIFIED',
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Seed 15 DFI windows
    op.execute("""
        INSERT INTO dfi_windows (name, institution, instrument_type, sectors, geographies,
            min_size_usd, max_size_usd, eligible_stages, gender_focus, climate_focus, description, url)
        VALUES
        (
            'Readiness & Preparatory Support',
            'Green Climate Fund (GCF)',
            'GRANT',
            '["Energy", "Agriculture", "Cross-Sector"]',
            '["GLOBAL"]',
            300000, 3000000,
            '["Concept", "Feasibility"]',
            true, true,
            'Readiness support for countries and direct access entities to develop bankable climate projects.',
            'https://www.greenclimate.fund/projects/readiness'
        ),
        (
            'Project Finance Window',
            'Green Climate Fund (GCF)',
            'BLENDED',
            '["Energy", "Agriculture"]',
            '["GLOBAL"]',
            10000000, NULL,
            '["Development", "Construction"]',
            true, true,
            'Large-scale climate mitigation and adaptation financing through grants, concessional loans, and equity.',
            'https://www.greenclimate.fund/projects/submit'
        ),
        (
            'Agriculture & Agro-industry Development Policy Programme (ADPP)',
            'African Development Bank (AfDB)',
            'CONCESSIONAL_LOAN',
            '["Agriculture"]',
            '["ECOWAS", "West Africa"]',
            5000000, 50000000,
            '["Development", "Construction", "Operational"]',
            false, false,
            'Policy-based lending for agricultural transformation in ECOWAS member states.',
            'https://www.afdb.org/en/topics-and-sectors/sectors/agriculture-agro-industry'
        ),
        (
            'Affirmative Finance Action for Women in Africa (AFAWA)',
            'African Development Bank (AfDB)',
            'BLENDED',
            '["Agriculture", "Energy", "Cross-Sector"]',
            '["Africa"]',
            500000, 10000000,
            '["Concept", "Feasibility", "Development"]',
            true, false,
            'Gender-smart blended finance to increase access to finance for women entrepreneurs across Africa.',
            'https://www.afdb.org/en/the-high-5/afawa-affirmative-finance-action-for-women-in-africa'
        ),
        (
            'Agribusiness & Infrastructure Investment',
            'International Finance Corporation (IFC)',
            'BLENDED',
            '["Agriculture", "Energy", "Minerals", "Digital"]',
            '["Africa"]',
            10000000, NULL,
            '["Development", "Construction", "Operational"]',
            false, false,
            'Direct equity and debt investment in private sector agribusiness, energy, and infrastructure.',
            'https://www.ifc.org/en/what-we-do/sector-expertise/agribusiness-forestry'
        ),
        (
            'Agrofinance Programme',
            'PROPARCO (AFD Group)',
            'BLENDED',
            '["Agriculture"]',
            '["Africa", "West Africa"]',
            5000000, 100000000,
            '["Development", "Construction", "Operational"]',
            false, true,
            'French DFI financing for agribusiness value chains including processing, inputs, and smallholder finance.',
            'https://www.proparco.fr/en/sectors/agribusiness'
        ),
        (
            'Agribusiness & Energy Investment',
            'British International Investment (BII)',
            'BLENDED',
            '["Agriculture", "Energy", "Digital"]',
            '["West Africa", "Africa"]',
            5000000, NULL,
            '["Development", "Construction", "Operational"]',
            true, true,
            'UK DFI providing equity and debt to private sector projects in Sub-Saharan Africa.',
            'https://www.bii.co.uk/en/our-investments/'
        ),
        (
            'Agribusiness & Renewable Energy Financing',
            'FMO (Dutch Development Bank)',
            'BLENDED',
            '["Agriculture", "Energy", "Cross-Sector"]',
            '["Africa"]',
            5000000, NULL,
            '["Development", "Construction", "Operational"]',
            true, true,
            'Dutch DFI providing senior debt, mezzanine, and equity to private sector projects in emerging markets.',
            'https://www.fmo.nl/sectors'
        ),
        (
            'Private Sector Financing Programme (PSFP)',
            'IFAD',
            'BLENDED',
            '["Agriculture"]',
            '["GLOBAL"]',
            2000000, 20000000,
            '["Feasibility", "Development", "Construction"]',
            true, false,
            'Blended finance for private sector investments that benefit smallholder farmers and rural populations.',
            'https://www.ifad.org/en/private-sector'
        ),
        (
            'Infrastructure & Agriculture Financing',
            'Islamic Development Bank (IsDB)',
            'CONCESSIONAL_LOAN',
            '["Agriculture", "Energy", "Infrastructure"]',
            '["ECOWAS", "West Africa"]',
            3000000, NULL,
            '["Feasibility", "Development", "Construction"]',
            false, false,
            'Concessional financing and technical assistance for IsDB member country development projects.',
            'https://www.isdb.org/sectors'
        ),
        (
            'Development Financing',
            'Arab Bank for Economic Development in Africa (BADEA)',
            'CONCESSIONAL_LOAN',
            '["Agriculture", "Energy", "Infrastructure"]',
            '["Africa"]',
            1000000, 30000000,
            '["Feasibility", "Development", "Construction"]',
            false, false,
            'Arab-African development cooperation through concessional loans and grants.',
            'https://www.badea.org'
        ),
        (
            'Agricultural Transformation Grants',
            'AGRA (Alliance for a Green Revolution in Africa)',
            'GRANT',
            '["Agriculture"]',
            '["West Africa", "Africa"]',
            100000, 5000000,
            '["Concept", "Feasibility", "Development"]',
            true, false,
            'Grant funding for agricultural transformation including input systems, market development, and policy.',
            'https://agra.org/grant-funding/'
        ),
        (
            'Private Sector Development Finance',
            'DEG (German Development Finance)',
            'BLENDED',
            '["Agriculture", "Energy", "Minerals"]',
            '["Africa"]',
            5000000, NULL,
            '["Development", "Construction", "Operational"]',
            false, true,
            'German DFI providing long-term loans, equity, and mezzanine to private sector development projects.',
            'https://www.deginvest.de/en'
        ),
        (
            'Infrastructure & Natural Resources',
            'Africa Finance Corporation (AFC)',
            'BLENDED',
            '["Energy", "Minerals", "Agriculture", "Infrastructure"]',
            '["Africa"]',
            20000000, NULL,
            '["Development", "Construction", "Operational"]',
            false, false,
            'Pan-African DFI specializing in infrastructure, natural resources, and heavy industry.',
            'https://www.africafc.org/investments'
        ),
        (
            'Scaling Up Renewable Energy Programme (SREP)',
            'Climate Investment Funds (CIF)',
            'BLENDED',
            '["Energy"]',
            '["ECOWAS", "West Africa", "Africa"]',
            5000000, NULL,
            '["Feasibility", "Development", "Construction"]',
            false, true,
            'Concessional finance to pilot low-carbon technologies and scale up renewable energy in developing countries.',
            'https://www.climateinvestmentfunds.org/topics/energy'
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_dfi_matches;")
    op.execute("DROP TABLE IF EXISTS dfi_windows;")
    op.execute("DROP TYPE IF EXISTS dfimatchstatus;")
    op.execute("DROP TYPE IF EXISTS dfiinstrumenttype;")
