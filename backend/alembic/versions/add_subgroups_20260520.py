"""add subgroups tables and document subgroup_id

Revision ID: add_subgroups_20260520
Revises: eaa36aa892bd
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'add_subgroups_20260520'
down_revision = 'eaa36aa892bd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subgroups',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('twg_id', UUID(as_uuid=True), sa.ForeignKey('twgs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_subgroups_twg_id', 'subgroups', ['twg_id'])

    op.create_table(
        'subgroup_members',
        sa.Column('subgroup_id', UUID(as_uuid=True), sa.ForeignKey('subgroups.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('joined_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.add_column('documents', sa.Column(
        'subgroup_id', UUID(as_uuid=True),
        sa.ForeignKey('subgroups.id', ondelete='SET NULL'),
        nullable=True
    ))


def downgrade():
    op.drop_column('documents', 'subgroup_id')
    op.drop_table('subgroup_members')
    op.drop_index('ix_subgroups_twg_id', table_name='subgroups')
    op.drop_table('subgroups')
