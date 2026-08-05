"""Add selective meeting attendance.

Revision ID: r14_select_attend
Revises: r13_public_summary_20260706
Create Date: 2026-08-05
"""

from alembic import op
from alembic import context
import sqlalchemy as sa

revision = "r14_select_attend"
down_revision = "r13_public_summary_20260706"
branch_labels = None
depends_on = None

attendance_mode = sa.Enum(
    "all_twg_members", "specific_twg_members", name="attendancemode"
)

def _inspector():
    return None if context.is_offline_mode() else sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    attendance_mode.create(op.get_bind(), checkfirst=True)
    if inspector is None or "attendance_mode" not in {column["name"] for column in inspector.get_columns("meetings")}:
        op.add_column(
        "meetings",
        sa.Column(
            "attendance_mode",
            attendance_mode,
            nullable=False,
            server_default="all_twg_members",
        ),
        )
    if inspector is None or "attendance_mode" not in {column["name"] for column in inspector.get_columns("recurring_meetings")}:
        op.add_column(
        "recurring_meetings",
        sa.Column(
            "attendance_mode",
            attendance_mode,
            nullable=False,
            server_default="all_twg_members",
        ),
        )
    if inspector is None or "recurring_meeting_selected_members" not in inspector.get_table_names():
        op.create_table(
        "recurring_meeting_selected_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recurring_meeting_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recurring_meeting_id"], ["recurring_meetings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recurring_meeting_id", "user_id", name="uq_recurring_selected_member"
        ),
        )


def downgrade() -> None:
    inspector = _inspector()
    if inspector is None or "recurring_meeting_selected_members" in inspector.get_table_names():
        op.drop_table("recurring_meeting_selected_members")
    if inspector is None or "attendance_mode" in {column["name"] for column in inspector.get_columns("recurring_meetings")}:
        op.drop_column("recurring_meetings", "attendance_mode")
    if inspector is None or "attendance_mode" in {column["name"] for column in inspector.get_columns("meetings")}:
        op.drop_column("meetings", "attendance_mode")
    attendance_mode.drop(op.get_bind(), checkfirst=True)
