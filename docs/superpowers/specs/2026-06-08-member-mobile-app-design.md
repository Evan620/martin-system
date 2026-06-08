# Member Mobile App — Design Spec

**Date:** 2026-06-08
**Status:** Approved in brainstorm; ready for implementation planning (Phase 1)
**Builders:** Lazarus + Claude (AI-assisted)

---

## 1. Purpose

Give TWG **members** a beautiful, AI-first mobile app that makes interacting with the ECOWAS Summit / AfCEN platform effortless. Facilitators, admins, and the secretariat keep using the existing web platform; the mobile app is **member-facing only** and personalizes the experience around what an individual member needs.

The app does not replace the platform — it is a member-shaped front door to data and capabilities that already exist in the backend, with **Martin** (the AI assistant) as the primary way members get things done.

## 2. Locked decisions (brainstorm outcomes)

| Decision | Choice |
|---|---|
| Visual identity | **Sovereign** — deep navy + gold, serif headlines, institutional/diplomatic gravitas. Same look on iPhone & Android. |
| Interaction model | **AI-first** — Martin is the front door; members mostly converse to get things done. |
| AI capability scope | **Level 2 · Assistant** — Martin sees/explains everything relevant and performs the member's **personal** actions only. Never facilitator/admin powers. |
| Platform | **Flutter** — one codebase → real native iOS + Android apps (separate store listings, shared backend). |
| Navigation | **Martin-center** — raised gold center button (Martin / home + contextual quick-ask) flanked by destination tabs. |
| Scope now | **Phase 1** (see §9). Deal Room and other depth deferred to Phase 2. |

## 3. Users & boundaries

- **In scope:** users with role `TWG_MEMBER`.
- **The safety line (enforced server-side):** members never get facilitator/admin capabilities — creating meetings for others, inviting/emailing people, broadcasts, editing the deal pipeline/scores, investor matching, memo generation, user management. These remain on the web platform.
- Facilitators/admins may *log into* the app, but the app is designed and scoped for the member experience; their management work stays on web.

## 4. Experience design

**Design system — "Sovereign":** deep navy surfaces (`#0a1f44`-family), gold accent (`#c9a227`), serif display headlines, generous spacing, restrained ceremonial feel. One consistent identity across both platforms, with light native respect for each OS (back gesture, safe areas, system fonts for body text).

**Navigation (Martin-center):** a bottom bar with destination tabs and a raised gold **Martin** button in the center. In **Phase 1** the tabs are **Meetings · Documents · Me**; the **Deals** tab is added in Phase 2. The app opens to Martin. Tapping the center button anywhere opens a contextual quick-ask (ask without losing your place).

**Screens (Phase 1 unless noted):**
1. **Home · Martin** — morning briefing that surfaces what needs the member today (next meeting + their action items), plus full chat with Martin. Suggestion chips for common asks (RSVP, brief me, find a doc).
2. **Meeting** — title, time, Join (Google Meet) link, agenda, attendees, and RSVP (Going / Maybe / No). RSVP also doable by asking Martin.
3. **Documents** — documents shared with the member's TWG, searchable, openable, with one-tap "summarize via Martin."
4. **Me** — profile, the member's action items (mark done), reminders, notification settings.
5. **Deal Room** *(Phase 2)* — read-only, role-filtered project list (status + scores), with Martin able to brief on a project.

## 5. Member-Martin engine (the heart)

Principle: **the same Martin agent the platform already runs, scoped to a member at the server.** The app holds no special permissions; the backend decides what Martin may do based on the authenticated user's role.

Flow:
1. The Flutter app calls the existing backend REST API, sending the member's auth token on every request.
2. Martin (the AI chat endpoint, today `martin.py`) runs the same agent + tool registry the platform uses.
3. The tool registry's access-control layer (`ToolAccessDenied`) reads the role (`TWG_MEMBER`) and only permits the **member toolset**; any tool outside it is denied for member sessions.

This reuses existing infrastructure (agent, tool registry, access control), so the app adds a new front door but **no new security surface**.

## 6. The member toolset

**✅ Allowed for members (read + personal actions):**
- See my meetings, agenda, time, join link, who's attending
- Find and **summarize** documents shared with me / my TWG
- Read my action items and deadlines; mark my own task done
- **RSVP** to a meeting (my own response)
- Add a meeting to my calendar; set my own reminders / nudges
- Read meeting summaries, decisions, notifications
- *(Phase 2)* Read projects relevant to me (role-filtered): `get_project_details`, `list_flagship_projects`

**⛔ Never exposed to members:**
- Create/schedule meetings for others; invite or email people; broadcasts
- Investor matching, generate investment memos, edit scores / pipeline, move project stages
- Manage users; any admin/facilitator settings

The exact tool-name → role mapping is finalized in the implementation plan; the registry's access control is the enforcement point.

## 7. Architecture

- **App:** Flutter (Dart), single codebase, custom Sovereign theme. Talks to the existing backend over HTTPS/REST. No business logic or permissions live in the app.
- **Backend:** reused as-is (FastAPI). Existing routes cover the data: `meetings`, `documents`, `action_items`, `notifications`, `auth`, `martin` (AI), `pipeline` (Phase 2). New backend work is limited to push (see §9) and confirming/defining the member tool scope.
- **AI:** member chat goes through the existing Martin endpoint with the member's identity; member toolset enforced via the tool registry.

## 8. Auth & onboarding

- Reuse existing authentication. Members are invited by email and set a password (the existing invitation flow).
- App login: **email + password** against the existing auth endpoints; store the token securely (`flutter_secure_storage`); support token refresh and "stay signed in."
- **Biometric reopen** (Face ID / fingerprint) after first login for one-tap return.
- Logout clears stored credentials.
- (Magic-link login is a possible later convenience, not Phase 1.)

## 9. Push notifications

- **Firebase Cloud Messaging (FCM)** — one integration covers iOS + Android.
- New backend: store each device's FCM token (per user/device) and a "send push" step.
- Phase 1 trigger: **meeting reminder** (~30 min before a session). In-app notifications already exist; this makes the device buzz.
- Phase 2 triggers: RSVP nudges, new document in my TWG, action item due.

## 10. Phasing

**Phase 1 — the real, usable member app (this plan):**
- Auth: login (email+password), secure token storage, biometric reopen, logout
- App shell: Sovereign design system + Martin-center navigation
- Home · Martin: briefing (next meeting + action items) + chat with member toolset + contextual quick-ask
- Meetings: list + detail (join, agenda, attendees) + RSVP
- Documents: list (shared with me) + open + summarize-via-Martin
- Me: profile, my action items (mark done), reminders, notification settings
- Member-Martin: chat endpoint + member-scoped toolset enforced server-side
- Push: meeting reminders via FCM (device-token registration + send)

**Phase 2 — depth (after Phase 1 is tested):**
- Deal Room (read-only, role-filtered) + Martin deal read-tools
- Martin **voice** input
- Richer push (RSVP nudges, new docs, task due)
- Offline caching
- App-store launch polish (store listings, assets, review)

## 11. Data flow & offline (Phase 1)

- Live REST calls for all data; cache the last-known briefing/meetings/documents for fast open and a graceful read-only view when offline.
- Write actions (RSVP, mark task done, set reminder) require connectivity in Phase 1; clear feedback if offline. Robust offline write/queue is Phase 2.

## 12. Error handling & edge cases

- **Auth expiry:** silent token refresh; fall back to re-login if refresh fails.
- **Offline:** show cached data with an explicit "offline" state; block/queue writes with clear messaging.
- **Martin tool error / denied:** graceful, plain-language message; never expose internal errors or attempt blocked actions.
- **Push permission denied:** app still works; reminders fall back to in-app only.
- **Empty states:** no meetings / no docs / no tasks each get a designed, encouraging empty state.

## 13. Testing approach

- **Backend:** tests asserting member sessions can use the allowed toolset and are denied blocked tools (extend existing tool-registry tests). Push send path tested with a mock FCM.
- **App:** widget tests for the core screens; one integration test covering login → see briefing → RSVP; manual testing on a real iPhone and Android device before any release.

## 14. Assumptions & open questions

- Member login is email + password (reusing existing auth); no separate SSO required for members. *(confirm)*
- A Firebase project will be created (Google account) for FCM. *(setup task)*
- Flutter state management, HTTP client, and exact package choices are decided in the implementation plan.
- The precise member-allowed tool list (tool names) is finalized in the plan, using §6 as the contract.
