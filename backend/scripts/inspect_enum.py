import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine

async def inspect_enum():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'twgpillar'"))
        labels = [row[0] for row in result]
        print(f"Current twgpillar labels: {labels}")

if __name__ == "__main__":
    asyncio.run(inspect_enum())
