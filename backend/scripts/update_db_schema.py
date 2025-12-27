import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine

NEW_PILLARS = [
    "energy_infrastructure",
    "agriculture_food_systems",
    "critical_minerals_industrialization",
    "digital_economy_transformation",
    "protocol_logistics",
    "resource_mobilization"
]

async def update_enum():
    print("🛠️ Updating database enum type 'twgpillar'...")
    async with engine.connect() as conn:
        for pillar in NEW_PILLARS:
            try:
                # PostgreSQL command to add a value to an existing enum
                # We use text() to wrap the SQL command.
                # COMMIT is needed between ALTER TYPE calls if multiple are made in some environments,
                # but here engine handles it or we can do it one by one.
                print(f"  Adding '{pillar}'...")
                # Note: ALTER TYPE ... ADD VALUE cannot run inside a transaction block in some PG versions.
                # However, asyncpg/sqlalchemy usually handles this. If it fails, we might need a different approach.
                await conn.execute(text(f"ALTER TYPE twgpillar ADD VALUE IF NOT EXISTS '{pillar}'"))
                await conn.commit()
            except Exception as e:
                print(f"  ⚠️ Could not add '{pillar}': {e}")
                await conn.rollback()

    print("✅ Enum update attempt complete.")

if __name__ == "__main__":
    asyncio.run(update_enum())
