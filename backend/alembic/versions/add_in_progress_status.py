"""Add IN_PROGRESS to MeetingStatus enum

Revision ID: add_in_progress_status
Revises: 
Create Date: 2026-01-27 11:08:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_in_progress_status'
down_revision = None  # Update this if you have previous migrations
branch_labels = None
depends_on = None


def upgrade():
    # Add IN_PROGRESS to the meetingstatus enum if it doesn't exist
    # Note: PostgreSQL doesn't support IF NOT EXISTS for ALTER TYPE ADD VALUE
    # So we need to check first
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'IN_PROGRESS' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'meetingstatus'
                )
            ) THEN
                ALTER TYPE meetingstatus ADD VALUE 'IN_PROGRESS';
            END IF;
        END$$;
    """)


def downgrade():
    # Cannot remove enum values in PostgreSQL without recreating the entire type
    # This is intentionally left as a no-op
    pass
