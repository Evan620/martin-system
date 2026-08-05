"""Regression: a TWG_MEMBER's POST /agents/task must run under the
member-scoped agent (MEMBER_TOOLS), never the facilitator/pillar agent.

The hole (now fixed): /agents/task -> run_background_task -> chat_with_tools was
dispatched WITHOUT force_agent_id, so a member's task ran under the pillar agent
(granted send_email, create_meeting_invite, advance_project_stage, ...),
bypassing the MEMBER_TOOLS gate. The fix scopes a member to
force_agent_id="member" bound to their verified TWG, and denies a member who
lacks access to the requested TWG. Admin/facilitator routing is unchanged.

These call the route function directly (deterministic — no reliance on when
Starlette runs the background task) and assert what gets scheduled.
"""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.background import BackgroundTasks

import app.api.routes.agents as agents_module
from app.api.routes.agents import assign_agent_task, run_background_task
from app.models.models import UserRole
from app.schemas.schemas import AgentTaskRequest


class _FakeRequest:
    """Minimal stand-in for fastapi.Request: only .headers.get is used."""

    def __init__(self):
        self.headers = {}


def _task(twg_id):
    return AgentTaskRequest(
        task_type="drafting", twg_id=twg_id, details={}, title="draft a communique"
    )


def _user(role):
    return SimpleNamespace(id=uuid.uuid4(), role=role)


@pytest.mark.asyncio
async def test_member_task_is_scoped_to_member_agent(monkeypatch):
    test_user = _user(UserRole.TWG_MEMBER)
    assert test_user.role == UserRole.TWG_MEMBER  # conftest default
    monkeypatch.setattr(agents_module, "has_twg_access", lambda user, tid: True)
    twg_id = uuid.uuid4()
    bg = BackgroundTasks()

    result = await assign_agent_task(_task(twg_id), bg, _FakeRequest(), current_user=test_user)

    assert result["status"] == "queued"
    assert len(bg.tasks) == 1
    task = bg.tasks[0]
    assert task.func is run_background_task
    # The member's task is gated to the member agent, bound to their TWG.
    assert task.kwargs["force_agent_id"] == "member"
    assert task.kwargs["twg_id"] == str(twg_id)


@pytest.mark.asyncio
async def test_member_task_denied_without_twg_access(monkeypatch):
    test_user = _user(UserRole.TWG_MEMBER)
    monkeypatch.setattr(agents_module, "has_twg_access", lambda user, tid: False)
    bg = BackgroundTasks()

    with pytest.raises(HTTPException) as ei:
        await assign_agent_task(_task(uuid.uuid4()), bg, _FakeRequest(), current_user=test_user)

    assert ei.value.status_code == 403
    assert bg.tasks == []  # nothing scheduled when denied


@pytest.mark.asyncio
async def test_admin_task_not_member_scoped():
    admin_user = _user(UserRole.ADMIN)
    bg = BackgroundTasks()

    result = await assign_agent_task(_task(uuid.uuid4()), bg, _FakeRequest(), current_user=admin_user)

    assert result["status"] == "queued"
    # No member gate for admins — routing is unchanged (force_agent_id=None).
    assert bg.tasks[0].kwargs["force_agent_id"] is None


@pytest.mark.asyncio
async def test_run_background_task_forwards_force_agent_id(monkeypatch):
    calls = []

    class _FakeSup:
        async def chat_with_tools(self, message, twg_id=None, thread_id=None,
                                  user_timezone=None, force_agent_id=None,
                                  auth_binding_token=None):
            calls.append(force_agent_id)
            return {"response": "ok"}

    monkeypatch.setattr(agents_module, "get_supervisor", lambda: _FakeSup())
    await run_background_task(
        "tid", "hello", "twg-1", "UTC", force_agent_id="member",
        user_id=str(uuid.uuid4()), user_role=UserRole.TWG_MEMBER,
    )
    assert calls == ["member"]


@pytest.mark.asyncio
async def test_task_background_entry_binds_initiating_user_and_cleans_up(monkeypatch):
    """Execute the real queued BackgroundTask and authorize its supervisor entry."""
    from app.tools._rbac import get_thread_user_context

    observed = []

    admin_user = SimpleNamespace(id=uuid.uuid4(), role=UserRole.ADMIN)

    class _FakeSup:
        async def chat_with_tools(self, message, twg_id=None, thread_id=None,
                                  user_timezone=None, force_agent_id=None,
                                  auth_binding_token=None):
            observed.append((
                thread_id,
                get_thread_user_context(thread_id, auth_binding_token),
            ))
            return {"response": "ok"}

    monkeypatch.setattr(agents_module, "get_supervisor", lambda: _FakeSup())
    bg = BackgroundTasks()
    result = await assign_agent_task(
        _task(uuid.uuid4()), bg, _FakeRequest(), current_user=admin_user
    )

    queued = bg.tasks[0]
    assert "user_id" in queued.kwargs and "user_role" in queued.kwargs
    assert "user_id" not in result and "user_role" not in result
    await queued()

    task_id = result["task_id"]
    assert observed == [(task_id, (str(admin_user.id), admin_user.role))]
    assert get_thread_user_context(task_id) is None


@pytest.mark.asyncio
async def test_task_background_entry_rejects_rebound_owner(monkeypatch):
    """A queued run cannot consume a newer binding owned by another run."""
    from app.tools._rbac import get_thread_user_context, set_user_for_thread

    observed = []

    admin_user = SimpleNamespace(id=uuid.uuid4(), role=UserRole.ADMIN)

    class _FakeSup:
        async def chat_with_tools(self, message, twg_id=None, thread_id=None,
                                  user_timezone=None, force_agent_id=None,
                                  auth_binding_token=None):
            observed.append(
                get_thread_user_context(thread_id, auth_binding_token)
            )
            return {"response": "ok"}

    monkeypatch.setattr(agents_module, "get_supervisor", lambda: _FakeSup())
    bg = BackgroundTasks()
    result = await assign_agent_task(
        _task(uuid.uuid4()), bg, _FakeRequest(), current_user=admin_user
    )
    task_id = result["task_id"]
    newer_user = str(uuid.uuid4())
    newer_token = set_user_for_thread(task_id, newer_user, UserRole.TWG_MEMBER)

    await bg.tasks[0]()

    assert observed == [(str(admin_user.id), UserRole.ADMIN)]
    assert get_thread_user_context(task_id, newer_token) is None


@pytest.mark.asyncio
async def test_task_background_entry_denies_unauthorized_facilitator_scope(monkeypatch):
    """The real queued entry reaches central scope auth and never runs the agent."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.agents.agent_loop import AgentResponse
    from app.agents.supervisor_loop import SupervisorLoop

    class _Agent:
        def __init__(self):
            self.run = AsyncMock(
                return_value=AgentResponse(content="must not run", agent_id="energy")
            )

    agent = _Agent()
    loop = SupervisorLoop(llm=object(), twg_agents={"energy": agent})
    responses = []

    class _Adapter:
        async def chat_with_tools(self, message, twg_id=None, thread_id=None,
                                  user_timezone=None, force_agent_id=None,
                                  auth_binding_token=None):
            response = await loop.run(
                message,
                thread_id,
                twg_id=twg_id,
                force_agent_id=force_agent_id,
                auth_binding_token=auth_binding_token,
            )
            responses.append(response.content)

    facilitator = _user(UserRole.TWG_FACILITATOR)
    bg = BackgroundTasks()
    monkeypatch.setattr(agents_module, "get_supervisor", lambda: _Adapter())
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = membership_result

    class _DbContext:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *args):
            return False

    with (
        patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="energy"),
        patch("app.core.database.get_db_session_context", return_value=_DbContext()),
    ):
        await assign_agent_task(
            _task(uuid.uuid4()), bg, _FakeRequest(), current_user=facilitator
        )
        await bg.tasks[0]()

    assert responses == ["Access denied: unauthorized TWG scope."]
    agent.run.assert_not_awaited()
