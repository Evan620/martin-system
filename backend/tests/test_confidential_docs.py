"""
P0-9 (gap report): server-side confidential-document filtering.

A TWG_MEMBER must NOT receive documents flagged is_confidential from any
member-reachable surface (documents list, download/fetch-by-id, TWG detail
documents array, meeting documents), even for TWGs they belong to.
ADMIN / SECRETARIAT_LEAD / TWG_FACILITATOR keep current behavior.
"""
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.models import (
    Document, Meeting, MeetingStatus, SubGroup, TWG, TWGPillar, User, UserRole,
)
from app.utils.security import create_access_token


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
async def facilitator_user(db_session):
    """Create a TWG facilitator for testing."""
    user = User(
        email=f"test_facilitator_{uuid.uuid4()}@ecowas.int",
        hashed_password="hashed_secret",
        full_name="Test Facilitator",
        role=UserRole.TWG_FACILITATOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def facilitator_token_headers(facilitator_user):
    token = create_access_token(data={"sub": str(facilitator_user.id)})
    return {"Authorization": f"Bearer {token}"}


async def _seed_twg_with_docs(db_session, uploader, members=(), tmp_path=None):
    """Create a TWG (with the given members) plus one public and one
    confidential document. If tmp_path is given, back the confidential doc
    with a real local file so downloads succeed for allowed roles."""
    twg = TWG(
        id=uuid.uuid4(),
        name=f"ConfTest TWG {uuid.uuid4().hex[:8]}",
        pillar=TWGPillar.energy_infrastructure,
    )
    for m in members:
        twg.members.append(m)

    secret_path = f"/uploads/conf_test_secret_{uuid.uuid4().hex}.pdf"
    secret_meta = None
    if tmp_path is not None:
        secret_file = tmp_path / f"secret_{uuid.uuid4().hex}.pdf"
        secret_file.write_bytes(b"%PDF-1.4 confidential test content")
        secret_path = str(secret_file)
        secret_meta = {"storage_mode": "local"}

    public_doc = Document(
        id=uuid.uuid4(),
        twg_id=twg.id,
        file_name=f"conf_test_public_{uuid.uuid4().hex[:8]}.pdf",
        file_path=f"/uploads/conf_test_public_{uuid.uuid4().hex}.pdf",
        file_type="application/pdf",
        uploaded_by_id=uploader.id,
        is_confidential=False,
    )
    secret_doc = Document(
        id=uuid.uuid4(),
        twg_id=twg.id,
        file_name=f"conf_test_secret_{uuid.uuid4().hex[:8]}.pdf",
        file_path=secret_path,
        file_type="application/pdf",
        uploaded_by_id=uploader.id,
        is_confidential=True,
        metadata_json=secret_meta,
    )
    db_session.add_all([twg, public_doc, secret_doc])
    await db_session.commit()
    return twg, public_doc, secret_doc


def _doc_ids(payload):
    return {str(d["id"]) for d in payload}


# ---------------------------------------------------------------------------
# GET /api/v1/documents/ (list)
# ---------------------------------------------------------------------------

async def test_member_list_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    resp = await client.get("/api/v1/documents/", headers=normal_user_token_headers)
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json())
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) not in ids


async def test_member_list_with_twg_filter_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    resp = await client.get(
        f"/api/v1/documents/?twg_id={twg.id}", headers=normal_user_token_headers
    )
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json())
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) not in ids


async def test_facilitator_list_includes_confidential(
    client: AsyncClient, db_session, facilitator_user, facilitator_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[facilitator_user]
    )
    resp = await client.get("/api/v1/documents/", headers=facilitator_token_headers)
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json())
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) in ids


async def test_admin_list_includes_confidential(
    client: AsyncClient, db_session, admin_user, admin_token_headers
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user
    )
    resp = await client.get("/api/v1/documents/", headers=admin_token_headers)
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json())
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) in ids


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{id}/download (fetch by id)
# ---------------------------------------------------------------------------

async def test_member_cannot_download_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers,
    admin_user, tmp_path,
):
    twg, _, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user], tmp_path=tmp_path
    )
    resp = await client.get(
        f"/api/v1/documents/{secret_doc.id}/download", headers=normal_user_token_headers
    )
    assert resp.status_code in (403, 404), resp.text


async def test_facilitator_can_download_confidential(
    client: AsyncClient, db_session, facilitator_user, facilitator_token_headers,
    admin_user, tmp_path,
):
    twg, _, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[facilitator_user], tmp_path=tmp_path
    )
    resp = await client.get(
        f"/api/v1/documents/{secret_doc.id}/download", headers=facilitator_token_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.content == b"%PDF-1.4 confidential test content"


async def test_admin_can_download_confidential(
    client: AsyncClient, db_session, admin_user, admin_token_headers, tmp_path
):
    twg, _, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, tmp_path=tmp_path
    )
    resp = await client.get(
        f"/api/v1/documents/{secret_doc.id}/download", headers=admin_token_headers
    )
    assert resp.status_code == 200, resp.text


async def test_member_cannot_translate_download_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers,
    admin_user, tmp_path,
):
    twg, _, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user], tmp_path=tmp_path
    )
    resp = await client.get(
        f"/api/v1/documents/{secret_doc.id}/translate-download?language=fr",
        headers=normal_user_token_headers,
    )
    assert resp.status_code in (403, 404), resp.text


async def test_member_cannot_ingest_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers,
    admin_user, tmp_path,
):
    twg, _, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user], tmp_path=tmp_path
    )
    resp = await client.post(
        f"/api/v1/documents/{secret_doc.id}/ingest", headers=normal_user_token_headers
    )
    assert resp.status_code in (403, 404), resp.text


# ---------------------------------------------------------------------------
# GET /api/v1/twgs/{id} (TWG detail documents array)
# ---------------------------------------------------------------------------

async def test_member_twg_detail_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    resp = await client.get(f"/api/v1/twgs/{twg.id}", headers=normal_user_token_headers)
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json()["documents"])
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) not in ids


async def test_admin_twg_detail_includes_confidential(
    client: AsyncClient, db_session, admin_user, admin_token_headers
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user
    )
    resp = await client.get(f"/api/v1/twgs/{twg.id}", headers=admin_token_headers)
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json()["documents"])
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) in ids


async def test_member_twg_list_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    resp = await client.get("/api/v1/twgs/", headers=normal_user_token_headers)
    assert resp.status_code == 200, resp.text
    all_ids = set()
    for t in resp.json():
        all_ids |= _doc_ids(t.get("documents") or [])
    assert str(secret_doc.id) not in all_ids


# ---------------------------------------------------------------------------
# Meeting document surfaces
# ---------------------------------------------------------------------------

async def _attach_meeting(db_session, twg, public_doc, secret_doc):
    meeting = Meeting(
        id=uuid.uuid4(),
        twg_id=twg.id,
        title=f"ConfTest Meeting {uuid.uuid4().hex[:8]}",
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        duration_minutes=60,
        status=MeetingStatus.SCHEDULED,
        meeting_type="virtual",
    )
    public_doc.meeting_id = meeting.id
    secret_doc.meeting_id = meeting.id
    db_session.add(meeting)
    db_session.add_all([public_doc, secret_doc])
    await db_session.commit()
    return meeting


async def test_member_meeting_documents_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    meeting = await _attach_meeting(db_session, twg, public_doc, secret_doc)
    resp = await client.get(
        f"/api/v1/meetings/{meeting.id}/documents", headers=normal_user_token_headers
    )
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json())
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) not in ids


async def test_member_meeting_detail_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    meeting = await _attach_meeting(db_session, twg, public_doc, secret_doc)
    resp = await client.get(
        f"/api/v1/meetings/{meeting.id}", headers=normal_user_token_headers
    )
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json().get("documents") or [])
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) not in ids


async def test_admin_meeting_detail_includes_confidential(
    client: AsyncClient, db_session, admin_user, admin_token_headers
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user
    )
    meeting = await _attach_meeting(db_session, twg, public_doc, secret_doc)
    resp = await client.get(
        f"/api/v1/meetings/{meeting.id}", headers=admin_token_headers
    )
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json().get("documents") or [])
    assert str(secret_doc.id) in ids


async def test_member_meetings_router_download_confidential_blocked(
    client: AsyncClient, db_session, test_user, normal_user_token_headers,
    admin_user, tmp_path,
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user], tmp_path=tmp_path
    )
    resp = await client.get(
        f"/api/v1/meetings/documents/{secret_doc.id}/download",
        headers=normal_user_token_headers,
    )
    assert resp.status_code in (403, 404), resp.text


# ---------------------------------------------------------------------------
# Subgroup documents list
# ---------------------------------------------------------------------------

async def test_member_subgroup_documents_excludes_confidential(
    client: AsyncClient, db_session, test_user, normal_user_token_headers, admin_user
):
    twg, public_doc, secret_doc = await _seed_twg_with_docs(
        db_session, uploader=admin_user, members=[test_user]
    )
    sg = SubGroup(id=uuid.uuid4(), twg_id=twg.id, name=f"ConfTest SG {uuid.uuid4().hex[:8]}")
    public_doc.subgroup_id = sg.id
    secret_doc.subgroup_id = sg.id
    db_session.add(sg)
    db_session.add_all([public_doc, secret_doc])
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/twgs/{twg.id}/subgroups/{sg.id}/documents",
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 200, resp.text
    ids = _doc_ids(resp.json())
    assert str(public_doc.id) in ids
    assert str(secret_doc.id) not in ids
