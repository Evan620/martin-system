"""Rename TWGs to match official client names

Revision ID: r3n4m3_twg_n4m3s
Revises: a1t1m3st4mps
Create Date: 2026-03-02

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'r3n4m3_twg_n4m3s'
down_revision: Union[str, Sequence[str], None] = 'a1t1m3st4mps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old name -> New name, keyed by pillar enum value
RENAMES = {
    "digital_economy_transformation": "Digital Transformation",
    "energy_infrastructure": "Energy Trade and Industrial Growth",
    "critical_minerals_industrialization": "Strategic Minerals and Natural Resource Development",
}


def upgrade() -> None:
    """Update TWG display names to match official client naming."""
    connection = op.get_bind()
    for pillar, new_name in RENAMES.items():
        connection.execute(text("""
            UPDATE twgs SET name = :name WHERE pillar = :pillar
        """), {"name": new_name, "pillar": pillar})


def downgrade() -> None:
    """Revert TWG display names."""
    connection = op.get_bind()
    old_names = {
        "digital_economy_transformation": "Digital Economy & Transformation",
        "energy_infrastructure": "Energy & Infrastructure",
        "critical_minerals_industrialization": "Critical Minerals & Industrialization",
    }
    for pillar, old_name in old_names.items():
        connection.execute(text("""
            UPDATE twgs SET name = :name WHERE pillar = :pillar
        """), {"name": old_name, "pillar": pillar})
