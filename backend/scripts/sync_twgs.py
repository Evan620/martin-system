import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from app.core.database import AsyncSessionLocal, engine
from app.models.models import TWG, TWGPillar, Project, Meeting, ActionItem, Document, Agenda, Minutes

OFFICIAL_TWGS = [
    {
        "name": "Energy & Infrastructure",
        "pillar": TWGPillar.energy_infrastructure,
        "status": "active"
    },
    {
        "name": "Agriculture & Food Systems",
        "pillar": TWGPillar.agriculture_food_systems,
        "status": "active"
    },
    {
        "name": "Critical Minerals & Industrialization",
        "pillar": TWGPillar.critical_minerals_industrialization,
        "status": "active"
    },
    {
        "name": "Digital Economy & Transformation",
        "pillar": TWGPillar.digital_economy_transformation,
        "status": "active"
    },
    {
        "name": "Protocol & Logistics",
        "pillar": TWGPillar.protocol_logistics,
        "status": "active"
    },
    {
        "name": "Resource Mobilization",
        "pillar": TWGPillar.resource_mobilization,
        "status": "active"
    }
]

async def sync_twgs():
    print("🚀 Starting TWG Synchronization...")
    async with AsyncSessionLocal() as db:
        try:
            # 1. Purge existing dependent records
            print("Cleaning up dependent records...")
            await db.execute(delete(ActionItem))
            await db.execute(delete(Agenda))
            await db.execute(delete(Minutes))
            await db.execute(delete(Meeting))
            await db.execute(delete(Project))
            await db.execute(delete(Document))
            
            # 2. Purge existing TWGs
            print("Purging old TWG records...")
            await db.execute(delete(TWG))
            await db.commit()
            
            # 3. Seed official TWGs
            print("Seeding 6 official Summit Pillars...")
            for twg_data in OFFICIAL_TWGS:
                data = twg_data.copy()
                data['pillar'] = data['pillar'].value
                db_twg = TWG(**data)
                db.add(db_twg)
                print(f"  + Added: {twg_data['name']}")
            
            await db.commit()
            print("\n✅ TWG Synchronization Complete!")
            print("The following pillars are now official:")
            for t in OFFICIAL_TWGS:
                print(f"  - {t['name']} ({t['pillar']})")
                
        except Exception as e:
            print(f"❌ Error during synchronization: {e}")
            await db.rollback()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(sync_twgs())
