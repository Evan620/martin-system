"""widen_lead_country_and_land_status_to_text

Revision ID: 79130ce80c1e
Revises: a62ab7bf978a
Create Date: 2026-05-13 13:11:55.997515

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '79130ce80c1e'
down_revision: Union[str, Sequence[str], None] = 'a62ab7bf978a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('projects', 'lead_country',
               existing_type=sa.String(length=100),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('projects', 'land_status',
               existing_type=sa.String(length=100),
               type_=sa.Text(),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('projects', 'land_status',
               existing_type=sa.Text(),
               type_=sa.String(length=100),
               existing_nullable=True)
    op.alter_column('projects', 'lead_country',
               existing_type=sa.Text(),
               type_=sa.String(length=100),
               existing_nullable=True)
