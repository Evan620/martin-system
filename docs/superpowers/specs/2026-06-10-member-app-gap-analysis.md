# Member Mobile App — Gap Analysis

**Date:** 2026-06-10 · **Branch audited:** `feat/backend-member-martin` · **Prod:** Railway, deploys from `origin/main`
**Inputs:** Vision = Joseph docx §1–13 + six 2026-06-09 end-to-end specs + WAIIS roadmap (member-relevant slices). Implementation = `/mobile` Flutter app (45 lib files, 40 test files). Backend = prod OpenAPI/endpoint probes + branch commit audit (`7efc772^..284f1fd`).

**Status legend:** ✅ done · 🟡 partial · 🔴 missing · ⬜ stub · 🚀 built-not-deployed

---

## 1. Executive summary

Of **87 envisioned features**: **44 ✅ done (51%)**, **8 🚀 built-but-not-deployed**, **11 🟡 partial**, **4 ⬜ stubs**, **20 🔴 missing** — of which 12 are Phase-2/deferred-by-design, so only **8 are true Phase-1 reds** — 6 clustered in push + offline + token refresh, plus 2 missing Martin tools ("Add meeting to my calendar" and `set_reminder`).

**Completion by area (Phase-1 scope, client-side):**

| Area | Built | Usable on prod today | Notes |
|---|---|---|---|
| Auth | ~80% | ~80% | Silent token refresh missing (doc comment promises it; code doesn't) |
| Shell / design system | ~95% | ~95% | Nav, theme, glass, transitions all shipped |
| Home (briefing + TWGs) | ~90% | ~90% | Join pill decorative |
| Martin chat (client) | ~90% | **0% — unsafe** | Prod chat is ungated: member runs facilitator agent |
| Meetings | ~90% | ~75% | RSVP 404s on prod (route branch-only) |
| Documents | ~85% | ~85% | ✦ Summarise still a stub SnackBar |
| Me (profile/tasks/reminders) | ~95% | ~70% | Reminders 404 on prod (hidden gracefully) |
| Workspace | ~90% | ~90% | Doc rows dead-end to a SnackBar |
| Deals | 0% | 0% | Phase-2 placeholder by design |
| Push notifications | **0%** | 0% | No firebase_messaging anywhere |
| Offline | **0%** | 0% | No cache layer; network-only + Retry |

**The 3 biggest gaps:**

1. **The deploy gap is a security gap.** `/agents/chat/stream` is live on prod **ungated** — a TWG_MEMBER chats with the facilitator/pillar agent (send_email, create_meeting_invite, advance_project_stage…). The member-agent allowlist (`MEMBER_TOOLS`, `agent_id="member"`), `my-rsvp`, and `/reminders/` all sit in 11 branch-only commits + 1 unrun migration (`r9_rsvp_tentative_20260609.py`) — and no migration for the `reminders` table exists yet; it still has to be authored. Shipping the app against today's prod is privilege escalation, not just missing features.
2. **Push notifications: 0%.** Phase 1 explicitly promises the 30-min meeting reminder buzz (Joseph docx §9–10). No FCM packages, no token registration, no backend send. Me-screen toggles and reminders write to stores nothing consumes on-device.
3. **Offline: 0%.** Phase 1 promises cached briefing/meetings/documents + an explicit offline state (docx §11). There is no cache layer (no hive/drift/sqflite), no connectivity awareness; every tab refetches and errors when offline — the wrong failure mode for a West-African field app.

**Definition of done for v1:**
> A TWG member on a real, release-signed iPhone or Android device logs in against prod, sees their briefing, chats with a Martin that can only see and act on their own data (verified by allow/deny tests), RSVPs to a meeting, opens a document, marks a task done and sets a reminder — and gets a push buzz 30 minutes before their next meeting.

Everything except the final clause is one backend deploy + small app fixes away. The buzz is the only net-new build.

Note the two distinct bars here: **pilot-ready** means P0 complete (everything above except the buzz), while the **v1 DoD** as written additionally requires the 30-min push buzz — which lives in P1-1, not P0.

---

## 2. Gap matrix

*Spec'd: P1 / P2 / Def (explicitly deferred by spec). Built/On prod/Tested: ✅ / 🟡 / ❌ / — (n/a, client-only or not built). Every envisioned feature appears.*

### Auth

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Email+password login (existing platform auth) | P1 | ✅ | ✅ | ✅ | ✅ |
| Secure token storage + stay signed in | P1 | 🟡 refresh token stored but never used; expiry = forced re-login | ✅ | ✅ | 🟡 |
| Biometric reopen (Face ID / fingerprint) | P1 | ✅ BiometricService, bootstrap gate (cold-start only; no re-lock on background, no toggle) | — | ✅ | ✅ |
| Logout clears credentials (Me sign-out) | P1 | ✅ | ✅ | ✅ | ✅ |
| Silent token refresh on 401, re-login fallback | P1 | ❌ doc comment in api_client.dart promises `_refreshAndRetry` that doesn't exist | — | ❌ | 🔴 |
| Magic-link login | P2 | ❌ | ❌ | ❌ | 🔴 (P2) |

### Platform / shell

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Flutter single codebase, native iOS+Android | P1 | ✅ | — | ✅ smoke | ✅ |
| Sovereign design system (navy+gold, serif, glass) | P1 | ✅ glass.dart + sovereign_theme ('Georgia' serif not bundled on Android) | — | ✅ | ✅ |
| Martin-center bottom nav (✦ FAB, Meetings·Docs·Me, Deals slot) | P1 | ✅ app_shell.dart, 5 tabs (Deals = stub) | — | ✅ | ✅ |
| Contextual quick-ask (gold button anywhere → ask Martin) | P1 | ✅ `/martin` FAB route (full-screen push; shell preserves place) | ⚠ needs member-agent gate | ✅ | ✅ |
| Persistent floating nav on detail routes (StatefulShellRoute) | P1 | ✅ | — | ✅ | ✅ |
| sovereignPage transition (fade + rise) | P1 | ✅ sovereign_page.dart | — | ✅ | ✅ |
| Richer ambient backdrop on detail screens | P1 | 🟡 not separately verified in inventory | — | — | 🟡 |
| REST/HTTPS + JWT bearer, zero client business logic | P1 | ✅ Dio Bearer interceptor (no timeouts configured) | ✅ | ✅ | ✅ |
| Designed empty states on every list | P1 | ✅ | — | ✅ | ✅ |
| Four-state UX incl. **explicit offline state** | P1 | 🟡 loading/error/empty yes; no offline state or connectivity awareness | — | 🟡 | 🟡 |
| FCM push integration (token reg + backend send) | P1 | ❌ no firebase_messaging in pubspec | ❌ | ❌ | 🔴 |
| Push: meeting reminder ~30 min before | P1 | ❌ | ❌ | ❌ | 🔴 |
| Push: RSVP nudges, new TWG doc, action item due | P2 | ❌ | ❌ | ❌ | 🔴 (P2) |
| Push-denied graceful in-app fallback | P1 | ❌ n/a until push exists | ❌ | ❌ | 🔴 |
| Offline P1: cached briefing/meetings/docs, read-only view | P1 | ❌ zero cache layer | — | ❌ | 🔴 |
| Offline P2: write/queue for field settings | P2 | ❌ | — | ❌ | 🔴 (P2) |
| App-store presence (listings, assets, review) | P2 | ❌ (release build debug-signed) | — | ❌ | 🔴 (P2) |
| Testing bar: allow/deny + mock-FCM + widget + integration + device | P1 | 🟡 ~78 unit + 19 widget tests, all features but Deals; no FCM tests, login→briefing→RSVP integration test not found | — | 🟡 | 🟡 |

### Home

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Morning briefing (greeting, meetings, alerts, overdue items) | P1 | ✅ | ✅ /martin/briefing | ✅ | ✅ |
| Suggestion chips seeding chat | P1 | ✅ | — | ✅ | ✅ |
| Ask-Martin bar → full-screen chat with seed | P1 | ✅ /home/chat?q= | — | ✅ | ✅ |
| Next-meeting card with **Join** | P1 | 🟡 _JoinPill is decorative — no onTap, no video link in BriefingMeeting | — | ✅ | 🟡 |
| 'Your TWGs' cards (pulse from loaded data, → Workspace) | P1 | ✅ your_twgs_section.dart, zero extra fetches | — | ✅ | ✅ |
| Home stays cross-TWG; Workspace is the deep dive | P1 | ✅ | — | ✅ | ✅ |
| Empty state 'Nothing urgent — ask Martin anything' | P1 | ✅ | — | ✅ | ✅ |

### Martin

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| AI-first front door; app opens to Martin | P1 | ✅ opens on Home/Martin branch | — | ✅ | ✅ |
| Level 2 Assistant scope (member's own actions only) | P1 | ✅ on branch | ❌ ungated | — | 🚀 |
| Member engine: tool-registry access control, ToolAccessDenied | P1 | ✅ branch 7efc772 (MEMBER_TOOLS) | ❌ | — | 🚀 |
| Dedicated 'member' agent (member.txt, direct routing, no supervisor) | P1 | ✅ branch bc1ae68/10b3ff0 | ❌ **security blocker** | — | 🚀 |
| SSE streaming chat (start/thinking/tool/token/final/done) | P1 | ✅ chunk-safe client, 257-line test | ✅ route live (⚠ ungated) | ✅ | ✅ |
| Live tool-activity chips | P1 | ✅ | — | ✅ | ✅ |
| conversation_id continuity | P1 | 🟡 single global notifier — one thread shared across FAB / Home / all TWG scopes | — | ✅ | 🟡 |
| Chat UX (gold/glass bubbles, disabled input, error bubble) | P1 | ✅ (no markdown rendering) | — | ✅ | ✅ |
| Member toolset — reads (meetings, docs, tasks, summaries…) | P1 | ✅ branch | ❌ | — | 🚀 |
| Member toolset — personal actions (RSVP, done, calendar, reminders) | P1 | 🟡 rsvp_meeting only; calendar + set_reminder tools absent | ❌ | — | 🟡 |
| rsvp_meeting tool (shared update helper with REST) | P1 | ✅ branch e6e8f4e/c5d4f1f | ❌ | — | 🚀 |
| set_reminder tool (same store as Me) | P1 (later slice) | ❌ | ❌ | ❌ | 🔴 |
| ✦ Summarise via Martin on every document | P1 | ⬜ SnackBar 'coming with the assistant' — never rewired though chat shipped | — | — | ⬜ |
| Project briefing tools (get_project_details, list_flagship_projects) | P2 | ❌ | ❌ | ❌ | 🔴 (P2) |
| Martin voice | P2 | ❌ (mic icon decorative) | ❌ | ❌ | 🔴 (P2) |
| Hard exclusions (no scheduling/email/broadcast/pipeline-edit/admin) | P1 | ✅ branch allowlist | ❌ prod = facilitator tools exposed | — | 🚀 |
| Graceful tool denial in plain language | P1 | 🟡 error banner exists; denial UX unverifiable until gate deploys | ❌ | 🟡 | 🟡 |
| Citations + suggestions rendering; multi-conversation history | Def | ❌ | — | ❌ | 🔴 (Def) |

### Meetings

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Live list, TWG-scoped, Upcoming\|Past toggle | P1 | ✅ | ✅ | ✅ | ✅ |
| Glass cards: title, TWG, relative time, Join pill, RSVP chip | P1 | ✅ | ✅ | ✅ | ✅ |
| Meeting detail: time, location, Join, agenda, attendees+RSVPs, own RSVP | P1 | ✅ (1032-line screen) | ✅ | ✅ | ✅ |
| Join Google Meet via url_launcher | P1 | ✅ | ✅ | ✅ | ✅ |
| Self-RSVP Going/Maybe/No (PUT my-rsvp + TENTATIVE enum + migration) | P1 | ✅ app + branch route | ❌ **404 on prod** | ✅ app | 🚀 |
| Optimistic RSVP + rollback + toast; one record via tap or Martin | P1 | ✅ (detail silently no-ops if list state unloaded — deep-link edge) | ❌ blocked by above | ✅ | ✅ |
| Detail Layout B: collapsing sliver header + expandable sections + pinned bar | P1 | 🟡 built as tabs (Overview/Agenda/People/Docs) + pinned bar — deliberate variant | — | ✅ | 🟡 |
| Agenda in detail (eager payload, /agenda fallback) | P1 | ✅ 404-tolerant | ✅ | ✅ | ✅ |
| Attached docs in detail (tap to open, ✦ summarise) | P1 | ⬜ rows display-only → SnackBar 'Opens in Documents' | — | ✅ | ⬜ |
| Minutes section only when minutes exist | P1 | ✅ | ✅ | ✅ | ✅ |
| Add meeting to my calendar (toolset) | P1 | ❌ | ❌ | ❌ | 🔴 |
| RSVP → Google-Calendar write-back / attendee sync | Def | ❌ deferred by meetings spec §6/§9 | — | ❌ | 🔴 (Def) |
| Deferred: offline reads, push reminders, live presence | Def | ❌ | — | ❌ | 🔴 (Def) |

### Documents

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Server-scoped list, glass cards (type/name/TWG/date) | P1 | ✅ | ✅ | ✅ | ✅ |
| Client-side search + category filter chips | P1 | ✅ | — | ✅ | ✅ |
| Open: PDF in-app (pdfx, JWT bytes), others via OpenFilex | P1 | ✅ (web build needs pinned pdfjs CDN; full files buffered in memory) | ✅ | ✅ | ✅ |
| ✦ Summarise on every card | P1 | ⬜ confirmed stub SnackBar (documents_screen.dart:55-62) | — | — | ⬜ |
| Confidential hidden client-side (server fix flagged) | P1 | ✅ as spec'd — server-side filter still pending | 🟡 | ✅ | ✅ |
| Server vector search (GET /documents/search) | Def | ❌ deferred for v1 per spec | ✅ exists | — | 🔴 (Def) |
| Member upload; offline docs | Def | ❌ | — | ❌ | 🔴 (Def) |

### Me

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Profile from /auth/me (name, role, TWGs, initials) | P1 | ✅ | ✅ | ✅ | ✅ |
| My action items (status/priority/due) | P1 | ✅ | ✅ | ✅ | ✅ |
| Mark own task done (optimistic PATCH + rollback) | P1 | ✅ (no un-complete; done rows onTap=null) | ✅ | ✅ | ✅ |
| Personal reminders CRUD (/reminders/ + glass add sheet) | P1 | ✅ app (best-effort load hides prod absence) | ❌ **404 on prod** | ✅ app | 🚀 |
| Reminder delivery (the buzz) via FCM; Martin set_reminder same store | P1 (later) | ❌ no delivery path | ❌ | ❌ | 🔴 |
| Notification toggles (device-local SharedPreferences, on/on/off) | P1 | ✅ as spec'd — but nothing consumes them yet | — | ✅ | ✅ |
| Backend notification-preference sync | Def | ❌ deferred by Me spec §8 | — | ❌ | 🔴 (Def) |
| Member avatars | Def | ❌ deferred by Me spec §8 | — | ❌ | 🔴 (Def) |

### Workspace

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Per-TWG hub /home/workspace/:twgId (nav persists) | P1 | ✅ | ✅ /twgs/:id | ✅ | ✅ |
| Header: back, TWG name, pillar chip, avatar row+count | P1 | ✅ | — | ✅ | ✅ |
| TWG switcher (2+ memberships, context.replace) | P1 | ✅ | — | ✅ | ✅ |
| Next-meeting tile with Join (?twg_id=) | P1 | ✅ | ✅ | ✅ | ✅ |
| Recent TWG docs (tap → existing preview) | P1 | 🟡 rows dead-end → SnackBar 'Open it from the Documents tab.' | ✅ | ✅ | 🟡 |
| 'Your tasks' (?twg_id=&mine_only=true) | P1 | ✅ | ✅ | ✅ | ✅ |
| Ask Martin card scoped to twgId | P1 | 🟡 scoping works but continues the one global conversation thread | ⚠ gate | ✅ | 🟡 |
| Per-section best-effort resilience | P1 | ✅ detail fatal, sections try/catch | — | ✅ | ✅ |
| Deferred: TWG alerts, minutes view, pulse stats, pinning | Def | ❌ | — | ❌ | 🔴 (Def) |

### Deals

| Feature | Spec'd | Built | On prod | Tested | Status |
|---|---|---|---|---|---|
| Deal Room tab: read-only pillar projects + readiness scores | P2 | ⬜ static 'PHASE 2' placeholder card; no controller/repo/models | — | ❌ only untested feature | ⬜ |
| Martin briefs on Deal Room projects | P2 | ❌ | ❌ | ❌ | 🔴 (P2) |
| Members never edit pipeline (server-enforced) | P1 ctx | ✅ | ✅ R5-leak shipped (Stage-0 404s for TWG_MEMBER) | — | ✅ |
| WAIIS 9-criterion scores available for future Deal Room | ctx | — | ✅ A2 shipped | — | ✅ |

---

## 3. Non-functional gaps

| Concern | Spec position | Reality | Verdict |
|---|---|---|---|
| **Offline** | P1: cached reads + explicit offline state; P2: write queue | Nothing. No hive/drift/sqflite; every screen network-fetches on init; only tokens + notification prefs persist | 🔴 worst NFR gap for the stated field-use audience |
| **Push notifications** | FCM both platforms; P1 = 30-min meeting reminder; in-app-only fallback | No firebase_messaging / flutter_local_notifications at all; toggles and reminders are write-only stores | 🔴 |
| **French / i18n** | **Not envisioned anywhere**; WAIIS roadmap lists multi-language as out of scope; English-only implicit | Hardcoded English, no i18n scaffolding | ✅ matches spec — but see open question 5 (ECOWAS is officially trilingual) |
| **Biometrics** | Face ID / fingerprint reopen | Real implementation (BiometricService + bootstrap gate + tests, fail-open) | ✅ — gaps: no re-lock on backgrounding, no opt-out toggle, cancel strands user at login |
| **Release signing** | (implicit for store distribution) | **Release builds signed with debug keys** — android/app/build.gradle.kts:30-32 `signingConfig = signingConfigs.getByName("debug")` with the Flutter template TODO still in place; Android label still `member_app` vs app title 'ECOWAS Summit'; no iOS distribution profile evidence | 🔴 blocks any distribution, even pilot APK/TestFlight |
| **Store distribution** | P2: real listings both stores | Nothing started (assets, listings, review readiness) | 🔴 (P2, on plan) |
| **Monitoring / crash reporting** | Not in any spec | No Sentry/Crashlytics/analytics anywhere; all DioExceptions collapsed to one generic message — field failures will be invisible | 🔴 spec gap *and* build gap |
| **Accessibility** | Light: native respect (back gesture, safe areas, system fonts); voice (P2) partly for a11y | Safe areas/back work via Flutter defaults; no semantics audit, no large-text/contrast verification; voice absent; serif fallback on Android | 🟡 |
| **Security posture** | Server-side enforcement only; no new surface | Sound design, but prod currently violates it (ungated agent — §4); confidential docs filtered client-side only; prod `/api/v1/openapi.json` publicly readable; no Dio timeouts (hang risk) | 🟡 until branch deploys |
| **Performance / reliability** | Cached fast open; optimistic writes; best-effort sections | Optimistic+rollback ✅, best-effort Workspace ✅; no caching, no pagination, whole documents/PDFs buffered in memory | 🟡 |
| **Quality bar** | Allow/deny tests, mock-FCM tests, widget tests, login→briefing→RSVP integration test, real-device pass | Widget+unit coverage is genuinely good (40 test files); allow/deny tests live with the branch; mock-FCM n/a; integration test + device pass not evidenced | 🟡 |

---

## 4. Deployment gap — the phone vs prod, today

Prod (Railway, `origin/main`) was probed read-only against `/api/v1/openapi.json` + endpoint status codes. Eleven backend commits on `feat/backend-member-martin` (`7efc772^..284f1fd`) have never deployed, and **1 Alembic migration** (`r9_rsvp_tentative_20260609.py`, TENTATIVE rsvp enum) has never run. **No migration creates the `reminders` table** — one must first be authored before `/reminders/` can work in any environment.

**Works on a phone against prod TODAY:** login/me/logout · Home briefing (`/martin/briefing`) · meetings list/detail/agenda/minutes + Join · documents list/search/open/download · action items list + mark done · TWG workspace (`/twgs/:id`) · profile/sign-out.

**Broken or dangerous against prod TODAY:**

| App feature | Prod behaviour | Why |
|---|---|---|
| RSVP buttons (list, detail) | **404** → optimistic flip then rollback+toast, every time | `PUT /meetings/{id}/my-rsvp` branch-only; prod has only the facilitator path |
| Reminders (Me) | **404** → section hides (best-effort load) | `/reminders/` router + Reminder model branch-only |
| Martin chat / quick-ask | **Works — and that's the problem.** A TWG_MEMBER streams against the facilitator/pillar agent: send_email, create_meeting_invite, advance_project_stage… | `agent_id="member"` + MEMBER_TOOLS gating is branch-only; `/agents/chat/stream` is live ungated |
| `/agents/task` | Same escalation: member task runs under facilitator agent | member-scope fix (284f1fd) branch-only |

**After deploying the branch + running the RSVP migration:** every Phase-1 app feature is live and member-safe except Reminders — which would 500 until a reminders-table migration is authored and run — and the items that were never built — push, offline, Summarise wiring, token refresh, set_reminder/calendar tools.

**Hard rule:** do not put the app in any member's hands — pilot included — before the member-agent gate deploys. This is the one gap that is a security incident, not a bug. (Also: consider gating prod's public `openapi.json`.)

---

## 5. Prioritized roadmap

### P0 — blocks any v1 pilot

| # | Item | Effort | Why this order |
|---|---|---|---|
| 1 | **Deploy `feat/backend-member-martin` backend to prod + run the RSVP migration + author and run a new reminders-table migration** (member agent gate, my-rsvp+TENTATIVE, reminders) | **S** | Unblocks RSVP, Reminders, safe chat in one motion; everything else assumes it. Note: the reminders migration does not exist yet — it must be authored, not just run |
| 2 | **Verify the gate on prod**: run allow/deny toolset tests against prod role TWG_MEMBER; manual probe that member chat cannot reach facilitator tools | **S** | The deploy is only done when the escalation is provably closed |
| 3 | **Implement 401 refresh-and-retry** in api_client (the stored refresh token is currently dead weight) — or consciously cut it and delete the lying doc comment | **M** | Without it every token expiry mid-pilot is a silent sign-out |
| 4 | **Wire ✦ Summarise → `/home/chat?q=Summarise <doc>`** (documents list; also meeting-detail + workspace doc rows → open instead of SnackBar) | **S** | The flagship demo moment is a one-line rewire away |
| 5 | **Fix chat scope state**: per-scope conversation (or reset conversation_id on TWG switch); replace the 4× hardcoded 'first TWG' default (chat_controller.dart:74, meetings_screen.dart:106, documents_screen.dart:126, me_screen.dart:212) | **M** | Cross-TWG members get wrong-scope answers in a "safety line" feature |
| 6 | **Release signing + identity**: real keystore, Android label/app id, iOS profile (currently debug-signed, label `member_app`) | **S** | Can't hand out a build otherwise |
| 7 | **Pilot hardening**: Dio connect/receive timeouts; Home Join pill — wire it (add video_link to briefing payload) or remove it; meeting-detail RSVP no-op on deep link | **S** | Cheap fixes to embarrassing-in-demo defects |
| 8 | **The promised integration test (login → briefing → RSVP) + manual pass on real iPhone and Android** | **M** | The spec's own release bar (docx §13) |
| 9 | **Server-side confidential-document filtering for member roles** (close the client-only filter) | **M** | Second data-exposure gap: the list endpoint returns confidential docs; only the client hides them |

### P1 — needed for real rollout

| # | Item | Effort |
|---|---|---|
| 1 | FCM push end-to-end: token registration endpoint + device handling + backend send job for the 30-min meeting reminder; in-app-only fallback on permission denial; wire Me toggles to topics | **L** |
| 2 | Phase-1 offline: cache last briefing/meetings/documents (e.g. drift/hive), explicit offline state, block writes with clear messaging | **L** |
| 3 | Crash reporting + minimal analytics (Sentry or Crashlytics) — flying blind in the field otherwise | **S** |
| 4 | Reminder delivery: server-side scheduler → push (rides P1-1); add Martin `set_reminder` + calendar-add tools to MEMBER_TOOLS | **M** |
| 5 | Error-handling pass: distinguish 403/timeout/offline per repo; markdown rendering + 'new conversation' affordance in chat | **M** |
| 6 | Pagination on meetings/documents/action-items; stream document downloads instead of full buffering | **M** |
| 7 | Gate prod `openapi.json`; rotate anything exposed; biometric re-lock-on-background + settings toggle | **S** |

### P2 — polish / later (matches the spec's own phasing)

Deal Room tab (real data + WAIIS scores, read-only) **L** · Martin project-briefing tools **M** · Martin voice **L** · richer push (RSVP nudges, new doc, item due) **M** · offline write/queue **L** · store listings + launch **M** · magic-link login **M** · avatars, multi-conversation history, citations rendering **M** · un-complete action items **S** · i18n/French — only if §6 Q5 resolves to yes **L**.

---

## 6. Open product questions (the specs never decided)

1. **Meeting creation for members** — members can only RSVP. Who do they ask when they need a slot moved or a session scheduled? Is "ask your facilitator via Martin handoff" a feature or a shrug?
2. **Offline expectations for the pilot** — Phase 1 spec promises cached reads; nothing is built. Is an online-only pilot acceptable for ECOWAS field conditions, or does P1-offline become P0?
3. **Notification channels** — specs assume FCM only. The org already runs a WhatsApp gateway and a Resend email sender: should meeting reminders fall back to WhatsApp/email when push is denied or the app is uninstalled? (Likely higher delivery rates in-region than push.)
4. **Reminder delivery semantics** — reminders are stored server-side with no delivery mechanism designed. Server push at `remind_at`? Local notifications? What happens to reminders created before FCM ships?
5. **French (and Portuguese)** — every source is English-only and the roadmap excludes multi-language, yet ECOWAS works in EN/FR/PT. Deliberate product decision or unexamined default? Decides whether i18n scaffolding goes in before screens multiply.
6. **Default TWG scope for multi-TWG members** — 'first TWG' is a code accident, not a decision. Should chat/headers default to a chosen primary TWG, last-used, or always cross-TWG?
7. **Quick-ask form factor** — spec says overlay "without losing your place"; the build pushes a full-screen route. Accept the variant or build the overlay?
8. **Biometric policy** — re-lock on backgrounding? user opt-out? what's the UX when biometrics are cancelled (today: stranded at login with live tokens)?
9. **Un-completing tasks** — one-way mark-done is built. Is irreversibility intended, or do members need undo?
10. **Pilot distribution** — TestFlight + Play internal track, sideloaded APK, or MDM? Determines how urgent P0-6 signing and P2 store work are.
11. **Citations** — Martin's answers carry citations the UI never renders. Is "trust me" acceptable for a diplomatic audience, or does citation rendering move up?

---

*Every claim above traces to: the vision inventory (Joseph docx + 2026-06-09 end-to-end specs + WAIIS roadmap), the implementation inventory of `/mobile` (file:line evidence cited there), the backend prod probe (`openapi.json` + status codes, branch commits `7efc772^..284f1fd`), and two direct checks made for this report: `android/app/build.gradle.kts:30-32` (debug signing) and `pubspec.yaml` (`name: member_app`, `version: 1.0.0+1`).*
