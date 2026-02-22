"""Add stage to documents

Revision ID: 495f5fdab1c6
Revises: 391968dcbfc3
Create Date: 2026-01-07 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '495f5fdab1c6'
down_revision: Union[str, Sequence[str], None] = '044d9e8f2g3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        # Create enum type for PostgreSQL idempotently
        op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documentstage') THEN CREATE TYPE documentstage AS ENUM ('ZERO_DRAFT', 'RAP_MODE', 'DECLARATION_TXT', 'FINAL'); END IF; END $$;")
        
        # Add column for PostgreSQL
        op.add_column('documents', 
            sa.Column('stage', postgresql.ENUM('ZERO_DRAFT', 'RAP_MODE', 'DECLARATION_TXT', 'FINAL', name='documentstage', create_type=False), 
            nullable=False, 
            server_default='FINAL')
        )
    else:
        # SQLite compatibility
        op.add_column('documents', 
            sa.Column('stage', sa.String(50), 
            nullable=False, 
            server_default='FINAL')
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'stage')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS documentstage")
