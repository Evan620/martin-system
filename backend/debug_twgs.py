import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.models import TWG
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(TWG))
        twgs = res.scalars().all()
        for t in twgs:
            print(f'NAME: [{t.name}] PILLAR: [{t.pillar}]')

if __name__ == "__main__":
    asyncio.run(check())
