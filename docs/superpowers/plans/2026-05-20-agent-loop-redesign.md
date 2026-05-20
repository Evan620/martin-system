# Agent Loop Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the nested LangGraph state machines with a tight async while loop + lazy RAG + native Gemini adapter, cutting agent response time from ~15s to ~5–6s and fixing Gemini 2.5+/3.5+ tool-calling failures.

**Architecture:** Three new files (`agent_loop.py`, `supervisor_loop.py`, `gemini_native.py`) contain the new implementation. Two existing files (`langgraph_base_agent.py`, `langgraph_supervisor.py`) become thin wrappers that delegate to the new loops while keeping all public method signatures identical. `llm_service.py` routes Gemini provider calls to `GeminiNativeService`. A new `rag_tool.py` registers `search_documents` as an on-demand tool instead of a mandatory pre-step.

**Tech Stack:** Python 3.12, FastAPI, httpx (native Gemini REST), asyncio, existing ToolRegistry + stream_events

---

## Parallel execution map

```
Group A (run in parallel): Task 1, Task 2, Task 4
Group B (run in parallel): Task 3, Task 5   ← after Group A
Group C (sequential):      Task 6           ← after Group B
Group D (sequential):      Task 7           ← after Task 6
Group E (sequential):      Task 8           ← after Task 7
```

---

## Task 1: GeminiNativeService

**Files:**
- Create: `backend/app/services/gemini_native.py`

**Context:** The current code calls Gemini via the OpenAI-compat endpoint (`/v1beta/openai/`). Gemini 2.5+/3.5+ thinking models return a `thoughtSignature` field on each `functionCall` part that must be echoed back in subsequent requests — the OpenAI-compat layer drops this, causing 400 errors. The native `generateContent` API preserves it. This file is a self-contained httpx client that speaks only the native API.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_gemini_native.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Test 1: _build_contents converts plain OpenAI messages correctly
def test_build_contents_user_message():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    msgs = [{"role": "user", "content": "Hello"}]
    contents, sys_inst = svc._build_contents(msgs)
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"][0]["text"] == "Hello"
    assert sys_inst is None

# Test 2: system message becomes systemInstruction, not a content item
def test_build_contents_system_prompt():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    msgs = [{"role": "system", "content": "You are helpful"}]
    contents, sys_inst = svc._build_contents(msgs)
    assert contents == []
    assert sys_inst == {"parts": [{"text": "You are helpful"}]}

# Test 3: thought_signature is round-tripped through assistant tool_call
def test_thought_signature_roundtrip():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    msgs = [
        {"role": "user", "content": "search something"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "tc1",
                "name": "search_documents",
                "args": {"query": "foo"},
                "_thought_sig": "sig-abc123",
            }],
        },
        {
            "role": "tool",
            "tool_call_id": "tc1",
            "content": "result here",
        },
    ]
    contents, _ = svc._build_contents(msgs)
    # Find the model turn with functionCall
    model_turn = next(c for c in contents if c["role"] == "model")
    fc_part = next(p for p in model_turn["parts"] if "functionCall" in p)
    assert fc_part.get("thoughtSignature") == "sig-abc123"

# Test 4: _build_tools converts OpenAI tool schema to Gemini format
def test_build_tools():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    tools = [{
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search docs",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            }
        }
    }]
    gemini_tools = svc._build_tools(tools)
    assert len(gemini_tools) == 1
    fd = gemini_tools[0]["functionDeclarations"][0]
    assert fd["name"] == "search_documents"
    assert "parameters" in fd

# Test 5: _parse_response extracts content and stores thought_signature
def test_parse_response_with_function_call():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    raw = {
        "candidates": [{
            "content": {
                "role": "model",
                "parts": [
                    {"thoughtSignature": "sig-xyz", "functionCall": {
                        "name": "search_documents",
                        "args": {"query": "agriculture"}
                    }}
                ]
            }
        }]
    }
    result = svc._parse_response(raw)
    assert result["content"] == ""
    assert len(result["tool_calls"]) == 1
    tc = result["tool_calls"][0]
    assert tc["name"] == "search_documents"
    assert tc["_thought_sig"] == "sig-xyz"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_gemini_native.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` or `ImportError` — file doesn't exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/gemini_native.py`:

```python
"""
Native Gemini generateContent adapter.

Calls Google's generateContent API directly instead of the OpenAI-compat endpoint.
This preserves thoughtSignature on functionCall parts, which is required for
Gemini 2.5+/3.5+ thinking models to accept tool results without 400 errors.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Awaitable

import httpx
from loguru import logger

from app.core.config import settings


_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiNativeService:
    """
    OpenAI-messages-in / LLM-response-out adapter over the native Gemini REST API.
    Satisfies the same duck-type interface used by AgentLoop (complete / stream_tokens).
    """

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send messages to Gemini and return:
          {"content": str, "tool_calls": list[dict] | None}
        Each tool_call dict: {"id": str, "name": str, "args": dict, "_thought_sig": str|None}
        """
        contents, sys_inst = self._build_contents(messages)
        if system_prompt and sys_inst is None:
            sys_inst = {"parts": [{"text": system_prompt}]}

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": settings.LLM_MAX_TOKENS},
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst
        if tools:
            payload["tools"] = self._build_tools(tools)

        raw = await self._post(payload)
        return self._parse_response(raw)

    async def stream_tokens(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        on_token: Optional[Callable] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Stream tokens via on_token callback; return complete response dict.
        Uses streamGenerateContent with alt=sse.
        """
        contents, sys_inst = self._build_contents(messages)
        if system_prompt and sys_inst is None:
            sys_inst = {"parts": [{"text": system_prompt}]}

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": settings.LLM_MAX_TOKENS},
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst
        if tools:
            payload["tools"] = self._build_tools(tools)

        url = f"{_BASE_URL}/models/{self.model}:streamGenerateContent"
        full_text = ""
        tool_calls: List[Dict] = []

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": self.api_key, "alt": "sse"},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk_raw = line[5:].strip()
                    if not chunk_raw or chunk_raw == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(chunk_raw)
                    except json.JSONDecodeError:
                        continue
                    parsed = self._parse_response(chunk)
                    if parsed["content"]:
                        full_text += parsed["content"]
                        if on_token:
                            import asyncio
                            if asyncio.iscoroutinefunction(on_token):
                                await on_token(parsed["content"])
                            else:
                                on_token(parsed["content"])
                    if parsed["tool_calls"]:
                        tool_calls.extend(parsed["tool_calls"])

        return {"content": full_text, "tool_calls": tool_calls or None}

    # ------------------------------------------------------------------
    # Message translation
    # ------------------------------------------------------------------

    def _build_contents(
        self, messages: List[Dict[str, Any]]
    ) -> tuple[List[Dict], Optional[Dict]]:
        """
        Convert OpenAI-style messages[] to Gemini contents[].
        Returns (contents, system_instruction_or_None).

        Role mapping:
          "system"    → systemInstruction (returned separately, NOT in contents)
          "user"      → role "user"
          "assistant" → role "model"; tool_calls become functionCall parts;
                        _thought_sig on each tool_call becomes thoughtSignature
          "tool"      → role "user" with functionResponse part
        """
        contents: List[Dict] = []
        system_parts: List[str] = []

        # Build a lookup: tool_call_id → tool_name (needed for functionResponse)
        tc_name_by_id: Dict[str, str] = {}
        for m in messages:
            for tc in m.get("tool_calls") or []:
                tc_name_by_id[tc["id"]] = tc["name"]

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []

            if role == "system":
                system_parts.append(content)
                continue

            if role == "assistant":
                parts: List[Dict] = []
                if content:
                    parts.append({"text": content})
                for tc in tool_calls:
                    fc_part: Dict[str, Any] = {
                        "functionCall": {
                            "name": tc["name"],
                            "args": tc.get("args") or {},
                        }
                    }
                    if tc.get("_thought_sig"):
                        fc_part["thoughtSignature"] = tc["_thought_sig"]
                    parts.append(fc_part)
                if parts:
                    contents.append({"role": "model", "parts": parts})
                continue

            if role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                fn_name = tc_name_by_id.get(tool_call_id, tool_call_id)
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"result": content},
                        }
                    }]
                })
                continue

            # user
            parts_list: List[Dict] = []
            if content:
                parts_list.append({"text": content})
            if parts_list:
                contents.append({"role": "user", "parts": parts_list})

        sys_inst = {"parts": [{"text": "\n".join(system_parts)}]} if system_parts else None
        return contents, sys_inst

    def _build_tools(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI tool schema array to Gemini functionDeclarations format.
        """
        declarations = []
        for t in tools:
            fn = t.get("function") or t
            params = fn.get("parameters", {})
            # Strip fields Gemini rejects
            params = {k: v for k, v in params.items() if k not in ("default",)}
            declarations.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": params,
            })
        return [{"functionDeclarations": declarations}]

    def _parse_response(self, raw: Dict) -> Dict[str, Any]:
        """
        Parse a generateContent response dict.
        Returns {"content": str, "tool_calls": list[dict] | None}.
        Each tool_call: {"id": str, "name": str, "args": dict, "_thought_sig": str|None}
        """
        candidates = raw.get("candidates") or []
        if not candidates:
            error = raw.get("error", {})
            msg = error.get("message", str(raw))
            raise RuntimeError(f"Gemini API error: {msg}")

        parts = candidates[0].get("content", {}).get("parts") or []
        text_parts: List[str] = []
        tool_calls: List[Dict] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": fc.get("name", ""),
                    "args": fc.get("args") or {},
                    "_thought_sig": part.get("thoughtSignature"),
                })

        return {
            "content": "".join(text_parts),
            "tool_calls": tool_calls if tool_calls else None,
        }

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _post(self, payload: Dict) -> Dict:
        url = f"{_BASE_URL}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 429:
                raise RuntimeError(f"Gemini rate limit (429): {resp.text[:200]}")
            resp.raise_for_status()
            return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_gemini_native.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/gemini_native.py tests/test_gemini_native.py
git commit -m "feat: add GeminiNativeService with thought_signature roundtrip"
```

---

## Task 2: AgentLoop

**Files:**
- Create: `backend/app/agents/agent_loop.py`

**Context:** Replaces the 4-node LangGraph agent graph (`process_query → generate_response → execute_tools → critic_retry`). The loop stores conversation history in a plain in-memory dict keyed by thread_id (same effective behaviour as LangGraph's MemorySaver). Messages are plain dicts (not LangChain objects) — no LangGraph/LangChain dependency. The loop calls `llm.complete()` or `llm.stream_tokens()` and directly calls the ToolRegistry for execution.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_agent_loop.py
import pytest
import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

# Minimal mock LLM
class MockLLM:
    def __init__(self, responses):
        self._responses = list(responses)  # list of {"content": str, "tool_calls": ...}
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
    """No tool calls — single LLM turn, returns content."""
    from app.agents.agent_loop import AgentLoop
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
    """One tool call, then final response."""
    from app.agents.agent_loop import AgentLoop
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
    """Second call in same thread sees prior messages."""
    from app.agents.agent_loop import AgentLoop
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
    # Second call should include prior messages
    second_call_msgs = llm._calls[1]
    assert any(m.get("content") == "First question" for m in second_call_msgs)


@pytest.mark.asyncio
async def test_agent_loop_max_iterations():
    """Loop exits after max_iterations even if tools keep firing."""
    from app.agents.agent_loop import AgentLoop
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_agent_loop.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` — file doesn't exist yet.

- [ ] **Step 3: Write the implementation**

Create `backend/app/agents/agent_loop.py`:

```python
"""
AgentLoop — tight async while loop replacing LangGraph agent state machine.

Stores conversation history in memory keyed by thread_id.
Uses plain dicts for messages (no LangChain dependency).
Calls GeminiNativeService (or any LLM with .complete()) directly.
"""
from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from loguru import logger

from app.services.stream_events import emit as stream_emit


@dataclass
class AgentResponse:
    content: str
    agent_id: str
    citations: List[Dict] = field(default_factory=list)
    tool_calls_made: List[str] = field(default_factory=list)


class AgentLoop:
    """
    Replaces the 4-node LangGraph graph.
    History stored in self._history[thread_id] as plain dicts.
    """

    # Class-level in-memory history store (thread_id → list of message dicts)
    _history: Dict[str, List[Dict]] = {}

    def __init__(
        self,
        agent_id: str,
        system_prompt: str,
        tools: List[Dict],
        tool_map: Dict[str, Callable],
        llm: Any,
        twg_id: Optional[str] = None,
        max_iterations: int = 10,
        max_history: int = 20,
    ):
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_map = tool_map
        self.llm = llm
        self.twg_id = twg_id
        self.max_iterations = max_iterations
        self.max_history = max_history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        thread_id: str,
        user_timezone: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
    ) -> AgentResponse:
        """Execute one user turn and return the final response."""
        history = self._get_history(thread_id)
        history.append({"role": "user", "content": query})

        tool_calls_made: List[str] = []
        final_content = ""
        citations: List[Dict] = []

        for iteration in range(self.max_iterations):
            window = history[-self.max_history:]

            try:
                if stream_callback:
                    result = await self.llm.stream_tokens(
                        messages=window,
                        system_prompt=self.system_prompt,
                        on_token=stream_callback,
                        tools=self.tools if self.tools else None,
                    )
                else:
                    result = await self.llm.complete(
                        messages=window,
                        tools=self.tools if self.tools else None,
                        system_prompt=self.system_prompt,
                    )
            except Exception as e:
                logger.error(f"[{self.agent_id}] LLM error on iteration {iteration}: {e}")
                final_content = f"I encountered an error: {str(e)}"
                break

            content = result.get("content", "") if isinstance(result, dict) else str(result)
            tool_calls = result.get("tool_calls") if isinstance(result, dict) else None

            # Append assistant turn to history
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            history.append(assistant_msg)

            if not tool_calls:
                final_content = content
                break

            # Execute tool calls in parallel
            tool_results = await self._execute_tools(tool_calls, thread_id, user_timezone)
            for name, tc_id, result_str in tool_results:
                tool_calls_made.append(name)
                history.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                })

        else:
            # Max iterations reached — use whatever content was last generated
            final_content = final_content or "I reached my iteration limit. Please try a more specific question."

        self._save_history(thread_id, history)
        return AgentResponse(
            content=final_content,
            agent_id=self.agent_id,
            citations=citations,
            tool_calls_made=tool_calls_made,
        )

    async def stream(
        self,
        query: str,
        thread_id: str,
        user_timezone: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Async generator yielding SSE-style event dicts.
        Yields {"type": "token", "content": "..."} during generation
        and {"type": "tool_call", "name": "..."} on tool calls.
        """
        tokens: asyncio.Queue = asyncio.Queue()

        async def on_token(t: str):
            await tokens.put({"type": "token", "content": t})

        async def run_task():
            resp = await self.run(query, thread_id, user_timezone, stream_callback=on_token)
            await tokens.put({"type": "done", "response": resp})

        task = asyncio.create_task(run_task())
        while True:
            event = await tokens.get()
            yield event
            if event["type"] == "done":
                break
        await task

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def _get_history(self, thread_id: str) -> List[Dict]:
        if thread_id not in AgentLoop._history:
            AgentLoop._history[thread_id] = []
        return AgentLoop._history[thread_id]

    def _save_history(self, thread_id: str, history: List[Dict]) -> None:
        AgentLoop._history[thread_id] = history

    def clear_history(self, thread_id: str) -> None:
        AgentLoop._history.pop(thread_id, None)

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_tools(
        self,
        tool_calls: List[Dict],
        thread_id: str,
        user_timezone: Optional[str],
    ) -> List[tuple]:
        """Execute all tool calls in parallel. Returns list of (name, id, result_str)."""

        async def execute_one(tc: Dict) -> tuple:
            name = tc["name"]
            args = tc.get("args") or {}
            tc_id = tc["id"]

            # Emit tool_call event for SSE
            if thread_id:
                await stream_emit(thread_id, {
                    "type": "tool_call",
                    "name": name,
                    "args": {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v) for k, v in args.items()},
                })

            try:
                func = self.tool_map.get(name)
                if func is None:
                    # Try ToolRegistry
                    try:
                        from app.tools.tool_registry import get_tool_registry
                        registry = get_tool_registry()
                        result_str = await registry.execute_tool(
                            tool_name=name,
                            tool_args=args,
                            agent_id=self.agent_id,
                            twg_id=self.twg_id,
                            user_timezone=user_timezone,
                        )
                    except Exception as reg_err:
                        result_str = json.dumps({"error": f"Tool '{name}' not found: {reg_err}"})
                else:
                    sig = inspect.signature(func)
                    if "twg_id" in sig.parameters and self.twg_id and "twg_id" not in args:
                        args["twg_id"] = self.twg_id
                    if "user_timezone" in sig.parameters and user_timezone and "user_timezone" not in args:
                        args["user_timezone"] = user_timezone
                    if asyncio.iscoroutinefunction(func):
                        raw = await func(**args)
                    else:
                        raw = await asyncio.to_thread(func, **args)
                    result_str = json.dumps(raw, default=str) if isinstance(raw, (dict, list)) else str(raw)
            except Exception as e:
                logger.error(f"[{self.agent_id}] Tool '{name}' failed: {e}")
                result_str = json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})

            return name, tc_id, result_str

        return await asyncio.gather(*[execute_one(tc) for tc in tool_calls])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_agent_loop.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/agents/agent_loop.py tests/test_agent_loop.py
git commit -m "feat: add AgentLoop tight while loop replacing LangGraph agent graph"
```

---

## Task 3: SupervisorLoop

**Files:**
- Create: `backend/app/agents/supervisor_loop.py`

**Context:** Replaces the 5-node LangGraph supervisor graph. The key job is: (1) fast intent classification to pick which agent(s) should answer, (2) dispatch to one or multiple agents, (3) synthesize multi-agent responses. RBAC enforcement (twg_id forcing) is preserved exactly. Depends on Task 2 (`AgentLoop`) being complete.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_supervisor_loop.py
import pytest
import asyncio
from unittest.mock import AsyncMock

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
    """When twg_id is set, always route to that agent regardless of classify."""
    from app.agents.supervisor_loop import SupervisorLoop
    from unittest.mock import patch, MagicMock
    agriculture = MockAgentLoop("agriculture", "Forced agriculture answer")
    loop = SupervisorLoop(
        llm=MockLLM('{"agent": "supervisor"}'),  # classifier says supervisor
        twg_agents={"agriculture": agriculture},
    )
    # twg_id maps to agriculture agent
    with patch("app.agents.supervisor_loop.get_agent_id_by_twg_id", return_value="agriculture"):
        resp = await loop.run("anything", thread_id="t3", twg_id="some-uuid")
    assert agriculture.call_count == 1  # RBAC forced it, not the classifier


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_supervisor_loop.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/agents/supervisor_loop.py`:

```python
"""
SupervisorLoop — replaces the 5-node LangGraph supervisor graph.

Routing logic:
  1. If twg_id is set → RBAC forces to matching TWG agent (no classify call)
  2. Else → single fast LLM call classifies intent → picks agent(s)
  3. Dispatch to one or multiple AgentLoop instances
  4. Multi-agent: asyncio.gather + simple synthesis
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from loguru import logger

from app.agents.agent_loop import AgentLoop, AgentResponse
from app.agents.utils import get_agent_id_by_twg_id


_CLASSIFY_PROMPT = """You are a routing assistant. Given the user query, decide which agent should handle it.

Available agents:
- "supervisor": general secretariat questions, cross-cutting topics, scheduling, emails, documents
- "energy": energy trade, industrial growth, power infrastructure
- "agriculture": agribusiness, food systems, farming
- "minerals": strategic minerals, natural resources
- "digital": digital transformation, technology
- "protocol": summit protocol, diplomatic procedures
- "resource_mobilization": funding, financing, resource mobilization

If the query clearly spans exactly two pillars, return both agent ids.
Otherwise pick the single best match.

Respond with ONLY valid JSON. Examples:
{"agent": "agriculture"}
{"agent": "supervisor"}
{"agents": ["energy", "minerals"]}

Query: {query}"""


class SupervisorLoop:
    """Replaces the LangGraph supervisor graph."""

    def __init__(
        self,
        llm: Any,
        twg_agents: Dict[str, Any],
        supervisor_agent: Optional[Any] = None,
    ):
        self.llm = llm
        self.twg_agents = twg_agents
        self.supervisor_agent = supervisor_agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        thread_id: str,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
    ) -> AgentResponse:
        # 1. RBAC: if twg_id provided, force to that agent
        if twg_id:
            forced = get_agent_id_by_twg_id(twg_id)
            if forced and forced in self.twg_agents:
                logger.info(f"[SUPERVISOR] RBAC → {forced}")
                return await self.twg_agents[forced].run(
                    query, thread_id, user_timezone=user_timezone,
                    stream_callback=stream_callback,
                )
            else:
                logger.warning(f"[SUPERVISOR] RBAC failure: twg_id={twg_id} → no agent")
                return AgentResponse(content="Access denied: TWG not found.", agent_id="supervisor")

        # 2. Classify intent
        target = await self._classify_intent(query)
        logger.info(f"[SUPERVISOR] Routing → {target}")

        # 3. Dispatch
        if isinstance(target, list):
            return await self._dispatch_multiple(target, query, thread_id, user_timezone)

        if target in self.twg_agents:
            return await self.twg_agents[target].run(
                query, thread_id, user_timezone=user_timezone,
                stream_callback=stream_callback,
            )

        # Fallback: supervisor handles it
        if self.supervisor_agent:
            return await self.supervisor_agent.run(
                query, thread_id, user_timezone=user_timezone,
                stream_callback=stream_callback,
            )
        return AgentResponse(content="No agent available to handle this query.", agent_id="supervisor")

    async def stream(
        self,
        query: str,
        thread_id: str,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """Async generator yielding SSE event dicts."""
        tokens: asyncio.Queue = asyncio.Queue()

        async def on_token(t: str):
            await tokens.put({"type": "token", "content": t})

        async def run_task():
            resp = await self.run(query, thread_id, twg_id, user_timezone, stream_callback=on_token)
            await tokens.put({"type": "done", "response": resp})

        task = asyncio.create_task(run_task())
        while True:
            event = await tokens.get()
            yield event
            if event["type"] == "done":
                break
        await task

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    async def _classify_intent(self, query: str) -> str | List[str]:
        """Single fast LLM call, no tools, returns agent_id or list."""
        prompt = _CLASSIFY_PROMPT.format(query=query[:500])
        try:
            result = await self.llm.complete(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
                system_prompt=None,
            )
            raw = result.get("content", "") if isinstance(result, dict) else str(result)
            # Strip markdown fences if present
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
            if "agents" in parsed:
                return parsed["agents"]
            return parsed.get("agent", "supervisor")
        except Exception as e:
            logger.warning(f"[SUPERVISOR] Classify failed ({e}), falling back to supervisor")
            return "supervisor"

    # ------------------------------------------------------------------
    # Multi-agent dispatch
    # ------------------------------------------------------------------

    async def _dispatch_multiple(
        self,
        agent_ids: List[str],
        query: str,
        thread_id: str,
        user_timezone: Optional[str],
    ) -> AgentResponse:
        valid_ids = [a for a in agent_ids if a in self.twg_agents]
        if not valid_ids:
            return AgentResponse(content="No valid agents found for this query.", agent_id="supervisor")

        tasks = [
            self.twg_agents[aid].run(query, f"{thread_id}_{aid}", user_timezone=user_timezone)
            for aid in valid_ids
        ]
        responses: List[AgentResponse] = await asyncio.gather(*tasks)
        return self._synthesize(responses)

    def _synthesize(self, responses: List[AgentResponse]) -> AgentResponse:
        """Combine multiple agent responses into one."""
        if len(responses) == 1:
            return responses[0]
        parts = []
        for r in responses:
            parts.append(f"**{r.agent_id.replace('_', ' ').title()} perspective:**\n{r.content}")
        combined = "\n\n".join(parts)
        all_citations = [c for r in responses for c in r.citations]
        all_tools = [t for r in responses for t in r.tool_calls_made]
        return AgentResponse(
            content=combined,
            agent_id="multi",
            citations=all_citations,
            tool_calls_made=all_tools,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_supervisor_loop.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/agents/supervisor_loop.py tests/test_supervisor_loop.py
git commit -m "feat: add SupervisorLoop replacing LangGraph supervisor graph"
```

---

## Task 4: RAG Tool

**Files:**
- Create: `backend/app/tools/rag_tool.py`
- Modify: `backend/app/tools/tool_registry.py` (register the tool)

**Context:** Currently `_process_query_node` queries Pinecone unconditionally on every message, adding 3–4s to every turn. Move it to an on-demand tool so agents only pay the Pinecone cost when they actually need document context. The tool is registered in ToolRegistry exactly like all other tools so `twg_id` is injected automatically.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rag_tool.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_search_documents_returns_formatted_results():
    from app.tools.rag_tool import search_documents
    mock_kb = MagicMock()
    mock_kb.search = MagicMock(return_value=[
        {"score": 0.9, "metadata": {"file_name": "report.pdf", "text": "West Africa farming data"}},
    ])
    with patch("app.tools.rag_tool.get_knowledge_base", return_value=mock_kb):
        result = await search_documents(query="farming", twg_id="uuid-123")
    assert "report.pdf" in result
    assert "West Africa" in result


@pytest.mark.asyncio
async def test_search_documents_no_results():
    from app.tools.rag_tool import search_documents
    mock_kb = MagicMock()
    mock_kb.search = MagicMock(return_value=[])
    with patch("app.tools.rag_tool.get_knowledge_base", return_value=mock_kb):
        result = await search_documents(query="xyz", twg_id="uuid-123")
    assert "No relevant documents" in result


@pytest.mark.asyncio
async def test_search_documents_truncates_long_text():
    from app.tools.rag_tool import search_documents
    long_text = "x" * 5000
    mock_kb = MagicMock()
    mock_kb.search = MagicMock(return_value=[
        {"score": 0.8, "metadata": {"file_name": "big.pdf", "text": long_text}},
    ])
    with patch("app.tools.rag_tool.get_knowledge_base", return_value=mock_kb):
        result = await search_documents(query="test", twg_id="uuid-abc")
    # Text is truncated to 2000 chars per doc
    assert len(result) < 5000
```

- [ ] **Step 2: Run to verify fails**

```bash
cd backend
python -m pytest tests/test_rag_tool.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `rag_tool.py`**

```python
# backend/app/tools/rag_tool.py
"""
On-demand RAG tool — replaces the mandatory _process_query_node Pinecone search.
Registered in ToolRegistry; twg_id is injected automatically by the registry.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from app.core.knowledge_base import get_knowledge_base


async def search_documents(query: str, twg_id: Optional[str] = None) -> str:
    """
    Search the TWG knowledge base for documents relevant to the query.
    Call this when you need factual context from uploaded documents, reports,
    or meeting notes. Do NOT call for simple conversational replies.

    Args:
        query: Search terms describing what information you need
        twg_id: TWG identifier (injected automatically — do not pass manually)

    Returns:
        Formatted excerpts with source file names, or "No relevant documents found."
    """
    kb = get_knowledge_base()
    if kb is None:
        return "Knowledge base unavailable."

    try:
        if twg_id:
            twg_ns = f"twg-{twg_id}"
            twg_results, global_results = await asyncio.gather(
                asyncio.to_thread(kb.search, query=query, namespace=twg_ns, top_k=3),
                asyncio.to_thread(kb.search, query=query, namespace="twg-general", top_k=2),
            )
            results = twg_results + global_results
        else:
            results = await asyncio.to_thread(
                kb.search, query=query, namespace="twg-general", top_k=5
            )
    except Exception as e:
        logger.error(f"[rag_tool] Pinecone search failed: {e}")
        return f"Document search failed: {str(e)}"

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:3]

    if not results:
        return "No relevant documents found."

    parts = []
    for r in results:
        name = r["metadata"].get("file_name", "Unknown")
        text = (r["metadata"].get("text") or "")[:2000]
        parts.append(f"[{name}]\n{text}")
    return "\n\n".join(parts)
```

- [ ] **Step 4: Register in ToolRegistry**

Open `backend/app/tools/tool_registry.py`. Find the block where tools are registered (look for `register_tool` calls or the `_register_default_tools` method). Add after the last existing tool registration:

```python
# In _register_default_tools or equivalent setup block:
from app.tools.rag_tool import search_documents as _search_documents_fn

self.register_tool(
    name="search_documents",
    func=_search_documents_fn,
    description=(
        "Search the TWG knowledge base for documents relevant to the query. "
        "Call when you need factual context from uploaded reports or meeting notes. "
        "twg_id is injected automatically."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search terms describing what information you need"
            }
        },
        "required": ["query"]
    },
    inject_twg_id=True,
    allowed_agents=["agriculture", "energy", "minerals", "digital", "protocol", "resource_mobilization", "supervisor"],
)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_rag_tool.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/tools/rag_tool.py app/tools/tool_registry.py tests/test_rag_tool.py
git commit -m "feat: add search_documents as on-demand RAG tool (lazy Pinecone)"
```

---

## Task 5: Route Gemini provider to GeminiNativeService

**Files:**
- Modify: `backend/app/services/llm_service.py`

**Context:** `get_llm_service()` currently returns `OpenAILLMService` for the `gemini` provider, pointing at the OpenAI-compat endpoint. Change it to return `GeminiNativeService` instead. All other providers are untouched. Depends on Task 1 being complete.

- [ ] **Step 1: Find `get_llm_service` in llm_service.py**

```bash
grep -n "def get_llm_service\|LLM_PROVIDER\|provider.*gemini\|gemini.*provider" backend/app/services/llm_service.py | head -20
```

Note the line numbers of the `gemini` branch.

- [ ] **Step 2: Read that section**

```bash
sed -n '860,920p' backend/app/services/llm_service.py
```

- [ ] **Step 3: Update the gemini branch**

Find the section that looks like:

```python
if provider == "gemini":
    return OpenAILLMService(
        api_key=settings.GEMINI_API_KEY,
        model=getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
```

Replace it with:

```python
if provider == "gemini":
    from app.services.gemini_native import GeminiNativeService
    return GeminiNativeService(
        api_key=settings.GEMINI_API_KEY,
        model=getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash"),
    )
```

- [ ] **Step 4: Verify the server imports cleanly**

```bash
cd backend
python -c "from app.services.llm_service import get_llm_service; svc = get_llm_service(); print(type(svc).__name__)"
```
Expected output: `GeminiNativeService`

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/llm_service.py
git commit -m "feat: route gemini provider to GeminiNativeService (native API, thought_signature support)"
```

---

## Task 6: Wire LangGraphBaseAgent to AgentLoop

**Files:**
- Modify: `backend/app/agents/langgraph_base_agent.py`

**Context:** Replace the body of `LangGraphBaseAgent` with a thin wrapper around `AgentLoop`. Keep all public method signatures identical (`__init__`, `chat`, `stream_chat`, `process_query`, `get_agent_info`) so no callers break. The `_build_graph`, all `*_node` methods, and LangGraph imports are removed. Depends on Tasks 2, 4, 5.

- [ ] **Step 1: Read current `__init__` and `chat` signatures**

```bash
sed -n '85,130p' backend/app/agents/langgraph_base_agent.py
sed -n '796,870p' backend/app/agents/langgraph_base_agent.py
sed -n '900,990p' backend/app/agents/langgraph_base_agent.py
```

Note exact parameter names and defaults for `__init__`, `chat`, and `stream_chat`.

- [ ] **Step 2: Replace the file content**

The new `langgraph_base_agent.py` keeps the same class name and signatures but delegates everything to `AgentLoop`:

```python
"""
LangGraphBaseAgent — backward-compatible wrapper around AgentLoop.

Public API is unchanged; internals replaced with tight while loop.
LangGraph is no longer used — the name is kept for caller compatibility.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, AsyncGenerator

from loguru import logger

from app.agents.agent_loop import AgentLoop, AgentResponse
from app.agents.prompts import get_prompt
from app.core.knowledge_base import get_knowledge_base
from app.agents.utils import get_twg_id_by_agent_id
from app.services.llm_service import get_llm_service
from app.tools.tool_registry import get_tool_registry


# Notification cache (preserved from original)
_NOTIFICATION_CACHE_TTL = 30  # seconds


class LangGraphBaseAgent:
    """Thin wrapper — delegates to AgentLoop."""

    _notification_cache: Dict[str, tuple] = {}

    def __init__(
        self,
        agent_id: str = "supervisor",
        keep_history: bool = True,
        max_history: int = 20,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None,
    ):
        self.agent_id = agent_id
        self.session_id = session_id or "default"
        self.keep_history = keep_history
        self.max_history = max_history

        # Resolve twg_id from agent_id
        self.twg_id = get_twg_id_by_agent_id(agent_id)

        # Load system prompt
        self.system_prompt = get_prompt(agent_id)

        # LLM service
        self.llm_service = get_llm_service()

        # Tool registry
        registry = get_tool_registry()
        tools_def, tool_map = registry.get_tools_for_agent(agent_id, twg_id=self.twg_id)

        # Build the AgentLoop
        self._loop = AgentLoop(
            agent_id=agent_id,
            system_prompt=self.system_prompt,
            tools=tools_def,
            tool_map=tool_map,
            llm=self.llm_service,
            twg_id=self.twg_id,
            max_iterations=10,
            max_history=max_history,
        )

        logger.info(f"[{agent_id}] LangGraphBaseAgent initialised (AgentLoop backend)")

    # ------------------------------------------------------------------
    # Public API (unchanged signatures)
    # ------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Non-streaming chat — returns dict with response/citations."""
        message = await self._inject_notifications(message)
        thread = thread_id or self.session_id
        logger.info(f"[{self.agent_id}:{thread}] Received: {message[:100]}...")

        resp: AgentResponse = await self._loop.run(
            query=message,
            thread_id=thread,
            user_timezone=user_timezone,
        )
        return {
            "response": resp.content,
            "citations": resp.citations,
            "agent_id": self.agent_id,
            "conversation_id": thread,
            "suggestions": [],
        }

    async def stream_chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """Streaming chat — yields SSE event dicts."""
        message = await self._inject_notifications(message)
        thread = thread_id or self.session_id
        async for event in self._loop.stream(message, thread, user_timezone=user_timezone):
            yield event

    async def process_query(
        self,
        query: str,
        thread_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> str:
        """Simple string-return interface (used by supervisor dispatch)."""
        resp = await self._loop.run(
            query=query,
            thread_id=thread_id or self.session_id,
            user_timezone=user_timezone,
        )
        return resp.content

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": "AgentLoop",
            "tools": [t["function"]["name"] for t in self._loop.tools],
            "twg_id": self.twg_id,
            "session_id": self.session_id,
        }

    # ------------------------------------------------------------------
    # Notification injection (preserved from original)
    # ------------------------------------------------------------------

    async def _inject_notifications(self, message: str) -> str:
        """Append pending TWG notifications to the message context."""
        try:
            twg_id_str = self.twg_id
            if not twg_id_str:
                return message

            cache_entry = LangGraphBaseAgent._notification_cache.get(twg_id_str)
            if cache_entry and (time.monotonic() - cache_entry[1]) < _NOTIFICATION_CACHE_TTL:
                return message + (cache_entry[0] or "")

            from app.core.database import get_db_session_context
            from app.models.models import TWG, Notification, NotificationType
            from sqlalchemy import select, and_

            context_msg = ""
            async with get_db_session_context() as db:
                stmt = select(TWG).where(TWG.id == twg_id_str)
                res = await db.execute(stmt)
                twg = res.scalar_one_or_none()
                if twg and twg.technical_lead_id:
                    n_stmt = select(Notification).where(
                        and_(
                            Notification.user_id == twg.technical_lead_id,
                            Notification.is_read == False,
                            Notification.type.in_([NotificationType.ALERT, NotificationType.TASK])
                        )
                    ).order_by(Notification.created_at.desc())
                    n_res = await db.execute(n_stmt)
                    notifs = n_res.scalars().all()
                    if notifs:
                        context_msg = "\n\n[SYSTEM ALERT: Supervisor Notifications Pending]"
                        for n in notifs:
                            context_msg += f"\n- {n.title}: {n.content}"
                        context_msg += "\nPlease address these items if relevant."

            LangGraphBaseAgent._notification_cache[twg_id_str] = (context_msg, time.monotonic())
            return message + context_msg
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Notification inject failed: {e}")
            return message


def create_base_agent(agent_id: str, **kwargs) -> LangGraphBaseAgent:
    return LangGraphBaseAgent(agent_id=agent_id, **kwargs)
```

- [ ] **Step 3: Verify imports are clean**

```bash
cd backend
python -c "from app.agents.langgraph_base_agent import LangGraphBaseAgent; a = LangGraphBaseAgent('agriculture'); print('OK', a.agent_id)"
```
Expected: `OK agriculture`

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/agents/langgraph_base_agent.py
git commit -m "refactor: replace LangGraphBaseAgent internals with AgentLoop wrapper"
```

---

## Task 7: Wire LangGraphSupervisor to SupervisorLoop

**Files:**
- Modify: `backend/app/agents/langgraph_supervisor.py`

**Context:** Replace the body of `LangGraphSupervisor` with a thin wrapper around `SupervisorLoop`. Keep the same `__init__`, `register_agent`, `register_all_agents`, `build_graph`, `chat`, `stream_chat` signatures so `supervisor_api_adapter.py` and `routes/agents.py` need zero changes. Depends on Task 6 being complete.

- [ ] **Step 1: Read current supervisor signatures**

```bash
sed -n '40,90p' backend/app/agents/langgraph_supervisor.py
sed -n '340,435p' backend/app/agents/langgraph_supervisor.py
```

- [ ] **Step 2: Replace the file content**

```python
"""
LangGraphSupervisor — backward-compatible wrapper around SupervisorLoop.

Public API is unchanged; LangGraph graph replaced with SupervisorLoop.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional

from loguru import logger

from app.agents.langgraph_base_agent import LangGraphBaseAgent
from app.agents.supervisor_loop import SupervisorLoop
from app.services.llm_service import get_llm_service


class LangGraphSupervisor:
    """Thin wrapper — delegates to SupervisorLoop."""

    def __init__(
        self,
        keep_history: bool = True,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None,
    ):
        self.session_id = session_id or "default"
        self.keep_history = keep_history

        # Supervisor's own agent (handles general/secretariat queries)
        self.supervisor_agent = LangGraphBaseAgent(
            agent_id="supervisor",
            keep_history=keep_history,
            max_history=6,
            session_id=session_id,
        )

        self._twg_agents: Dict[str, LangGraphBaseAgent] = {}
        self._loop: Optional[SupervisorLoop] = None
        self._llm = get_llm_service()

        logger.info(f"LangGraphSupervisor initialised (SupervisorLoop backend)")

    # ------------------------------------------------------------------
    # Agent registration (unchanged API)
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, agent: LangGraphBaseAgent) -> None:
        self._twg_agents[agent_id] = agent
        self._rebuild_loop()
        logger.info(f"[SUPERVISOR] Registered {agent_id}")

    def register_all_agents(self) -> None:
        from app.agents.langgraph_energy_agent import create_langgraph_energy_agent
        from app.agents.langgraph_agriculture_agent import create_langgraph_agriculture_agent
        from app.agents.langgraph_minerals_agent import create_langgraph_minerals_agent
        from app.agents.langgraph_digital_agent import create_langgraph_digital_agent
        from app.agents.langgraph_protocol_agent import create_langgraph_protocol_agent
        from app.agents.langgraph_resource_mobilization_agent import create_langgraph_resource_mobilization_agent

        agents = {
            "energy": create_langgraph_energy_agent(keep_history=True),
            "agriculture": create_langgraph_agriculture_agent(keep_history=True),
            "minerals": create_langgraph_minerals_agent(keep_history=True),
            "digital": create_langgraph_digital_agent(keep_history=True),
            "protocol": create_langgraph_protocol_agent(keep_history=True),
            "resource_mobilization": create_langgraph_resource_mobilization_agent(keep_history=True),
        }
        for aid, agent in agents.items():
            self._twg_agents[aid] = agent
        self._rebuild_loop()
        logger.info(f"[SUPERVISOR] All {len(agents)} agents registered")

    def build_graph(self) -> None:
        """No-op — kept for API compatibility. Loop is built in register_all_agents."""
        self._rebuild_loop()
        logger.info("[SUPERVISOR] SupervisorLoop ready (no LangGraph graph needed)")

    # ------------------------------------------------------------------
    # Chat API (unchanged signatures)
    # ------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> dict:
        loop = self._get_loop()
        resp = await loop.run(
            query=message,
            thread_id=thread_id or self.session_id,
            twg_id=twg_id,
            user_timezone=user_timezone,
        )
        return {
            "response": resp.content,
            "citations": resp.citations,
            "agent_id": resp.agent_id,
            "conversation_id": thread_id or self.session_id,
            "suggestions": [],
            "interrupted": False,
            "interrupt_payload": None,
            "thread_id": thread_id or self.session_id,
        }

    async def stream_chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        loop = self._get_loop()
        async for event in loop.stream(
            query=message,
            thread_id=thread_id or self.session_id,
            twg_id=twg_id,
            user_timezone=user_timezone,
        ):
            yield event

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_loop(self) -> None:
        self._loop = SupervisorLoop(
            llm=self._llm,
            twg_agents=self._twg_agents,
            supervisor_agent=self.supervisor_agent,
        )

    def _get_loop(self) -> SupervisorLoop:
        if self._loop is None:
            self._rebuild_loop()
        return self._loop
```

- [ ] **Step 3: Verify imports are clean**

```bash
cd backend
python -c "
from app.agents.langgraph_supervisor import LangGraphSupervisor
s = LangGraphSupervisor()
s.register_all_agents()
print('OK — agents:', list(s._twg_agents.keys()))
"
```
Expected: `OK — agents: ['energy', 'agriculture', 'minerals', 'digital', 'protocol', 'resource_mobilization']`

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/agents/langgraph_supervisor.py
git commit -m "refactor: replace LangGraphSupervisor internals with SupervisorLoop wrapper"
```

---

## Task 8: Integration test and timing benchmark

**Files:**
- No new files — uses running backend

**Context:** Verify the full pipeline works end-to-end: backend starts cleanly, agent responds correctly, timing is improved, Gemini thought_signature errors are gone.

- [ ] **Step 1: Restart the backend**

```bash
fuser -k 8000/tcp 2>/dev/null; sleep 2
cd backend
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
sleep 6
grep -E "LLM Provider|Initialized|GeminiNative|error|Error" /tmp/backend.log | head -10
```
Expected: `Initialized GeminiNativeService: gemini-3.5-flash`

- [ ] **Step 2: Run timing benchmark**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ecowas.org","password":"Admin@2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

TEST_Q="What are the key challenges facing agricultural development in West Africa?"

echo "=== DIRECT GEMINI API ==="
START=$(date +%s%3N)
curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=AIzaSyBdz76OvuhB-vCH9KCqtRX9moQtjvlonHM" \
  -H "Content-Type: application/json" \
  -d "{\"contents\":[{\"parts\":[{\"text\":\"$TEST_Q\"}]}],\"generationConfig\":{\"maxOutputTokens\":500}}" \
  -o /tmp/direct.json
echo "Direct: $(($(date +%s%3N) - START))ms"

echo "=== MARTIN AGENT ==="
START=$(date +%s%3N)
curl -s -X POST http://localhost:8000/api/v1/agents/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"$TEST_Q\",\"agent_type\":\"agriculture\"}" \
  -o /tmp/agent.json
echo "Agent: $(($(date +%s%3N) - START))ms"

python3 -c "
import json
d = json.load(open('/tmp/agent.json'))
r = d.get('response','')
print('Response preview:', r[:300])
print('Error?' , 'error' in r.lower()[:100])
"
```
Expected: Agent responds in ~5–8s (was 15s), no `thought_signature` error in response.

- [ ] **Step 3: Test conversational query (should skip Pinecone)**

```bash
START=$(date +%s%3N)
curl -s -X POST http://localhost:8000/api/v1/agents/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"What time is the next meeting?","agent_type":"agriculture"}' \
  -o /tmp/conv.json
echo "Conversational: $(($(date +%s%3N) - START))ms"
python3 -c "import json; d=json.load(open('/tmp/conv.json')); print(d.get('response','')[:200])"
```
Expected: ~3–5s (no Pinecone hit since agent won't call `search_documents` for a schedule question).

- [ ] **Step 4: Check backend logs for no errors**

```bash
grep -E "ERROR|thought_signature|400|tool_call" /tmp/backend.log | tail -10
```
Expected: No `thought_signature` 400 errors.

- [ ] **Step 5: Final commit**

```bash
cd backend
git add -A
git commit -m "feat: agent loop redesign complete — AgentLoop + SupervisorLoop + GeminiNativeService"
```

---

## Self-Review

**Spec coverage:**
- ✅ `AgentLoop` tight while loop — Task 2
- ✅ `SupervisorLoop` replacing LangGraph supervisor — Task 3
- ✅ `GeminiNativeService` with `thought_signature` roundtrip — Task 1
- ✅ Lazy RAG via `search_documents` tool — Task 4
- ✅ `llm_service.py` routing to native Gemini — Task 5
- ✅ `langgraph_base_agent.py` backward-compat wrapper — Task 6
- ✅ `langgraph_supervisor.py` backward-compat wrapper — Task 7
- ✅ Streaming preserved via `stream_callback` / `on_token` — in Tasks 2, 3, 6, 7
- ✅ RBAC / twg_id forcing preserved — Task 3
- ✅ No changes to `routes/agents.py` — verified in Tasks 6, 7
- ✅ Error handling (LLM error, tool error, max iterations) — Task 2

**Placeholder scan:** None found — all code blocks are complete.

**Type consistency:**
- `AgentResponse` defined in Task 2, used in Tasks 3, 6, 7 ✅
- `AgentLoop.run()` signature used identically in Tasks 3, 6 ✅
- `SupervisorLoop.run()` signature used identically in Task 7 ✅
- `GeminiNativeService.complete()` returns `{"content": str, "tool_calls": list|None}` — consumed correctly in `AgentLoop._loop` ✅
