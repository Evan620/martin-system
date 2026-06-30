"""add subgroup_id to meetings and action_items, raw_owner_name to action_items

Revision ID: r12_subgroup_links_20260630
Revises: r11_project_interest_20260610
Create Date: 2026-06-30

Chains off r11_project_interest_20260610 (the single current head) to keep the
migration history linear — `alembic upgrade head` must resolve to one head or the
production entrypoint (`alembic upgrade head && uvicorn ...`) crash-loops. The
`subgroups` table these FKs reference is created by add_subgroups_20260520, which
is an ancestor of r11 on the main line, so the FK targets already exist here.
"""
from alembic import op
import sqlalchemy as sa


revision = "r12_subgroup_links_20260630"
down_revision = "r11_project_interest_20260610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meetings",
        sa.Column(
            "subgroup_id",
            sa.Uuid(),
            sa.ForeignKey("subgroups.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "action_items",
        sa.Column(
            "subgroup_id",
            sa.Uuid(),
            sa.ForeignKey("subgroups.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "action_items",
        sa.Column("raw_owner_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("action_items", "raw_owner_name")
    op.drop_column("action_items", "subgroup_id")
    op.drop_column("meetings", "subgroup_id")
