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


@pytest.mark.asyncio
async def test_member_task_is_scoped_to_member_agent(test_user, monkeypatch):
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
async def test_member_task_denied_without_twg_access(test_user, monkeypatch):
    monkeypatch.setattr(agents_module, "has_twg_access", lambda user, tid: False)
    bg = BackgroundTasks()

    with pytest.raises(HTTPException) as ei:
        await assign_agent_task(_task(uuid.uuid4()), bg, _FakeRequest(), current_user=test_user)

    assert ei.value.status_code == 403
    assert bg.tasks == []  # nothing scheduled when denied


@pytest.mark.asyncio
async def test_admin_task_not_member_scoped(admin_user):
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
                                  user_timezone=None, force_agent_id=None):
            calls.append(force_agent_id)
            return {"response": "ok"}

    monkeypatch.setattr(agents_module, "get_supervisor", lambda: _FakeSup())
    await run_background_task("tid", "hello", "twg-1", "UTC", force_agent_id="member")
    assert calls == ["member"]
