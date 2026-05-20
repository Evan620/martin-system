import pytest
import asyncio
from unittest.mock import AsyncMock

class MockLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._calls = []

    async def complete(self, messages, tools=None, system_prompt=None):
        self._calls.append(messages)
        return self._responses.pop(0)

    async def stream_tokens(self, messages, system_prompt=None, on_token=None, tools=None, **kw):
        resp = self._responses.pop(0)
        if on_token and resp.get("content"):
            await on_token(resp["content"])
        return resp


@pytest.mark.asyncio
async def test_agent_loop_simple_response():
    from app.agents.agent_loop import AgentLoop
    AgentLoop._history.clear()
    llm = MockLLM([{"content": "West Africa has great potential.", "tool_calls": None}])
    loop = AgentLoop(
        agent_id="agriculture",
        system_prompt="You are an agriculture expert.",
        tools=[],
        tool_map={},
        llm=llm,
        max_iterations=5,
    )
    resp = await loop.run("What about West Africa?", thread_id="t1")
    assert "West Africa" in resp.content
    assert len(llm._calls) == 1


@pytest.mark.asyncio
async def test_agent_loop_tool_call_then_respond():
    from app.agents.agent_loop import AgentLoop
    AgentLoop._history.clear()
    mock_tool = AsyncMock(return_value="Soil degradation is the main issue.")
    llm = MockLLM([
        {"content": "", "tool_calls": [{"id": "tc1", "name": "get_info", "args": {"q": "soil"}, "_thought_sig": None}]},
        {"content": "Based on search: soil degradation.", "tool_calls": None},
    ])
    loop = AgentLoop(
        agent_id="agriculture",
        system_prompt="Expert.",
        tools=[],
        tool_map={"get_info": mock_tool},
        llm=llm,
        max_iterations=5,
    )
    resp = await loop.run("Tell me about soil", thread_id="t2")
    assert "soil" in resp.content.lower()
    mock_tool.assert_called_once_with(q="soil")
    assert len(llm._calls) == 2


@pytest.mark.asyncio
async def test_agent_loop_history_preserved():
    from app.agents.agent_loop import AgentLoop
    AgentLoop._history.clear()
    llm = MockLLM([
        {"content": "First answer.", "tool_calls": None},
        {"content": "Second answer.", "tool_calls": None},
    ])
    loop = AgentLoop(
        agent_id="agriculture",
        system_prompt="Expert.",
        tools=[],
        tool_map={},
        llm=llm,
        max_iterations=5,
    )
    await loop.run("First question", thread_id="t3")
    await loop.run("Second question", thread_id="t3")
    second_call_msgs = llm._calls[1]
    assert any(m.get("content") == "First question" for m in second_call_msgs)


@pytest.mark.asyncio
async def test_agent_loop_max_iterations():
    from app.agents.agent_loop import AgentLoop
    AgentLoop._history.clear()
    always_tool = [
        {"content": "", "tool_calls": [{"id": f"tc{i}", "name": "t", "args": {}, "_thought_sig": None}]}
        for i in range(20)
    ]
    llm = MockLLM(always_tool)
    mock_tool = AsyncMock(return_value="result")
    loop = AgentLoop(
        agent_id="agri",
        system_prompt="X",
        tools=[],
        tool_map={"t": mock_tool},
        llm=llm,
        max_iterations=3,
    )
    resp = await loop.run("loop forever", thread_id="t4")
    assert mock_tool.call_count <= 3
