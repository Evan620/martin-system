import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, engine, Base
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.utils.security import create_access_token
from app.models.models import (
    User, UserRole, TWG, TWGPillar, Meeting, MeetingStatus,
    Minutes, MinutesStatus, ActionItem, ActionItemStatus, ActionItemPriority,
    Document, Project, ProjectStatus,
)
import uuid



@pytest.fixture
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


# =============================================================================
# Seed Data Fixtures (module-scoped, committed to real DB for tool tests)
# =============================================================================

# Mapping of pillar short names to TWGPillar enum values
PILLAR_MAP = {
    "energy": TWGPillar.energy_infrastructure,
    "agriculture": TWGPillar.agriculture_food_systems,
    "minerals": TWGPillar.critical_minerals_industrialization,
    "digital": TWGPillar.digital_economy_transformation,
    "protocol": TWGPillar.protocol_logistics,
    "resource_mobilization": TWGPillar.resource_mobilization,
}


def _cleanup_seed_data_sync():
    """Delete all seed data using sync engine (idempotent, no event loop issues)."""
    from sqlalchemy import text as sa_text
    from app.core.database import SyncSessionLocal
    session = SyncSessionLocal()
    try:
        session.execute(sa_text(
            "DELETE FROM minutes WHERE meeting_id IN "
            "(SELECT id FROM meetings WHERE title LIKE '%Sync' OR title LIKE '%Review Session' OR title LIKE '%Test Booking%')"
        ))
        session.execute(sa_text("DELETE FROM action_items WHERE description LIKE '%task for testing%'"))
        session.execute(sa_text(
            "DELETE FROM documents WHERE file_name LIKE '%_policy_v1.pdf' OR file_name LIKE '%_brief_v1.pdf'"
        ))
        session.execute(sa_text(
            "DELETE FROM projects WHERE name IN ('West Africa Solar Farm','Sahel Wind Energy','ECOWAS Grid Interconnection')"
        ))
        session.execute(sa_text(
            "DELETE FROM meetings WHERE title LIKE '%Sync' OR title LIKE '%Review Session' "
            "OR title LIKE '%Test Booking%' OR title LIKE '%Updated%' OR title LIKE '%Ag TWG%'"
        ))
        session.execute(sa_text("DELETE FROM twg_members WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'seed_%')"))
        session.execute(sa_text("DELETE FROM users WHERE email LIKE 'seed_%'"))
        session.execute(sa_text(
            "DELETE FROM twgs WHERE name IN "
            "('Energy TWG','Agriculture TWG','Minerals TWG','Digital TWG',"
            "'Protocol TWG','Resource Mobilization TWG')"
        ))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture(scope="module")
def seed_db():
    """
    Module-scoped SYNC fixture that seeds the database with comprehensive test data.
    Uses the sync engine to avoid asyncpg event loop mismatch issues.
    Returns a dict of all created object IDs for use in tests.
    """
    from sqlalchemy import text, select as sa_select
    from app.core.database import SyncSessionLocal, sync_engine

    # Ensure tables exist (sync)
    Base.metadata.create_all(sync_engine)

    # Clean up any leftover data from previous runs
    _cleanup_seed_data_sync()

    ids = {
        "twgs": {},         # pillar_name -> TWG id
        "users": {},        # role_key -> User id
        "meetings": {},     # key -> Meeting id
        "minutes": {},      # key -> Minutes id
        "action_items": {}, # key -> ActionItem id
        "documents": {},    # key -> Document id
        "projects": {},     # key -> Project id
    }

    session = SyncSessionLocal()
    try:
        # --- 1. Create admin user ---
        admin = User(
            email="seed_admin@ecowas.int",
            hashed_password="hashed_secret",
            full_name="Seed Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        session.flush()
        ids["users"]["admin"] = admin.id

        # --- 2. Create 6 TWGs ---
        twg_objects = {}
        for short_name, pillar in PILLAR_MAP.items():
            twg = TWG(
                name=f"{short_name.replace('_', ' ').title()} TWG",
                pillar=pillar,
                status="active",
            )
            session.add(twg)
            session.flush()
            ids["twgs"][short_name] = twg.id
            twg_objects[short_name] = twg

        # --- 3. Create 6 TWG member users (one per TWG) ---
        for short_name, twg in twg_objects.items():
            member = User(
                email=f"seed_{short_name}@ecowas.int",
                hashed_password="hashed_secret",
                full_name=f"Seed {short_name.replace('_', ' ').title()} Member",
                role=UserRole.TWG_MEMBER,
                is_active=True,
            )
            session.add(member)
            session.flush()
            ids["users"][short_name] = member.id
            # Associate member with TWG via the association table
            session.execute(
                text("INSERT INTO twg_members (twg_id, user_id) VALUES (:twg_id, :user_id)"),
                {"twg_id": str(twg.id), "user_id": str(member.id)},
            )

        # --- 4. Create meetings (1 future + 1 past per TWG) ---
        now = datetime.utcnow()
        for short_name, twg_id in ids["twgs"].items():
            # Future meeting
            future = Meeting(
                twg_id=twg_id,
                title=f"{short_name.title()} Weekly Sync",
                scheduled_at=now + timedelta(days=3),
                duration_minutes=60,
                location="Virtual (Google Meet)",
                status=MeetingStatus.SCHEDULED,
                meeting_type="virtual",
            )
            session.add(future)
            session.flush()
            ids["meetings"][f"{short_name}_future"] = future.id

            # Past meeting
            past = Meeting(
                twg_id=twg_id,
                title=f"{short_name.title()} Review Session",
                scheduled_at=now - timedelta(days=5),
                duration_minutes=90,
                location="Conference Room A",
                status=MeetingStatus.COMPLETED,
                meeting_type="in-person",
            )
            session.add(past)
            session.flush()
            ids["meetings"][f"{short_name}_past"] = past.id

        # --- 5. Create minutes for 3 past meetings ---
        for short_name in ["energy", "agriculture", "minerals"]:
            meeting_id = ids["meetings"][f"{short_name}_past"]
            mins = Minutes(
                meeting_id=meeting_id,
                content=f"# {short_name.title()} Review Minutes\n\n- Discussed progress\n- Reviewed action items",
                key_decisions=f"Approved {short_name} framework draft",
                status=MinutesStatus.APPROVED,
            )
            session.add(mins)
            session.flush()
            ids["minutes"][short_name] = mins.id

        # --- 6. Create action items (2 per TWG: PENDING + IN_PROGRESS) ---
        for short_name, twg_id in ids["twgs"].items():
            owner_id = ids["users"][short_name]
            for status, label in [
                (ActionItemStatus.PENDING, "pending"),
                (ActionItemStatus.IN_PROGRESS, "in_progress"),
            ]:
                ai = ActionItem(
                    twg_id=twg_id,
                    description=f"[{short_name}] {label} task for testing",
                    owner_id=owner_id,
                    due_date=now + timedelta(days=14),
                    status=status,
                    priority=ActionItemPriority.MEDIUM,
                )
                session.add(ai)
                session.flush()
                ids["action_items"][f"{short_name}_{label}"] = ai.id

        # --- 7. Create documents (2 per TWG: policy + brief) ---
        uploader_id = ids["users"]["admin"]
        for short_name, twg_id in ids["twgs"].items():
            for doc_type, label in [("policy", "Policy Framework"), ("brief", "Summary Brief")]:
                doc = Document(
                    twg_id=twg_id,
                    file_name=f"{short_name}_{doc_type}_v1.pdf",
                    file_path=f"/uploads/{short_name}_{doc_type}_v1.pdf",
                    file_type="application/pdf",
                    document_type=doc_type,
                    uploaded_by_id=uploader_id,
                    is_confidential=False,
                    category="twg_specific",
                )
                session.add(doc)
                session.flush()
                ids["documents"][f"{short_name}_{doc_type}"] = doc.id

        # --- 8. Create projects (3 for resource_mobilization, 1 flagship) ---
        rm_twg_id = ids["twgs"]["resource_mobilization"]
        for i, (name, size, flagship) in enumerate([
            ("West Africa Solar Farm", Decimal("50000000.00"), True),
            ("Sahel Wind Energy", Decimal("30000000.00"), False),
            ("ECOWAS Grid Interconnection", Decimal("120000000.00"), False),
        ]):
            proj = Project(
                twg_id=rm_twg_id,
                name=name,
                description=f"Test project: {name}",
                investment_size=size,
                currency="USD",
                readiness_score=7.5 if flagship else 5.0,
                afcen_score=Decimal("85.00") if flagship else Decimal("60.00"),
                status=ProjectStatus.PIPELINE,
                pillar="resource_mobilization",
                lead_country="Nigeria" if i == 0 else "Ghana",
                is_flagship=flagship,
            )
            session.add(proj)
            session.flush()
            ids["projects"][f"project_{i}"] = proj.id

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    yield ids

    # Teardown: best-effort cleanup
    try:
        _cleanup_seed_data_sync()
    except Exception:
        pass


@pytest.fixture(autouse=True)
async def reset_async_pool():
    """
    Dispose the async engine's connection pool before each test.
    This prevents asyncpg 'attached to a different loop' errors when
    pytest-asyncio creates a new event loop per test.
    """
    await engine.dispose()
    yield


@pytest.fixture
def fresh_registry():
    """Create a fresh ToolRegistry instance (bypasses singleton)."""
    from app.tools.tool_registry import ToolRegistry
    registry = ToolRegistry()
    registry.register_all()
    return registry
