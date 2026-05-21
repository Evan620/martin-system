"""r5 incubation stage 0

Revision ID: r5_1nc0bat10n
Revises: r4_ecowas_w8ght
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'r5_1nc0bat10n'
down_revision = 'r4_ecowas_w8ght'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add INCUBATION to the projectstatus enum BEFORE DRAFT
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'INCUBATION' BEFORE 'DRAFT'")

    # Seed incubation_graduation_threshold setting
    op.execute("""
        INSERT INTO platform_settings (key, value)
        VALUES ('incubation_graduation_threshold', '40')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — migration is one-way
    op.execute("""
        DELETE FROM platform_settings WHERE key = 'incubation_graduation_threshold'
    """)
