"""add_invitation_messages

Revision ID: i1j2k3l4m5n6
Revises: c3d4e5f6g7h8
Create Date: 2026-02-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i1j2k3l4m5n6'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type conditionally (ignore if exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invitationmessagesender AS ENUM ('ADMIN', 'INVITEE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """)

    # Create invitation_messages table using raw SQL to avoid SQLAlchemy enum issues
    op.execute("""
        CREATE TABLE IF NOT EXISTS invitation_messages (
            id UUID NOT NULL PRIMARY KEY,
            invitation_id UUID NOT NULL REFERENCES organization_invitations(id) ON DELETE CASCADE,
            sender_type invitationmessagesender NOT NULL,
            sender_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            sender_name VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            is_read_by_admin BOOLEAN NOT NULL DEFAULT false,
            is_read_by_invitee BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    # Create indexes for efficient querying
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_invitation_messages_invitation_id ON invitation_messages(invitation_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_invitation_messages_created_at ON invitation_messages(created_at)
    """)

    # Add unread count columns to organization_invitations
    op.execute("""
        ALTER TABLE organization_invitations
        ADD COLUMN IF NOT EXISTS unread_by_admin_count INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE organization_invitations
        ADD COLUMN IF NOT EXISTS unread_by_invitee_count INTEGER NOT NULL DEFAULT 0
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_invitation_messages_created_at")
    op.execute("DROP INDEX IF EXISTS ix_invitation_messages_invitation_id")
    op.execute("DROP TABLE IF EXISTS invitation_messages")

    op.execute("ALTER TABLE organization_invitations DROP COLUMN IF EXISTS unread_by_invitee_count")
    op.execute("ALTER TABLE organization_invitations DROP COLUMN IF EXISTS unread_by_admin_count")

    # Drop enum type conditionally
    op.execute("""
        DO $$ BEGIN
            DROP TYPE IF EXISTS invitationmessagesender;
        END $$
    """)
