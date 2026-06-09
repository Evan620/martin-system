"""Regression: a TWG_MEMBER's slash command must NOT escape the member gate.

The hole (now fixed): POST /chat/stream and POST /chat/enhanced parse a member's
slash command (e.g. '/email send ...', '/broadcast ...') as MessageParseType.COMMAND
and dispatched it via handle_command -> supervisor.chat_with_tools WITHOUT
force_agent_id. With twg_id set + force_agent_id=None, SupervisorLoop.run routes to
the facilitator/pillar agent (granted send_email, create_meeting_invite,
advance_project_stage, get_twg_members, ...), fully bypassing the MEMBER_TOOLS gate.

Fix: a TWG_MEMBER's message is forced to NATURAL so it flows through the
natural-language path that threads force_agent_id="member" — the member always runs
under agent_id="member" (gated to MEMBER_TOOLS), never the pillar agent.

These tests assert that contract at the route boundary by capturing what
force_agent_id the supervisor is actually invoked with, and proving the
command/pillar path (handle_command -> chat_with_tools) is never reached for a
member command.
"""
import json
import uuid

import pytest

import app.api.routes.agents as agents_module
from app.models.models import UserRole


class _FakeSupervisor:
    """Records how the route invokes the supervisor.

    - stream_chat_events is the NATURAL-language streaming path. The route passes
      force_agent_id here; we capture it. For a member it MUST be "member".
    - chat_with_tools is what handle_command/handle_mention call (the COMMAND /
      MENTION / MIXED branches). The route's command branches never pass
      force_agent_id, so a member reaching this is the bug. We record every call.
    """

    def __init__(self):
        self.stream_force_agent_ids = []
        self.chat_with_tools_calls = []  # list of force_agent_id values (None for command path)

    async def stream_chat_events(self, message, twg_id=None, thread_id=None,
                                 user_timezone=None, force_agent_id=None):
        self.stream_force_agent_ids.append(force_agent_id)
        yield {"type": "final_response", "content": "ok"}

    async def chat_with_tools(self, message, twg_id=None, thread_id=None,
                              user_timezone=None, force_agent_id=None):
        self.chat_with_tools_calls.append(force_agent_id)
        return {"response": "ok", "citations": []}


@pytest.fixture
def fake_supervisor(monkeypatch):
    fake = _FakeSupervisor()
    monkeypatch.setattr(agents_module, "get_supervisor", lambda: fake)
    return fake


def _collect_stream(resp_text):
    """Parse SSE 'data:' lines into event dicts."""
    events = []
    for line in resp_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                events.append(json.loads(line[len("data:"):].strip()))
            except json.JSONDecodeError:
                pass
    return events


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "/email send to:victim@example.org subject:Hi body:hello",
        "/broadcast everyone please submit your reports",
        "/schedule a meeting next tuesday",
    ],
)
async def test_member_slash_command_runs_under_member_agent_in_stream(
    client, test_user, normal_user_token_headers, fake_supervisor, message
):
    """A TWG_MEMBER's slash command on POST /chat/stream runs under
    force_agent_id='member' (member-scoped), and NEVER through the
    command/pillar path (chat_with_tools without force_agent_id)."""
    assert test_user.role == UserRole.TWG_MEMBER  # conftest default

    resp = await client.post(
        "/api/v1/agents/chat/stream",
        headers=normal_user_token_headers,
        json={"message": message, "twg_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 200, resp.text

    # The member's command was forced to NATURAL → routed through the streaming
    # natural-language path with force_agent_id="member".
    assert fake_supervisor.stream_force_agent_ids == ["member"], (
        f"member command did not run under the member agent: "
        f"{fake_supervisor.stream_force_agent_ids}"
    )
    # And it NEVER reached the command/pillar path (handle_command -> chat_with_tools).
    assert fake_supervisor.chat_with_tools_calls == [], (
        f"member command leaked to the pillar/command path: "
        f"{fake_supervisor.chat_with_tools_calls}"
    )

    # The parsing event must report NATURAL (the gate downgraded the command).
    events = _collect_stream(resp.text)
    parsing = [e for e in events if e.get("type") == "parsing"]
    assert parsing, "expected a parsing event"
    assert "NATURAL" in parsing[0]["result"]["message_type"]


@pytest.mark.asyncio
async def test_admin_slash_command_still_uses_command_path(
    client, admin_user, admin_token_headers, fake_supervisor
):
    """No regression: an ADMIN's slash command still flows through the command
    path (handle_command -> chat_with_tools), not the member gate."""
    resp = await client.post(
        "/api/v1/agents/chat/stream",
        headers=admin_token_headers,
        json={"message": "/email send to:x@example.org subject:Hi body:yo"},
    )
    assert resp.status_code == 200, resp.text
    # Admin command goes through handle_command -> chat_with_tools.
    assert fake_supervisor.chat_with_tools_calls, "admin command should use the command path"
    # Admin command was NOT downgraded to the member streaming path.
    assert fake_supervisor.stream_force_agent_ids == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "/email send to:victim@example.org subject:Hi body:hello",
        "/broadcast everyone please submit your reports",
    ],
)
async def test_member_slash_command_runs_under_member_agent_in_enhanced(
    client, test_user, normal_user_token_headers, fake_supervisor, monkeypatch, message
):
    """POST /chat/enhanced: a TWG_MEMBER's slash command runs under
    force_agent_id='member' via chat_with_tools, never via handle_command."""
    assert test_user.role == UserRole.TWG_MEMBER

    # The member must have access to the TWG they pass (the enhanced gate verifies).
    twg_id = uuid.uuid4()
    monkeypatch.setattr(agents_module, "has_twg_access", lambda user, tid: True)

    resp = await client.post(
        "/api/v1/agents/chat/enhanced",
        headers=normal_user_token_headers,
        json={"message": message, "twg_id": str(twg_id)},
    )
    assert resp.status_code == 200, resp.text

    # Forced to NATURAL → single chat_with_tools call carrying force_agent_id="member".
    assert fake_supervisor.chat_with_tools_calls == ["member"], (
        f"member enhanced command did not run under the member agent: "
        f"{fake_supervisor.chat_with_tools_calls}"
    )


@pytest.mark.asyncio
async def test_member_enhanced_requires_twg_id(
    client, test_user, normal_user_token_headers, fake_supervisor
):
    """POST /chat/enhanced denies a member with no twg_id with a real 400
    (not a masked 200 agent message), and never invokes the supervisor."""
    resp = await client.post(
        "/api/v1/agents/chat/enhanced",
        headers=normal_user_token_headers,
        json={"message": "/broadcast hi"},
    )
    assert resp.status_code == 400, resp.text
    assert fake_supervisor.chat_with_tools_calls == []
    assert fake_supervisor.stream_force_agent_ids == []
