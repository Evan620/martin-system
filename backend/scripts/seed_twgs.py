#!/usr/bin/env python3
"""
Seed script to create default TWGs in the database
"""
import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import TWG, TWGPillar

async def seed_twgs():
    """Create default TWGs if they don't exist"""

    twgs_to_create = [
        {
            "name": "Energy Trade and Industrial Growth",
            "pillar": TWGPillar.energy_infrastructure,
            "status": "active",
            "group_type": "twg"
        },
        {
            "name": "Agribusiness and Food Systems Transformation",
            "pillar": TWGPillar.agriculture_food_systems,
            "status": "active",
            "group_type": "twg"
        },
        {
            "name": "Strategic Minerals and Natural Resource Development",
            "pillar": TWGPillar.critical_minerals_industrialization,
            "status": "active",
            "group_type": "twg"
        },
        {
            "name": "Digital Transformation",
            "pillar": TWGPillar.digital_economy_transformation,
            "status": "active",
            "group_type": "twg"
        },
        {
            "name": "Protocol & Logistics TWG",
            "pillar": TWGPillar.protocol_logistics,
            "status": "active",
            "group_type": "twg"
        },
        {
            "name": "Resource Mobilization TWG",
            "pillar": TWGPillar.resource_mobilization,
            "status": "active",
            "group_type": "twg"
        },
        {
            "name": "TWG Leads Council",
            "pillar": TWGPillar.protocol_logistics,
            "status": "active",
            "group_type": "leads_council"
        }
    ]

    async with AsyncSessionLocal() as db:
        print("Checking existing TWGs...")

        result = await db.execute(select(TWG))
        existing_twgs = result.scalars().all()

        if existing_twgs:
            print(f"Found {len(existing_twgs)} existing TWGs:")
            for twg in existing_twgs:
                print(f"  - {twg.name} ({twg.pillar}) [type: {getattr(twg, 'group_type', 'twg')}]")
            
            # Check if Leads Council exists, create if missing
            has_leads = any(getattr(t, 'group_type', 'twg') == 'leads_council' for t in existing_twgs)
            if not has_leads:
                print("\n⚠️  TWG Leads Council not found. Creating...")
                leads_data = twgs_to_create[-1]  # Last entry
                twg = TWG(**leads_data)
                db.add(twg)
                await db.commit()
                print(f"  ✓ Created: {leads_data['name']}")
            else:
                print("\n✅ TWG Leads Council already exists.")
            return

        print("No TWGs found. Creating default TWGs...")

        for twg_data in twgs_to_create:
            twg = TWG(**twg_data)
            db.add(twg)
            print(f"  ✓ Created: {twg_data['name']}")

        await db.commit()
        print(f"\n✅ Successfully created {len(twgs_to_create)} TWGs!")

if __name__ == "__main__":
    print("=" * 60)
    print("TWG Seed Script")
    print("=" * 60)

    try:
        asyncio.run(seed_twgs())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("=" * 60)
    print("Done!")
