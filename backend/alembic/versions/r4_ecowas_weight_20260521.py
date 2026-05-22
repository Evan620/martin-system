"""r4 ecowas weight rebalance

Revision ID: r4_ecowas_w8ght
Revises: g3nd3r_yn_fl4gs
Create Date: 2026-05-21
"""
from alembic import op

revision = 'r4_ecowas_w8ght'
down_revision = 'g3nd3r_yn_fl4gs'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE scoring_criteria
        SET weight = 0.10
        WHERE criterion_name = 'ECOWAS Integration'
    """)
    op.execute("""
        UPDATE scoring_criteria
        SET weight = 0.10
        WHERE criterion_name = 'Country & Political Enablement'
    """)


def downgrade():
    op.execute("""
        UPDATE scoring_criteria
        SET weight = 0.05
        WHERE criterion_name = 'ECOWAS Integration'
    """)
    op.execute("""
        UPDATE scoring_criteria
        SET weight = 0.15
        WHERE criterion_name = 'Country & Political Enablement'
    """)
