"""create reminders table

Revision ID: r10_reminders_table_20260610
Revises: r9_rsvp_tentative_20260609
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = "r10_reminders_table_20260610"
down_revision = "r9_rsvp_tentative_20260609"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("remind_at", sa.DateTime(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_user_id"), "reminders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reminders_user_id"), table_name="reminders")
    op.drop_table("reminders")
