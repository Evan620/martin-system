# Meetings (Member App) — End-to-End Design

**Date:** 2026-06-09
**Status:** Approved in brainstorm; ready for implementation planning
**Builders:** Lazarus + Claude (AI-assisted)
**Related:** [Member Mobile App — Design Spec](2026-06-08-member-mobile-app-design.md) §4 (Meeting screen), §6 (member toolset)

---

## 1. Purpose & scope

Make the member app's **Meetings** page real and working end-to-end against the live platform: a TWG member opens Meetings, sees their actual TWG meetings (live from the backend), opens one for full detail, **joins** the Google Meet, and **RSVPs** Going / Maybe / No — both by tapping and by asking Martin.

Reading meetings (list + detail + join link) is already supported member-side on the backend, so that part is app-side wiring. The new platform work is the **RSVP write path** for members, which today is facilitator-only.

**In scope:** live meetings list, meeting detail, Join (Google Meet), member self-RSVP (REST + Martin tool), a `TENTATIVE` ("Maybe") state, the Sovereign-glass UI states (loading / error / empty / offline).

**Out of scope (deferred):** offline caching of reads, RSVP→Google-Calendar write-back, 401 silent-refresh, push reminders, and surfacing minutes/documents *inside* the meeting detail (documents stay on the Documents screen). See §9.

---

## 2. What already exists (no change needed)

Backend (FastAPI, `backend/app`):

| Operation | Method · Path | Auth | Member-scoped? | Notes |
|---|---|---|---|---|
| List meetings | `GET /meetings` (`api/routes/meetings.py:367`) | JWT bearer | ✅ filtered to `user.twgs`, excludes `CANCELLED` | Returns `List[MeetingRead]` |
| Meeting detail | `GET /meetings/{id}` (`meetings.py:408`) | JWT + `has_twg_access` | ✅ | Eager-loads participants, agenda, minutes, documents, `video_link` |
| Agenda | `GET /meetings/{id}/agenda` (`meetings.py:445`) | JWT | ✅ | `AgendaRead { content }` |

`MeetingRead` (`schemas/schemas.py:350`) carries: `id, twg_id, title, scheduled_at, duration_minutes, location, status, meeting_type, video_link, twg, participants[]`.
`MeetingParticipant` (`models/models.py:217`): `id, meeting_id, user_id, rsvp_status, attended, name, email, user`.

Flutter (`mobile/lib`) conventions to mirror (from the auth feature):
- Dio via `core/network/api_client.dart::buildAuthInterceptedDio` (base = `AppConfig.apiV1` = `API_BASE_URL` + `/api/v1`, bearer-token interceptor).
- Riverpod: `Provider` for singletons, `NotifierProvider` + a sealed state class for async flows.
- Repository returns models, throws a typed exception; manual `fromJson` (no codegen), const ctors, enum `_fromApi` switches.
- Current member + TWG ids come from `authControllerProvider` → `AppUser.twgs` (`AppUser.id` is the member's user id, needed to find "my" participant row).

---

## 3. Backend changes (3)

### 3.1 Add `TENTATIVE` to `RsvpStatus`
`RsvpStatus` (`models/models.py:37`) becomes `PENDING | ACCEPTED | DECLINED | TENTATIVE`. The column is a native Postgres `Enum(RsvpStatus)` (`models.py:225`), so this needs an **Alembic migration**:

```sql
ALTER TYPE rsvpstatus ADD VALUE 'TENTATIVE';
```

Gotcha: Postgres `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block. The migration must commit/run it autonomously (e.g. `op.execute` after `op.get_bind().execute("COMMIT")`, or set the migration to non-transactional). The plan owns the exact mechanism.

The RSVP read schema (`MeetingParticipantRead`) and the existing facilitator route already serialize the enum, so they accept the new value automatically.

### 3.2 Member self-RSVP route
New: `PUT /meetings/{meeting_id}/my-rsvp`

- **Auth:** `get_current_active_user` (any authenticated user; no facilitator role).
- **Body:** `{ "rsvp_status": "ACCEPTED" | "DECLINED" | "TENTATIVE" }`.
- **Behavior:**
  1. Load meeting; `404` if missing.
  2. `has_twg_access(current_user, meeting.twg_id)` else `403`.
  3. Find the `MeetingParticipant` where `meeting_id == {id}` **and** `user_id == current_user.id`.
     - If none: `404 "You are not a participant of this meeting."` (members RSVP only to meetings they're invited to; the app hides RSVP otherwise — see §5).
  4. Set `rsvp_status`, commit, return `MeetingParticipantRead`.
- **Why a new route** (not relax the existing one): the existing `PUT /.../participants/{participant_id}/rsvp` (`meetings.py:1923`, `require_facilitator`) lets a facilitator set *anyone's* RSVP by participant id. The member route is deliberately "my own row only," keyed by the authenticated user — a smaller, safer surface that needs no participant id from the client.

### 3.3 Implement the `rsvp_meeting` Martin tool
`rsvp_meeting` is already in `MEMBER_TOOLS` (`tools/tool_registry.py:116`) but unimplemented. Implement it (in `tools/calendar_tools.py`, alongside `get_schedule`):

- **Args:** `meeting_id` (Martin selects it from `get_schedule`), `response` (going/maybe/no → mapped to `ACCEPTED/TENTATIVE/DECLINED`).
- **Behavior:** resolve the member's `user_id` from the agent session, find their participant row in that meeting (within their TWG scope), update `rsvp_status`, return a plain-language confirmation. Reuses the same update logic as 3.2 (extract a shared helper so chat + REST write identically).
- **Access:** already gated by the registry's member allowlist + TWG scope; no new security surface.

---

## 4. Flutter architecture

Mirror the auth feature's layering:

```
features/meetings/
  data/
    meetings_models.dart      Meeting, MeetingDetail, Participant, RsvpStatus (+ fromJson, DateTime, enum helpers)
    meetings_repository.dart   MeetingsRepository: listMeetings(), meetingDetail(id), setMyRsvp(id, status); throws MeetingException
  application/
    meetings_controller.dart   meetingsRepositoryProvider; MeetingsListController (NotifierProvider + sealed MeetingsListState);
                               MeetingDetailController (family by id); RSVP action method
  presentation/
    meetings_screen.dart       existing glass list, rewired to live data (ConsumerStatefulWidget)
    meeting_detail_screen.dart new pushed route
```

- **Models:** `Meeting` (list item) parses `participants[]` and exposes `myRsvp(String userId)` by matching `user_id`; `MeetingDetail` adds agenda content + the attendee list. `RsvpStatus { pending, accepted, declined, tentative }` with `_fromApi` / `toApi`. `scheduled_at` parsed via `DateTime.parse(...).toLocal()`.
- **Repository:** injects `dioProvider`; `GET /meetings`, `GET /meetings/{id}`, `PUT /meetings/{id}/my-rsvp`; catches `DioException` → `MeetingException` with friendly text.
- **Controllers:** `MeetingsListState` sealed = `loading | data(List<Meeting>) | error(msg) | empty`. RSVP is **optimistic**: flip the local state immediately, call the repo, roll back + surface a toast on failure.
- **Identity:** controllers read `authControllerProvider` for `AppUser.id` (to derive "my RSVP") and TWG context (for the Martin path).
- **Routing:** add `/meetings/:id` to `routing/app_router.dart` (GoRouter), pushed from a list card.

Dependencies: add `url_launcher` (Join link) and `intl` (local + relative time strings like "Tomorrow · 14:00", "in 2h").

---

## 5. Data flow & UX

**List** — `GET /meetings` → a segmented **Upcoming | Past** toggle (split on `scheduled_at` vs now), **Upcoming** selected by default; within the selected segment, cards are sorted by time → glass cards showing title, TWG, relative time ("Tomorrow · 14:00", "in 2h"), a **Join** pill (if `video_link`), and the member's current RSVP chip.

**Detail** — tap a card → push `/meetings/:id` → `GET /meetings/{id}` → title, local time + duration, location, **Join**, agenda, attendee list (name + their RSVP), and the member's own RSVP control. RSVP buttons appear **only if the member is a participant** of that meeting.

**RSVP** — tap Going / Maybe / No → optimistic fill → `PUT /my-rsvp` → on error, roll back and show a glass toast. Asking Martin ("I'll attend Thursday's energy meeting") writes the same record; re-opening the screen reflects it.

**States** (all in Sovereign glass): **loading** (spinner/shimmer), **error** (message + Retry), **empty** ("No meetings scheduled yet"), **offline** (explicit offline note; RSVP disabled with clear feedback rather than a silent failure). **Join** opens `video_link` via `url_launcher` (external Meet app / browser); if absent, the Join control is hidden.

---

## 6. Decisions (locked in brainstorm)

- RSVP path: **both** REST buttons and the Martin tool, writing one shared record.
- "Maybe": **add `TENTATIVE`** to the backend (full Going/Maybe/No).
- Detail: **pushed full screen** (not bottom sheet).
- List: **Upcoming | Past** segmented toggle, Upcoming default.
- RSVP UI: **optimistic** with rollback.
- **No** Google-Calendar write-back this pass (DB + app only).

---

## 7. Testing

**Backend**
- Member *can* self-RSVP via `/my-rsvp` (ACCEPTED, DECLINED, **TENTATIVE**).
- Member *cannot* RSVP for a meeting outside their TWG (`403`) or when not a participant (`404`).
- The facilitator route is unchanged and still requires `require_facilitator`.
- `rsvp_meeting` tool: happy path writes the row; denied/owned correctly; shares the helper with the REST route.
- Migration smoke: enum accepts `TENTATIVE` after upgrade.

**App**
- `meetings_models` `fromJson` (incl. `myRsvp` matching + DateTime/enum parsing).
- `MeetingsRepository.setMyRsvp` with a mocked Dio (success + error → `MeetingException`).
- Controller state transitions (loading→data/empty/error; optimistic RSVP + rollback).
- One widget test: list → tap → detail → RSVP reflects.

---

## 8. Error handling & edge cases

- **Not a participant:** RSVP control hidden in UI; `/my-rsvp` returns `404` as a guard.
- **No `video_link`:** Join control hidden.
- **Auth expiry:** out of scope this pass (no silent refresh yet); a `401` surfaces as an error state and the member re-logs in. Tracked as a follow-up.
- **Offline / network error:** read shows error+Retry; RSVP is blocked with explicit feedback (no optimistic flip persisted).
- **Empty TWG / no meetings:** designed empty state.

---

## 9. Deferred (explicitly not now)

Offline caching of reads · RSVP→Google-Calendar attendee sync · 401 silent-refresh + retry · push reminders (FCM) · minutes & documents inside the meeting detail · per-attendee live presence. Each is a later slice; none blocks this pass.

---

## 10. Assumptions

- Members are added as `MeetingParticipant` rows when invited; "my RSVP" is found by `user_id == current_user.id`. *(holds per current invite flow)*
- The DB is Postgres in all environments (native enum type) — so the `ALTER TYPE` migration applies. *(confirm in plan)*
- `GET /meetings` with no `twg_id` returning all of the member's TWG meetings is sufficient; no extra "my meetings" filter is needed.
