"""Seed TWG data

Revision ID: 044d9e8f2g3b
Revises: 033c8d9e1f2a
Create Date: 2026-01-07 02:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import uuid

# revision identifiers, used by Alembic.
revision: str = '044d9e8f2g3b'
down_revision: Union[str, Sequence[str], None] = '033c8d9e1f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed TWG table with default pillars."""
    connection = op.get_bind()
    
    twgs = [
        {
            "name": "Energy Trade and Industrial Growth",
            "pillar": "energy_infrastructure"
        },
        {
            "name": "Agriculture & Food Systems",
            "pillar": "agriculture_food_systems"
        },
        {
            "name": "Strategic Minerals and Natural Resource Development",
            "pillar": "critical_minerals_industrialization"
        },
        {
            "name": "Digital Transformation",
            "pillar": "digital_economy_transformation"
        },
        {
            "name": "Protocol & Logistics",
            "pillar": "protocol_logistics"
        },
        {
            "name": "Resource Mobilization",
            "pillar": "resource_mobilization"
        }
    ]
    
    for twg in twgs:
        # Check if exists
        result = connection.execute(text("""
            SELECT count(*) FROM twgs WHERE pillar = :pillar
        """), {"pillar": twg["pillar"]})
        
        if result.scalar() == 0:
            # Insert
            connection.execute(text("""
                INSERT INTO twgs (id, name, pillar, status)
                VALUES (:id, :name, :pillar, 'active')
            """), {
                "id": str(uuid.uuid4()),
                "name": twg["name"],
                "pillar": twg["pillar"]
            })


def downgrade() -> None:
    """Remove seeded data."""
    connection = op.get_bind()
    # We generally don't delete data in downgrade unless strictly needed
    # preventing accidental data loss if user added leads to these TWGs
    pass
