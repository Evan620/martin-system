import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from backend.app.models.models import User, TWG, Meeting, TWGPillar, UserRole, MeetingStatus

@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test creating a user."""
    user = User(
        full_name="John Doe",
        email=f"john.doe.{uuid.uuid4()}@example.com",
        role=UserRole.TWG_FACILITATOR
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.id is not None
    assert user.full_name == "John Doe"
    
    # Verify in DB
    result = await db_session.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.email == user.email

@pytest.mark.asyncio
async def test_create_twg_and_meeting(db_session):
    """Test creating a TWG and a meeting associated with it."""
    # 1. Create a lead user
    lead = User(
        full_name="Lead Expert",
        email=f"lead.{uuid.uuid4()}@ecowas.int",
        role=UserRole.SECRETARIAT_LEAD
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)

    # 2. Create a TWG
    twg = TWG(
        name="Energy Integration TWG",
        pillar=TWGPillar.ENERGY,
        technical_lead_id=lead.id
    )
    db_session.add(twg)
    await db_session.commit()
    await db_session.refresh(twg)

    assert twg.id is not None
    assert twg.technical_lead_id == lead.id

    # 3. Create a Meeting
    meeting = Meeting(
        twg_id=twg.id,
        title="Inaugural Energy Strategy Session",
        scheduled_at=datetime.utcnow() + timedelta(days=7),
        duration_minutes=90,
        status=MeetingStatus.SCHEDULED
    )
    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)

    assert meeting.id is not None
    assert meeting.twg_id == twg.id
    
    # 4. Check Relationship
    result = await db_session.execute(select(TWG).where(TWG.id == twg.id))
    db_twg = result.scalar_one_or_none()
    assert len(db_twg.meetings) >= 1
    assert db_twg.meetings[0].title == "Inaugural Energy Strategy Session"
