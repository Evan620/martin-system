"""Member reminders CRUD — scoped to the caller."""
import uuid
from datetime import datetime, timedelta
import pytest


@pytest.mark.asyncio
async def test_create_list_delete_reminder(client, test_user, normal_user_token_headers):
    when = (datetime.utcnow() + timedelta(days=1)).isoformat()
    # create
    r = await client.post("/api/v1/reminders/", headers=normal_user_token_headers,
                          json={"message": "Prep budget notes", "remind_at": when})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["message"] == "Prep budget notes"

    # list — includes it
    r2 = await client.get("/api/v1/reminders/", headers=normal_user_token_headers)
    assert r2.status_code == 200
    assert any(x["id"] == rid for x in r2.json())

    # delete
    r3 = await client.delete(f"/api/v1/reminders/{rid}", headers=normal_user_token_headers)
    assert r3.status_code == 204
    r4 = await client.get("/api/v1/reminders/", headers=normal_user_token_headers)
    assert all(x["id"] != rid for x in r4.json())


@pytest.mark.asyncio
async def test_delete_others_reminder_404(client, db_session, test_user, normal_user_token_headers):
    from app.models.models import Reminder, User, UserRole
    other = User(id=uuid.uuid4(), full_name="Other", email=f"o-{uuid.uuid4()}@x.org",
                 hashed_password="x", role=UserRole.TWG_MEMBER, is_active=True)
    # Reminder has no ORM relationship to User, so SQLAlchemy's unit-of-work does
    # not order the inserts by the FK. Flush the user first so the FK target exists.
    db_session.add(other)
    await db_session.flush()
    rem = Reminder(id=uuid.uuid4(), user_id=other.id, message="theirs",
                   remind_at=datetime.utcnow() + timedelta(days=1))
    db_session.add(rem)
    await db_session.commit()
    r = await client.delete(f"/api/v1/reminders/{rem.id}", headers=normal_user_token_headers)
    assert r.status_code == 404
