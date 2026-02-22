
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
UTC = timezone.utc

from app.core.database import Base
from app.models.models import (
    Project, Investor, ProjectStatus, TWG, TWGPillar, 
    InvestorMatchStatus, User, UserRole, ProjectInvestorMatch
)
from app.services.project_pipeline_service import ProjectPipelineService
from app.services.investor_matching_service import InvestorMatchingService

# SQLite in-memory database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_afcen_scoring(db_session):
    service = ProjectPipelineService(db_session)
    
    # Test 1: Perfect Score
    score = service.calculate_afcen_score(10.0, 10.0, 10.0)
    assert score == Decimal("100.00")
    
    # Test 2: Zero Score
    score = service.calculate_afcen_score(0.0, 0.0, 0.0)
    assert score == Decimal("0.00")
    
    # Test 3: Mixed (4*0.4 + 6*0.3 + 5*0.3) = 1.6 + 1.8 + 1.5 = 4.9 -> 49.00
    score = service.calculate_afcen_score(4.0, 6.0, 5.0)
    assert score == Decimal("49.00")
    
    # Test 4: Default Regional Impact (5.0)
    # (8*0.4 + 8*0.3 + 5*0.3) = 3.2 + 2.4 + 1.5 = 7.1 -> 71.00
    score = service.calculate_afcen_score(8.0, 8.0)
    assert score == Decimal("71.00")

@pytest.mark.asyncio
async def test_project_ingestion(db_session):
    # Setup TWG
    twg = TWG(id=uuid4(), name="Test TWG", pillar=TWGPillar.energy_infrastructure)
    db_session.add(twg)
    await db_session.commit()
    
    service = ProjectPipelineService(db_session)
    
    data = {
        "twg_id": str(twg.id),
        "name": "Solar Farm Alpha",
        "description": "Big solar farm",
        "investment_size": Decimal("50000000.00"),
        "readiness_score": 8.5,
        "strategic_alignment_score": 9.0,
        "pillar": "Energy"
    }
    
    result = await service.ingest_project_proposal(data)
    
    project = result["project"]
    assert project.name == "Solar Farm Alpha"
    assert project.afcen_score is not None
    assert project.status == ProjectStatus.IDENTIFIED
    
    # Check score calculation:
    # (8.5*0.4) + (9.0*0.3) + (5.0*0.3) = 3.4 + 2.7 + 1.5 = 7.6 -> 76.00
    assert project.afcen_score == Decimal("76.00")

@pytest.mark.asyncio
async def test_investor_matching_logic(db_session):
    # Setup Data
    project = Project(
        id=uuid4(),
        twg_id=uuid4(), # Mock ID, FK check might fail if strict but sqlite memory handles it loosely usually or we need strict setup
        name="Wind Power Project",
        description="Wind farm",
        investment_size=Decimal("20000000.00"), # 20M
        currency="USD",
        readiness_score=8.0,
        status=ProjectStatus.IDENTIFIED,
        pillar="Energy",
        lead_country="Kenya"
    )
    
    # Investor 1: Perfect Match
    inv1 = Investor(
        id=uuid4(),
        name="Green Energy Fund",
        sector_preferences=["Energy", "Infrastructure"],
        ticket_size_min=Decimal("10000000.00"), # 10M
        ticket_size_max=Decimal("50000000.00"), # 50M
        geographic_focus=["Kenya", "East Africa"]
    )
    
    # Investor 2: No Match (Wrong Sector, Too Small)
    inv2 = Investor(
        id=uuid4(),
        name="Small Tech VC",
        sector_preferences=["Digital"],
        ticket_size_min=Decimal("100000.00"),
        ticket_size_max=Decimal("1000000.00"), # 1M
        geographic_focus=["Nigeria"]
    )
    
    # We need to bypass FK constraint for TWG since we didn't create it, 
    # but let's create it properly to be safe
    twg = TWG(id=project.twg_id, name="Energy TWG", pillar=TWGPillar.energy_infrastructure)
    db_session.add(twg)
    db_session.add(project)
    db_session.add(inv1)
    db_session.add(inv2)
    await db_session.commit()
    
    matching_service = InvestorMatchingService(db_session)
    result = await matching_service.match_investors(project.id)
    
    assert result["new_matches"] == 1
    
    matches = await matching_service.get_matches_for_project(project.id)
    assert len(matches) == 1
    
    match = matches[0]
    assert match["investor_name"] == "Green Energy Fund"
    # Score Check:
    # Sector: Energy matches Energy (40)
    # Size: 20M is in 10M-50M (40)
    # Geo: Kenya matches Kenya (20)
    # Total: 100.00
    assert match["score"] == 100.0

@pytest.mark.asyncio
async def test_protocol_agent_trigger(db_session):
    # Setup Protocol TWG
    proto_twg = TWG(
        id=uuid4(), 
        name="Protocol TWG", 
        pillar=TWGPillar.protocol_logistics,
        technical_lead_id=uuid4() # Mock User ID
    )
    db_session.add(proto_twg)
    
    # Setup Project & Investor & Match
    project = Project(
        id=uuid4(), twg_id=uuid4(), name="VIP Hotel", description="Luxury hotel project",
        investment_size=Decimal("10000000.00"), currency="USD", readiness_score=8.0, 
        status=ProjectStatus.IDENTIFIED
    )
    investor = Investor(id=uuid4(), name="Hilton Group")
    match = ProjectInvestorMatch(
        id=uuid4(),
        project_id=project.id,
        investor_id=investor.id,
        match_score=Decimal("90.00"),
        status=InvestorMatchStatus.CONTACTED
    )
    
    db_session.add(project)
    db_session.add(investor)
    db_session.add(match)
    await db_session.commit()
    
    matching_service = InvestorMatchingService(db_session)
    
    # Update Status to INTERESTED
    result = await matching_service.update_match_status(
        match_id=match.id,
        new_status=InvestorMatchStatus.INTERESTED,
        notes="They want a meeting next week"
    )
    
    # Verify Protocol Task Created
    assert result["protocol_task_id"] is not None
    
    # Check updated status
    assert result["match"].status == InvestorMatchStatus.INTERESTED
    assert "They want a meeting next week" in result["match"].notes
