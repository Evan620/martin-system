"""Behavioral contract tests for Martin's generated capability surfaces."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from app.api.routes import agents
from app.api.routes.agents import ExecuteActionRequest, execute_action
from app.capabilities.emit_tool import registry_tools_for
from app.capabilities.gate import invoke_capability
from app.capabilities.spec import (
    CAPABILITIES,
    CapabilityAccessDenied,
    CapabilityContext,
    capability,
)
from app.core.config import settings
from app.models.models import UserRole
from app.tools import _rbac


class ExampleInput(BaseModel):
    required_text: str
    optional_count: int = 1


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    original_capabilities = dict(CAPABILITIES)
    CAPABILITIES.clear()
    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    _rbac._user_ctx.set(None)
    monkeypatch.setattr(settings, "CAPABILITY_REGISTRY_ENABLED", True)
    yield
    CAPABILITIES.clear()
    CAPABILITIES.update(original_capabilities)
    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    _rbac._user_ctx.set(None)


@pytest.fixture
def user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.ADMIN,
        is_active=True,
    )


def declare_capability(
    name: str,
    calls: list[str],
    *,
    danger: str = "read",
    scopes: list[str] | None = None,
    agent_allowed: bool | None = None,
):
    @capability(
        name=name,
        description=f"Test capability {name}",
        danger=danger,
        input_model=ExampleInput,
        scopes=scopes or ["test_agent", UserRole.ADMIN.value],
        summary_template="Run for {required_text}",
        agent_allowed=agent_allowed,
    )
    async def handler(payload: ExampleInput, context: CapabilityContext):
        calls.append(payload.required_text)
        return {"handled": payload.required_text}

    return CAPABILITIES[name]


def test_tool_schema_is_derived_from_input_model_with_required_params():
    declaration = declare_capability("schema_probe", [])

    definitions, handlers = registry_tools_for("test_agent")
    emitted = next(
        item for item in definitions if item["function"]["name"] == declaration.name
    )
    parameters = emitted["function"]["parameters"]

    assert parameters["properties"]["required_text"]["type"] == "string"
    assert parameters["properties"]["optional_count"]["type"] == "integer"
    assert parameters["required"] == ["required_text"]
    assert declaration.name in handlers


@pytest.mark.asyncio
async def test_read_capability_executes_immediately(user):
    calls: list[str] = []
    declaration = declare_capability("read_probe", calls)

    result = await invoke_capability(
        declaration,
        {"required_text": "now"},
        CapabilityContext(user=user, db=object()),
        agent_id="test_agent",
    )

    assert result == {"handled": "now"}
    assert calls == ["now"]


@pytest.mark.asyncio
async def test_write_returns_frontend_confirm_card_without_running_handler(user):
    calls: list[str] = []
    declaration = declare_capability("write_probe", calls, danger="write")

    card = await invoke_capability(
        declaration,
        {"required_text": "later"},
        CapabilityContext(user=user, db=object()),
        agent_id="test_agent",
    )

    assert set(card) == {
        "status",
        "type",
        "action_id",
        "action_type",
        "summary",
        "payload",
        "irreversible",
        "confirm_endpoint",
    }
    assert card["status"] == "confirmation_required"
    assert card["type"] == "action_required"
    assert card["action_type"] == declaration.name
    assert card["summary"] == "Run for later"
    assert card["payload"] == {"required_text": "later", "optional_count": 1}
    assert card["irreversible"] is False
    assert card["confirm_endpoint"] == "/api/v1/agents/execute"
    assert json.dumps(card).strip().startswith("{")
    assert card["action_id"] and card["confirm_endpoint"]
    assert calls == []


@pytest.mark.asyncio
async def test_execute_confirmation_runs_handler_exactly_once(user):
    calls: list[str] = []
    declaration = declare_capability("confirm_probe", calls, danger="write")
    card = await invoke_capability(
        declaration,
        {"required_text": "approved"},
        CapabilityContext(user=user, db=object()),
        agent_id="test_agent",
    )

    result = await execute_action(
        ExecuteActionRequest(action_id=card["action_id"], confirmed=True),
        current_user=user,
        db=object(),
    )

    assert result == {"handled": "approved"}
    assert calls == ["approved"]
    assert card["action_id"] not in agents._pending_actions
    with pytest.raises(HTTPException) as second_attempt:
        await execute_action(
            ExecuteActionRequest(action_id=card["action_id"], confirmed=True),
            current_user=user,
            db=object(),
        )
    assert second_attempt.value.status_code == 400
    assert calls == ["approved"]


@pytest.mark.asyncio
async def test_destructive_defaults_to_agent_denied(user):
    calls: list[str] = []
    declaration = declare_capability(
        "destructive_denied_probe",
        calls,
        danger="destructive",
    )

    definitions, handlers = registry_tools_for("test_agent")
    assert declaration.agent_allowed is False
    assert declaration.name not in handlers
    assert all(item["function"]["name"] != declaration.name for item in definitions)
    with pytest.raises(CapabilityAccessDenied):
        await invoke_capability(
            declaration,
            {"required_text": "no"},
            CapabilityContext(user=user, db=object()),
            agent_id="test_agent",
        )
    assert calls == []


@pytest.mark.asyncio
async def test_agent_allowed_destructive_emits_irreversible_card(user):
    calls: list[str] = []
    declaration = declare_capability(
        "destructive_allowed_probe",
        calls,
        danger="destructive",
        agent_allowed=True,
    )

    card = await invoke_capability(
        declaration,
        {"required_text": "danger"},
        CapabilityContext(user=user, db=object()),
        agent_id="test_agent",
    )

    assert card["status"] == "confirmation_required"
    assert card["irreversible"] is True
    assert calls == []


@pytest.mark.asyncio
async def test_out_of_scope_capability_is_not_offered_and_is_refused(user):
    declaration = declare_capability(
        "scoped_probe",
        [],
        scopes=["another_agent", UserRole.ADMIN.value],
    )

    definitions, handlers = registry_tools_for("blocked_agent")
    assert declaration.name not in handlers
    assert all(item["function"]["name"] != declaration.name for item in definitions)
    with pytest.raises(CapabilityAccessDenied):
        await invoke_capability(
            declaration,
            {"required_text": "blocked"},
            CapabilityContext(user=user, db=object()),
            agent_id="blocked_agent",
        )


@pytest.mark.asyncio
async def test_user_cannot_confirm_another_users_action(user):
    calls: list[str] = []
    declaration = declare_capability("ownership_probe", calls, danger="write")
    card = await invoke_capability(
        declaration,
        {"required_text": "owned"},
        CapabilityContext(user=user, db=object()),
        agent_id="test_agent",
    )
    other_user = SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.ADMIN,
        is_active=True,
    )

    with pytest.raises(HTTPException) as denied:
        await execute_action(
            ExecuteActionRequest(action_id=card["action_id"], confirmed=True),
            current_user=other_user,
            db=object(),
        )

    assert denied.value.status_code == 400
    assert calls == []
    assert card["action_id"] in agents._pending_actions


@pytest.mark.asyncio
async def test_expired_and_unknown_action_ids_are_rejected(user):
    declaration = declare_capability("expiry_probe", [], danger="write")
    card = await invoke_capability(
        declaration,
        {"required_text": "expired"},
        CapabilityContext(user=user, db=object()),
        agent_id="test_agent",
    )
    agents._pending_actions[card["action_id"]]["expires_at"] = (
        datetime.utcnow() - timedelta(seconds=1)
    ).isoformat()

    for action_id in (card["action_id"], "unknown-action"):
        with pytest.raises(HTTPException) as rejected:
            await execute_action(
                ExecuteActionRequest(action_id=action_id, confirmed=True),
                current_user=user,
                db=object(),
            )
        assert rejected.value.status_code == 400
        assert rejected.value.detail == "Action expired or not found"


def test_duplicate_capability_names_raise_at_declaration_time():
    declare_capability("duplicate_probe", [])

    with pytest.raises(ValueError, match="Duplicate capability name"):
        declare_capability("duplicate_probe", [])
