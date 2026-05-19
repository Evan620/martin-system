"""widen_project_scores_detail_score_column

Revision ID: b3c4d5e6f7a8
Revises: a62ab7bf978a
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a62ab7bf978a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen score column from NUMERIC(3,1) to NUMERIC(5,2) to support 0-100 WAIIS scores."""
    op.alter_column(
        'project_scores_detail',
        'score',
        type_=sa.Numeric(5, 2),
        existing_type=sa.Numeric(3, 1),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'project_scores_detail',
        'score',
        type_=sa.Numeric(3, 1),
        existing_type=sa.Numeric(5, 2),
        existing_nullable=True,
    )
