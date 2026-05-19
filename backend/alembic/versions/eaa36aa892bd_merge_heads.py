"""merge_heads

Revision ID: eaa36aa892bd
Revises: b3c4d5e6f7a8, c4d5e6f7g8h9
Create Date: 2026-05-19 16:30:23.819461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eaa36aa892bd'
down_revision: Union[str, Sequence[str], None] = ('b3c4d5e6f7a8', 'c4d5e6f7g8h9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
