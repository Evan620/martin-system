"""Deal Room — member-facing project DETAIL endpoint.

Covers:
- GET /api/v1/pipeline/member/{project_id} — ProjectMemberDetail: all
  ProjectMemberRead fields PLUS member-safe extras and a stripped
  score_breakdown (criterion/weight/score only, weight desc).
- Exact field-SET equality on the response (and on each breakdown row) so
  any leak — key contacts, financing internals, scorer notes — fails loudly.
- Sparse project: extras null, score_breakdown [].
- Cross-TWG -> 404 (anti-enumeration), ARCHIVED -> 404,
  pillar-matched-but-mislinked TWG -> 200.
"""
import uuid
from decimal import Decimal

import pytest

from app.models.models import (
    Project, ProjectScoreDetail, ProjectStatus, ScoringCriteria,
    TWG, TWGPillar, User, UserRole, twg_members,
)
from app.utils.security import create_access_token


# The EXACT member-facing LIST contract (mirrors tests/test_deal_room.py).
MEMBER_FIELDS = {
    "id", "name", "sector", "status", "investment_size", "currency",
    "readiness_score", "afcen_score", "strategic_alignment_score",
    "location", "description", "is_following", "interest_count", "twg_id",
}

# The EXACT member-facing DETAIL contract: list fields + member-safe extras.
# Set equality proves we do NOT leak key_contact_*, assigned_agent,
# metadata_json, approved_by_id, approval_date, deal_room_priority,
# site_lat/site_lon, revenue_model, macroeconomic_roi, funding_secured_usd...
MEMBER_DETAIL_FIELDS = MEMBER_FIELDS | {
    "subsector", "investment_stage_label", "project_sponsor",
    "is_cross_border", "financing_structure", "technical_studies",
    "land_status", "permits_licences", "climate_impact",
    "smallholder_farmers_reached", "submitted_by", "updated_at",
    "score_breakdown",
}

# Each score_breakdown row: EXACTLY these — never notes / scored_by.
SCORE_BREAKDOWN_FIELDS = {"criterion", "weight", "score"}

# 9 criteria, strictly descending weights so the expected order is unambiguous.
NINE_CRITERIA = [
    ("Market Demand", Decimal("0.20"), Decimal("82.00")),
    ("Financial Viability", Decimal("0.18"), Decimal("74.50")),
    ("Technical Readiness", Decimal("0.15"), Decimal("66.00")),
    ("Sponsor Capacity", Decimal("0.12"), Decimal("58.00")),
    ("Regulatory Fit", Decimal("0.10"), Decimal("91.00")),
    ("Climate Impact", Decimal("0.09"), Decimal("88.00")),
    ("Gender & Youth", Decimal("0.07"), Decimal("45.00")),
    ("Regional Integration", Decimal("0.05"), Decimal("70.00")),
    ("Data Completeness", Decimal("0.04"), Decimal("100.00")),
]


@pytest.fixture
async def deal_detail_setup(db_session):
    """Two TWGs; a TWG_MEMBER in TWG A; one fully-populated TWG-A project with
    a 9-row score breakdown (notes + scorer set, to prove they are stripped);
    one sparse project; cross-TWG, ARCHIVED and pillar-mislinked projects."""
    suffix = uuid.uuid4().hex[:8]

    twg_a = TWG(name=f"Detail Energy {suffix}", pillar=TWGPillar.energy_infrastructure, status="active")
    twg_b = TWG(name=f"Detail Digital {suffix}", pillar=TWGPillar.digital_economy_transformation, status="active")
    db_session.add_all([twg_a, twg_b])
    await db_session.flush()

    member = User(
        email=f"detail_member_{suffix}@ecowas.int",
        hashed_password="hashed_secret",
        full_name="Detail Room Member",
        role=UserRole.TWG_MEMBER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.flush()
    await db_session.execute(twg_members.insert().values(twg_id=twg_a.id, user_id=member.id))

    def _project(twg: TWG, name: str, status: ProjectStatus) -> Project:
        return Project(
            twg_id=twg.id,
            name=f"{name} {suffix}",
            description=f"Description for {name}",
            investment_size=Decimal("25000000.00"),
            currency="USD",
            status=status,
            pillar=twg.pillar.value,
            lead_country="Ghana",
            readiness_score=4.2,
            afcen_score=Decimal("55.00"),
        )

    # Fully populated — including every facilitator-only field, so that exact
    # field-set equality on the response proves none of them leak.
    p_rich = _project(twg_a, "Rich Solar Corridor", ProjectStatus.SUMMIT_READY)
    p_rich.subsector = "Solar Mini-grids"
    p_rich.investment_stage_label = "Investment-ready"
    p_rich.project_sponsor = "Government of Mali (PPP)"
    p_rich.is_cross_border = True
    p_rich.financing_structure = "PPP / Blended Finance"
    p_rich.technical_studies = "Feasibility study complete (2025)"
    p_rich.land_status = "Land secured — 99-year lease"
    p_rich.permits_licences = "Generation licence issued"
    p_rich.climate_impact = "1.2 MtCO2e avoided over lifetime"
    p_rich.smallholder_farmers_reached = "15,000"
    p_rich.submitted_by = "FAO"
    # MUST NEVER reach members:
    p_rich.key_contact_name = "SECRET Contact"
    p_rich.key_contact_email = "secret.contact@example.com"
    p_rich.assigned_agent = "SECRET Agent"
    p_rich.metadata_json = {"internal": "SECRET"}
    p_rich.deal_room_priority = 1
    p_rich.site_lat = 12.65
    p_rich.site_lon = -8.0
    p_rich.revenue_model = "SECRET revenue model"
    p_rich.macroeconomic_roi = "SECRET ROI analysis"
    p_rich.funding_secured_usd = Decimal("5000000.00")

    p_sparse = _project(twg_a, "Sparse Grid Idea", ProjectStatus.INCUBATION)
    p_archived = _project(twg_a, "Archived Plant", ProjectStatus.ARCHIVED)
    p_cross_twg = _project(twg_b, "Cross TWG Fibre", ProjectStatus.PIPELINE)
    # PROD DATA REALITY: twg_id points at the WRONG TWG but the pillar matches
    # the member's TWG pillar — detail must still be visible (twg OR pillar).
    p_mislinked = _project(twg_b, "Mislinked Pillar Solar", ProjectStatus.PIPELINE)
    p_mislinked.pillar = twg_a.pillar.value

    projects = [p_rich, p_sparse, p_archived, p_cross_twg, p_mislinked]
    db_session.add_all(projects)
    await db_session.flush()

    # 9 scoring criteria + 9 score rows on the rich project. notes/scored_by_id
    # are set on every row precisely so the test proves they are stripped.
    criteria = []
    score_rows = []
    for name, weight, score in NINE_CRITERIA:
        crit = ScoringCriteria(
            criterion_name=f"{name} {suffix}",
            criterion_type="readiness",
            weight=weight,
            description=f"{name} description",
        )
        db_session.add(crit)
        criteria.append(crit)
    await db_session.flush()
    for crit, (_, _, score) in zip(criteria, NINE_CRITERIA):
        row = ProjectScoreDetail(
            project_id=p_rich.id,
            criterion_id=crit.id,
            score=score,
            scored_by_id=member.id,
            notes="INTERNAL SCORER NOTE — must never leak",
        )
        db_session.add(row)
        score_rows.append(row)
    await db_session.commit()

    token = create_access_token(data={"sub": str(member.id)})
    yield {
        "member": member,
        "headers": {"Authorization": f"Bearer {token}"},
        "twg_a": twg_a,
        "twg_b": twg_b,
        "rich": p_rich,
        "sparse": p_sparse,
        "archived": p_archived,
        "cross_twg": p_cross_twg,
        "mislinked": p_mislinked,
        "suffix": suffix,
    }

    # Best-effort cleanup (tests run against a real DB).
    from sqlalchemy import text as sa_text
    try:
        for p in projects:
            await db_session.execute(
                sa_text("DELETE FROM project_scores_detail WHERE project_id = :pid"), {"pid": p.id})
            await db_session.execute(
                sa_text("DELETE FROM project_interests WHERE project_id = :pid"), {"pid": p.id})
            await db_session.execute(
                sa_text("DELETE FROM projects WHERE id = :pid"), {"pid": p.id})
        for crit in criteria:
            await db_session.execute(
                sa_text("DELETE FROM scoring_criteria WHERE id = :cid"), {"cid": crit.id})
        await db_session.execute(
            sa_text("DELETE FROM twg_members WHERE user_id = :uid"), {"uid": member.id})
        await db_session.execute(
            sa_text("DELETE FROM users WHERE id = :uid"), {"uid": member.id})
        await db_session.execute(
            sa_text("DELETE FROM twgs WHERE id IN (:a, :b)"), {"a": twg_a.id, "b": twg_b.id})
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest.mark.asyncio
async def test_member_detail_exact_fields_and_score_breakdown(client, deal_detail_setup):
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['rich'].id}", headers=s["headers"])
    assert r.status_code == 200, r.text
    body = r.json()

    # EXACT field set — any extra key (key contacts, financing internals,
    # facilitator metadata) makes this fail.
    assert set(body.keys()) == MEMBER_DETAIL_FIELDS

    # List-contract fields still behave like _project_to_member_read.
    assert body["id"] == str(s["rich"].id)
    assert body["twg_id"] == str(s["twg_a"].id)
    assert body["name"] == s["rich"].name
    assert body["sector"] == "energy_infrastructure"
    assert body["status"] == "SUMMIT_READY"
    assert Decimal(str(body["investment_size"])) == Decimal("25000000.00")
    assert body["currency"] == "USD"
    assert body["readiness_score"] == pytest.approx(4.2)
    assert body["afcen_score"] == pytest.approx(55.0)
    assert body["location"] == "Ghana"
    assert body["is_following"] is False
    assert body["interest_count"] == 0

    # Member-safe extras.
    assert body["subsector"] == "Solar Mini-grids"
    assert body["investment_stage_label"] == "Investment-ready"
    assert body["project_sponsor"] == "Government of Mali (PPP)"
    assert body["is_cross_border"] is True
    assert body["financing_structure"] == "PPP / Blended Finance"
    assert body["technical_studies"] == "Feasibility study complete (2025)"
    assert body["land_status"] == "Land secured — 99-year lease"
    assert body["permits_licences"] == "Generation licence issued"
    assert body["climate_impact"] == "1.2 MtCO2e avoided over lifetime"
    assert body["smallholder_farmers_reached"] == "15,000"
    assert body["submitted_by"] == "FAO"
    assert body["updated_at"] is not None

    # Score breakdown: 9 rows, stripped to criterion/weight/score, weight desc.
    breakdown = body["score_breakdown"]
    assert len(breakdown) == 9
    for row in breakdown:
        assert set(row.keys()) == SCORE_BREAKDOWN_FIELDS
    weights = [row["weight"] for row in breakdown]
    assert weights == sorted(weights, reverse=True)
    expected = {
        f"{name} {s['suffix']}": (float(weight), float(score))
        for name, weight, score in NINE_CRITERIA
    }
    got = {row["criterion"]: (row["weight"], row["score"]) for row in breakdown}
    assert got == expected


@pytest.mark.asyncio
async def test_member_detail_never_leaks_internal_fields(client, deal_detail_setup):
    """Belt-and-braces on top of set equality: the raw payload text must not
    contain any forbidden key OR any of the secret values we planted."""
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['rich'].id}", headers=s["headers"])
    assert r.status_code == 200, r.text

    forbidden_keys = [
        "key_contact_name", "key_contact_email", "assigned_agent",
        "metadata_json", "approved_by_id", "approval_date",
        "deal_room_priority", "site_lat", "site_lon", "revenue_model",
        "macroeconomic_roi", "funding_secured_usd", "notes", "scored_by",
        "scored_by_id", "changed_by",
    ]
    for key in forbidden_keys:
        assert f'"{key}"' not in r.text, f"forbidden key leaked: {key}"

    for secret in [
        "SECRET Contact", "secret.contact@example.com", "SECRET Agent",
        "SECRET revenue model", "SECRET ROI analysis",
        "INTERNAL SCORER NOTE",
    ]:
        assert secret not in r.text, f"forbidden value leaked: {secret}"


@pytest.mark.asyncio
async def test_member_detail_sparse_project_nulls_and_empty_breakdown(client, deal_detail_setup):
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['sparse'].id}", headers=s["headers"])
    assert r.status_code == 200, r.text
    body = r.json()

    assert set(body.keys()) == MEMBER_DETAIL_FIELDS
    for field in [
        "subsector", "investment_stage_label", "project_sponsor",
        "financing_structure", "technical_studies", "land_status",
        "permits_licences", "climate_impact", "smallholder_farmers_reached",
        "submitted_by",
    ]:
        assert body[field] is None, f"{field} expected null on sparse project"
    # DB defaults apply to these two — they exist but are non-secret defaults.
    assert body["is_cross_border"] in (False, None)
    assert body["score_breakdown"] == []


@pytest.mark.asyncio
async def test_member_detail_cross_twg_404(client, deal_detail_setup):
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['cross_twg'].id}", headers=s["headers"])
    assert r.status_code == 404, r.text
    # Nonexistent → 404 too (no enumeration signal difference).
    r = await client.get(f"/api/v1/pipeline/member/{uuid.uuid4()}", headers=s["headers"])
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_member_detail_archived_404(client, deal_detail_setup):
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['archived'].id}", headers=s["headers"])
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_member_detail_pillar_matched_mislinked_twg_200(client, deal_detail_setup):
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['mislinked'].id}", headers=s["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == MEMBER_DETAIL_FIELDS
    assert body["id"] == str(s["mislinked"].id)
    assert body["sector"] == "energy_infrastructure"


@pytest.mark.asyncio
async def test_member_detail_requires_auth(client, deal_detail_setup):
    s = deal_detail_setup
    r = await client.get(f"/api/v1/pipeline/member/{s['rich'].id}")
    assert r.status_code in (401, 403)
