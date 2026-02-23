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
    # Enum type 'invitationmessagesender' should already exist or be created manually
    # Using raw SQL to handle the enum type creation conditionally
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invitationmessagesender AS ENUM ('ADMIN', 'INVITEE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """)

    # Create invitation_messages table
    op.create_table('invitation_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('invitation_id', sa.Uuid(), nullable=False),
        sa.Column('sender_type', sa.Enum('ADMIN', 'INVITEE', name='invitationmessagesender', create_type=False), nullable=False),
        sa.Column('sender_user_id', sa.Uuid(), nullable=True),
        sa.Column('sender_name', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_read_by_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_read_by_invitee', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['invitation_id'], ['organization_invitations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_invitation_messages_invitation_id', 'invitation_messages', ['invitation_id'])
    op.create_index('ix_invitation_messages_created_at', 'invitation_messages', ['created_at'])

    # Add unread count columns to organization_invitations
    op.add_column('organization_invitations',
        sa.Column('unread_by_admin_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('organization_invitations',
        sa.Column('unread_by_invitee_count', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_invitation_messages_created_at', table_name='invitation_messages')
    op.drop_index('ix_invitation_messages_invitation_id', table_name='invitation_messages')
    op.drop_table('invitation_messages')

    op.drop_column('organization_invitations', 'unread_by_invitee_count')
    op.drop_column('organization_invitations', 'unread_by_admin_count')

    # Drop enum type
    sender_enum = sa.Enum('ADMIN', 'INVITEE', name='invitationmessagesender')
    sender_enum.drop(op.get_bind(), checkfirst=True)
