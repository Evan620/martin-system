"""Member deal-room tools: list_my_deals + enriched get_project_brief.

Modeled on tests/test_member_tools.py — same _session_factory monkeypatch, same
unique-suffix fixtures (the test DB is shared, so counts are asserted against
ground truth computed through the SAME session the tool uses).

Scope contract (mirrors get_project_brief / GET /pipeline/member exactly):
TWG link OR TWG-pillar match, ARCHIVED excluded, no cross-TWG leakage.
"""
import json
import uuid
from collections import Counter
from decimal import Decimal

import pytest
from sqlalchemy import or_, select

from app.models.models import (
    Project,
    ProjectScoreDetail,
    ProjectStatus,
    ProjectStatusHistory,
    ScoringCriteria,
    TWG,
    TWGPillar,
    User,
    UserRole,
)


def _session_factory(session):
    """Zero-arg callable usable as `async with AsyncSessionLocal() as s` that
    yields the test's transactional session without closing it."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield session

    return _factory


def _hum(raw: str) -> str:
    """Humanize a stage value the same way the tool does: 'SUMMIT_READY' → 'Summit ready'."""
    return raw.replace("_", " ").strip().capitalize()


async def _scope_projects(db_session, twg):
    """Ground truth: the member-visible scope (TWG link OR pillar, ARCHIVED excluded),
    computed through the SAME session the tool will use — robust to pre-existing rows."""
    pillar_value = twg.pillar.value
    return (
        await db_session.execute(
            select(Project).where(
                or_(Project.twg_id == twg.id, Project.pillar == pillar_value),
                Project.status != ProjectStatus.ARCHIVED,
            )
        )
    ).scalars().all()


async def _make_deal_room(db_session):
    """Two TWGs; caller scoped to TWG A (energy).

    Visible to the caller: own (TWG A link), own2 (TWG A link), mislinked
    (TWG B link but energy pillar — the prod twg-links-mis-assigned reality).
    NOT visible: cross (TWG B link, digital pillar), archived (TWG A, ARCHIVED).

    Names carry a '000-' prefix so they sort FIRST in the name-ordered row list
    even when the shared test DB already contains other in-pillar projects.
    """
    suffix = uuid.uuid4().hex[:8]
    twg_a = TWG(id=uuid.uuid4(), name=f"Deals Energy {suffix}", pillar=TWGPillar.energy_infrastructure)
    twg_b = TWG(id=uuid.uuid4(), name=f"Deals Digital {suffix}", pillar=TWGPillar.digital_economy_transformation)
    own = Project(
        id=uuid.uuid4(),
        twg_id=twg_a.id,
        name=f"000-{suffix} Bagre Solar Plant",
        description="A 50MW grid-connected solar PV plant near Bagre.",
        investment_size=Decimal("25000000.00"),
        currency="USD",
        status=ProjectStatus.SUMMIT_READY,
        pillar=TWGPillar.energy_infrastructure.value,
        lead_country="Burkina Faso",
        readiness_score=72.5,
        afcen_score=Decimal("81.25"),
    )
    own2 = Project(
        id=uuid.uuid4(),
        twg_id=twg_a.id,
        name=f"000-{suffix} Kandadji Hydro",
        description="Run-of-river hydro expansion serving Niger's grid.",
        investment_size=Decimal("60000000.00"),
        currency="USD",
        status=ProjectStatus.PIPELINE,
        pillar=TWGPillar.energy_infrastructure.value,
        lead_country="Niger",
        readiness_score=40.0,
    )
    mislinked = Project(
        id=uuid.uuid4(),
        twg_id=twg_b.id,  # WRONG twg link (prod data reality) ...
        name=f"000-{suffix} Mislinked Wind Farm",
        description="Wind farm mis-linked to another TWG row but in the caller's pillar.",
        investment_size=Decimal("12000000.00"),
        currency="USD",
        status=ProjectStatus.PIPELINE,
        pillar=TWGPillar.energy_infrastructure.value,  # ... but caller's pillar
        lead_country="Mali",
        readiness_score=51.0,
    )
    cross = Project(
        id=uuid.uuid4(),
        twg_id=twg_b.id,
        name=f"000-{suffix} Cross Fibre Backbone",
        description="A cross-border fibre project in another TWG.",
        investment_size=Decimal("9000000.00"),
        currency="USD",
        status=ProjectStatus.PIPELINE,
        pillar=TWGPillar.digital_economy_transformation.value,
        lead_country="Ghana",
        readiness_score=40.0,
    )
    archived = Project(
        id=uuid.uuid4(),
        twg_id=twg_a.id,
        name=f"000-{suffix} Archived Coal Retrofit",
        description="An archived project that must never be listed.",
        investment_size=Decimal("5000000.00"),
        currency="USD",
        status=ProjectStatus.ARCHIVED,
        pillar=TWGPillar.energy_infrastructure.value,
        lead_country="Togo",
        readiness_score=10.0,
    )
    db_session.add_all([twg_a, twg_b, own, own2, mislinked, cross, archived])
    await db_session.flush()
    return {
        "twg_a": twg_a, "twg_b": twg_b,
        "own": own, "own2": own2, "mislinked": mislinked,
        "cross": cross, "archived": archived, "suffix": suffix,
    }


# ---------------------------------------------------------------------------
# list_my_deals — scope, counts, exclusions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_my_deals_counts_and_scope(db_session, monkeypatch):
    """Totals + per-stage counts match the member scope ground truth; rows show
    own-TWG and pillar-matched deals with stage/sector/value/score/location."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    in_scope = await _scope_projects(db_session, data["twg_a"])
    expected_total = len(in_scope)
    expected_counts = Counter(_hum(p.status.value) for p in in_scope)

    result = await member_tools.list_my_deals(
        limit=30,
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    assert result["total"] == expected_total

    text = result["deals"]
    assert f"{expected_total} project" in text
    for stage_label, n in expected_counts.items():
        assert f"{stage_label}: {n}" in text, f"missing stage count '{stage_label}: {n}' in:\n{text}"

    # Rows: own-TWG + pillar-matched deals are listed ('000-' prefix sorts first)
    assert data["own"].name in text
    assert data["own2"].name in text
    assert data["mislinked"].name in text
    # Row facts for the summit-ready deal: stage, sector, value, score (afcen), location
    assert "Summit ready" in text
    assert "Energy infrastructure" in text
    assert "USD 25,000,000" in text
    assert "81.25" in text  # afcen_score preferred over readiness
    assert "Burkina Faso" in text


@pytest.mark.asyncio
async def test_list_my_deals_excludes_archived_and_cross_twg(db_session, monkeypatch):
    """ARCHIVED and cross-TWG (other pillar) projects never appear — names absent
    from the entire payload, and the total does not count them."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    in_scope = await _scope_projects(db_session, data["twg_a"])

    result = await member_tools.list_my_deals(
        limit=30,
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    dumped = json.dumps(result)
    assert data["cross"].name not in dumped
    assert data["archived"].name not in dumped
    assert result["total"] == len(in_scope)
    scope_ids = {p.id for p in in_scope}
    assert data["cross"].id not in scope_ids and data["archived"].id not in scope_ids


@pytest.mark.asyncio
async def test_list_my_deals_stage_filter_fuzzy(db_session, monkeypatch):
    """A fuzzy stage filter ('summit ready', 'Summit-Ready') returns only that
    stage's rows while still reporting the full scope total."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    in_scope = await _scope_projects(db_session, data["twg_a"])
    expected_total = len(in_scope)
    expected_matched = sum(1 for p in in_scope if p.status == ProjectStatus.SUMMIT_READY)

    for spelling in ("summit ready", "Summit-Ready"):
        result = await member_tools.list_my_deals(
            stage=spelling,
            limit=30,
            twg_id=str(data["twg_a"].id),
            user_id=str(uuid.uuid4()),
            user_role=UserRole.TWG_MEMBER,
        )
        assert result.get("success") is True, f"unexpected result for '{spelling}': {result}"
        assert result["total"] == expected_total
        assert result["matched"] == expected_matched
        text = result["deals"]
        assert data["own"].name in text          # SUMMIT_READY → listed
        assert data["own2"].name not in text     # PIPELINE → filtered out of rows
        assert data["mislinked"].name not in text


@pytest.mark.asyncio
async def test_list_my_deals_unknown_stage_errors(db_session, monkeypatch):
    """An unrecognisable stage returns a friendly error, not a crash/empty list."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    result = await member_tools.list_my_deals(
        stage="zzz totally unknown stage",
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_list_my_deals_limit_caps_rows(db_session, monkeypatch):
    """limit=1 lists exactly one numbered row and signals there are more."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    result = await member_tools.list_my_deals(
        limit=1,
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    text = result["deals"]
    assert "\n1. " in text
    assert "\n2. " not in text
    assert "more" in text  # "+K more" hint


@pytest.mark.asyncio
async def test_list_my_deals_requires_twg_scope(db_session, monkeypatch):
    """Without an injected twg_id the tool refuses (per-request member binding)."""
    import app.tools.member_tools as member_tools

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.list_my_deals(
        twg_id=None,
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_list_my_deals_output_stays_under_tool_cap(db_session, monkeypatch):
    """The full payload stays comfortably under the 3000-char agent-loop cap."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    result = await member_tools.list_my_deals(
        limit=30,
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True
    assert len(json.dumps(result)) < 3000


# ---------------------------------------------------------------------------
# get_project_brief — enriched member-safe fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_project_brief_shows_new_fields_when_populated(db_session, monkeypatch):
    """Populated member-safe extras appear; long text fields are truncated to one line."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    p = data["own"]
    long_climate = (
        "Avoids an estimated 1.2 MtCO2e over the project lifetime through displacement "
        "of diesel generation, with additional resilience benefits for irrigation "
        "schemes downstream of the Bagre dam and significant co-benefits for local "
        "air quality, soil health, and household energy affordability across the region."
    )
    assert len(long_climate) > 200
    p.subsector = "Utility-scale solar PV"
    p.investment_stage_label = "Investment-ready"
    p.project_sponsor = "Societe Bagre Energies"
    p.financing_structure = "70/30 debt-equity with DFI senior debt"
    p.climate_impact = long_climate
    p.smallholder_farmers_reached = "12,000 farmers via irrigation offtake"
    p.technical_studies = "Feasibility complete (2025); ESIA underway"
    await db_session.flush()

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.get_project_brief(
        project=str(p.id),
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    brief = result["brief"]
    assert "Utility-scale solar PV" in brief
    assert "Investment-ready" in brief
    assert "Societe Bagre Energies" in brief
    assert "70/30 debt-equity with DFI senior debt" in brief
    assert "Avoids an estimated 1.2 MtCO2e" in brief
    assert "12,000 farmers via irrigation offtake" in brief
    assert "Feasibility complete (2025); ESIA underway" in brief
    # Long climate text is truncated (~200 chars), so its tail never appears.
    assert "household energy affordability" not in brief
    assert len(brief) < 2800


@pytest.mark.asyncio
async def test_get_project_brief_omits_empty_fields(db_session, monkeypatch):
    """Unpopulated extras produce NO empty labels in the brief."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    result = await member_tools.get_project_brief(
        project=str(data["own2"].id),  # has none of the extras populated
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    brief = result["brief"]
    for label in (
        "Subsector:", "Investment stage:", "Sponsor:", "Financing structure:",
        "Climate impact:", "Smallholder farmers reached:", "Technical studies:",
        "Score breakdown",
    ):
        assert label not in brief, f"empty field '{label}' leaked into brief:\n{brief}"


async def _score_project(db_session, data):
    """Attach two scored criteria (with facilitator-only notes + scorer) to 'own'."""
    suffix = data["suffix"]
    scorer = User(
        id=uuid.uuid4(),
        full_name="LEAK SCORER NAME",
        email=f"scorer-{suffix}@example.org",
        hashed_password="x",
        role=UserRole.ADMIN,
    )
    c1 = ScoringCriteria(
        id=uuid.uuid4(), criterion_name=f"Readiness {suffix}",
        criterion_type="readiness", weight=Decimal("0.20"),
    )
    c2 = ScoringCriteria(
        id=uuid.uuid4(), criterion_name=f"Bankability {suffix}",
        criterion_type="bankability", weight=Decimal("0.18"),
    )
    # Flush criteria + scorer FIRST: ProjectScoreDetail has no relationship()
    # to ScoringCriteria, so the unit of work can't order these inserts itself.
    db_session.add_all([scorer, c1, c2])
    await db_session.flush()
    d1 = ProjectScoreDetail(
        id=uuid.uuid4(), project_id=data["own"].id, criterion_id=c1.id,
        score=Decimal("60.00"), scored_by_id=scorer.id, notes="LEAK-SCORE-NOTES",
    )
    d2 = ProjectScoreDetail(
        id=uuid.uuid4(), project_id=data["own"].id, criterion_id=c2.id,
        score=Decimal("75.00"), scored_by_id=scorer.id, notes="LEAK-SCORE-NOTES-2",
    )
    db_session.add_all([d1, d2])
    await db_session.flush()
    return {"scorer": scorer, "c1": c1, "c2": c2}


@pytest.mark.asyncio
async def test_get_project_brief_include_scores_without_notes(db_session, monkeypatch):
    """include_scores=True prints 'Criterion (weight%): score' rows, weight desc —
    NEVER the scorer's notes or identity. Default call prints no breakdown."""
    import app.tools.member_tools as member_tools

    data = await _make_deal_room(db_session)
    scored = await _score_project(db_session, data)
    suffix = data["suffix"]
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    # Default: no breakdown.
    plain = await member_tools.get_project_brief(
        project=str(data["own"].id),
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert plain.get("success") is True
    assert "Score breakdown" not in plain["brief"]
    assert f"Readiness {suffix}" not in plain["brief"]

    # include_scores: criterion (weight%) and score, ordered by weight desc.
    result = await member_tools.get_project_brief(
        project=str(data["own"].id),
        twg_id=str(data["twg_a"].id),
        include_scores=True,
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    brief = result["brief"]
    assert "Score breakdown" in brief
    assert f"Readiness {suffix} (20%): 60" in brief
    assert f"Bankability {suffix} (18%): 75" in brief
    assert brief.index(f"Readiness {suffix} (20%)") < brief.index(f"Bankability {suffix} (18%)")
    dumped = json.dumps(result)
    assert "LEAK-SCORE-NOTES" not in dumped
    assert scored["scorer"].full_name not in dumped
    assert len(brief) < 2800


# ---------------------------------------------------------------------------
# Hard non-exposure contract — facilitator-only fields NEVER reach members
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_member_deal_tools_never_expose_forbidden_fields(db_session, monkeypatch):
    """Contract: key contacts, assigned_agent, metadata_json, approval fields,
    deal_room_priority, site coords, revenue_model, macroeconomic_roi,
    funding_secured_usd, score notes/scorer and status-history notes are ABSENT
    from BOTH list_my_deals and get_project_brief(include_scores=True) output."""
    import app.tools.member_tools as member_tools
    from datetime import datetime

    data = await _make_deal_room(db_session)
    await _score_project(db_session, data)
    p = data["own"]

    approver = User(
        id=uuid.uuid4(),
        full_name="LEAK APPROVER NAME",
        email=f"approver-{data['suffix']}@example.org",
        hashed_password="x",
        role=UserRole.ADMIN,
    )
    db_session.add(approver)
    await db_session.flush()

    p.key_contact_name = "LEAK-CONTACT-NAME"
    p.key_contact_email = "leak-contact@secret.example"
    p.assigned_agent = "LEAK-ASSIGNED-AGENT"
    p.metadata_json = {"internal": "LEAK-METADATA-VALUE"}
    p.approved_by_id = approver.id
    p.approval_date = datetime(2026, 1, 2, 3, 4, 5)
    p.deal_room_priority = 7
    p.site_lat = 11.1111
    p.site_lon = 22.2222
    p.revenue_model = "LEAK-REVENUE-MODEL"
    p.macroeconomic_roi = "LEAK-MACRO-ROI"
    p.funding_secured_usd = Decimal("4242424.00")
    history = ProjectStatusHistory(
        id=uuid.uuid4(),
        project_id=p.id,
        previous_status=ProjectStatus.PIPELINE,
        new_status=ProjectStatus.SUMMIT_READY,
        changed_by_id=approver.id,
        notes="LEAK-HISTORY-NOTES",
    )
    db_session.add(history)
    await db_session.flush()

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    common = dict(
        twg_id=str(data["twg_a"].id),
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    brief = await member_tools.get_project_brief(
        project=str(p.id), include_scores=True, **common
    )
    listing = await member_tools.list_my_deals(limit=30, **common)
    assert brief.get("success") is True, f"unexpected result: {brief}"
    assert listing.get("success") is True, f"unexpected result: {listing}"

    dumped = json.dumps(brief) + json.dumps(listing)
    for marker in (
        "LEAK-CONTACT-NAME", "leak-contact@secret.example", "LEAK-ASSIGNED-AGENT",
        "LEAK-METADATA-VALUE", "LEAK APPROVER NAME", "2026-01-02",
        "11.1111", "22.2222", "LEAK-REVENUE-MODEL", "LEAK-MACRO-ROI",
        "4242424", "4,242,424", "LEAK-SCORE-NOTES", "LEAK SCORER NAME",
        "LEAK-HISTORY-NOTES", "priority",
    ):
        assert marker not in dumped, f"forbidden field value '{marker}' leaked to member output"


# ---------------------------------------------------------------------------
# Registry contract — allowlisted, registered, TWG-gated
# ---------------------------------------------------------------------------

def test_list_my_deals_in_member_allowlist_and_registered():
    """list_my_deals is in MEMBER_TOOLS, TWG-scoped, registered (lookup succeeds),
    granted to the member agent WITH a twg scope and denied without one —
    exactly like get_project_brief."""
    from app.tools.tool_registry import (
        ToolRegistry,
        ToolAccessDenied,
        MEMBER_TOOLS,
        TWG_SCOPED_TOOLS,
    )

    assert "list_my_deals" in MEMBER_TOOLS
    assert "list_my_deals" in TWG_SCOPED_TOOLS

    reg = ToolRegistry()
    reg.register_all()
    twg = str(uuid.uuid4())

    assert "list_my_deals" in reg.list_tools()
    info = reg.get_tool_info("list_my_deals")
    assert info is not None and info["name"] == "list_my_deals"
    assert reg.validate_tool_access("list_my_deals", "member", twg_id=twg) is True
    with pytest.raises(ToolAccessDenied):
        reg.validate_tool_access("list_my_deals", "member", twg_id=None)

    _defs, tool_map = reg.get_tools_for_agent("member", twg_id=twg)
    assert "list_my_deals" in tool_map
