import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import AsyncSessionLocal, engine, Base
from typing import AsyncGenerator
from httpx import AsyncClient
from backend.app.main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    """Create a database engine for the session."""
    async with engine.begin() as conn:
        # For testing purposes, we might want to recreate the schema
        # In production tests, you'd use a separate test DB
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Optional: cleanup
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for a single test."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback() # Rollback to keep tests isolated

@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing API endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
