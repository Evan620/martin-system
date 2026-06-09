# Meeting Detail Polish + Persistent Nav + Transition — Design

**Date:** 2026-06-09
**Status:** Approved in brainstorm (Sub-project #1 of "member screens end-to-end"); ready for planning
**Builders:** Lazarus + Claude
**Related:** [Meetings end-to-end](2026-06-09-meetings-end-to-end-design.md), [Member app design](2026-06-08-member-mobile-app-design.md)

---

## 1. Purpose

The meeting detail screen exists but reads as incomplete and the page transition is a plain platform slide. This sub-project finishes the detail screen (best-practice dense-data layout), keeps the floating nav **persistent** on it, and gives the app a **Sovereign page transition** — all reusing existing backend reads (no backend change).

## 2. Locked decisions (from brainstorm + mockups)

- **Layout B — collapsing header + expandable sections + pinned actions.** A collapsing header (title/TWG/status), then tap-to-expand sections each showing a **count** (Agenda · 3, Attendees · 12, Documents · 4, Minutes), with a **pinned bottom action bar (Join + RSVP)** that never scrolls away.
- **Persistent navbar.** The detail renders *inside* the shell so the floating glass nav stays on screen, with **Meetings** kept active/gold while viewing a meeting.
- **Sovereign page transition.** Replace go_router's default `MaterialPage` with a shared `CustomTransitionPage`: fade + slight upward rise (~280ms, `easeOutCubic`).
- **Richer ambient backdrop** on detail (navyRaised→navy→navyDeep + faint gold glow) so it isn't flat.
- **Content added:** status badge, **agenda** (`GET /meetings/{id}/agenda`), **attached documents** (`MeetingRead.documents`), optional **minutes/summary** (`GET /meetings/{id}/minutes`).

## 3. Architecture

### 3.1 Persistent nav — `StatefulShellRoute.indexedStack`
Refactor routing so the floating nav is the **shell** wrapping branch navigators, and pushing a detail route inside the Meetings branch keeps the nav visible.

- `routing/app_router.dart`: replace the flat `GoRoute('/')→AppShell` + `GoRoute('/meetings/:id')` with a `StatefulShellRoute.indexedStack`:
  - `builder: (context, state, navigationShell) => AppShell(navigationShell: navigationShell)` — AppShell renders the **existing grow-gold floating nav** and hosts `navigationShell` as the body.
  - 4 branches: Meetings, Documents, Home(Martin), Me — each a `StatefulShellBranch` with its routes. The Meetings branch contains `/meetings` (list) and the nested `meetings/:id` (detail), so detail pushes **within** the branch and the shell (nav) persists.
- `shell/app_shell.dart`: change from owning an `IndexedStack` of 4 const screens + `_index` to driving `navigationShell.currentIndex` / `navigationShell.goBranch(i)`. **Keep the grow-gold `_item` animation, ✦ Martin center, and glass pill exactly as they are** — only the data source for "which tab is active" and the tap handler change. The Martin center maps to the Home branch.
- Back from detail: `context.pop()` returns to the Meetings list with the nav intact; tapping another tab switches branch.

### 3.2 Page transition
A shared helper `routing/sovereign_page.dart::sovereignPage<T>({child})` returning a `CustomTransitionPage` (opacity 0→1 + `Offset(0,0.04)`→`Offset.zero` slide, 280ms `easeOutCubic`). Detail (and future pushed pages) use `pageBuilder: (c,s)=>sovereignPage(child: ...)`.

### 3.3 Layout B (the detail body)
`CustomScrollView` with:
- `SliverAppBar` (pinned, `expandedHeight`): collapses from the big serif title + TWG eyebrow + **status badge** to a compact bar on scroll. Transparent over the ambient backdrop; glass back button.
- `SliverList` of **expandable section cards** (a small `_ExpandableSection` stateful widget: header row with label + count + chevron, animates open/closed via `AnimatedSize`):
  - **Agenda · N** (open by default) — numbered items from the agenda content.
  - **Attendees · N** — name + RSVP badge rows.
  - **Documents · N** — type badge + name rows (tap → open; ✦ summarise lands with Martin later).
  - **Minutes** — shown only if minutes exist; the summary/decisions text.
- A **pinned bottom action bar** (outside the scroll, above the floating nav): **Join** pill (when `video_link`) + the **RSVP** Going/Maybe/No control (participants only), reusing the existing chip + `setRsvp` flow.
- The whole screen sits on the ambient navy+gold backdrop.

### 3.4 Model
Extend the meetings data layer to carry detail content:
- `Meeting` (or a `MeetingDetail`) parses `documents[]` (id, name, type, url) and a nullable `agendaContent`/`minutes` — the detail endpoint already eager-loads agenda + minutes + documents, so prefer parsing them from `GET /meetings/{id}` rather than extra calls. If the single-meeting payload doesn't inline agenda text, fall back to `GET /meetings/{id}/agenda`.
- Keep list parsing unchanged.

## 4. Testing
- Model: parses documents + agenda/minutes from a detail JSON fixture.
- Widget: detail renders title + status; sections expand/collapse on tap; Join + RSVP are present and pinned; tapping RSVP calls the controller.
- Routing: `redirectFor` unchanged; the StatefulShellRoute keeps the nav on a detail location; existing `app_router_test` + `app_shell_test` updated to the shell-route shape and still green.

## 5. Out of scope
Documents in-app preview, the ✦ Summarise action (lands with Martin), minutes editing, offline caching. No backend changes.

## 6. Risks
- The `StatefulShellRoute` refactor touches `app_shell.dart` + `app_router.dart` + their tests — must preserve the grow-gold nav visuals and the `Key('martin-center')`. Keep the nav widget code intact; only rewire selection to the navigation shell.
