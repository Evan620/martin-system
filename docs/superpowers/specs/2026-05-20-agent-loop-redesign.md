# Agent Loop Redesign: Replace LangGraph with Tight While Loop + Lazy RAG + Native Gemini

## Goal

Replace the nested LangGraph state machines (supervisor graph + per-agent graph) with a pair of plain async while loops, move RAG from a mandatory hot-path step to an on-demand tool, and add a native Gemini adapter that correctly handles `thought_signature` — bringing agent response time from ~15s down to ~5–6s and fixing tool-calling failures with Gemini 2.5+/3.5+.

## Architecture

### Current flow (two nested state machines, 9 nodes total)

```
Request
  → SupervisorGraph (LangGraph, 5 nodes)
      route_query → dispatch_multiple / supervisor → synthesis / single_agent_response → END
        ↓ (per agent)
      AgentGraph (LangGraph, 4 nodes)
          process_query (mandatory Pinecone RAG) → generate_response → execute_tools → critic_retry
```

Every query traverses all 9 nodes. Graph compilation, state serialisation, and edge routing add ~2–3s per turn before any LLM call happens.

### New flow (two plain async loops)

```
Request
  → SupervisorLoop.run()
      [1 LLM call: classify intent → pick agent(s)]
      if multi:  asyncio.gather(AgentLoop per agent) → synthesize response
      if single: AgentLoop.run(agent_id)

  → AgentLoop.run()
      while iterations < max_iterations:
          response = await llm.complete(messages, tools)
          if no tool_calls → break
          results = await asyncio.gather(*[execute(tc) for tc in tool_calls])
          messages.extend(results)
      return final content
```

No graph compilation. No state transitions. Same external API surface — `routes/agents.py` is untouched.

## Tech Stack

- Python 3.12, FastAPI, asyncio
- `httpx` for native Gemini REST calls (already a dep)
- Existing `ToolRegistry`, `MemoryManager`, Redis, Pinecone (all preserved)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/agents/agent_loop.py` | **Create** | `AgentLoop` — tight while loop, tool execution, memory, streaming |
| `app/agents/supervisor_loop.py` | **Create** | `SupervisorLoop` — intent classification, agent dispatch, synthesis |
| `app/services/gemini_native.py` | **Create** | Native `generateContent` client with `thought_signature` roundtrip |
| `app/agents/langgraph_base_agent.py` | **Modify** | Strip graph/node methods; `chat()` and `stream_chat()` delegate to `AgentLoop` |
| `app/agents/langgraph_supervisor.py` | **Modify** | Strip graph; `chat()` and `stream_chat()` delegate to `SupervisorLoop` |
| `app/services/llm_service.py` | **Modify** | Auto-route to `GeminiNativeService` when provider is `gemini`; extract/preserve `thought_signature` |
| Everything else | **Unchanged** | Routes, tools, memory, prompts, schemas, DB |

---

## Component Specifications

### 1. `AgentLoop` (`app/agents/agent_loop.py`)

Replaces the 4-node LangGraph agent graph.

```python
class AgentLoop:
    def __init__(
        self,
        agent_id: str,
        system_prompt: str,
        tools: list[dict],          # tool schemas (same format as before)
        tool_map: dict,             # name → callable
        memory_manager: MemoryManager,
        llm: LLMService,
        twg_id: str | None = None,
        max_iterations: int = 10,
    ): ...

    async def run(
        self,
        query: str,
        thread_id: str,
        user_timezone: str | None = None,
        stream_callback: Callable[[str], Awaitable] | None = None,
    ) -> AgentResponse:
        """
        1. Load conversation history from memory_manager (Redis).
        2. Append user message.
        3. while iterations < max_iterations:
               a. Call llm.complete(messages, tools, system_prompt)
               b. Stream tokens via stream_callback if provided.
               c. If no tool_calls → break.
               d. Execute all tool calls in parallel via asyncio.gather().
               e. Append assistant message + tool result messages.
        4. Save updated history to memory_manager.
        5. Return AgentResponse(content, citations, tool_calls_made).
        """
```

**Key differences from LangGraph:**
- No `_process_query_node` — Pinecone is NOT called automatically
- No `critic_retry` node — LLM handles quality inline
- Tool calls execute in parallel (`asyncio.gather`) rather than sequentially
- `stream_callback` is called token-by-token during the LLM call

### 2. `SupervisorLoop` (`app/agents/supervisor_loop.py`)

Replaces the 5-node LangGraph supervisor graph.

```python
class SupervisorLoop:
    def __init__(
        self,
        supervisor_agent: AgentLoop,    # the supervisor's own LLM loop
        twg_agents: dict[str, AgentLoop],
        memory_manager: MemoryManager,
        llm: LLMService,
    ): ...

    async def run(
        self,
        query: str,
        thread_id: str,
        twg_id: str | None = None,
        user_timezone: str | None = None,
        stream_callback: Callable | None = None,
    ) -> AgentResponse:
        """
        1. Single LLM call: classify intent → returns agent_id(s) or "supervisor".
        2. if agent_ids is list (multi):
               responses = await asyncio.gather(*[agent.run(q) for agent in selected])
               return await synthesize(responses)
           elif agent_id == "supervisor":
               return await supervisor_agent.run(query, thread_id)
           else:
               return await twg_agents[agent_id].run(query, thread_id)
        """

    async def _classify_intent(self, query: str, twg_id: str | None) -> str | list[str]:
        """
        Fast single LLM call (no tools, low max_tokens) to pick:
        - "supervisor" — secretariat / cross-cutting query
        - "energy" | "agriculture" | "minerals" | "digital" | "protocol" | "resource_mobilization"
        - ["energy", "agriculture"] — multi-agent (only when query explicitly spans pillars)
        Returns agent_id string or list of agent_id strings.
        """
```

**Key differences from LangGraph supervisor:**
- `route_query` node → single `_classify_intent()` LLM call with a short prompt
- `dispatch_multiple` node → `asyncio.gather()` (already parallel, just no graph overhead)
- `synthesis` node → simple `_synthesize()` call (same logic, no node wrapper)
- `negotiation` node → preserved as a method called when classify returns `"negotiation"`

### 3. `GeminiNativeService` (`app/services/gemini_native.py`)

Calls `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` directly, bypassing the broken OpenAI-compat endpoint.

```python
class GeminiNativeService:
    """
    Translates OpenAI-style messages[] + tools[] into Gemini's native
    'contents' + 'tools' format and back. Handles thought_signature
    roundtrip so Gemini 2.5+/3.5+ tool calls work correctly.
    """

    async def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system_prompt: str | None = None,
        stream_callback: Callable | None = None,
    ) -> LLMResponse:
        contents, system_instruction = self._build_contents(messages)
        payload = {
            "contents": contents,
            "systemInstruction": system_instruction,
            "tools": self._build_tools(tools) if tools else [],
            "generationConfig": {"maxOutputTokens": settings.LLM_MAX_TOKENS},
        }
        raw = await self._post(payload)
        return self._parse_response(raw)

    def _build_contents(self, messages):
        """
        Convert OpenAI messages[] to Gemini contents[].
        For assistant messages with tool_calls:
          - Include thoughtSignature from tool_call["_thought_sig"] in the
            functionCall part (required for Gemini 2.5+/3.5+).
        For tool messages:
          - Emit as 'user' role with 'functionResponse' parts.
        """

    def _parse_response(self, raw) -> LLMResponse:
        """
        Parse Gemini generateContent response.
        For functionCall parts:
          - Store raw part's thoughtSignature in tool_call["_thought_sig"]
            so it is replayed on the next turn.
        """
```

**`thought_signature` roundtrip:**
```
Turn N:  Gemini returns functionCall part with thoughtSignature="abc123"
         → we store tool_call["_thought_sig"] = "abc123"
         → we append assistant message with this tool_call

Turn N+1: We build contents from messages
         → for that tool_call, emit functionCall part with thoughtSignature="abc123"
         → Gemini accepts it, no 400 error
```

### 4. Lazy RAG — `search_documents` tool

Remove the mandatory `_process_query_node` Pinecone search. Add `search_documents` as an explicit tool registered for every agent.

```python
# app/tools/rag_tool.py  (new small file)

async def search_documents(query: str, twg_id: str) -> str:
    """
    Search the TWG knowledge base for documents relevant to the query.
    Call this when you need factual context from uploaded documents,
    reports, or meeting notes. Do NOT call for conversational replies.

    Args:
        query: Search terms describing what you need
        twg_id: TWG identifier (injected automatically)

    Returns:
        Formatted excerpts with source file names
    """
    kb = get_knowledge_base()
    twg_results, global_results = await asyncio.gather(
        asyncio.to_thread(kb.search, query=query, namespace=f"twg-{twg_id}", top_k=3),
        asyncio.to_thread(kb.search, query=query, namespace="twg-general", top_k=2),
    )
    results = sorted(twg_results + global_results, key=lambda x: x["score"], reverse=True)[:3]
    if not results:
        return "No relevant documents found."
    parts = []
    for r in results:
        name = r["metadata"].get("file_name", "Unknown")
        text = r["metadata"].get("text", "")[:2000]
        parts.append(f"[{name}]\n{text}")
    return "\n\n".join(parts)
```

Registered via `ToolRegistry` exactly like other tools — `twg_id` injected automatically, no change to calling code.

**Impact:** Conversational queries (schedule, quick answers) skip Pinecone entirely, saving 3–4s. Document queries still get full RAG — agent just calls the tool explicitly.

---

## Data Flow (single-agent turn)

```
POST /api/v1/agents/chat
  ↓
routes/agents.py (unchanged)
  ↓
SupervisorLoop.run(query, thread_id)
  ↓ _classify_intent() — 1 fast LLM call, ~300ms
  ↓
AgentLoop.run("agriculture", query, thread_id)
  ↓ memory_manager.get_context() — Redis, ~50ms
  ↓
  while loop iteration 1:
    GeminiNativeService.complete(messages, tools)   ← ~3–4s (model)
    → response has tool_calls? (e.g. search_documents)
    → execute tool → Pinecone search ~1.5s
    → append tool result
  while loop iteration 2:
    GeminiNativeService.complete(messages, tools)   ← ~2–3s (model, shorter)
    → no tool_calls → break
  ↓
memory_manager.save() — Redis, ~50ms
  ↓
return AgentResponse
```

**Expected end-to-end with tool call:** ~7–8s
**Expected end-to-end without tool call (conversational):** ~4–5s
**Current:** ~15s + error

---

## LLMService routing

Add auto-detection in `get_llm_service()`:

```python
def get_llm_service() -> LLMService:
    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        return GeminiNativeService(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )
    # ... existing providers unchanged
```

The `GeminiNativeService` satisfies the same `LLMService` interface (`complete()`, `stream_tokens()`), so `AgentLoop` needs no provider-specific code.

---

## Streaming

`AgentLoop` accepts a `stream_callback: Callable[[str], Awaitable]` and calls it with each text delta during the LLM call. `GeminiNativeService` streams via SSE from the native API (`alt=sse` query param) and forwards tokens. The SSE route in `routes/agents.py` continues to work unchanged — it passes the same callback it currently passes to `stream_chat()`.

---

## Backward Compatibility

`langgraph_base_agent.py` and `langgraph_supervisor.py` keep their class names and public method signatures (`chat()`, `stream_chat()`, `process_query()`). They become thin wrappers:

```python
class LangGraphBaseAgent:
    def __init__(self, ...):
        self._loop = AgentLoop(...)   # new implementation

    async def chat(self, query, thread_id=None, ...):
        return await self._loop.run(query, thread_id, ...)

    async def stream_chat(self, query, thread_id=None, ...):
        async for event in self._loop.stream(query, thread_id, ...):
            yield event
```

No changes required in `routes/agents.py`, `supervisor_api_adapter.py`, or any other caller.

---

## Error Handling

- **LLM error mid-loop**: catch, emit `{"type": "error"}` SSE event, return partial content if any
- **Tool execution error**: return `{"error": "..."}` as tool result string; loop continues — agent sees the error and can retry or explain
- **Max iterations reached**: return whatever content was generated so far with a note
- **Gemini 429 / quota**: propagate as `LLMRateLimitError`; existing retry logic in `routes/agents.py` handles it

---

## Testing

Each new component is independently testable without a running server:

```python
# Test AgentLoop in isolation
loop = AgentLoop(agent_id="agriculture", llm=MockLLM(), ...)
response = await loop.run("What are key challenges?", thread_id="test-1")
assert response.content  # no Pinecone, no Redis needed

# Test thought_signature roundtrip
svc = GeminiNativeService(api_key=..., model="gemini-3.5-flash")
response = await svc.complete(messages_with_tool_results)
assert response.content  # verifies no 400 error

# Test lazy RAG — confirm Pinecone NOT called on conversational query
loop = AgentLoop(..., tool_map={"search_documents": mock_pinecone})
await loop.run("What time is the next meeting?", thread_id="test-2")
assert mock_pinecone.call_count == 0  # agent didn't call search_documents
```

---

## Out of Scope

- Changing the tool registry, memory manager, or prompts
- Modifying the frontend or SSE event schema
- Changing the database schema
- The `critic_retry` node is dropped — the quality improvement from faster iterations and better models makes it unnecessary
