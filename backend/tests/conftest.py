import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, engine, Base
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.utils.security import create_access_token
from app.models.models import User, UserRole
import uuid



@pytest.fixture(scope="session")
async def db_engine():
    """Create a database engine for the session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for a single test."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing API endpoints."""
    from app.core.database import get_db
    
    # Override get_db dependency
    async def override_get_db():
        return db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a normal user for testing."""
    # Use random email to avoid uniqueness constraint violations
    email = f"test_normal_{uuid.uuid4()}@ecowas.int"
    user = User(
        email=email,
        hashed_password="hashed_secret",
        full_name="Test Normal",
        role=UserRole.TWG_MEMBER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user for testing."""
    email = f"test_admin_{uuid.uuid4()}@ecowas.int"
    user = User(
        email=email,
        hashed_password="hashed_secret",
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
def normal_user_token_headers(test_user):
    """Return headers with access token for normal user."""
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def admin_token_headers(admin_user):
    """Return headers with access token for admin user."""
    access_token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {access_token}"}
