import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine

async def migrate():
    print("🔧 Migrating documents.file_type column...")
    async with engine.connect() as conn:
        try:
            # Alter the column type
            await conn.execute(text("ALTER TABLE documents ALTER COLUMN file_type TYPE VARCHAR(255)"))
            await conn.commit()
            print("✅ Migration complete: file_type is now VARCHAR(255)")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await conn.rollback()

if __name__ == "__main__":
    asyncio.run(migrate())
