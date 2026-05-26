"""r8 append ARCHIVED to projectstatus enum

Revision ID: r8_4rchiv3d
Revises: r8_sync_b_dfi
Create Date: 2026-05-26

The R5 archived-status work added 'ARCHIVED' to the Python ProjectStatus
enum and uses it for the 90-day stale-incubation auto-expiry job, but
the underlying Postgres enum type was never updated. Prod symptom:
    InvalidTextRepresentationError: invalid input value for enum
    projectstatus: "ARCHIVED"

This is the same SQL as the never-committed local r5_archived_status_
20260525.py migration (revision r5_4rch1v3d), recreated under a new
revision id so it can chain cleanly off the current prod head.

ALTER TYPE ... ADD VALUE IF NOT EXISTS is idempotent in PostgreSQL 12+
so this is safe to re-run.
"""
from alembic import op


revision = 'r8_4rchiv3d'
down_revision = 'r8_sync_b_dfi'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ARCHIVED sits after ON_HOLD (both are terminal/dormant states)
    op.execute(
        "ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'ARCHIVED' AFTER 'ON_HOLD'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; one-way.
    pass
