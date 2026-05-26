"""r8 sync buyers + dfi_windows columns added via Base.metadata.create_all

Revision ID: r8_sync_b_dfi
Revises: r8_sync_proj
Create Date: 2026-05-26

Same as r8_sync_proj but for the buyers and dfi_windows tables. These
gained columns through model evolution (R6 certifications, R7 eligibility
rules + investor FK) without ever getting ALTER TABLE migrations.

Prod symptom (after projects sync landed):
    UndefinedColumnError: column buyers.certifications_accepted does not exist

All ADDs use IF NOT EXISTS so this is safe to re-run.
"""
from alembic import op


revision = 'r8_sync_b_dfi'
down_revision = 'r8_sync_proj'
branch_labels = None
depends_on = None


_BUYER_COLS = [
    ("certifications_accepted", "JSON"),
    ("verification_status", "VARCHAR(20) NOT NULL DEFAULT 'demo'"),
]

_DFI_WINDOW_COLS = [
    # FK to investors. SET NULL on delete so existing rows survive an investor
    # being removed. Added as plain UUID first; the FK is added separately so
    # the migration tolerates an existing column without one.
    ("investor_id", "UUID"),
    ("concessional_eligibility_rules", "JSON"),
]


def upgrade() -> None:
    for col_name, col_type in _BUYER_COLS:
        op.execute(f"ALTER TABLE buyers ADD COLUMN IF NOT EXISTS {col_name} {col_type}")

    for col_name, col_type in _DFI_WINDOW_COLS:
        op.execute(f"ALTER TABLE dfi_windows ADD COLUMN IF NOT EXISTS {col_name} {col_type}")

    # Best-effort FK on investor_id — only add if the constraint isn't already
    # present and the investors table exists. Wrap in DO block for idempotency.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'investors')
               AND NOT EXISTS (
                   SELECT 1 FROM information_schema.table_constraints
                   WHERE table_name = 'dfi_windows'
                     AND constraint_name = 'fk_dfi_windows_investor_id'
               )
            THEN
                ALTER TABLE dfi_windows
                ADD CONSTRAINT fk_dfi_windows_investor_id
                FOREIGN KEY (investor_id) REFERENCES investors(id) ON DELETE SET NULL;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # One-way; the columns carry seed data (verification_status defaults to
    # 'demo', certifications_accepted populated by seed scripts).
    pass
