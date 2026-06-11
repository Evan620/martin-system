"""create project_interests table (Deal Room member follow/interest)

Revision ID: r11_project_interest_20260610
Revises: r10_reminders_table_20260610
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = "r11_project_interest_20260610"
down_revision = "r10_reminders_table_20260610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_interest_project_user"),
    )
    op.create_index(op.f("ix_project_interests_project_id"), "project_interests", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_interests_user_id"), "project_interests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_interests_user_id"), table_name="project_interests")
    op.drop_index(op.f("ix_project_interests_project_id"), table_name="project_interests")
    op.drop_table("project_interests")
