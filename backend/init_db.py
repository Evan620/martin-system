"""
Database Initialization Script

Creates all database tables defined in the models.
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, Base
from app.models.models import (
    User, TWG, Meeting, Agenda, Minutes, ActionItem,
    Project, Document, RefreshToken, AuditLog
)

async def init_db():
    """Initialize the database by creating all tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Drop all tables (use with caution in production!)
        # await conn.run_sync(Base.metadata.drop_all)

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Database tables created successfully!")

    # Close the engine
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
