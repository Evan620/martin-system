import pytest
import asyncio
import uuid
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


class _FakeToolFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments  # JSON string (OpenAI wire shape)


class _FakeToolCall:
    def __init__(self, id, function):
        self.id = id
        self.function = function


class _FakeResponseWrapper:
    """Mimics llm_service._AnthropicResponseWrapper (returned by stream_tokens)."""
    def __init__(self, content, tool_calls):
        self.content = content
        self.tool_calls = tool_calls if tool_calls else None


class StreamShapeMockLLM:
    """Mimics the REAL stream_tokens contract: returns a plain string when
    there are no tool calls, and an OpenAI-shaped wrapper object (NOT a dict)
    when the model calls a tool. Regression for the empty-answer bug where
    AgentLoop only unpacked dict results, so streaming tool turns never
    executed tools and returned the wrapper's repr as the answer."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._calls = []

    async def complete(self, messages, tools=None, system_prompt=None):
        raise AssertionError("streaming path must use stream_tokens")

    async def stream_tokens(self, messages, system_prompt=None, on_token=None, tools=None, **kw):
        self._calls.append(messages)
        resp = self._responses.pop(0)
        if on_token and isinstance(resp, str):
            await on_token(resp)
        return resp


@pytest.mark.asyncio
async def test_agent_loop_streaming_tool_call_then_respond():
    """A tool-call turn on the STREAMING path (stream_callback set) must
    execute the tool and return the second-pass answer — not the wrapper repr."""
    from app.agents.agent_loop import AgentLoop
    AgentLoop._history.clear()
    mock_tool = AsyncMock(return_value="3 meetings tomorrow")
    llm = StreamShapeMockLLM([
        _FakeResponseWrapper(
            content="",
            tool_calls=[_FakeToolCall("tc1", _FakeToolFunction("get_my_meetings", '{"when": "next"}'))],
        ),
        "Your next meeting is tomorrow at 10am.",
    ])
    tokens = []

    async def on_token(t):
        tokens.append(t)

    loop = AgentLoop(
        agent_id="member",
        system_prompt="You are Martin.",
        tools=[{"type": "function", "function": {"name": "get_my_meetings"}}],
        tool_map={"get_my_meetings": mock_tool},
        llm=llm,
        max_iterations=5,
    )
    resp = await loop.run("What is my next meeting?", thread_id="ts1", stream_callback=on_token)

    mock_tool.assert_called_once_with(when="next")
    assert resp.content == "Your next meeting is tomorrow at 10am."
    assert resp.tool_calls_made == ["get_my_meetings"]
    assert "object at 0x" not in resp.content
    # second-pass tokens streamed
    assert "".join(tokens) == "Your next meeting is tomorrow at 10am."
    # second LLM pass received the tool result in history
    second_msgs = llm._calls[1]
    assert any(m.get("role") == "tool" and "3 meetings" in m.get("content", "") for m in second_msgs)


@pytest.mark.asyncio
async def test_agent_loop_streaming_plain_string_response():
    """No-tool streaming turns return the plain string stream_tokens gives back."""
    from app.agents.agent_loop import AgentLoop
    AgentLoop._history.clear()
    llm = StreamShapeMockLLM(["Hi, I'm Martin."])

    async def on_token(t):
        pass

    loop = AgentLoop(
        agent_id="member",
        system_prompt="You are Martin.",
        tools=[],
        tool_map={},
        llm=llm,
        max_iterations=5,
    )
    resp = await loop.run("hello", thread_id="ts2", stream_callback=on_token)
    assert resp.content == "Hi, I'm Martin."


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_twg_id",
    ["Carren Feature Test", str(uuid.uuid4())],
    ids=["display-name", "different-uuid"],
)
async def test_agent_loop_raw_handler_replaces_model_twg_id_with_context(model_twg_id):
    """Raw tool_map handlers must obey the agent's authorized TWG scope.

    The model may emit a display name or a valid but unrelated UUID. Neither may
    reach a scoped handler when the AgentLoop already has an authorized twg_id.
    """
    from app.agents.agent_loop import AgentLoop

    contextual_twg_id = str(uuid.uuid4())
    received = []

    async def raw_handler(twg_id, title):
        received.append({"twg_id": twg_id, "title": title})
        return {"status": "ok"}

    loop = AgentLoop(
        agent_id="energy",
        system_prompt="Expert.",
        tools=[],
        tool_map={"create_meeting": raw_handler},
        llm=MockLLM([]),
        twg_id=contextual_twg_id,
    )

    await loop._execute_tools(
        [{
            "id": "create-1",
            "name": "create_meeting",
            "args": {"twg_id": model_twg_id, "title": "Scoped meeting"},
        }],
        thread_id="scope-test",
        user_timezone=None,
    )

    assert received == [{
        "twg_id": contextual_twg_id,
        "title": "Scoped meeting",
    }]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_twg_id",
    ["Carren Feature Test", str(uuid.uuid4())],
    ids=["kwargs-display-name", "kwargs-foreign-uuid"],
)
async def test_agent_loop_kwargs_handler_replaces_model_twg_id_with_context(model_twg_id):
    """A **kwargs raw handler accepts scope injection and must not trust the model."""
    from app.agents.agent_loop import AgentLoop

    contextual_twg_id = str(uuid.uuid4())
    received = []

    async def raw_handler(**kwargs):
        received.append(kwargs)
        return {"status": "ok"}

    loop = AgentLoop(
        agent_id="energy",
        system_prompt="Expert.",
        tools=[],
        tool_map={"create_meeting": raw_handler},
        llm=MockLLM([]),
        twg_id=contextual_twg_id,
    )

    await loop._execute_tools(
        [{
            "id": "create-kwargs-1",
            "name": "create_meeting",
            "args": {"twg_id": model_twg_id, "title": "Scoped meeting"},
        }],
        thread_id="kwargs-scope-test",
        user_timezone=None,
    )

    assert received == [{
        "twg_id": contextual_twg_id,
        "title": "Scoped meeting",
    }]


@pytest.mark.asyncio
async def test_agent_loop_kwargs_handler_preserves_unscoped_supervisor_twg_argument():
    from app.agents.agent_loop import AgentLoop

    received = []

    async def raw_handler(**kwargs):
        received.append(kwargs)
        return {"status": "ok"}

    loop = AgentLoop("supervisor", "General.", [], {"tool": raw_handler}, MockLLM([]))
    await loop._execute_tools(
        [{"id": "unscoped", "name": "tool", "args": {"twg_id": "energy"}}],
        thread_id="unscoped-supervisor",
        user_timezone=None,
    )

    assert received == [{"twg_id": "energy"}]
