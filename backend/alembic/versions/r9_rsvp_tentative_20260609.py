"""add TENTATIVE to rsvpstatus enum

Revision ID: r9_rsvp_tentative_20260609
Revises: r8_agent_audit
Create Date: 2026-06-09
"""
from alembic import op

revision = "r9_rsvp_tentative_20260609"
down_revision = "r8_agent_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    # Commit the migration's implicit transaction first, then add the value.
    op.execute("COMMIT")
    op.execute("ALTER TYPE rsvpstatus ADD VALUE IF NOT EXISTS 'TENTATIVE'")


def downgrade() -> None:
    # Postgres cannot DROP a value from an enum; downgrade is a no-op.
    pass
