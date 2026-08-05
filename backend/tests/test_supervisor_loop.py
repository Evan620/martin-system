import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.agent_loop import AgentLoop, AgentResponse
from app.models.models import UserRole


class MockAgentLoop:
    def __init__(self, agent_id, response_text):
        self.agent_id = agent_id
        self._response = response_text
        self.call_count = 0

    async def run(self, query, thread_id, user_timezone=None, stream_callback=None,
                  auth_binding_token=None):
        self.call_count += 1
        return AgentResponse(content=self._response, agent_id=self.agent_id)


class MockLLM:
    def __init__(self, classify_result):
        self._result = classify_result

    async def complete(self, messages, tools=None, system_prompt=None):
        return {"content": self._result, "tool_calls": None}


@pytest.mark.asyncio
async def test_supervisor_routes_to_single_agent():
    from app.agents.supervisor_loop import SupervisorLoop
    agriculture = MockAgentLoop("agriculture", "Farming answer")
    loop = SupervisorLoop(
        llm=MockLLM('{"agent": "agriculture"}'),
        twg_agents={"agriculture": agriculture},
    )
    resp = await loop.run("Tell me about farming", thread_id="t1")
    assert agriculture.call_count == 1
    assert "Farming" in resp.content


@pytest.mark.asyncio
async def test_supervisor_routes_to_supervisor_for_general():
    from app.agents.supervisor_loop import SupervisorLoop
    supervisor_agent = MockAgentLoop("supervisor", "General answer")
    loop = SupervisorLoop(
        llm=MockLLM('{"agent": "supervisor"}'),
        twg_agents={},
        supervisor_agent=supervisor_agent,
    )
    resp = await loop.run("General question", thread_id="t2")
    assert supervisor_agent.call_count == 1


@pytest.mark.asyncio
async def test_supervisor_rbac_forces_twg_agent():
    from app.agents.supervisor_loop import SupervisorLoop
    agriculture = MockAgentLoop("agriculture", "Forced agriculture answer")
    loop = SupervisorLoop(
        llm=MockLLM('{"agent": "supervisor"}'),
        twg_agents={"agriculture": agriculture},
    )
    from app.tools._rbac import set_user_for_thread
    auth_token = set_user_for_thread("t3", str(uuid.uuid4()), UserRole.ADMIN)
    with (
        patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="agriculture"),
        patch.object(
            loop, "_build_scoped_pillar_agent", return_value=agriculture,
        ) as build_scoped,
    ):
        resp = await loop.run(
            "anything", thread_id="t3", twg_id="some-uuid",
            auth_binding_token=auth_token,
        )
    build_scoped.assert_called_once_with("agriculture", "some-uuid")
    assert agriculture.call_count == 1


class StreamingMockAgentLoop:
    def __init__(self, agent_id, tokens, final):
        self.agent_id = agent_id
        self._tokens = tokens
        self._final = final

    async def run(self, query, thread_id, user_timezone=None, stream_callback=None):
        if stream_callback:
            for t in self._tokens:
                await stream_callback(t)
        return AgentResponse(content=self._final, agent_id=self.agent_id)


@pytest.mark.asyncio
async def test_supervisor_stream_emits_final_response():
    """SupervisorLoop.stream must emit a "final_response" event carrying the
    answer — the API route drops the bare "done" event, so without this the
    client's response frame was always empty."""
    from app.agents.supervisor_loop import SupervisorLoop
    agent = StreamingMockAgentLoop("supervisor", ["Hello", " there"], "Hello there")
    loop = SupervisorLoop(
        llm=MockLLM('{"agent": "supervisor"}'),
        twg_agents={},
        supervisor_agent=agent,
    )
    events = []
    async for ev in loop.stream("hi", thread_id="s1"):
        events.append(ev)

    types = [e["type"] for e in events]
    assert types == ["token", "token", "final_response", "done"]
    final = next(e for e in events if e["type"] == "final_response")
    assert final["content"]["response"] == "Hello there"
    assert "citations" in final["content"]


@pytest.mark.asyncio
async def test_supervisor_multi_agent_dispatch():
    from app.agents.supervisor_loop import SupervisorLoop
    energy = MockAgentLoop("energy", "Energy answer")
    agriculture = MockAgentLoop("agriculture", "Agriculture answer")
    loop = SupervisorLoop(
        llm=MockLLM('{"agents": ["energy", "agriculture"]}'),
        twg_agents={"energy": energy, "agriculture": agriculture},
    )
    resp = await loop.run("Cross-sector question", thread_id="t4")
    assert energy.call_count == 1
    assert agriculture.call_count == 1
    assert "Energy" in resp.content or "Agriculture" in resp.content


@pytest.mark.asyncio
async def test_scoped_same_pillar_requests_bind_exact_twg_and_never_use_cached_agent():
    """Each authorized TWG request gets its exact scope, even for one pillar.

    This also proves a scoped write path cannot silently fall back to the cached
    pillar agent, whose default lookup may be bound to the first TWG in that
    pillar.
    """
    from app.agents.supervisor_loop import SupervisorLoop

    first_twg_id = str(uuid.uuid4())
    second_twg_id = str(uuid.uuid4())
    routed_calls = []

    class ExactScopedLoop(AgentLoop):
        async def run(self, query, thread_id, user_timezone=None, stream_callback=None,
                      auth_binding_token=None):
            routed_calls.append((self.agent_id, self.twg_id, query, thread_id))
            return AgentResponse(content=self.twg_id, agent_id=self.agent_id)

    cached_first_twg_agent = ExactScopedLoop(
        "energy", "cached prompt", [], {}, object(), twg_id="cached-twg"
    )
    loop = SupervisorLoop(
        llm=MockLLM('{"agent": "supervisor"}'),
        twg_agents={"energy": cached_first_twg_agent},
    )
    from app.tools._rbac import set_user_for_thread
    auth_token = set_user_for_thread(
        "shared-thread", str(uuid.uuid4()), UserRole.ADMIN
    )

    with (
        patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="energy"),
    ):
        first = await loop.run(
            "Create meeting one", thread_id="shared-thread", twg_id=first_twg_id,
            auth_binding_token=auth_token,
        )
        second = await loop.run(
            "Create meeting two", thread_id="shared-thread", twg_id=second_twg_id,
            auth_binding_token=auth_token,
        )

    assert routed_calls == [
        ("energy", first_twg_id, "Create meeting one", "shared-thread"),
        ("energy", second_twg_id, "Create meeting two", "shared-thread"),
    ]
    assert first.content == first_twg_id
    assert second.content == second_twg_id
    assert cached_first_twg_agent.twg_id == "cached-twg"


@pytest.mark.asyncio
@pytest.mark.parametrize("context", [None, (str(uuid.uuid4()), UserRole.TWG_FACILITATOR)])
async def test_scoped_routing_fails_closed_without_authorized_thread_user(context):
    """Missing context and a facilitator outside the TWG cannot run an agent."""
    from app.agents.supervisor_loop import SupervisorLoop

    agent = MockAgentLoop("energy", "must not run")
    loop = SupervisorLoop(llm=MockLLM("{}"), twg_agents={"energy": agent})
    requested_twg = str(uuid.uuid4())

    with (
        patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="energy"),
        patch("app.tools._rbac.get_thread_user_context", return_value=context),
        patch.object(loop, "_thread_user_has_twg_access", new=AsyncMock(return_value=False), create=True),
    ):
        response = await loop.run("private", "restricted-thread", twg_id=requested_twg)

    assert response.content == "Access denied: unauthorized TWG scope."
    assert agent.call_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "membership_count", "expected"),
    [
        (UserRole.TWG_FACILITATOR, 1, True),
        (UserRole.TWG_MEMBER, 1, True),
        (UserRole.TWG_FACILITATOR, 0, False),
        (UserRole.ADMIN, 0, True),
        (UserRole.SECRETARIAT_LEAD, 0, True),
    ],
)
async def test_thread_user_twg_policy(role, membership_count, expected):
    """Central policy allows secretariat cross-TWG and restricted own-TWG only."""
    from app.agents.supervisor_loop import SupervisorLoop

    loop = SupervisorLoop(llm=MockLLM("{}"), twg_agents={})
    user_id = str(uuid.uuid4())
    twg_id = str(uuid.uuid4())
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = 1 if membership_count else None
    db = AsyncMock()
    db.execute.return_value = scalar

    class FakeDbContext:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *args):
            return False

    with (
        patch("app.tools._rbac.get_thread_user_context", return_value=(user_id, role)),
        patch("app.core.database.get_db_session_context", return_value=FakeDbContext()),
    ):
        actual = await loop._thread_user_has_twg_access("policy-thread", twg_id)

    assert actual is expected
    if role in (UserRole.ADMIN, UserRole.SECRETARIAT_LEAD):
        db.execute.assert_not_awaited()
    else:
        db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_scoped_routing_rejects_contextvar_without_thread_binding():
    from app.agents.supervisor_loop import SupervisorLoop
    from app.tools._rbac import set_user_context

    set_user_context(str(uuid.uuid4()), UserRole.ADMIN)
    agent = MockAgentLoop("energy", "must not run")
    loop = SupervisorLoop(llm=MockLLM("{}"), twg_agents={"energy": agent})
    with patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="energy"):
        response = await loop.run(
            "private", f"unbound-{uuid.uuid4()}", twg_id=str(uuid.uuid4())
        )

    assert response.content == "Access denied: unauthorized TWG scope."
    assert agent.call_count == 0


def test_scoped_clone_preserves_custom_loop_and_does_not_mutate_cache():
    """Resource Mobilization custom handlers/config survive exact-TWG cloning."""
    from app.agents.supervisor_loop import SupervisorLoop

    async def summary_handler():
        return "summary"

    async def matching_handler(project_name):
        return project_name

    custom_tools = [
        {"type": "function", "function": {"name": "get_deal_pipeline_summary_tool"}},
        {"type": "function", "function": {"name": "get_project_matches_tool"}},
    ]
    cached_twg = str(uuid.uuid4())
    requested_twg = str(uuid.uuid4())
    llm = object()
    cached = AgentLoop(
        agent_id="resource_mobilization",
        system_prompt="exact investment prompt",
        tools=custom_tools,
        tool_map={
            "get_deal_pipeline_summary_tool": summary_handler,
            "get_project_matches_tool": matching_handler,
        },
        llm=llm,
        twg_id=cached_twg,
        max_iterations=7,
        max_history=15,
    )
    supervisor = SupervisorLoop(llm=MockLLM("{}"), twg_agents={"resource_mobilization": cached})

    scoped = supervisor._build_scoped_pillar_agent("resource_mobilization", requested_twg)

    assert scoped is not cached
    assert scoped.agent_id == cached.agent_id
    assert scoped.system_prompt == cached.system_prompt
    assert scoped.tools == cached.tools
    assert scoped.tool_map == cached.tool_map
    assert scoped.llm is llm
    assert scoped.max_iterations == 7
    assert scoped.max_history == 15
    assert scoped.twg_id == requested_twg
    assert cached.twg_id == cached_twg
    assert scoped.tool_map["get_deal_pipeline_summary_tool"] is summary_handler
    assert scoped.tool_map["get_project_matches_tool"] is matching_handler


@pytest.mark.asyncio
async def test_concurrent_and_successive_scoped_clones_are_isolated_and_history_is_thread_keyed():
    from app.agents.supervisor_loop import SupervisorLoop

    cached_twg = str(uuid.uuid4())
    first_twg = str(uuid.uuid4())
    second_twg = str(uuid.uuid4())
    cached = AgentLoop("energy", "prompt", [], {}, MockLLM([]), twg_id=cached_twg)
    supervisor = SupervisorLoop(llm=MockLLM("{}"), twg_agents={"energy": cached})

    first, second = await asyncio.gather(
        asyncio.to_thread(supervisor._build_scoped_pillar_agent, "energy", first_twg),
        asyncio.to_thread(supervisor._build_scoped_pillar_agent, "energy", second_twg),
    )
    third = supervisor._build_scoped_pillar_agent("energy", first_twg)

    assert first.twg_id == third.twg_id == first_twg
    assert second.twg_id == second_twg
    assert cached.twg_id == cached_twg
    assert len({id(first), id(second), id(third), id(cached)}) == 4
    first._get_history("same-thread").append({"role": "user", "content": "remember"})
    assert third._get_history("same-thread")[-1]["content"] == "remember"
    assert second._get_history("other-thread") == []
