"""Deal Room — member-scoped project read + interest (follow) toggle.

Covers:
- GET    /api/v1/pipeline/member               — own-TWG projects at ALL stages
  (incl. INCUBATION/DRAFT), member-safe fields ONLY, cross-TWG excluded.
- POST   /api/v1/pipeline/{project_id}/interest — idempotent follow.
- DELETE /api/v1/pipeline/{project_id}/interest — idempotent unfollow.
- Cross-TWG project: absent from list; interest on it -> 404 (anti-enumeration).
"""
import uuid
from decimal import Decimal

import pytest

from app.models.models import (
    Project, ProjectStatus, TWG, TWGPillar, User, UserRole, twg_members,
)
from app.utils.security import create_access_token


# The EXACT member-facing contract — set equality also proves we do NOT leak
# facilitator fields (key_contact_email, financing_structure, ...).
MEMBER_FIELDS = {
    "id", "name", "sector", "status", "investment_size", "currency",
    "readiness_score", "afcen_score", "strategic_alignment_score",
    "location", "description", "is_following", "interest_count", "twg_id",
}


@pytest.fixture
async def deal_room_setup(db_session):
    """Two TWGs; a TWG_MEMBER in TWG A; TWG-A projects at several stages
    (incl. early ones) plus an ARCHIVED one; one cross-TWG project in TWG B."""
    suffix = uuid.uuid4().hex[:8]

    twg_a = TWG(name=f"DealRoom Energy {suffix}", pillar=TWGPillar.energy_infrastructure, status="active")
    twg_b = TWG(name=f"DealRoom Digital {suffix}", pillar=TWGPillar.digital_economy_transformation, status="active")
    db_session.add_all([twg_a, twg_b])
    await db_session.flush()

    member = User(
        email=f"deal_member_{suffix}@ecowas.int",
        hashed_password="hashed_secret",
        full_name="Deal Room Member",
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

    p_incubation = _project(twg_a, "Solar Incubation", ProjectStatus.INCUBATION)
    p_draft = _project(twg_a, "Grid Draft", ProjectStatus.DRAFT)
    p_ready = _project(twg_a, "Wind Summit Ready", ProjectStatus.SUMMIT_READY)
    p_archived = _project(twg_a, "Old Mothballed", ProjectStatus.ARCHIVED)
    p_cross_twg = _project(twg_b, "Cross TWG Fibre", ProjectStatus.PIPELINE)
    # PROD DATA REALITY: projects are systematically linked to the WRONG TWG row
    # (e.g. all agriculture projects carry the Energy TWG's twg_id). This one is
    # linked to the UNRELATED TWG B but carries TWG A's pillar — the TWG-A member
    # must still see it (twg-link OR twg-pillar rule).
    p_mislinked = _project(twg_b, "Mislinked Pillar Solar", ProjectStatus.PIPELINE)
    p_mislinked.pillar = twg_a.pillar.value
    projects = [p_incubation, p_draft, p_ready, p_archived, p_cross_twg, p_mislinked]
    db_session.add_all(projects)
    await db_session.commit()

    token = create_access_token(data={"sub": str(member.id)})
    yield {
        "member": member,
        "headers": {"Authorization": f"Bearer {token}"},
        "twg_a": twg_a,
        "twg_b": twg_b,
        "incubation": p_incubation,
        "draft": p_draft,
        "ready": p_ready,
        "archived": p_archived,
        "cross_twg": p_cross_twg,
        "mislinked": p_mislinked,
    }

    # Best-effort cleanup (tests run against a real DB).
    from sqlalchemy import text as sa_text
    try:
        for p in projects:
            await db_session.execute(
                sa_text("DELETE FROM project_interests WHERE project_id = :pid"), {"pid": p.id})
            await db_session.execute(
                sa_text("DELETE FROM projects WHERE id = :pid"), {"pid": p.id})
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
async def test_member_list_scoped_to_own_twg_all_stages(client, deal_room_setup):
    s = deal_room_setup
    r = await client.get("/api/v1/pipeline/member", headers=s["headers"])
    assert r.status_code == 200, r.text
    items = r.json()
    ids = {item["id"] for item in items}

    # Own-TWG projects at multiple stages — including the early ones the staff
    # pipeline list hides from members (INCUBATION) — are all present.
    assert str(s["incubation"].id) in ids
    assert str(s["draft"].id) in ids
    assert str(s["ready"].id) in ids
    # ARCHIVED is excluded, cross-TWG project is NOT in the member list.
    assert str(s["archived"].id) not in ids
    assert str(s["cross_twg"].id) not in ids


@pytest.mark.asyncio
async def test_member_list_exact_member_safe_fields(client, deal_room_setup):
    s = deal_room_setup
    r = await client.get("/api/v1/pipeline/member", headers=s["headers"])
    assert r.status_code == 200, r.text
    items = [i for i in r.json() if i["id"] == str(s["ready"].id)]
    assert len(items) == 1
    item = items[0]

    # EXACT field set — anything extra (key contacts, financing internals) fails.
    assert set(item.keys()) == MEMBER_FIELDS
    assert item["name"] == s["ready"].name
    assert item["sector"] == "energy_infrastructure"
    assert item["status"] == "SUMMIT_READY"
    assert Decimal(str(item["investment_size"])) == Decimal("25000000.00")
    assert item["currency"] == "USD"
    assert item["readiness_score"] == pytest.approx(4.2)
    assert item["afcen_score"] == pytest.approx(55.0)
    assert item["location"] == "Ghana"
    assert item["description"].startswith("Description for")
    assert item["is_following"] is False
    assert item["interest_count"] == 0
    # Multi-TWG grounding: the read carries the owning TWG's id.
    assert item["twg_id"] == str(s["twg_a"].id)


@pytest.mark.asyncio
async def test_interest_toggle_idempotent(client, deal_room_setup):
    s = deal_room_setup
    pid = s["ready"].id
    h = s["headers"]

    # Follow — twice; second call is a no-op, count stays 1.
    for _ in range(2):
        r = await client.post(f"/api/v1/pipeline/{pid}/interest", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["project_id"] == str(pid)
        assert body["is_following"] is True
        assert body["interest_count"] == 1

    # The member read reflects the follow state.
    r = await client.get("/api/v1/pipeline/member", headers=h)
    item = next(i for i in r.json() if i["id"] == str(pid))
    assert item["is_following"] is True
    assert item["interest_count"] == 1

    # Unfollow — twice; second call is a no-op, count stays 0.
    for _ in range(2):
        r = await client.delete(f"/api/v1/pipeline/{pid}/interest", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_following"] is False
        assert body["interest_count"] == 0

    r = await client.get("/api/v1/pipeline/member", headers=h)
    item = next(i for i in r.json() if i["id"] == str(pid))
    assert item["is_following"] is False
    assert item["interest_count"] == 0


@pytest.mark.asyncio
async def test_cross_twg_interest_denied(client, deal_room_setup):
    s = deal_room_setup
    h = s["headers"]

    # Interest on a project in a TWG the member does not belong to → 403/404
    # (implementation returns 404 to avoid leaking existence via enumeration).
    r = await client.post(f"/api/v1/pipeline/{s['cross_twg'].id}/interest", headers=h)
    assert r.status_code in (403, 404), r.text
    r = await client.delete(f"/api/v1/pipeline/{s['cross_twg'].id}/interest", headers=h)
    assert r.status_code in (403, 404), r.text

    # Nonexistent project → 404.
    r = await client.post(f"/api/v1/pipeline/{uuid.uuid4()}/interest", headers=h)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_member_list_includes_pillar_matched_project_despite_wrong_twg_link(client, deal_room_setup):
    """Regression (prod twg links mis-assigned): a project whose twg_id points at
    an UNRELATED TWG but whose pillar matches the member's TWG pillar IS returned;
    a project with non-matching twg_id AND non-matching pillar is NOT returned."""
    s = deal_room_setup
    r = await client.get("/api/v1/pipeline/member", headers=s["headers"])
    assert r.status_code == 200, r.text
    ids = {item["id"] for item in r.json()}

    # Wrong TWG link, but pillar == member's TWG pillar → visible.
    assert str(s["mislinked"].id) in ids
    # Wrong TWG link AND wrong pillar → still hidden (cross-TWG isolation holds).
    assert str(s["cross_twg"].id) not in ids


@pytest.mark.asyncio
async def test_interest_allowed_on_pillar_matched_project(client, deal_room_setup):
    """Interest follows the same twg-or-pillar rule: posting interest on a
    pillar-matched (but mis-linked) project is ALLOWED; cross-pillar stays 404
    (covered by test_cross_twg_interest_denied)."""
    s = deal_room_setup
    pid = s["mislinked"].id
    h = s["headers"]

    r = await client.post(f"/api/v1/pipeline/{pid}/interest", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == str(pid)
    assert body["is_following"] is True
    assert body["interest_count"] == 1

    r = await client.delete(f"/api/v1/pipeline/{pid}/interest", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_following"] is False
    assert body["interest_count"] == 0


@pytest.mark.asyncio
async def test_member_list_requires_auth(client):
    r = await client.get("/api/v1/pipeline/member")
    assert r.status_code in (401, 403)
