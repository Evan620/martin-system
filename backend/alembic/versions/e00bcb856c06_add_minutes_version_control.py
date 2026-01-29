"""add_minutes_version_control

Revision ID: e00bcb856c06
Revises: add_in_progress_status
Create Date: 2026-01-28 11:42:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = 'e00bcb856c06'
down_revision = 'add_in_progress_status'
branch_labels = None
depends_on = None


def upgrade():
    # Create minutes_versions table
    op.create_table(
        'minutes_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('minutes_id', UUID(as_uuid=True), sa.ForeignKey('minutes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('key_decisions', sa.Text, nullable=True),
        sa.Column('change_summary', sa.String(500), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Create index for faster queries
    op.create_index('idx_minutes_versions_minutes_id', 'minutes_versions', ['minutes_id'])
    op.create_index('idx_minutes_versions_version_number', 'minutes_versions', ['minutes_id', 'version_number'])
    
    # Add version tracking fields to minutes table
    op.add_column('minutes', sa.Column('current_version', sa.Integer, nullable=False, server_default='1'))
    op.add_column('minutes', sa.Column('last_edited_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('minutes', sa.Column('last_edited_at', sa.DateTime, nullable=True))


def downgrade():
    # Remove version tracking fields from minutes
    op.drop_column('minutes', 'last_edited_at')
    op.drop_column('minutes', 'last_edited_by')
    op.drop_column('minutes', 'current_version')
    
    # Drop indexes
    op.drop_index('idx_minutes_versions_version_number')
    op.drop_index('idx_minutes_versions_minutes_id')
    
    # Drop minutes_versions table
    op.drop_table('minutes_versions')
