"""add public_summary JSON column to minutes

Revision ID: r13_minutes_public_summary_20260706
Revises: r12_subgroup_links_20260630
Create Date: 2026-07-06

Chains off r12_subgroup_links_20260630 (the single current head) to keep the
migration history linear — `alembic upgrade head` must resolve to one head or the
production entrypoint (`alembic upgrade head && uvicorn ...`) crash-loops.

Adds the nullable `public_summary` JSON column to the `minutes` row. This holds
the chair-approved, public-safe block (highlights / decisions_milestones /
institutions_public / next_milestone) — the ONLY minutes data that crosses the
wire to Campaign OS. sa.JSON() is cross-dialect (JSON on Postgres prod, TEXT-backed
on SQLite tests), matching the repo's existing JSON-column convention.
"""
from alembic import op
import sqlalchemy as sa


revision = "r13_minutes_public_summary_20260706"
down_revision = "r12_subgroup_links_20260630"
branch_labels = None
depends_on = None


def _minutes_columns(bind) -> set:
    return {c["name"] for c in sa.inspect(bind).get_columns("minutes")}


def upgrade() -> None:
    # Idempotency guard: both the web AND worker services run
    # `alembic upgrade head` at boot from the same image, so this migration can
    # be attempted twice near-simultaneously (or re-run). Skip the ADD if the
    # column already exists — avoids the DuplicateColumnError crash-loop we hit
    # with r12's drift. Additive + nullable, so the guard is fully safe.
    bind = op.get_bind()
    if "public_summary" not in _minutes_columns(bind):
        op.add_column(
            "minutes",
            sa.Column("public_summary", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "public_summary" in _minutes_columns(bind):
        op.drop_column("minutes", "public_summary")
