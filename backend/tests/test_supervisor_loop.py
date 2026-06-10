import pytest
import asyncio
from unittest.mock import patch

from app.agents.agent_loop import AgentLoop, AgentResponse


class MockAgentLoop:
    def __init__(self, agent_id, response_text):
        self.agent_id = agent_id
        self._response = response_text
        self.call_count = 0

    async def run(self, query, thread_id, user_timezone=None, stream_callback=None):
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
    with patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="agriculture"):
        resp = await loop.run("anything", thread_id="t3", twg_id="some-uuid")
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
