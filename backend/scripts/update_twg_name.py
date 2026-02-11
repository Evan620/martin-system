#!/usr/bin/env python3
"""
One-time script to rename the Agriculture TWG in production
"""
import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import TWG, TWGPillar

async def update_twg_name():
    async with AsyncSessionLocal() as db:
        print("Finding Agriculture/Agribusiness TWG...")
        
        # Find the TWG by its immutable enum pillar
        result = await db.execute(
            select(TWG).where(TWG.pillar == TWGPillar.agriculture_food_systems)
        )
        twg = result.scalar_one_or_none()
        
        if not twg:
            print("❌ Agribusiness TWG not found in database!")
            return

        print(f"Current name in DB: {twg.name}")
        
        target_name = "Agribusiness and Food Systems Transformation"
        
        if twg.name == target_name:
            print("✅ Name is already up to date.")
        else:
            twg.name = target_name
            await db.commit()
            print(f"✅ Successfully updated name to: {target_name}")

if __name__ == "__main__":
    try:
        asyncio.run(update_twg_name())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
