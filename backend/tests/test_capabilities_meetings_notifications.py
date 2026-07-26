"""Capability contracts for meetings and caller-owned notifications."""

from __future__ import annotations

import smtplib
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from pydantic import BaseModel

from app.api.routes import agents
from app.api.routes import meetings as meeting_routes
from app.api.routes import notifications as notification_routes
from app.api.routes import recurring_meetings as recurring_meeting_routes
from app.capabilities.declarations import meetings_notifications as declarations
from app.capabilities.emit_tool import tool_definition
from app.capabilities.gate import invoke_capability
from app.capabilities.spec import (
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
)
from app.core.config import settings
from app.models.models import (
    NotificationType,
    RecurrenceEndType,
    RecurrenceFrequency,
    RecurringMeetingStatus,
    UserRole,
)
from app.schemas.schemas import RecurringMeetingRead
from app.services import (
    email_service as email_service_module,
    meeting_capability_service,
    notification_service,
    recurring_meeting_service,
    resend_service,
    twg_webhook_service,
    whatsapp_service,
)
from app.tools import _rbac, email_tools, whatsapp_tools
from app.utils import email_guard


def _declaration(name: str) -> Capability:
    return getattr(declarations, name).__capability__


class _ScalarResult:
    def __init__(self, *, one=None, many=None):
        self._one = one
        self._many = [] if many is None else many

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._many


class _FakeDB:
    def __init__(self, results=()):
        self.execute = AsyncMock(side_effect=list(results))
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.add = MagicMock()


@pytest.fixture(autouse=True)
def isolate_actions_and_block_all_transmit_paths(monkeypatch):
    """Make every outward chokepoint fail closed for every test in this file."""

    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    _rbac._user_ctx.set(None)
    monkeypatch.setattr(settings, "CAPABILITY_REGISTRY_ENABLED", True)

    blocked = []

    def block_sync(target, attribute):
        mock = MagicMock(side_effect=AssertionError(f"outbound {attribute} called"))
        monkeypatch.setattr(target, attribute, mock)
        blocked.append(mock)
        return mock

    def block_async(target, attribute):
        mock = AsyncMock(side_effect=AssertionError(f"outbound {attribute} called"))
        monkeypatch.setattr(target, attribute, mock)
        blocked.append(mock)
        return mock

    block_sync(smtplib, "SMTP")
    block_sync(email_guard, "redirect_recipients")
    block_async(email_service_module.EmailService, "_send_via_resend")
    block_async(email_service_module.EmailService, "_send_via_smtp")
    block_async(
        email_service_module.email_service,
        "send_minutes_published_email",
    )
    block_sync(resend_service.ResendService, "send_message")
    block_sync(resend_service.resend.Emails, "send")
    block_async(email_tools, "send_email")
    block_async(email_tools, "send_email_from_template")
    block_async(whatsapp_tools, "send_whatsapp_message")
    block_async(whatsapp_tools, "send_whatsapp_to_group")
    block_async(whatsapp_service.WhatsAppService, "send_text")
    block_async(twg_webhook_service, "emit_minutes_published")
    block_sync(meeting_capability_service, "get_storage_service")

    yield

    for transmit_mock in blocked:
        transmit_mock.assert_not_called()
    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    _rbac._user_ctx.set(None)


@pytest.fixture
def admin_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.ADMIN,
        is_active=True,
        twgs=[],
    )


@pytest.mark.parametrize(
    ("name", "properties", "required"),
    [
        ("registry_get_meeting_agenda", {"meeting_id"}, ["meeting_id"]),
        ("registry_approve_meeting_minutes", {"meeting_id"}, ["meeting_id"]),
        ("registry_list_notifications", {"skip", "limit"}, []),
        ("registry_mark_all_notifications_read", set(), []),
        (
            "registry_get_recurring_meeting",
            {"recurring_meeting_id"},
            ["recurring_meeting_id"],
        ),
    ],
)
def test_generated_schema_has_exact_parameters_and_required_fields(
    name,
    properties,
    required,
):
    declaration = _declaration(name)
    function = tool_definition(declaration)["function"]
    parameters = function["parameters"]

    assert set(parameters["properties"]) == properties
    assert parameters["required"] == required
    assert "Example:" in function["description"]

    if "meeting_id" in properties:
        assert parameters["properties"]["meeting_id"]["format"] == "uuid"
    if "recurring_meeting_id" in properties:
        assert parameters["properties"]["recurring_meeting_id"]["format"] == "uuid"
    if name == "registry_list_notifications":
        assert parameters["properties"]["skip"]["default"] == 0
        assert parameters["properties"]["limit"]["default"] == 50


@pytest.mark.asyncio
async def test_get_meeting_agenda_read_returns_data_without_side_effects():
    meeting_id = uuid.uuid4()
    twg_id = uuid.uuid4()
    agenda_id = uuid.uuid4()
    created_at = datetime(2026, 7, 26, 9, 30)
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.TWG_MEMBER,
        twgs=[SimpleNamespace(id=twg_id)],
    )
    agenda = SimpleNamespace(
        id=agenda_id,
        meeting_id=meeting_id,
        content="1. Corridor financing update",
        created_at=created_at,
    )
    db = _FakeDB(
        [
            _ScalarResult(one=SimpleNamespace(twg_id=twg_id)),
            _ScalarResult(one=agenda),
        ]
    )

    result = await invoke_capability(
        _declaration("registry_get_meeting_agenda"),
        {"meeting_id": str(meeting_id)},
        CapabilityContext(user=user, db=db),
        agent_id="member",
    )

    assert result["id"] == str(agenda_id)
    assert result["meeting_id"] == str(meeting_id)
    assert result["content"] == agenda.content
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()
    db.add.assert_not_called()
    assert agents._pending_actions == {}


@pytest.mark.asyncio
async def test_list_notifications_read_returns_data_without_side_effects():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.TWG_MEMBER,
        twgs=[],
    )
    notification_id = uuid.uuid4()
    notification = SimpleNamespace(
        id=notification_id,
        user_id=user.id,
        type=NotificationType.INFO,
        title="Agenda published",
        content="The meeting agenda is ready.",
        link="/meetings/example",
        is_read=False,
        created_at=datetime(2026, 7, 26, 10, 0),
    )
    db = _FakeDB([_ScalarResult(many=[notification])])

    result = await invoke_capability(
        _declaration("registry_list_notifications"),
        {"skip": 0, "limit": 20},
        CapabilityContext(user=user, db=db),
        agent_id="member",
    )

    assert result[0]["id"] == str(notification_id)
    assert result[0]["user_id"] == str(user.id)
    assert result[0]["title"] == "Agenda published"
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()
    db.add.assert_not_called()
    assert agents._pending_actions == {}


@pytest.mark.asyncio
async def test_get_recurring_meeting_read_returns_data_without_side_effects():
    recurring_id = uuid.uuid4()
    twg_id = uuid.uuid4()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.TWG_MEMBER,
        twgs=[SimpleNamespace(id=twg_id)],
    )
    recurring = SimpleNamespace(
        id=recurring_id,
        twg_id=twg_id,
        title_template="Weekly Energy TWG",
        duration_minutes=60,
        location="Virtual",
        meeting_type="virtual",
        frequency=RecurrenceFrequency.WEEKLY,
        interval_weeks=1,
        day_of_week=2,
        start_date=datetime(2026, 7, 1, 8, 0),
        start_time="08:00",
        timezone="Africa/Nairobi",
        end_type=RecurrenceEndType.NEVER,
        end_date=None,
        max_occurrences=None,
        status=RecurringMeetingStatus.ACTIVE,
        occurrences_created=4,
        created_at=datetime(2026, 7, 1, 7, 0),
        created_by_id=user.id,
        instances=[],
    )
    db = _FakeDB([_ScalarResult(one=recurring)])

    result = await invoke_capability(
        _declaration("registry_get_recurring_meeting"),
        {"recurring_meeting_id": str(recurring_id)},
        CapabilityContext(user=user, db=db),
        agent_id="member",
    )

    assert result["id"] == str(recurring_id)
    assert result["title_template"] == "Weekly Energy TWG"
    assert result["upcoming_instances"] == []
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()
    db.add.assert_not_called()
    assert agents._pending_actions == {}


@pytest.mark.parametrize(
    ("name", "payload", "service_module", "service_name"),
    [
        (
            "registry_approve_meeting_minutes",
            {"meeting_id": str(uuid.uuid4())},
            meeting_capability_service,
            "approve_meeting_minutes",
        ),
        (
            "registry_mark_all_notifications_read",
            {},
            notification_service,
            "mark_all_notifications_read",
        ),
    ],
)
@pytest.mark.asyncio
async def test_write_returns_confirmation_without_executing_handler(
    monkeypatch,
    admin_user,
    name,
    payload,
    service_module,
    service_name,
):
    handler = AsyncMock(return_value={"unexpected": True})
    monkeypatch.setattr(service_module, service_name, handler)

    card = await invoke_capability(
        _declaration(name),
        payload,
        CapabilityContext(user=admin_user, db=_FakeDB()),
        agent_id="supervisor",
    )

    assert card["status"] == "confirmation_required"
    assert card["action_type"] == name
    assert card["irreversible"] is False
    assert card["confirm_endpoint"] == "/api/v1/agents/execute"
    assert card["action_id"] in agents._pending_actions
    handler.assert_not_awaited()


class _DestructiveInput(BaseModel):
    item_id: uuid.UUID


@pytest.mark.asyncio
async def test_destructive_capability_is_refused_by_default(admin_user):
    calls = []

    async def handler(payload, context):
        calls.append(payload.item_id)

    declaration = Capability(
        name="meetings_notifications_destructive_probe",
        description="Test the destructive default-deny rule.",
        danger="destructive",
        input_model=_DestructiveInput,
        handler=handler,
        scopes=["supervisor", UserRole.ADMIN.value],
        http=None,
    )

    assert declaration.agent_allowed is False
    with pytest.raises(CapabilityAccessDenied):
        await invoke_capability(
            declaration,
            {"item_id": str(uuid.uuid4())},
            CapabilityContext(user=admin_user, db=_FakeDB()),
            agent_id="supervisor",
        )
    assert calls == []


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("registry_get_meeting_agenda", {"meeting_id": str(uuid.uuid4())}),
        ("registry_approve_meeting_minutes", {"meeting_id": str(uuid.uuid4())}),
        ("registry_list_notifications", {}),
        ("registry_mark_all_notifications_read", {}),
        (
            "registry_get_recurring_meeting",
            {"recurring_meeting_id": str(uuid.uuid4())},
        ),
    ],
)
@pytest.mark.asyncio
async def test_every_capability_refuses_an_agent_outside_its_scopes(
    admin_user,
    name,
    payload,
):
    with pytest.raises(CapabilityAccessDenied):
        await invoke_capability(
            _declaration(name),
            payload,
            CapabilityContext(user=admin_user, db=_FakeDB()),
            agent_id="outside_registry_scope",
        )
    assert agents._pending_actions == {}


@pytest.mark.asyncio
async def test_approve_minutes_refuses_role_outside_its_scopes():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.TWG_MEMBER,
        is_active=True,
        twgs=[],
    )

    with pytest.raises(CapabilityAccessDenied):
        await invoke_capability(
            _declaration("registry_approve_meeting_minutes"),
            {"meeting_id": str(uuid.uuid4())},
            CapabilityContext(user=user, db=_FakeDB()),
            agent_id="supervisor",
        )
    assert agents._pending_actions == {}


@pytest.mark.asyncio
async def test_agenda_http_routes_and_capability_call_same_service(
    monkeypatch,
    admin_user,
):
    meeting_id = uuid.uuid4()
    agenda = SimpleNamespace(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        content="Agenda",
        created_at=datetime(2026, 7, 26, 11, 0),
    )
    shared = AsyncMock(return_value=agenda)
    monkeypatch.setattr(meeting_capability_service, "get_meeting_agenda", shared)
    db = _FakeDB()

    agenda_endpoints = [
        route.endpoint
        for route in meeting_routes.router.routes
        if route.path.endswith("/{meeting_id}/agenda")
        and "GET" in getattr(route, "methods", set())
    ]
    assert len(agenda_endpoints) == 2
    for endpoint in agenda_endpoints:
        assert (
            await endpoint(
                meeting_id=meeting_id,
                current_user=admin_user,
                db=db,
            )
            is agenda
        )

    capability_result = await declarations.registry_get_meeting_agenda(
        declarations.GetMeetingAgendaInput(meeting_id=meeting_id),
        CapabilityContext(user=admin_user, db=db),
    )

    assert capability_result["id"] == str(agenda.id)
    assert shared.await_args_list == [
        call(meeting_id, admin_user, db),
        call(meeting_id, admin_user, db),
        call(meeting_id, admin_user, db),
    ]


@pytest.mark.asyncio
async def test_approve_http_route_and_capability_call_same_service(
    monkeypatch,
    admin_user,
):
    meeting_id = uuid.uuid4()
    expected = {"message": "approved"}
    shared = AsyncMock(return_value=expected)
    monkeypatch.setattr(
        meeting_capability_service,
        "approve_meeting_minutes",
        shared,
    )
    db = _FakeDB()
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    route_result = await meeting_routes.approve_minutes(
        meeting_id=meeting_id,
        request=request,
        current_user=admin_user,
        db=db,
    )
    capability_result = await declarations.registry_approve_meeting_minutes(
        declarations.ApproveMeetingMinutesInput(meeting_id=meeting_id),
        CapabilityContext(user=admin_user, db=db),
    )

    assert route_result == capability_result == expected
    assert shared.await_args_list == [
        call(meeting_id, admin_user, db, client_ip="127.0.0.1"),
        call(meeting_id, admin_user, db, client_ip=None),
    ]


@pytest.mark.asyncio
async def test_notification_http_routes_and_capabilities_call_same_services(
    monkeypatch,
    admin_user,
):
    list_shared = AsyncMock(return_value=[])
    mark_shared = AsyncMock(
        return_value={
            "status": "success",
            "message": "All notifications marked as read",
        }
    )
    monkeypatch.setattr(notification_service, "list_notifications", list_shared)
    monkeypatch.setattr(
        notification_service,
        "mark_all_notifications_read",
        mark_shared,
    )
    db = _FakeDB()

    route_list = await notification_routes.get_notifications(
        skip=5,
        limit=10,
        db=db,
        current_user=admin_user,
    )
    capability_list = await declarations.registry_list_notifications(
        declarations.ListNotificationsInput(skip=5, limit=10),
        CapabilityContext(user=admin_user, db=db),
    )
    route_mark = await notification_routes.mark_all_as_read(
        db=db,
        current_user=admin_user,
    )
    capability_mark = await declarations.registry_mark_all_notifications_read(
        declarations.MarkAllNotificationsReadInput(),
        CapabilityContext(user=admin_user, db=db),
    )

    assert route_list == capability_list == []
    assert route_mark == capability_mark
    assert list_shared.await_args_list == [
        call(db, admin_user, skip=5, limit=10),
        call(db, admin_user, skip=5, limit=10),
    ]
    assert mark_shared.await_args_list == [
        call(db, admin_user),
        call(db, admin_user),
    ]


@pytest.mark.asyncio
async def test_recurring_http_route_and_capability_call_same_service(
    monkeypatch,
    admin_user,
):
    recurring_id = uuid.uuid4()
    recurring = RecurringMeetingRead(
        id=recurring_id,
        twg_id=uuid.uuid4(),
        title_template="Weekly Protocol TWG",
        duration_minutes=60,
        location="Virtual",
        meeting_type="virtual",
        frequency="weekly",
        interval_weeks=1,
        day_of_week=3,
        start_date=datetime(2026, 7, 1, 8, 0),
        start_time="08:00",
        timezone="Africa/Nairobi",
        end_type="never",
        end_date=None,
        max_occurrences=None,
        status="active",
        occurrences_created=4,
        created_at=datetime(2026, 7, 1, 7, 0),
        created_by_id=admin_user.id,
        upcoming_instances=[],
    )
    shared = AsyncMock(return_value=recurring)
    monkeypatch.setattr(
        recurring_meeting_service,
        "get_recurring_meeting_details",
        shared,
    )
    db = _FakeDB()

    route_result = await recurring_meeting_routes.get_recurring_meeting(
        recurring_meeting_id=recurring_id,
        current_user=admin_user,
        db=db,
    )
    capability_result = await declarations.registry_get_recurring_meeting(
        declarations.GetRecurringMeetingInput(
            recurring_meeting_id=recurring_id,
        ),
        CapabilityContext(user=admin_user, db=db),
    )

    assert route_result is recurring
    assert capability_result["id"] == str(recurring_id)
    assert shared.await_args_list == [
        call(db, recurring_id, admin_user),
        call(db, recurring_id, admin_user),
    ]
