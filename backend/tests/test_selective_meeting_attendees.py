import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.twgs import _sync_new_members_to_future_meetings
from app.api.routes import meetings as meeting_routes
from app.api.routes import recurring_meetings as recurring_routes
from app.core.config import settings
from app.models.models import (
    AttendanceMode,
    Meeting,
    MeetingParticipant,
    MeetingStatus,
    RecurringMeeting,
    RecurringMeetingSelectedMember,
    User,
    UserRole,
)
from app.schemas.schemas import MeetingCreate, RecurringMeetingCreate
from app.services.meeting_participant_service import resolve_meeting_members
from app.services.recurring_meeting_service import RecurringMeetingService
from app.services import recurring_meeting_service
from app.tools.calendar_tools import CREATE_MEETING_TOOL, CREATE_RECURRING_MEETING_TOOL
from app.tools import calendar_tools
from app.tools.database_tools import get_twg_members
from app.tools.tool_registry import ToolRegistry
from app.services.recurring_meeting_service import generate_all_upcoming_recurring_instances
from app.tasks import recurring_tasks


def _scalar_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _one_result(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


def _meeting_input(twg_id, selected_ids):
    return MeetingCreate(
        twg_id=twg_id,
        title="Selected sync",
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        attendance_mode="specific_twg_members",
        selected_member_ids=selected_ids,
    )


@pytest.mark.asyncio
async def test_create_meeting_route_stages_and_invites_only_selected_participants():
    twg_id = uuid.uuid4()
    selected = [
        MagicMock(spec=User, id=uuid.uuid4(), email=f"selected-{index}@example.test", is_active=True)
        for index in range(2)
    ]
    unselected = MagicMock(
        spec=User, id=uuid.uuid4(), email="unselected@example.test", is_active=True
    )
    current_user = MagicMock(spec=User, role=UserRole.TWG_FACILITATOR, twgs=[MagicMock(id=twg_id)])
    twg = MagicMock(id=twg_id)
    twg.name = "Energy"
    db = AsyncMock()
    db.add = MagicMock()
    invite_result = MagicMock()
    invite_result.all.return_value = [(member.email,) for member in selected]
    reloaded = MagicMock(spec=Meeting)
    db.execute.side_effect = [
        _scalar_result(selected),
        invite_result,
        _one_result(twg),
        _one_result(reloaded),
    ]
    background_recipients = []

    def close_background(coro):
        background_recipients.extend(coro.cr_frame.f_locals["_bg_emails"])
        coro.close()

    with patch.object(meeting_routes.asyncio, "create_task", side_effect=close_background):
        result = await meeting_routes.create_meeting(
            _meeting_input(twg_id, [member.id for member in selected]),
            current_user=current_user,
            db=db,
        )

    staged = [call.args[0] for call in db.add.call_args_list]
    participants = [row for row in staged if isinstance(row, MeetingParticipant)]
    assert result is reloaded
    assert {row.user_id for row in participants} == {member.id for member in selected}
    assert unselected.id not in {row.user_id for row in participants}
    invite_query = str(db.execute.await_args_list[1].args[0])
    assert "meeting_participants" in invite_query
    assert "meeting_participants.meeting_id" in invite_query
    assert background_recipients == [member.email for member in selected]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_kind", ["empty", "duplicate", "wrong_twg", "inactive"])
async def test_create_meeting_route_invalid_selection_stages_nothing_and_does_not_commit(invalid_kind):
    twg_id = uuid.uuid4()
    member_id = uuid.uuid4()
    selected_ids = {
        "empty": [],
        "duplicate": [member_id, member_id],
        "wrong_twg": [member_id],
        "inactive": [member_id],
    }[invalid_kind]
    current_user = MagicMock(spec=User, role=UserRole.TWG_FACILITATOR, twgs=[MagicMock(id=twg_id)])
    db = AsyncMock()
    db.add = MagicMock()
    if invalid_kind in {"wrong_twg", "inactive"}:
        db.execute.return_value = _scalar_result([])

    with pytest.raises(HTTPException) as exc:
        await meeting_routes.create_meeting(
            _meeting_input(twg_id, selected_ids), current_user=current_user, db=db
        )

    assert exc.value.status_code == 422
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_tool_create_meeting_uses_only_same_twg_selected_ids():
    twg_id = uuid.uuid4()
    members = [
        MagicMock(spec=User, id=uuid.uuid4(), email=f"tool-{index}@example.test", is_active=True)
        for index in range(2)
    ]
    twg = MagicMock(id=twg_id)
    twg.name = "Energy"
    current_user = MagicMock(spec=User, role=UserRole.TWG_FACILITATOR, twgs=[twg])
    session = AsyncMock()
    session.add = MagicMock()
    session.__aenter__.return_value = session
    session.execute.side_effect = [_one_result(twg), _scalar_result(members)]

    with patch("app.core.database.AsyncSessionLocal", return_value=session):
        result = json.loads(await calendar_tools.create_meeting(
            twg_id=str(twg_id),
            title="Tool selected sync",
            scheduled_at_iso="2026-08-10T10:00:00",
            attendance_mode="specific_twg_members",
            selected_member_ids=[str(member.id) for member in members],
            current_user=current_user,
        ))

    staged = [call.args[0] for call in session.add.call_args_list]
    participants = [row for row in staged if isinstance(row, MeetingParticipant)]
    assert result.get("success") is True, result
    assert {row.user_id for row in participants} == {member.id for member in members}
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_calendar_tool_create_meeting_denies_cross_twg_before_creation():
    own_twg = MagicMock(id=uuid.uuid4())
    requested_twg_id = uuid.uuid4()
    current_user = MagicMock(spec=User, role=UserRole.TWG_FACILITATOR, twgs=[own_twg])
    session = AsyncMock()
    session.add = MagicMock()
    session.__aenter__.return_value = session

    with patch("app.core.database.AsyncSessionLocal", return_value=session):
        result = json.loads(await calendar_tools.create_meeting(
            twg_id=str(requested_twg_id),
            title="Forbidden sync",
            scheduled_at_iso="2026-08-10T10:00:00",
            attendance_mode="specific_twg_members",
            selected_member_ids=[str(uuid.uuid4())],
            current_user=current_user,
        ))

    assert "do not have access" in result["error"]
    session.execute.assert_not_awaited()
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_weekly_dispatch_specific_meeting_uses_existing_participants_without_roster_fallback():
    meeting = MagicMock(
        spec=Meeting,
        id=uuid.uuid4(),
        twg_id=uuid.uuid4(),
        title="Selected weekly sync",
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        video_link="https://meet.example.test/selected",
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
    )
    roster = [MagicMock(spec=User, id=uuid.uuid4(), email=f"roster-{i}@example.test") for i in range(9)]
    participant_rows = []
    expected_emails = []
    for index in range(4):
        user = roster[index]
        participant = MagicMock(spec=MeetingParticipant, email=None, user_id=user.id)
        participant_rows.append((participant, user))
        expected_emails.append(user.email)

    db = AsyncMock()
    db.add = MagicMock()
    lock_result = MagicMock(scalar=MagicMock(return_value=True))
    meetings_result = _scalar_result([meeting])
    count_result = MagicMock(scalar=MagicMock(return_value=4))
    rows_result = MagicMock(all=MagicMock(return_value=participant_rows))
    unlock_result = MagicMock()
    db.execute.side_effect = [lock_result, meetings_result, count_result, rows_result, unlock_result]

    @asynccontextmanager
    async def db_context():
        yield db

    list_request = MagicMock()
    list_request.execute.return_value = {
        "items": [{"id": "calendar-event", "hangoutLink": meeting.video_link}]
    }
    patch_request = MagicMock()
    events = MagicMock()
    events.list.return_value = list_request
    events.patch.return_value = patch_request
    calendar = MagicMock()
    calendar.events.return_value = events
    credentials = MagicMock()
    credentials.with_subject.return_value = credentials

    with patch.object(recurring_tasks, "get_db_session_context", db_context), patch.object(
        settings, "INVITE_DISPATCH_ENABLED", True
    ), patch("google.oauth2.service_account.Credentials.from_service_account_info", return_value=credentials), patch(
        "googleapiclient.discovery.build", return_value=calendar
    ), patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": "{}"}):
        result = await recurring_tasks.run_weekly_invite_dispatch()

    assert result == {"sent": 1, "skipped": 0, "errors": 0}
    assert db.execute.await_count == 5
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
    assert events.patch.call_args.kwargs["body"] == {
        "attendees": [{"email": email} for email in expected_emails]
    }


@pytest.mark.asyncio
async def test_facilitator_meeting_list_does_not_hide_legitimate_test_titles():
    """Visibility is determined by TWG access, never by words in the title."""
    twg_id = uuid.uuid4()
    meeting = MagicMock(spec=Meeting, title="Carren selective test", twg_id=twg_id, documents=[])
    user = MagicMock(spec=User, role=UserRole.TWG_FACILITATOR, twgs=[MagicMock(id=twg_id)])
    db = AsyncMock()
    db.execute.return_value = _scalar_result([meeting])

    result = await meeting_routes.list_meetings(current_user=user, db=db)

    assert result == [meeting]
    query = str(db.execute.await_args.args[0]).lower()
    assert "lower(meetings.title) not like" not in query


@pytest.mark.asyncio
async def test_default_mode_resolves_all_active_twg_members():
    twg_id = uuid.uuid4()
    active = MagicMock(spec=User, id=uuid.uuid4(), is_active=True)
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value = _scalar_result([active])

    members = await resolve_meeting_members(db, twg_id, AttendanceMode.ALL_TWG_MEMBERS, [])

    assert members == [active]


@pytest.mark.asyncio
async def test_selected_mode_resolves_only_requested_active_members():
    twg_id = uuid.uuid4()
    selected = [MagicMock(spec=User, id=uuid.uuid4(), is_active=True) for _ in range(2)]
    db = AsyncMock()
    db.execute.return_value = _scalar_result(selected)

    members = await resolve_meeting_members(
        db, twg_id, AttendanceMode.SPECIFIC_TWG_MEMBERS, [m.id for m in selected]
    )

    assert {m.id for m in members} == {m.id for m in selected}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "selected_ids,found,error",
    [
        ([], [], "at least one"),
        ([uuid.uuid4(), uuid.uuid4()], [], "unique"),
        ([uuid.uuid4()], [], "active members"),
    ],
)
async def test_selected_mode_rejects_empty_duplicate_or_invalid_members(selected_ids, found, error):
    if error == "unique":
        selected_ids[1] = selected_ids[0]
    db = AsyncMock()
    db.execute.return_value = _scalar_result(found)

    with pytest.raises(HTTPException, match=error) as exc:
        await resolve_meeting_members(
            db, uuid.uuid4(), AttendanceMode.SPECIFIC_TWG_MEMBERS, selected_ids
        )

    assert exc.value.status_code == 422


def test_api_contract_defaults_and_exposes_selected_ids():
    one_off = MeetingCreate(
        twg_id=uuid.uuid4(), title="Sync", scheduled_at=datetime.utcnow()
    )
    recurring = RecurringMeetingCreate.model_validate(
        {
            "twg_id": uuid.uuid4(),
            "title_template": "Weekly sync",
            "recurrence_rule": {"frequency": "weekly"},
            "recurrence_end": {"end_type": "after_occurrences", "max_occurrences": 2},
            "start_date": datetime.utcnow(),
            "start_time": "10:00",
        }
    )

    assert one_off.attendance_mode == AttendanceMode.ALL_TWG_MEMBERS
    assert one_off.selected_member_ids == []
    assert recurring.attendance_mode == AttendanceMode.ALL_TWG_MEMBERS
    assert recurring.selected_member_ids == []


def test_agent_tool_schemas_expose_attendance_fields_and_member_lookup_instruction():
    for tool in (CREATE_MEETING_TOOL, CREATE_RECURRING_MEETING_TOOL):
        props = tool["input_schema"]["properties"]
        assert props["attendance_mode"]["enum"] == [
            "all_twg_members", "specific_twg_members"
        ]
        assert props["selected_member_ids"]["items"]["type"] == "string"
        assert "get_twg_members" in tool["description"]


@pytest.mark.asyncio
async def test_agent_recurring_handler_passes_selection_to_shared_schema():
    twg_id = uuid.uuid4()
    member_id = uuid.uuid4()
    twg = MagicMock(name="Energy TWG")
    twg.id = twg_id
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = UserRole.TWG_FACILITATOR
    user.twgs = [twg]
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=twg)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
    ]
    service = AsyncMock()
    service.create_recurring_meeting.return_value = MagicMock(
        id=uuid.uuid4(), title_template="Selected sync", instances=[]
    )

    with patch("app.core.database.AsyncSessionLocal", return_value=session), patch(
        "app.services.recurring_meeting_service.RecurringMeetingService", return_value=service
    ):
        await calendar_tools.create_recurring_meeting(
            twg_id=str(twg_id),
            title_template="Selected sync",
            start_date_iso="2026-08-10",
            start_time="10:00",
            frequency="weekly",
            attendance_mode="specific_twg_members",
            selected_member_ids=[str(member_id)],
            current_user=user,
        )

    payload = service.create_recurring_meeting.await_args.args[0]
    assert payload.attendance_mode.value == "specific_twg_members"
    assert payload.selected_member_ids == [member_id]


@pytest.mark.asyncio
async def test_new_member_sync_excludes_specific_attendance_meetings():
    twg_id = uuid.uuid4()
    all_meeting = MagicMock(
        spec=Meeting,
        id=uuid.uuid4(),
        twg_id=twg_id,
        attendance_mode=AttendanceMode.ALL_TWG_MEMBERS,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        status=MeetingStatus.SCHEDULED,
        participants=[],
        twg=None,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value = _scalar_result([all_meeting])

    def close_background(coro):
        coro.close()
    with patch("app.api.routes.twgs.asyncio.create_task", side_effect=close_background):
        await _sync_new_members_to_future_meetings(
            twg_id, [uuid.uuid4()], ["lazarusogero1@gmail.com"], db
        )

    query_text = str(db.execute.call_args.args[0])
    assert "attendance_mode" in query_text
    assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_recurring_specific_series_uses_fixed_relational_selection():
    selected_user = MagicMock(spec=User, id=uuid.uuid4(), is_active=True)
    series = MagicMock(
        spec=RecurringMeeting,
        id=uuid.uuid4(),
        twg_id=uuid.uuid4(),
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
        selected_members=[
            MagicMock(spec=RecurringMeetingSelectedMember, user_id=selected_user.id, user=selected_user)
        ],
    )
    db = AsyncMock()
    db.execute.return_value = _scalar_result([selected_user])
    service = RecurringMeetingService(db)

    members = await service._resolve_series_members(series)

    assert members == [selected_user]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_recurring_specific_series_queries_users_without_accessing_row_user():
    selected_user = MagicMock(spec=User, id=uuid.uuid4(), is_active=True)
    selected_row = MagicMock(spec=RecurringMeetingSelectedMember)
    selected_row.user_id = selected_user.id
    type(selected_row).user = property(
        lambda _self: (_ for _ in ()).throw(AssertionError("row.user lazy access"))
    )
    series = MagicMock(
        spec=RecurringMeeting,
        id=uuid.uuid4(),
        twg_id=uuid.uuid4(),
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
        selected_members=[selected_row],
    )
    db = AsyncMock()
    db.execute.return_value = _scalar_result([selected_user])

    members = await RecurringMeetingService(db)._resolve_series_members(series)

    assert members == [selected_user]
    query = str(db.execute.await_args.args[0])
    assert "recurring_meeting_selected_members" in query
    assert "twg_members" in query
    assert "users.is_active" in query


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["create_meeting", "create_recurring_meeting"])
async def test_twg_agent_registry_overrides_cross_twg_tool_argument(tool_name):
    authorized = str(uuid.uuid4())
    supplied = str(uuid.uuid4())
    registry = ToolRegistry()
    received = {}
    async def handler(twg_id: str):
        received["twg_id"] = twg_id
        return "ok"
    registry.register(tool_name, "", {"twg_id": {"type": "string"}}, handler)

    await registry.execute_tool(tool_name, {"twg_id": supplied}, "energy", authorized)

    assert received["twg_id"] == authorized


@pytest.mark.asyncio
@pytest.mark.parametrize("route_name", ["cancel_recurring_meeting", "pause_recurring_meeting", "resume_recurring_meeting"])
async def test_recurring_mutations_deny_cross_twg_access(route_name):
    series = MagicMock(spec=RecurringMeeting, id=uuid.uuid4(), twg_id=uuid.uuid4())
    result = MagicMock(scalar_one_or_none=MagicMock(return_value=series))
    db = AsyncMock()
    db.execute.return_value = result
    user = MagicMock(spec=User)
    user.role = UserRole.TWG_FACILITATOR
    user.twgs = []

    with pytest.raises(HTTPException) as exc:
        await getattr(recurring_routes, route_name)(series.id, current_user=user, db=db)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_bulk_generation_rolls_back_failed_series_before_continuing():
    failed_id = uuid.uuid4()
    succeeds_id = uuid.uuid4()
    failed = MagicMock(spec=RecurringMeeting, id=failed_id)
    succeeds = MagicMock(spec=RecurringMeeting, id=succeeds_id)
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [
        _scalar_result([failed_id, succeeds_id]),
        _one_result(failed),
        _one_result(succeeds),
    ]
    processed = []

    async def generate(series):
        processed.append(series)
        if series is failed:
            db.add(Meeting(id=uuid.uuid4(), twg_id=uuid.uuid4(), title="staged", scheduled_at=datetime.utcnow()))
            raise RuntimeError("participant resolution failed")
        assert db.rollback.await_count == 1
        return []

    with patch.object(RecurringMeetingService, "generate_instances", side_effect=generate), patch(
        "app.services.recurring_meeting_service.logger.error"
    ) as log_error:
        await generate_all_upcoming_recurring_instances(db)

    db.rollback.assert_awaited_once()
    assert processed == [failed, succeeds]
    assert db.execute.await_count == 3
    assert str(failed_id) in log_error.call_args.args[0]


@pytest.mark.asyncio
async def test_get_twg_members_excludes_inactive_and_nonmember_leads():
    member = MagicMock(spec=User, id=uuid.uuid4(), full_name="Lazarus Ogero", email="lazarusogero1@gmail.com", is_active=True, role=UserRole.TWG_MEMBER)
    inactive = MagicMock(spec=User, id=uuid.uuid4(), full_name="Inactive", email="lazarus.magwaro@africacen.org", is_active=False, role=UserRole.TWG_MEMBER)
    twg = MagicMock(id=uuid.uuid4(), members=[member, inactive], political_lead_id=uuid.uuid4(), technical_lead_id=member.id)
    result = MagicMock()
    result.scalars.return_value.first.return_value = twg
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.execute.return_value = result

    with patch("app.tools.database_tools.AsyncSessionLocal", return_value=session):
        members = await get_twg_members(twg_id=str(twg.id))

    assert members == [{"id": str(member.id), "name": member.full_name, "email": member.email, "role": "technical_lead"}]
    assert session.execute.await_count == 1


def _participant_route_user(twg_id):
    return MagicMock(
        spec=User,
        role=UserRole.TWG_FACILITATOR,
        twgs=[MagicMock(id=twg_id)],
    )


def _specific_occurrence(twg_id, series_id):
    return MagicMock(
        spec=Meeting,
        id=uuid.uuid4(),
        twg_id=twg_id,
        recurring_meeting_id=series_id,
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
    )


def _specific_series(twg_id, series_id):
    return MagicMock(
        spec=RecurringMeeting,
        id=series_id,
        twg_id=twg_id,
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
    )


@pytest.mark.asyncio
async def test_series_add_updates_fixed_template_and_future_generation_uses_member():
    twg_id, series_id = uuid.uuid4(), uuid.uuid4()
    meeting = _specific_occurrence(twg_id, series_id)
    sibling = _specific_occurrence(twg_id, series_id)
    member = MagicMock(spec=User, id=uuid.uuid4(), is_active=True, email=None)
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [
        _one_result(meeting),             # meeting
        _one_result(_specific_series(twg_id, series_id)),  # locked parent
        _scalar_result([member]),         # active TWG validation
        _scalar_result([]),               # existing current participants
        _scalar_result([]),               # existing selected template rows
        _scalar_result([sibling]),        # future siblings
        _scalar_result([]),               # sibling participants
    ]

    result = await meeting_routes.add_participants(
        meeting.id,
        [meeting_routes.MeetingParticipantCreate(user_id=member.id)],
        apply_to_series=True,
        current_user=_participant_route_user(twg_id),
        db=db,
    )

    staged = [call.args[0] for call in db.add.call_args_list]
    templates = [row for row in staged if isinstance(row, RecurringMeetingSelectedMember)]
    participant_rows = [row for row in staged if isinstance(row, MeetingParticipant)]
    assert [(row.recurring_meeting_id, row.user_id) for row in templates] == [(series_id, member.id)]
    assert {(row.meeting_id, row.user_id) for row in participant_rows} == {
        (meeting.id, member.id), (sibling.id, member.id)
    }
    assert result == [participant_rows[0]]
    db.commit.assert_awaited_once()

    generation_db = AsyncMock()
    generation_db.add = MagicMock()
    series = MagicMock(
        spec=RecurringMeeting,
        id=series_id,
        twg_id=twg_id,
        title_template="Selected sync",
        duration_minutes=60,
        location=None,
        meeting_type="virtual",
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
        end_type="never",
        occurrences_created=0,
    )
    generation_db.execute.side_effect = [
        _one_result(series),
        _scalar_result([]),
        _scalar_result([member] if templates else []),
        _scalar_result([]),
    ]
    generation_service = RecurringMeetingService(generation_db)
    with patch.object(
        generation_service,
        "calculate_occurrence_dates",
        return_value=[datetime.utcnow() + timedelta(days=30)],
    ), patch.object(recurring_meeting_service.asyncio, "create_task", side_effect=lambda coro: (coro.close(), MagicMock(done=lambda: True))[1]):
        generated = await generation_service.generate_instances(series)

    generated_participants = [
        call.args[0]
        for call in generation_db.add.call_args_list
        if isinstance(call.args[0], MeetingParticipant)
    ]
    assert len(generated) == 1
    assert [(row.meeting_id, row.user_id) for row in generated_participants] == [
        (generated[0].id, member.id)
    ]


@pytest.mark.asyncio
async def test_series_remove_deletes_fixed_template_and_future_generation_excludes_member():
    twg_id, series_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    meeting = _specific_occurrence(twg_id, series_id)
    sibling = _specific_occurrence(twg_id, series_id)
    participant = MagicMock(
        spec=MeetingParticipant, id=uuid.uuid4(), user_id=member_id, email=None
    )
    sibling_participant = MagicMock(spec=MeetingParticipant, user_id=member_id)
    template = MagicMock(
        spec=RecurringMeetingSelectedMember,
        recurring_meeting_id=series_id,
        user_id=member_id,
    )
    db = AsyncMock()
    db.execute.side_effect = [
        _one_result(meeting),
        _one_result(_specific_series(twg_id, series_id)),
        _one_result(participant),
        _one_result(template),
        _scalar_result([sibling]),
        _one_result(sibling_participant),
    ]

    await meeting_routes.remove_participant(
        meeting.id,
        participant.id,
        apply_to_series=True,
        current_user=_participant_route_user(twg_id),
        db=db,
    )

    deleted = [call.args[0] for call in db.delete.await_args_list]
    assert deleted == [participant, template, sibling_participant]
    db.commit.assert_awaited_once()

    generation_db = AsyncMock()
    generation_db.add = MagicMock()
    series = MagicMock(
        spec=RecurringMeeting,
        id=series_id,
        twg_id=twg_id,
        title_template="Selected sync",
        duration_minutes=60,
        location=None,
        meeting_type="virtual",
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
        end_type="never",
        occurrences_created=0,
    )
    generation_db.execute.side_effect = [
        _one_result(series),
        _scalar_result([]),
        _scalar_result([] if template in deleted else [MagicMock(id=member_id)]),
        _scalar_result([]),
    ]
    generation_service = RecurringMeetingService(generation_db)
    with patch.object(
        generation_service,
        "calculate_occurrence_dates",
        return_value=[datetime.utcnow() + timedelta(days=30)],
    ), patch.object(recurring_meeting_service.asyncio, "create_task", side_effect=lambda coro: (coro.close(), MagicMock(done=lambda: True))[1]):
        generated = await generation_service.generate_instances(series)

    generated_participants = [
        call.args[0]
        for call in generation_db.add.call_args_list
        if isinstance(call.args[0], MeetingParticipant)
    ]
    assert len(generated) == 1
    assert generated_participants == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["add", "remove"])
async def test_one_occurrence_participant_mutation_leaves_fixed_template_unchanged(mutation):
    twg_id, series_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    meeting = _specific_occurrence(twg_id, series_id)
    db = AsyncMock()
    db.add = MagicMock()
    if mutation == "add":
        db.execute.side_effect = [_one_result(meeting), _scalar_result([])]
        await meeting_routes.add_participants(
            meeting.id,
            [meeting_routes.MeetingParticipantCreate(user_id=member_id)],
            apply_to_series=False,
            current_user=_participant_route_user(twg_id),
            db=db,
        )
    else:
        participant = MagicMock(
            spec=MeetingParticipant, id=uuid.uuid4(), user_id=member_id, email=None
        )
        db.execute.side_effect = [_one_result(meeting), _one_result(participant)]
        await meeting_routes.remove_participant(
            meeting.id,
            participant.id,
            apply_to_series=False,
            current_user=_participant_route_user(twg_id),
            db=db,
        )

    staged = [call.args[0] for call in db.add.call_args_list]
    deleted = [call.args[0] for call in db.delete.await_args_list]
    assert not any(isinstance(row, RecurringMeetingSelectedMember) for row in staged)
    assert not any(isinstance(row, RecurringMeetingSelectedMember) for row in deleted)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_kind", ["nonmember", "guest"])
async def test_invalid_specific_series_addition_changes_nothing(invalid_kind):
    twg_id, series_id = uuid.uuid4(), uuid.uuid4()
    meeting = _specific_occurrence(twg_id, series_id)
    db = AsyncMock()
    db.add = MagicMock()
    if invalid_kind == "nonmember":
        payload = meeting_routes.MeetingParticipantCreate(user_id=uuid.uuid4())
        db.execute.side_effect = [
            _one_result(meeting),
            _one_result(_specific_series(twg_id, series_id)),
            _scalar_result([]),
        ]
    else:
        payload = meeting_routes.MeetingParticipantCreate(
            email="outside@example.org", name="Outside Guest"
        )
        db.execute.side_effect = [
            _one_result(meeting),
            _one_result(_specific_series(twg_id, series_id)),
            _scalar_result([]),
        ]

    with pytest.raises(HTTPException) as exc:
        await meeting_routes.add_participants(
            meeting.id,
            [payload],
            apply_to_series=True,
            current_user=_participant_route_user(twg_id),
            db=db,
        )

    assert exc.value.status_code == 422
    assert "active member" in exc.value.detail.lower() or "guest" in exc.value.detail.lower()
    db.add.assert_not_called()
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["add", "remove"])
async def test_specific_series_participant_commit_failure_rolls_back(mutation):
    twg_id, series_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    meeting = _specific_occurrence(twg_id, series_id)
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = RuntimeError("write failed")

    if mutation == "add":
        member = MagicMock(spec=User, id=member_id, is_active=True, email=None)
        db.execute.side_effect = [
            _one_result(meeting),
            _one_result(_specific_series(twg_id, series_id)),
            _scalar_result([member]),
            _scalar_result([]),
            _scalar_result([]),
            _scalar_result([]),
        ]
        operation = meeting_routes.add_participants(
            meeting.id,
            [meeting_routes.MeetingParticipantCreate(user_id=member_id)],
            apply_to_series=True,
            current_user=_participant_route_user(twg_id),
            db=db,
        )
    else:
        participant = MagicMock(
            spec=MeetingParticipant, id=uuid.uuid4(), user_id=member_id, email=None
        )
        template = MagicMock(spec=RecurringMeetingSelectedMember, user_id=member_id)
        db.execute.side_effect = [
            _one_result(meeting),
            _one_result(_specific_series(twg_id, series_id)),
            _one_result(participant),
            _one_result(template),
            _scalar_result([]),
        ]
        operation = meeting_routes.remove_participant(
            meeting.id,
            participant.id,
            apply_to_series=True,
            current_user=_participant_route_user(twg_id),
            db=db,
        )

    with pytest.raises(RuntimeError, match="write failed"):
        await operation

    db.commit.assert_awaited_once()
    db.rollback.assert_awaited_once()


def _is_series_lock(statement):
    return (
        "FROM recurring_meetings" in str(statement)
        and "recurring_meetings.id" in str(statement)
        and statement._for_update_arg is not None
    )


def test_shared_series_lock_compiles_to_postgresql_for_update():
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    statement = select(RecurringMeeting).where(
        RecurringMeeting.id == uuid.uuid4()
    ).with_for_update()

    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert compiled.rstrip().endswith("FOR UPDATE")


@pytest.mark.asyncio
async def test_generator_locks_and_reloads_series_before_instance_or_template_reads():
    series_id, twg_id, selected_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    stale = MagicMock(spec=RecurringMeeting, id=series_id)
    locked = MagicMock(
        spec=RecurringMeeting,
        id=series_id,
        twg_id=twg_id,
        title_template="Locked title",
        duration_minutes=45,
        location=None,
        meeting_type="virtual",
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
        end_type="never",
        occurrences_created=0,
    )
    selected = MagicMock(spec=User, id=selected_id, email=None, is_active=True)
    db = AsyncMock()
    db.add = MagicMock()
    events = []

    async def execute(statement):
        if not events:
            assert _is_series_lock(statement)
            events.append("series_lock")
            return _one_result(locked)
        query = str(statement)
        assert events[0] == "series_lock"
        if "FROM meetings" in query and "meeting_participants" not in query:
            events.append("instances")
            return _scalar_result([])
        if "recurring_meeting_selected_members" in query:
            events.append("template")
            return _scalar_result([selected])
        events.append("post_commit_participants")
        return _scalar_result([])

    db.execute.side_effect = execute
    service = RecurringMeetingService(db)
    with patch.object(
        service, "calculate_occurrence_dates",
        return_value=[datetime.utcnow() + timedelta(days=1)],
    ), patch.object(
        recurring_meeting_service.asyncio, "create_task",
        side_effect=lambda coro: (coro.close(), MagicMock(done=lambda: True))[1],
    ):
        generated = await service.generate_instances(stale)

    assert events[:3] == ["series_lock", "instances", "template"]
    assert generated[0].title == "Locked title"
    participants = [
        call.args[0] for call in db.add.call_args_list
        if isinstance(call.args[0], MeetingParticipant)
    ]
    assert [row.user_id for row in participants] == [selected_id]


@pytest.mark.asyncio
async def test_generator_commits_locked_series_when_no_occurrences_remain_without_staging_rows():
    series_id, twg_id = uuid.uuid4(), uuid.uuid4()
    stale = MagicMock(spec=RecurringMeeting, id=series_id)
    locked = MagicMock(
        spec=RecurringMeeting,
        id=series_id,
        twg_id=twg_id,
        end_type=recurring_meeting_service.RecurrenceEndType.AFTER_OCCURRENCES,
        max_occurrences=3,
        occurrences_created=3,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_one_result(locked), _scalar_result([])]

    service = RecurringMeetingService(db)
    with patch.object(service, "calculate_occurrence_dates", return_value=[]):
        generated = await service.generate_instances(stale)

    assert generated == []
    assert _is_series_lock(db.execute.await_args_list[0].args[0])
    db.commit.assert_awaited_once()
    db.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["add", "remove"])
async def test_series_mutation_locks_before_template_and_sibling_reads_and_observes_generated_occurrence(mutation):
    twg_id, series_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    current = _specific_occurrence(twg_id, series_id)
    generated = _specific_occurrence(twg_id, series_id)
    locked = MagicMock(
        spec=RecurringMeeting,
        id=series_id,
        twg_id=twg_id,
        attendance_mode=AttendanceMode.SPECIFIC_TWG_MEMBERS,
    )
    member = MagicMock(spec=User, id=member_id, email=None, is_active=True)
    current_participant = MagicMock(
        spec=MeetingParticipant, id=uuid.uuid4(), user_id=member_id, email=None
    )
    generated_participant = MagicMock(
        spec=MeetingParticipant, id=uuid.uuid4(), user_id=member_id, email=None
    )
    template = MagicMock(
        spec=RecurringMeetingSelectedMember,
        recurring_meeting_id=series_id,
        user_id=member_id,
    )
    db = AsyncMock()
    db.add = MagicMock()
    events = []

    async def execute(statement):
        query = str(statement)
        if not events:
            events.append("meeting")
            return _one_result(current)
        if len(events) == 1:
            assert _is_series_lock(statement)
            events.append("series_lock")
            return _one_result(locked)
        assert "series_lock" in events
        if mutation == "add" and "FROM users" in query:
            events.append("validate")
            return _scalar_result([member])
        if "meeting_participants.meeting_id" in query and "FROM meeting_participants" in query:
            if mutation == "add":
                if "meetings.id" not in query:
                    events.append("participants")
                    return _scalar_result([])
            else:
                if "current_participant" not in events:
                    events.append("current_participant")
                    return _one_result(current_participant)
                events.append("generated_participant")
                return _one_result(generated_participant)
        if "recurring_meeting_selected_members" in query:
            events.append("template")
            return _scalar_result([]) if mutation == "add" else _one_result(template)
        if "FROM meetings" in query:
            events.append("siblings")
            return _scalar_result([generated])
        raise AssertionError(f"unexpected query: {query}")

    db.execute.side_effect = execute
    user = _participant_route_user(twg_id)
    if mutation == "add":
        await meeting_routes.add_participants(
            current.id,
            [meeting_routes.MeetingParticipantCreate(user_id=member_id)],
            apply_to_series=True,
            current_user=user,
            db=db,
        )
        staged = [call.args[0] for call in db.add.call_args_list]
        assert any(
            isinstance(row, MeetingParticipant)
            and row.meeting_id == generated.id
            and row.user_id == member_id
            for row in staged
        )
    else:
        await meeting_routes.remove_participant(
            current.id,
            current_participant.id,
            apply_to_series=True,
            current_user=user,
            db=db,
        )
        deleted = [call.args[0] for call in db.delete.await_args_list]
        assert generated_participant in deleted

    assert events[:2] == ["meeting", "series_lock"]
    assert events.index("series_lock") < events.index("template")
    assert events.index("series_lock") < events.index("siblings")
