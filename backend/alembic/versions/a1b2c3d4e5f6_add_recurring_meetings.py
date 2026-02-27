"""add recurring meetings

Revision ID: a1b2c3d4e5f6
Revises: i1j2k3l4m5n6, g1h2i3j4k5l6
Create Date: 2026-02-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = ('i1j2k3l4m5n6', 'g1h2i3j4k5l6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create recurrence frequency enum
    op.execute("CREATE TYPE recurrencefrequency AS ENUM ('weekly', 'biweekly', 'monthly')")

    # Create recurrence end type enum
    op.execute("CREATE TYPE recurrenceendtype AS ENUM ('after_date', 'after_occurrences', 'never')")

    # Create recurring meeting status enum
    op.execute("CREATE TYPE recurringmeetingstatus AS ENUM ('active', 'paused', 'ended', 'cancelled')")

    # Create recurring_meetings table
    op.create_table(
        'recurring_meetings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('twg_id', sa.Uuid(), nullable=False),
        sa.Column('title_template', sa.String(length=255), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('meeting_type', sa.String(length=50), nullable=True, server_default='virtual'),
        sa.Column('frequency', postgresql.ENUM('weekly', 'biweekly', 'monthly', name='recurrencefrequency', create_type=False), nullable=False),
        sa.Column('interval_weeks', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('start_time', sa.String(length=10), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=True, server_default='UTC'),
        sa.Column('end_type', postgresql.ENUM('after_date', 'after_occurrences', 'never', name='recurrenceendtype', create_type=False), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('max_occurrences', sa.Integer(), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'paused', 'ended', 'cancelled', name='recurringmeetingstatus', create_type=False), nullable=True, server_default='active'),
        sa.Column('occurrences_created', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_by_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['twg_id'], ['twgs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for recurring_meetings
    op.create_index('ix_recurring_meetings_twg_id', 'recurring_meetings', ['twg_id'])
    op.create_index('ix_recurring_meetings_status', 'recurring_meetings', ['status'])
    op.create_index('ix_recurring_meetings_created_by_id', 'recurring_meetings', ['created_by_id'])

    # Add recurring meeting fields to meetings table
    op.add_column('meetings', sa.Column('recurring_meeting_id', sa.Uuid(), nullable=True))
    op.add_column('meetings', sa.Column('is_recurring_exception', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('meetings', sa.Column('original_scheduled_at', sa.DateTime(), nullable=True))

    # Create foreign key for meetings.recurring_meeting_id
    op.create_foreign_key(
        'fk_meetings_recurring_meeting_id',
        'meetings',
        'recurring_meetings',
        ['recurring_meeting_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index for meetings.recurring_meeting_id
    op.create_index('ix_meetings_recurring_meeting_id', 'meetings', ['recurring_meeting_id'])


def downgrade() -> None:
    # Drop index from meetings
    op.drop_index('ix_meetings_recurring_meeting_id', table_name='meetings')

    # Drop foreign key from meetings
    op.drop_constraint('fk_meetings_recurring_meeting_id', 'meetings', type_='foreignkey')

    # Drop columns from meetings
    op.drop_column('meetings', 'original_scheduled_at')
    op.drop_column('meetings', 'is_recurring_exception')
    op.drop_column('meetings', 'recurring_meeting_id')

    # Drop indexes from recurring_meetings
    op.drop_index('ix_recurring_meetings_created_by_id', table_name='recurring_meetings')
    op.drop_index('ix_recurring_meetings_status', table_name='recurring_meetings')
    op.drop_index('ix_recurring_meetings_twg_id', table_name='recurring_meetings')

    # Drop recurring_meetings table
    op.drop_table('recurring_meetings')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS recurringmeetingstatus')
    op.execute('DROP TYPE IF EXISTS recurrenceendtype')
    op.execute('DROP TYPE IF EXISTS recurrencefrequency')
