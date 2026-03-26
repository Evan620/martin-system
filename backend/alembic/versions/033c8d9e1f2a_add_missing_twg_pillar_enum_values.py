"""Add missing TWG pillar enum values

Revision ID: 033c8d9e1f2a
Revises: 022b7fbab1c5
Create Date: 2026-01-07 02:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '033c8d9e1f2a'
down_revision: Union[str, Sequence[str], None] = '022b7fbab1c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing enum values to twgpillar type."""
    # Get raw connection with autocommit to add enum values
    connection = op.get_bind()
    
    enum_values = [
        'energy_infrastructure',
        'agriculture_food_systems',
        'critical_minerals_industrialization',
        'digital_economy_transformation',
        'protocol_logistics',
        'resource_mobilization'
    ]
    
    if connection.dialect.name == "postgresql":
        for value in enum_values:
            # Check if value exists
            result = connection.execute(text("""
                SELECT COUNT(*) FROM pg_enum 
                WHERE enumlabel = :value 
                AND enumtypid = 'twgpillar'::regtype
            """), {"value": value})
            
            if result.scalar() == 0:
                # Commit current transaction before ALTER TYPE
                connection.execute(text("COMMIT"))
                # Add the enum value
                connection.execute(text(f"ALTER TYPE twgpillar ADD VALUE '{value}'"))


def downgrade() -> None:
    """Downgrade not supported for enum values."""
    pass
