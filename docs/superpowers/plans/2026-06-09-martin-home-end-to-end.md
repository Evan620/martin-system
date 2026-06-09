# Martin / Home End-to-End — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox steps. *(Executed via dynamic Workflows — 4a then 4b.)*

**Goal:** Home = live briefing + a full-screen, streaming, member-scoped chat with Martin.

**Architecture:** **4a** wires the Home screen to `GET /martin/briefing` (no backend change). **4b** wires a member-scoped `"member"` agent server-side (so chat is gated to `MEMBER_TOOLS`) and a Flutter SSE chat client over `POST /agents/chat/stream`.

**Tech Stack:** Backend — FastAPI, LangGraph agents, pytest. App — flutter_riverpod, dio (SSE via `ResponseType.stream`), go_router, mocktail.

**Spec:** `docs/superpowers/specs/2026-06-09-martin-home-end-to-end-design.md`

**Environment:** Backend `/Users/evan/ravishing-presence/backend`, `.venv/bin/python -m pytest`. Flutter `mobile/`, `export PATH="$PATH:/opt/homebrew/bin"`, package `member_app`. Commit per task; never push. Sequential.

**Verified backend contracts:**
- `GET /api/v1/martin/briefing` → `{greeting, upcoming_meetings:[{title,twg_name,starts_at,minutes_until}], threshold_alerts:[...], overdue_items:[{title,days_overdue}]}` — member-scoped. **No change.**
- `POST /api/v1/agents/chat/stream` → SSE (`text/event-stream`), events: `{type:"start"|"thinking"|"tool_start"|"tool_call"|"token"|"final_response"|"done", ...}`; `token` has `content`, `tool_call` has `name`/`args`, `final_response` has `content`+`conversation_id`. Request `EnhancedChatRequest {message, conversation_id?, twg_id}`.
- Member-agent wiring map (verified): `prompts.py AVAILABLE_AGENTS` + `get_prompt` (loads `prompts/<id>.txt`); `langgraph_supervisor.register_all_agents()` builds the agents dict + `_twg_agents`; `LangGraphBaseAgent(agent_id, ...)` resolves `twg_id = get_twg_id_by_agent_id(agent_id)` and binds tools via `get_tools_for_agent(agent_id, twg_id)` at construction; `tool_registry.validate_tool_access` already gates `agent_id=="member"` to `MEMBER_TOOLS` (and requires `twg_id` for TWG-scoped member tools); `agents.py` `/chat` TWG_MEMBER branch ~lines 299-322 + `/chat/stream` RBAC ~lines 593-618.

---

# PART 4a — Home briefing (Flutter only) — ship first

### Task A1: Briefing model
**Files:** Create `mobile/lib/features/home/data/briefing_models.dart`; Test `mobile/test/features/home/briefing_models_test.dart`
- [ ] **Test (RED):**
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
void main() {
  test('Briefing.fromJson parses greeting + next meeting + counts', () {
    final b = Briefing.fromJson({
      'greeting': 'Good morning',
      'upcoming_meetings': [
        {'title': 'Energy Sync', 'twg_name': 'Energy', 'starts_at': '2031-06-10T14:00:00Z', 'minutes_until': 120},
      ],
      'overdue_items': [{'title': 'Send notes', 'days_overdue': 2}],
    });
    expect(b.greeting, 'Good morning');
    expect(b.nextMeeting?.title, 'Energy Sync');
    expect(b.nextMeeting?.minutesUntil, 120);
    expect(b.overdueCount, 1);
  });
}
```
- [ ] **Implement:**
```dart
// lib/features/home/data/briefing_models.dart
class BriefingMeeting {
  const BriefingMeeting({required this.title, required this.twgName, required this.startsAt, required this.minutesUntil});
  final String title;
  final String? twgName;
  final DateTime? startsAt;
  final int? minutesUntil;
  factory BriefingMeeting.fromJson(Map<String, dynamic> j) => BriefingMeeting(
        title: (j['title'] ?? '').toString(),
        twgName: j['twg_name']?.toString(),
        startsAt: j['starts_at'] != null ? DateTime.tryParse(j['starts_at'].toString())?.toLocal() : null,
        minutesUntil: j['minutes_until'] as int?,
      );
}

class Briefing {
  const Briefing({required this.greeting, required this.nextMeeting, required this.overdueCount, required this.upcomingCount});
  final String greeting;
  final BriefingMeeting? nextMeeting;
  final int overdueCount;
  final int upcomingCount;
  factory Briefing.fromJson(Map<String, dynamic> j) {
    final ups = (j['upcoming_meetings'] as List?) ?? const [];
    return Briefing(
      greeting: (j['greeting'] ?? 'Hello').toString(),
      nextMeeting: ups.isNotEmpty ? BriefingMeeting.fromJson(ups.first as Map<String, dynamic>) : null,
      upcomingCount: ups.length,
      overdueCount: ((j['overdue_items'] as List?) ?? const []).length,
    );
  }
}
```
- [ ] Run GREEN; commit `feat(mobile): briefing model`.

### Task A2: Home repository
**Files:** Create `mobile/lib/features/home/data/home_repository.dart`; Test `mobile/test/features/home/home_repository_test.dart`
- [ ] **Test (RED):** mocked Dio `get('/martin/briefing')` returns a map → `getBriefing()` returns a `Briefing`; DioException → `HomeException`.
- [ ] **Implement:**
```dart
// lib/features/home/data/home_repository.dart
import 'package:dio/dio.dart';
import 'briefing_models.dart';
class HomeException implements Exception { HomeException(this.message); final String message; @override String toString() => message; }
class HomeRepository {
  HomeRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;
  Future<Briefing> getBriefing() async {
    try {
      final res = await _dio.get('/martin/briefing');
      return Briefing.fromJson(res.data as Map<String, dynamic>);
    } on DioException { throw HomeException('Could not load your briefing.'); }
  }
}
```
- [ ] GREEN; commit `feat(mobile): home repository (briefing)`.

### Task A3: Home controller
**Files:** Create `mobile/lib/features/home/application/home_controller.dart`; Test `.../home_controller_test.dart`
- [ ] Sealed `HomeState = loading|data(Briefing)|error`; `homeRepositoryProvider = Provider((ref)=>HomeRepository(dio: ref.watch(dioProvider)))`; `HomeController extends Notifier<HomeState>` with `load()`. Test transitions with a mock repo. GREEN; commit.

### Task A4: Wire the Home screen
**Files:** Modify `mobile/lib/features/home/presentation/home_screen.dart`; Test `.../home_screen_test.dart`
- [ ] ConsumerStatefulWidget: `load()` on init; render loading/error/data. Data: gold "WAIIS" eyebrow + serif greeting (`briefing.greeting + ',' + first name from authController`), a **Martin briefing GlassCard** (next meeting title + relative time + Join when present; "N action items due" from overdueCount), suggestion chips (Brief me / RSVP / Find a doc / What's due?), and an **"Ask Martin…" bar**. Chips + bar → `context.push('/home/chat?q=<seed>')` (route in 4b; until 4b lands, the push is a no-op-safe TODO — guard so it doesn't crash: only push if the route exists, or land in 4b). Reuse seed home widgets. Widget test: renders greeting + next meeting title from a mocked repo. GREEN; commit.

*(4a ships here: Home shows a live briefing. The Ask-Martin bar/chips become active in 4b.)*

---

# PART 4b — Member-agent + streaming chat

### Task B1: Member agent (backend, the safety line)
**Files:** Create `backend/app/agents/prompts/member.txt`; Modify `backend/app/agents/prompts.py`, `backend/app/agents/langgraph_supervisor.py`, `backend/app/api/routes/agents.py` (both `/chat` and `/chat/stream`), and whatever `chat_with_tools`/`SupervisorLoop.run` need to accept a `force_agent_id`; Test `backend/tests/test_member_agent.py`

**Goal:** a `TWG_MEMBER` chat runs under `agent_id="member"`, gated to `MEMBER_TOOLS`, **with the caller's `twg_id`** so TWG-scoped member reads (get_schedule, search_documents, get_meeting_minutes, get_action_items) are granted.

**CRITICAL SUBTLETY:** `LangGraphBaseAgent` binds its tools at construction using `twg_id = get_twg_id_by_agent_id(agent_id)`, which is `None` for `"member"` (not pillar-mapped). With `twg_id=None`, `validate_tool_access` **denies** the TWG-scoped member tools. So the member agent must be given the **caller's** `twg_id`. Implement one of:
  - **(preferred)** a per-request member agent: `LangGraphBaseAgent(agent_id="member", session_id=conv_id)` then override its tool binding for the request's twg_id — i.e. add an optional `twg_id` param to the constructor (defaulting to `get_twg_id_by_agent_id(agent_id)`) so `LangGraphBaseAgent(agent_id="member", twg_id=str(chat_in.twg_id), session_id=conv_id)` binds `get_tools_for_agent("member", twg_id)` correctly; or
  - thread `force_agent_id="member"` + `twg_id` through `chat_with_tools`→`SupervisorLoop.run` and have the loop build/run the member agent with that twg_id.

Choose the smallest change that makes `get_tools_for_agent("member", <twg_id>)` the agent's toolset. Read `langgraph_base_agent.py` + `supervisor_loop.py` to pick.

- [ ] **Step 1: Failing tests** (`backend/tests/test_member_agent.py`):
```python
"""The member agent is gated to MEMBER_TOOLS and gets TWG-scoped reads with a twg_id."""
import uuid
import pytest
from app.tools.tool_registry import get_tool_registry, ToolAccessDenied, MEMBER_TOOLS

def test_member_prompt_loads():
    from app.agents.prompts import get_prompt, AVAILABLE_AGENTS
    assert "member" in AVAILABLE_AGENTS
    assert isinstance(get_prompt("member"), str) and get_prompt("member").strip()

def test_member_toolset_is_subset_of_member_tools():
    reg = get_tool_registry()
    twg = str(uuid.uuid4())
    _defs, tool_map = reg.get_tools_for_agent(agent_id="member", twg_id=twg)
    assert set(tool_map.keys()).issubset(MEMBER_TOOLS)
    # with a twg_id, TWG-scoped member reads are granted
    assert "get_schedule" in tool_map

def test_member_denied_facilitator_tool():
    reg = get_tool_registry()
    with pytest.raises(ToolAccessDenied):
        reg.validate_tool_access("create_meeting", agent_id="member", twg_id=str(uuid.uuid4()))
```
- [ ] **Step 2:** RED (`.venv/bin/python -m pytest tests/test_member_agent.py -v`) — "member" not in AVAILABLE_AGENTS.
- [ ] **Step 3:** Create `prompts/member.txt` (member assistant: help with the member's own meetings, documents, action items, RSVP, reminders; read only within their TWG; NEVER facilitator/admin actions — no creating meetings for others, no emails/broadcasts, no pipeline/score edits, no user mgmt; be concise, diplomatic). Add `"member"` to `AVAILABLE_AGENTS`. Register the member agent in `register_all_agents()` (`"member": LangGraphBaseAgent(agent_id="member", keep_history=True)`). Apply the twg_id-binding fix (above) + route `TWG_MEMBER` to `agent_id="member"` in `agents.py` `/chat` and `/chat/stream` (set `agent_id="member"`, pass the caller's `twg_id`).
- [ ] **Step 4:** GREEN. Also run the existing agent tests to ensure no regression to admin/facilitator chat: `.venv/bin/python -m pytest tests/test_member_agent.py tests/test_member_tools.py tests/test_member_rsvp_route.py -v`.
- [ ] **Step 5:** Commit `feat(member): member-scoped chat agent (agent_id=member, MEMBER_TOOLS)`.

### Task B2: Chat models + SSE client (Flutter)
**Files:** Create `mobile/lib/features/home/data/chat_models.dart`, `mobile/lib/features/home/data/martin_chat_client.dart`; Test `mobile/test/features/home/martin_chat_client_test.dart`
- [ ] **chat_models.dart:** `enum ChatRole {user, martin}`; `class ChatMessage {role, text, toolActivity?}`; sealed `ChatEvent` = `TokenEvent(text)` | `ToolEvent(label)` | `FinalEvent(text, conversationId?)` | `DoneEvent` | `ErrorEvent(message)`.
- [ ] **SSE parser (testable, pure):** a top-level `ChatEvent? parseSseData(String dataJson)` mapping a decoded event map → `ChatEvent` (`token`→Token, `tool_call`/`tool_start`→Tool with a friendly label like `✦ ${name}…`, `final_response`→Final, `done`→Done). Unit-test it over sample event JSON strings.
- [ ] **client:** `MartinChatClient { Stream<ChatEvent> send({required String message, required String twgId, String? conversationId}) }` — POST `/agents/chat/stream` via Dio with `Options(responseType: ResponseType.stream)`, read `response.data.stream`, decode bytes, split on `\n`, strip `data: `, `jsonDecode`, map via `parseSseData`, yield events; emit `ErrorEvent` on failure. (Keep the byte-buffer split robust to partial lines.)
- [ ] **Test:** feed a fake `Stream<List<int>>` of `data: {...}\n\n` frames through the parser path and assert the emitted `ChatEvent`s (token×N, final, done). GREEN; commit.

### Task B3: Chat controller (Flutter)
**Files:** Create `mobile/lib/features/home/application/chat_controller.dart`; Test `.../chat_controller_test.dart`
- [ ] `martinChatClientProvider` (Dio); `ChatState {messages: List<ChatMessage>, streaming: bool}`; `ChatController` with `send(String text)` — appends a user message + an empty Martin draft, subscribes to `client.send(...)` (twgId from authController's first TWG), appends `TokenEvent`s to the draft, sets `toolActivity` from `ToolEvent`, finalizes on `FinalEvent`/`DoneEvent`, sets an error message on `ErrorEvent`; keeps `conversationId`. Test with a fake client returning a controlled `Stream<ChatEvent>`; assert the assembled Martin message + streaming flag. GREEN; commit.

### Task B4: Chat screen + route + Home wiring
**Files:** Create `mobile/lib/features/home/presentation/martin_chat_screen.dart`; Modify `mobile/lib/routing/app_router.dart` (nested `/home/chat` under the Home branch via `sovereignPage`); Modify `home_screen.dart` (ask bar/chips → `context.push('/home/chat?q=...')`); Test `.../martin_chat_screen_test.dart`
- [ ] Chat screen: a `ConsumerStatefulWidget` — `✦ Martin` header, a scrolling message list (user = gold bubble, martin = glass bubble; show `toolActivity` as a gold `✦ …` chip while streaming), an input bar (disabled while streaming) calling `chatController.send`. If a `?q=` seed arrives, prefill/send it. Reuse Sovereign styles.
- [ ] Route: add `GoRoute(path: 'chat', pageBuilder: (c,s)=>sovereignPage(child: MartinChatScreen(seed: s.uri.queryParameters['q'])))` nested under the existing `/home` branch (nav persists).
- [ ] Home wiring: the Ask-Martin bar + chips push `/home/chat?q=<text>`.
- [ ] Widget test: pump the chat screen with a fake client streaming "Hello"; assert the Martin bubble shows "Hello". GREEN; `flutter analyze lib` clean; commit.

---

## Final verification
- [ ] Backend: `.venv/bin/python -m pytest tests/test_member_agent.py tests/test_member_tools.py tests/test_member_rsvp_route.py tests/test_reminders_routes.py -v` → all pass.
- [ ] App: `flutter analyze && flutter test` → clean + green.
- [ ] Device (after deploy): Home shows a live briefing; Ask Martin → streaming chat that reads your data + does member actions; member-scoped (no facilitator tools).

## Notes / deploy
- **4b requires a prod deploy** (member-agent routing) for member chat to be correctly gated on the phone; until deployed, chat would use the old over-broad routing. Treat the member-agent wiring as a required deploy before exposing chat. The briefing (4a) already works against prod.
- Run as TWO workflows: 4a (Home briefing, low-risk, ships fast) then 4b (member agent + chat). The 4b backend (Task B1) is the riskiest change — rely on the adversarial review + the gating tests.
