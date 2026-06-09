# Martin / Home (Member App) End-to-End — Design

**Date:** 2026-06-09
**Status:** Approved in brainstorm (Sub-project #4 — the AI front door); ready for planning
**Builders:** Lazarus + Claude
**Related:** [Meetings](2026-06-09-meetings-end-to-end-design.md), [member toolset](2026-06-08-member-mobile-app-design.md) §5–6

---

## 1. Purpose
Make Home the AI front door: a live **briefing** (what needs the member today) plus a **full-screen chat with Martin** that reads the member's data and performs their personal actions (RSVP, summarise, find, set reminders) — **streaming**, with live "what I'm doing" activity, and **member-scoped on the server** (only the member toolset; never facilitator/admin powers).

## 2. Phasing
- **4a — Home briefing (fast, read-only):** wire the Home screen to `GET /martin/briefing`. No backend change. Ships first.
- **4b — Martin chat (the big one):** wire the **"member" agent** server-side (the safety line) + a Flutter streaming chat client over the existing SSE endpoint.

## 3. Backend (verified)
- **Briefing:** `GET /api/v1/martin/briefing` (`martin.py:159`) — member-scoped. Returns `{greeting, upcoming_meetings:[{title,twg_name,starts_at,minutes_until}], threshold_alerts:[...], overdue_items:[{title,days_overdue}]}`. **No change.**
- **Chat (non-stream):** `POST /api/v1/agents/chat` → `{response, conversation_id, citations, agent_id, suggestions}`.
- **Chat (stream):** `POST /api/v1/agents/chat/stream` → **SSE** (`text/event-stream`), event types: `start`, `thinking`, `tool_start`, `tool_call{name,args}`, `token{content}`, `final_response{content,conversation_id}`, `done`. This is what the app consumes.
- **User/thread wiring (works):** the chat endpoints call `set_user_for_thread(conv_id, user_id, role)`; `agent_loop` auto-injects `user_id`/`user_role` into member tools (so `rsvp_meeting` etc. act on the caller).

### 3.1 The member-agent gap (4b backend work — the safety line)
Today a `TWG_MEMBER` chat routes to the supervisor → a TWG agent (`agent_id="twg_…"`), which is **not** restricted to `MEMBER_TOOLS` — members could reach facilitator tools. The registry already has the `agent_id == "member"` gate (only `MEMBER_TOOLS`), but **no "member" agent is instantiated/routed**. Wire it:
1. Create `backend/app/agents/prompts/member.txt` — a member assistant prompt (personal actions only; never facilitator/admin; read within the member's TWG).
2. Add `"member"` to `AVAILABLE_AGENTS` (`prompts.py`).
3. Register a member agent (`LangGraphBaseAgent(agent_id="member", ...)`) in the supervisor/registry so it can be selected.
4. In `agents.py`, for `role == TWG_MEMBER`, route **directly to the member agent** (`agent_id="member"`), passing `twg_id` as read context — NOT supervisor delegation — for **both** `/agents/chat` and `/agents/chat/stream`.
5. Result: member chat is gated to `MEMBER_TOOLS` (existing registry check at `tool_registry.py:533`), `user_id` injected, TWG-scoped reads only.
6. Tests (pytest): a member chat run only exposes/uses `MEMBER_TOOLS` (assert a facilitator-only tool is denied for `agent_id="member"`); `get_tools_for_agent("member", twg_id)` ⊆ MEMBER_TOOLS; the member prompt loads.

## 4. Decisions (brainstorm)
- **Full-screen chat** reached from Home's **Ask-Martin bar** + **suggestion chips** (the ✦ nav button stays "Home/briefing").
- **Streaming + live tool activity** (token-by-token + `✦ Reading…/Updating…` chips from the SSE `tool_call`/`tool_start` events).
- Member-scoped server-side (only the member toolset).

## 5. Flutter architecture
```
features/home/
  data/
    briefing_models.dart     Briefing (greeting, nextMeeting?, dueCount, ...) + fromJson
    home_repository.dart      getBriefing()
    martin_chat_client.dart   POST /agents/chat/stream -> Stream<ChatEvent> (SSE parse: token/tool/final/done)
    chat_models.dart          ChatMessage (role, text, toolActivity?), ChatEvent
  application/
    home_controller.dart      briefing state (loading/data/error)
    chat_controller.dart      messages list + streaming state; send(message) consumes the event stream
  presentation/
    home_screen.dart          rewire seed: briefing card + chips + Ask-Martin bar (-> chat)
    martin_chat_screen.dart   full-screen conversation (bubbles, live tool chips, streaming token append, input bar)
```
- **Briefing:** `home_repository.getBriefing()` → `GET /martin/briefing`; `home_controller` sealed state; `home_screen` renders greeting + next meeting (with Join) + due items + suggestion chips + the Ask-Martin bar. Chips/bar → push the chat route with an optional seed prompt.
- **Chat client (SSE):** `martin_chat_client` POSTs to `/agents/chat/stream` with `{message, twg_id, conversation_id?}` using Dio `ResponseType.stream`; parse the `text/event-stream` lines (`data: {json}`) into a `Stream<ChatEvent>` (`Token`, `ToolActivity`, `Final`, `Done`). Bearer applied by the shared Dio.
- **Chat controller:** holds `List<ChatMessage>` + a `streaming` flag + the current assistant draft; `send()` appends the user message, opens the stream, appends tokens to the live assistant bubble, surfaces tool-activity chips, finalizes on `final_response`/`done`. Keeps `conversation_id` for continuity.
- **Routing:** chat is a route in the Home branch (`/home/chat`) via `sovereignPage` (nav persists); reached from the ask bar/chips. `twg_id` = member's first TWG (from `authController`).

## 6. UX states
- Briefing: loading/data/error(+Retry); graceful empty ("Nothing urgent — ask Martin anything").
- Chat: user bubbles (gold), assistant bubbles (glass) streaming in; tool-activity chips (`✦ …`) shown while a tool runs then cleared; input disabled while streaming; error bubble on stream failure; offline → clear message.

## 7. Testing
- Backend: member-agent gating (4b) as in §3.1.6.
- App: `briefing_models`/`chat_models` `fromJson`; `home_repository.getBriefing` (mocked Dio); the SSE parser turns a sample `data:` event stream into the right `ChatEvent`s; `chat_controller.send` appends tokens + finalizes (feed a fake event stream); widget: Home renders the greeting + next meeting; chat renders a streamed reply.

## 8. Out of scope / deferred
Voice, push, multi-conversation history UI, citations rendering (keep minimal), non-member roles in the app.

## 9. Risks
- **SSE over Dio:** must use `ResponseType.stream` + manually split `\n\n`/`data:` frames; handle partial chunks. (Alternative: `http` client's streamed response.) Pin the parsing with a unit test over a sample byte stream.
- **Member-agent routing security:** the whole point is gating to `MEMBER_TOOLS`; the backend test must prove a facilitator tool is denied for `agent_id="member"`. Do not regress the existing admin/facilitator chat paths.
- **Prod deploy:** chat (member agent) + briefing already exist on prod, but the **member-agent routing change** must be deployed for member chat to be correctly gated on the phone; until then chat would run with the old (over-broad) routing. Treat the member-agent wiring as a required deploy before exposing chat.
