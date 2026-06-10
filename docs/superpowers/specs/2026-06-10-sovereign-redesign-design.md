# Sovereign Redesign — UI/UX System Design Spec

**Date:** 2026-06-10
**Status:** Approved direction (Editorial + Motion + one-gold-action), brainstormed via visual companion; grounded in the Flutter-skills audit.
**Hard constraint:** the expanding-pill bottom nav and the floating ✦ Martin FAB are **untouchable** (visuals + behavior).

## Goal

Take the member app from MVP-looking to senior-level: clear visual hierarchy on every screen, a living motion system, and finish-quality polish — with zero regressions (the full test suite stays green throughout).

## Direction (chosen from 3 mockups)

- **A · Editorial (base):** one hero moment per screen; a real bundled serif display face; a strict type scale; sections read eyebrow → headline → detail.
- **C · Motion (layer):** content cascades in by importance; skeleton loaders replace every spinner; hero transitions list→detail; press feedback + haptics; pull-to-refresh.
- **B · One-gold-action (rule):** exactly one solid-gold element per screen — the primary action. All other gold is outline/text accent.

## Audit basis (what this fixes — file-level evidence in the audit)

- 'Georgia' serif referenced in 10+ TextStyles but **not bundled** (pubspec fonts commented out) → headers silently render in the default face.
- **99 inline `TextStyle()`s**, no centralized type scale → no hierarchy.
- Hardcoded bottom paddings (104/120/200) on 7 screens to clear the floating nav.
- Zero motion: no entrances/transitions/press feedback; `CircularProgressIndicator` everywhere.
- No `SystemUiOverlayStyle`, no splash config, no pull-to-refresh, sub-44px touch targets (RSVP chips, filters), missing Semantics labels, body alphas below AA contrast.
- `BackdropFilter` per glass surface with no `RepaintBoundary` (jank on mid-range devices).

## 1. Foundation — design tokens (`lib/core/theme/` additions)

**Typography** (`sovereign_type.dart` + ThemeData wiring):
- Bundle two faces as assets in `pubspec.yaml`: **Fraunces** (display serif — the editorial voice, replaces unbundled Georgia everywhere) and **Inter** (UI sans for body/labels). Download the .ttf files into `assets/fonts/`; no `google_fonts` runtime fetching (offline-safe).
- Type scale (the only sizes allowed): `display` 34 serif / `title` 26 serif / `heading` 20 serif / `section` 16 sans w600 / `body` 14.5 sans / `secondary` 13 sans / `caption` 12 sans / `eyebrow` 10.5 sans w700 +3.0 tracking gold.
- Exposed via `ThemeData.textTheme` mapping + a `context.sovereignText` extension. **Migration rule: no new inline `TextStyle()` for anything the scale covers; existing inline styles are migrated screen-by-screen in the per-screen tasks.**

**Spacing tokens** (`sovereign_spacing.dart`): 4 / 8 / 12 / 16 / 20 / 24 / 32; screen gutter = 20; section gap = 24. Constants only — no magic paddings in new code.

**Color/alpha tokens** (extend `SovereignColors`): `alphaHigh = .87` (primary text), `alphaMid = .70` (secondary — AA-safe bump from today's .55–.65), `alphaLow = .45` (decorative only, never body copy).

**One-gold-action rule:** per screen, exactly one solid-gold filled element (the primary action). Everything else: gold outline, gold text, or ivory. Enforced in the per-screen tasks; documented in the theme file header.

**Nav clearance:** new `SovereignScreen` scaffold helper (or `EdgeInsets get navClearance(BuildContext)`) computing bottom padding from the AppShell nav constants + `MediaQuery.padding.bottom` + safe gap. Replaces every hardcoded 104/120/200.

**System chrome:** `SystemUiOverlayStyle` (transparent status bar, light icons, navy system-nav) set once in `main.dart`; `flutter_native_splash` configured navy with the gold ✦ mark; launcher icon via `flutter_launcher_icons` (gold ✦ on navy) — label stays as WF-B sets it.

## 2. Motion system (`lib/core/motion/`)

- `motion.dart` tokens: `fast 150ms / base 250ms / gentle 400ms`; curves `easeOutCubic` (default), `easeOutBack` (emphasis only).
- **`CascadeIn(index, child)`** — reusable entrance: fade + 14px slide-up, 70ms stagger by index, capped at 8 staggered items (rest appear with the 8th). Used for screen sections and list items on first build only (not on every rebuild — guard with a per-screen "played" flag).
- **Skeletons** (`skeleton.dart`): `SkeletonBlock/SkeletonCard/SkeletonList` glass-toned shimmer widgets. Every `CircularProgressIndicator` in a screen body is replaced by a content-shaped skeleton inside an `AnimatedSwitcher(duration: base)` so skeleton→content cross-fades.
- **`PressableScale`** wrapper for all tappables: scale to 0.97 on press + `HapticFeedback.lightImpact()`; replaces bare `GestureDetector` on cards/chips/pills (nav + FAB excluded — untouchable).
- **Hero transitions:** meeting card title block → meeting-detail header (`Hero` tags by meeting id); document row badge → PDF viewer title.
- **Pull-to-refresh:** `RefreshIndicator` (gold on navyRaised) on Meetings, Documents, Me, Workspace, Home.
- Route transitions: keep `sovereignPage` fade+slide; tune to `base` duration with `easeOutCubic`.

## 3. Screen-by-screen hierarchy (Editorial + one-gold-action)

Each screen task migrates its inline styles to tokens, applies the hero/cascade pattern, and swaps spinner→skeleton. Per-screen primary gold action in parentheses:

- **Home** (gold = **Join** on the hero): eyebrow `WAIIS · <weekday date>` → serif greeting (display) → **hero next-meeting card** (big serif time, attending count, Join pill + quiet Agenda chip) → "THEN" section: task row + TWG workspace row (quiet glass) → Ask-Martin bar (gold outline, not filled).
- **Meetings** (gold = Join on the imminent card): serif title, day-grouped list, the next upcoming meeting rendered ~1.3× with serif time; RSVP chips ≥44px tall; cascade on first load.
- **Meeting detail** (gold = Join in the action bar): keep the tabbed structure + info header from this week's rework; apply tokens, Hero target, cascade on tab content.
- **Documents** (gold = Summarise, once WF-B wires it): serif title, search field, type-badge rows with `PressableScale`; skeleton list.
- **Me** (gold = Add reminder): serif profile header (name display, role/TWG secondary), sectioned action items + reminders with tokens; 44px toggles.
- **Workspace** (gold = Ask Martin card): keep structure; serif TWG name (already), tokens, cascade, skeleton.
- **Martin chat:** tokens only (the consolidation workflow owns its UX — do not collide; this task runs after it merges).
- **Login** (gold = Sign in): serif welcome, cascade entrance, error shake (gentle), loading state on the button itself.
- **Deals:** tokens pass only (Phase-2 screen).

## 4. Performance & accessibility riders

- `RepaintBoundary` around `GlassSurface`'s BackdropFilter; audit each screen to ≤6 live blur layers (compose inner panels without nested blurs — `GlassSurface.inner` may render as tinted opaque instead of a second blur).
- Touch targets ≥44px everywhere (RSVP chips, filter chips, switcher).
- `Semantics` labels: nav pills ("Meetings tab" etc. — labels only, no visual change), Martin FAB ("Ask Martin"), ask bar, RSVP chips, doc rows.
- Body text alphas ≥ .70; verify gold-on-navy and ivory-on-navy pairs ≥ AA for body sizes.
- `ListView.builder` for long lists (meetings/documents) instead of `Column` in `SingleChildScrollView` where item counts are unbounded.

## 5. Testing

- Keep the entire existing suite green; update assertions that reference replaced widgets (e.g. spinner finders → skeleton keys).
- Per redesigned screen: widget test asserting the hero/section structure renders from stubbed state + key Semantics labels exist.
- Motion: unit-test `CascadeIn` stagger math + the "plays once" guard; `PressableScale` triggers haptic callback (mockable).
- No golden tests this pass (device-dependent; deferred).

## 6. Execution & sequencing

- Implemented as **WF-E (redesign workflow)** — runs **after** WF-B (client P0) merges, so it never collides with the Martin-chat workflow or WF-B files. Backend (WF-A/C) is unaffected.
- Task order inside WF-E: T1 foundation tokens+fonts+chrome → T2 motion kit (+tests) → T3 Home → T4 Meetings + detail → T5 Documents + Me → T6 Workspace + Login (+ chat/deals token sweep) → T7 perf/a11y riders → T8 global sweep: zero remaining inline `TextStyle` for scale-covered cases, zero hardcoded nav paddings → full verify + adversarial review + fix.
- Each task: TDD where testable, `flutter analyze` clean + suite green before its commit.

## Out of scope (explicit)

Nav bar & FAB redesign (locked), offline, push (rides WF-B's local buzz only), Deal Room content, i18n, golden tests, any backend change.
