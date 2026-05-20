# Goal: Make Martin Work — Full Rebuild & Test

**Date:** 2026-05-13  
**Repo:** `martin-system`  
**Status:** In Progress  

---

## Problem

Martin is a multi-agent LangGraph system (1 Supervisor + 6 TWG agents: Energy, Agriculture, Minerals, Digital, Protocol, Resource Mobilization). It has **never successfully returned a response**. Every query shows "thinking..." and hangs indefinitely or throws silent errors. Tools are registered (~35 total) but none have ever been observed to execute. The system has never worked end-to-end.

Root cause is unknown — suspected: LLM provider timeout (currently Azure GPT-5.5), LangGraph graph misconfiguration, or tool execution failures swallowed silently.

---

## Goal

By end of this sprint, Martin should:

1. **Return a response** to any reasonable query within 30 seconds
2. **Call tools successfully** — calendar reads, document searches, meeting creation, action items, member lookups
3. **Show the user what it's doing in real time** — streaming tokens, visible tool calls, agent identity
4. **Be safe to test locally** — zero accidental emails or calendar invites to real people

---

## Work Streams (run in parallel)

### Stream 1 — LLM: Swap to DeepSeek on Azure AI Foundry

The current Azure GPT-5.5 endpoint appears to be causing hangs. Replace it with DeepSeek-V3 deployed on Azure AI Foundry — faster, cheaper, better tool-calling than Gemini or GPT-5.5 for this use case.

**Tasks:**
- Deploy DeepSeek-V3 on Azure AI Foundry (or use existing endpoint if available)
- Update `backend/app/services/llm_service.py` to support Azure AI Foundry endpoint format
- Update `backend/.env`: set `LLM_PROVIDER=azure_foundry`, `LLM_MODEL=deepseek-v3`, `AZURE_FOUNDRY_ENDPOINT=...`, `AZURE_FOUNDRY_API_KEY=...`
- Remove all other provider fallbacks for now (Gemini, Anthropic, OpenAI) — single clean provider
- Verify: send one raw query to the agent, confirm a response arrives within 10s

**Files to touch:**
- `backend/app/services/llm_service.py`
- `backend/app/core/config.py` (add Azure Foundry fields)
- `backend/.env`

---

### Stream 2 — Test Harness: Full Tool & Agent Capability Test (Ruflo Swarm)

Build a Python test harness that fires at `POST /api/v1/agents/chat` directly (no browser needed), tests every tool category, and produces a pass/fail report with response times.

**Test coverage:**

| Category | Test Query | Expected Tool Call |
|---|---|---|
| Calendar read | "What meetings do I have this week?" | `get_schedule` |
| Calendar past | "Show me last month's meetings" | `get_past_meetings` |
| Documents | "Find documents about energy policy" | `search_documents` |
| Document content | "Get the content of [doc]" | `retrieve_document_content` |
| Action items | "What are my open action items?" | `get_action_items` |
| Members | "Who are the members of the Energy TWG?" | `get_twg_members` |
| Meeting creation | "Schedule a meeting for next Monday at 10am" | `create_meeting_invite` |
| Supervisor routing | "What is the status of the summit?" | `get_summit_status_tool` |
| Multi-agent | "Compare energy and digital priorities" | routes to 2 agents + synthesis |
| Deal pipeline | "List the flagship investment projects" | `list_flagship_projects` |

**Test runner design:**
- `backend/tests/test_agent_capabilities.py`
- Each test: POST to `/api/v1/agents/chat`, 30s timeout, assert response not empty, log latency
- Run all tests in parallel via asyncio
- Output: `TEST_RESULTS.md` — pass/fail table with response time and first 200 chars of response
- Auth: use a seeded admin token (or bypass auth header for local test env)

**Ruflo swarm assignment:**
- Agent `researcher`: reads all tool schemas + prompts, builds test cases
- Agent `executor`: runs the test suite, captures results
- Agent `reviewer`: reads results, flags hanging tests, suggests fixes

---

### Stream 3 — UI: Claude Code-Inspired Streaming Chat

Replace the current polling-based agent chat with real-time SSE streaming. Inspired by Claude Code's terminal output — information-dense, functional, shows the machine working.

**What it should look like:**

```
┌─────────────────────────────────────────────────────────┐
│  Martin                                          [Admin] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  You: What meetings do I have this week?                 │
│                                                          │
│  ● Routing query...                                      │
│    → Energy TWG Agent                                    │
│                                                          │
│  ⚙ get_schedule(days=7, twg_id="energy")                │
│    ✓ 3 meetings found                                    │
│                                                          │
│  Energy Martin                                           │
│  You have 3 meetings this week:                          │
│  • Mon 15 May — Ministerial Briefing (10:00 WAT)        │
│  • Wed 17 May — TWG Technical Review (14:00 WAT) ▌      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Backend changes:**
- Add `GET /api/v1/agents/chat/stream` SSE endpoint
- Stream events: `routing`, `agent_selected`, `tool_call`, `tool_result`, `token`, `done`, `error`
- Each event is a JSON line: `data: {"type": "token", "content": "You have"}\n\n`

**Frontend changes (`frontend/src/`):**
- Replace current agent chat component with streaming-aware version
- Use `EventSource` or `fetch` with `ReadableStream` to consume SSE
- Show: pulsing dot while routing, agent name badge (colour-coded per TWG), tool call blocks collapsed by default with expand toggle, tokens streaming into the response bubble, citation chips at the bottom
- Typing indicator disappears once first token arrives
- Error state: red border + error message if stream dies

**Files to touch:**
- `backend/app/api/routes/agents.py` (add `/stream` endpoint)
- `frontend/src/components/AgentChat.*` (or equivalent)
- `frontend/src/hooks/useAgentStream.ts` (new SSE hook)

---

## Safety Requirements (already implemented — do not revert)

| What | How | Status |
|---|---|---|
| No real emails sent | `EMAILS_ENABLED=false` in `.env` + `email_service.py` checks it | ✅ Done |
| No calendar invites to real people | `TEST_MODE=true` → `sendUpdates='none'` on all GCal writes | ✅ Done |
| No prod database writes | Local Docker postgres:17 on port 5434 (prod snapshot, isolated) | ✅ Done |
| No prod LLM costs from bad loops | DeepSeek has lower cost per token | Pending Stream 1 |

**To re-enable for production:** remove `TEST_MODE=true` and `EMAILS_ENABLED=false` from `.env`. Everything reverts automatically. Do NOT revert the `sendUpdates` changes — they are now conditional, not hardcoded.

---

## Local Dev Environment

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:5173 | Vite dev, auto-reload |
| Backend | http://localhost:8000 | uvicorn, auto-reload |
| Test DB | localhost:5434 | Docker `martin-test-db`, postgres:17, prod snapshot |
| Prod DB (read-only ref) | yamabiko.proxy.rlwy.net:42144 | Do NOT point backend here during testing |

**Start everything:**
```bash
# DB
docker start martin-test-db

# Backend
cd backend && ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
cd frontend && npm run dev
```

**Tail logs:**
```bash
tail -f /tmp/martin-backend.log
```

---

## Definition of Done

- [ ] `POST /api/v1/agents/chat` with "what meetings do I have this week?" returns in < 15s
- [ ] Test harness shows ≥ 8/10 tool categories passing
- [ ] Zero test runs produce a real email or calendar invite
- [ ] Streaming UI shows: routing indicator → agent badge → tool call block → streaming response
- [ ] DeepSeek endpoint is the only configured LLM provider (no multi-provider confusion)
- [ ] All changes committed to `evan-fork` branch, not pushed to `origin` (prod) until verified

---

## What NOT to do

- Do not push to `origin/main` (FredrickOdondi's repo / Railway prod) until all tests pass
- Do not set `EMAILS_ENABLED=true` during testing
- Do not revert the `sendUpdates` conditional in `calendar_service.py`
- Do not run tests against the prod DB (`yamabiko.proxy.rlwy.net`)
- Do not add multiple LLM provider fallbacks — one provider, clean wiring
