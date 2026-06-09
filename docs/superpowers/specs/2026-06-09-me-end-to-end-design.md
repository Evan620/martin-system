# Me (Member App) End-to-End — Design

**Date:** 2026-06-09
**Status:** Approved in brainstorm (Sub-project #3); ready for planning
**Builders:** Lazarus + Claude
**Related:** [Meetings end-to-end](2026-06-09-meetings-end-to-end-design.md), [Documents](2026-06-09-documents-end-to-end-design.md)

---

## 1. Purpose
Wire the **Me** screen to live data: profile from the session, the member's **action items** (list + mark done), personal **reminders** (list + add + delete — needs new backend routes), and **device-local** notification toggles.

## 2. Backend (verified)
- **Profile:** `GET /auth/me` → `UserResponse` (`id, email, full_name, role, twgs[{id,name}], ...`). No avatar/initials — compute initials client-side (already have `AppUser`). **No change.**
- **Action items:** `GET /api/v1/action-items/?mine_only=true&status=` → `List[ActionItemRead]` (`id, twg_id, meeting_id, description, owner_id, due_date, status[PENDING|IN_PROGRESS|COMPLETED|OVERDUE], priority[low|medium|high|urgent], owner, created_at, completed_at`). `PATCH /api/v1/action-items/{id}` with `ActionItemUpdate {status,...}` — **member can update their OWN** (owner check at `action_items.py:170`); COMPLETED auto-sets `completed_at`. **No change.**
- **Reminders:** `Reminder` model exists (`models.py:237`: `id, user_id, message, remind_at, meeting_id?, is_sent, created_at`) but **NO REST routes**. **Need new member routes (this sub-project's backend work).**
- **Notifications:** read/mark-read routes exist; **no preference/toggle store** → toggles are **device-local** (per the brainstorm decision). No backend.

## 3. Decisions (brainstorm)
- **Action items:** live list of *my* items + tap-to-mark-done (PATCH to COMPLETED). 
- **Reminders:** **full** — list + add (+ delete); stored on the backend; **delivery** (a buzz) rides the later FCM phase. Martin's `set_reminder` (later) writes the same store.
- **Notifications:** **device-local** toggles (`shared_preferences`), used later to choose FCM topics.

## 4. Backend work (3 routes — mirror the meetings `my-rsvp` pattern)
New `app/api/routes/reminders.py` (register the router under `/api/v1`), all auth `get_current_active_user`, scoped to `current_user.id`:
- `GET /reminders` → `List[ReminderRead]` — the caller's reminders, ordered by `remind_at`.
- `POST /reminders` (`ReminderCreate {message, remind_at, meeting_id?}`) → `ReminderRead` (sets `user_id=current_user.id`, `is_sent=false`).
- `DELETE /reminders/{id}` → 204; 404 if not found or not the caller's.
- Schemas in `schemas.py`: `ReminderBase {message, remind_at, meeting_id?}`, `ReminderCreate(ReminderBase)`, `ReminderRead(ReminderBase){id, user_id, is_sent, created_at}`.
- Tests (pytest, mirror `test_member_rsvp_route.py`): member creates → appears in their GET; lists only own; deletes own (others' → 404).

## 5. Flutter architecture
```
features/profile/                      (Me lives here already as me_screen.dart seed)
  data/
    me_models.dart        ActionItem (+ ActionStatus enum), Reminder, fromJson
    me_repository.dart     listActionItems(); markDone(id); listReminders(); addReminder(msg,at); deleteReminder(id)
  application/
    me_controller.dart     meRepositoryProvider; sealed MeState combining action items + reminders;
                           notificationPrefs (local) via a NotificationPrefs service
  presentation/
    me_screen.dart         rewire the seed to live data (profile from authController; action items; reminders; toggles; sign out)
```
- **Repository** uses `dioProvider`. Action items: `GET /action-items/?mine_only=true`, `PATCH /action-items/{id} {status:'COMPLETED'}`. Reminders: the new routes.
- **Notification prefs:** a small `NotificationPrefs` (shared_preferences) with 3 bools (meetingUpdates, newDocuments, announcements), defaulting on/on/off.
- **Controller:** loads action items + reminders together; sealed `MeState = loading | data(items, reminders) | error`. Mark-done is optimistic (flip + PATCH, rollback on error); add/delete reminder updates the list.
- **Profile:** from `authControllerProvider` (`AppUser` name/role/first TWG; initials from name). Sign out → `authController.signOut()` (exists).

Dependency to add: `shared_preferences`.

## 6. UX states
Loading (spinner) · error (Retry) · empty per-section ("No tasks", "No reminders yet"). Add-reminder: a glass sheet with a message field + date/time picker → POST → prepend. Mark-done: checkbox fills gold + strike-through. Toggles: instant local persist.

## 7. Testing
- Backend: reminders create/list/delete member-scoped (own-only).
- App: models `fromJson`; repo calls (mocked Dio) incl. PATCH mark-done + reminder CRUD; controller transitions + optimistic mark-done rollback; `NotificationPrefs` persists; widget: Me renders profile + an action item + a reminder, toggling a notification persists.

## 8. Out of scope / deferred
Reminder delivery (FCM phase), backend notification-preference sync, action-item creation/editing (members only mark their own done), avatars.

## 9. Risks
- Reminder `remind_at` timezone: store UTC ISO; the picker yields local → convert to UTC on POST, display local.
- The `ActionItemRead.status` enum values are UPPERCASE (`PENDING`/`COMPLETED`/...); map carefully.
