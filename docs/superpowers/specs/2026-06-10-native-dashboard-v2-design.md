# Native Dashboard V2 — Design Spec (supersedes the Editorial direction)

**Date:** 2026-06-10 · **Status:** Approved (user: "v2 looks nice") after the Editorial redesign read like an article.
**Research basis:** `2026-06-10-mobile-ui-inspiration-research.md` (Revolut/CRED/Spotify/Monzo language).
**Hard constraints:** pill nav + ✦ FAB untouchable. Martin chat screen: token-sweep only. Palette stays Bright Sun `#FCDB32` on Big Stone `#141D38` (SovereignColors as committed). Full test suite stays green.

## The shift

Editorial (serif heroes, eyebrows, prose whitespace, 3 info units/screen) → **Native Dashboard**: compact headers, widget tiles, dense list rows, segmented controls, bottom sheets, 6–10 info units/screen, exactly one filled-yellow action per screen.

## What carries over from the landed work (do NOT redo)

- Palette/tokens/alpha (`sovereign_colors.dart`), spacing + `navClearance` (`sovereign_spacing.dart`), bundled fonts.
- The entire motion kit: `CascadeIn`, `PressableScale`, `SkeletonBlock/Card/List`, `Motion` tokens — reused on tiles/rows.
- Pull-to-refresh, AnimatedSwitcher skeleton→content, 44px targets, system chrome.
- Type scale file stays, but **screen usage changes**: `SovereignType.display/title (Fraunces serif) are RESERVED for the Login welcome and rare brand moments only — never on app screens.** App screens use Inter: header title 17–20 w800, tile numerals 19–24 w700, row title 14.5 w600, meta 12–13 @ alphaMid, section header 15 w700.

## New shared components (`lib/core/ui/`)

1. **`AppHeader`** — compact screen header: small date/context label (12, alphaMid) over screen title (17–20, w800), trailing actions (notification bell with yellow count `Badge`, 26px avatar with initials). NOT a 34px serif block.
2. **`StatTile`** — tappable widget tile for the 2-col grid (`GridView`/`Row` pairs): label (10–11 uppercase, alphaMid) → big value (19–24 w700 ivory) → sub line (12 alphaMid); optional embedded action pill. Surface `navyRaised`, 13px radius, `PressableScale`.
3. **`ListRow`** — the workhorse: 56–64px row, leading 28–36px icon container (yellow @12% bg, radius 9), title (14.5 w600, ellipsis), meta line (12 alphaMid), trailing chevron OR right-aligned meta. Rows grouped inside a `navyRaised` rounded container with hairline dividers (`RowGroup` wrapper).
4. **`SectionHeader`** — row: title (15 w700) + trailing "See all ›" (12.5 w700 yellow text).
5. **`SovereignSegmented`** — 2–4 segment control: pill track (ivory @6%), active segment `navyRaised` full-opacity; 44px tall.
6. **`SovereignSheet`** — `showModalBottomSheet` helper: `navyRaised`, top radius 20, drag handle, for quick actions (RSVP, add reminder, doc actions).
7. **`CountBadge`** — small yellow pill (min 16px) with navy bold count.

One-yellow-action rule continues: per screen exactly one filled-yellow element; badges/selected-states are the only other yellow fills (tiny).

## Screens (rework T3/T4 outputs + build the rest)

- **Home:** `AppHeader` ("Tue 10 Jun" / "Home" / bell+badge / avatar) → **2×2 StatTiles**: Next meeting (label "NEXT MEETING · 2h", value time, sub title+going, embedded **Join** = THE yellow action, hidden when no link), Tasks due (count, overdue flag), My TWG (name, members, → workspace), New docs (count this week). → `SectionHeader` "Today" + `RowGroup` of up to 5 mixed rows (today's meeting / due task / recent doc) each navigating to its feature. FAB stays. Empty briefing → tiles show 0-states, never blank.
- **Meetings:** `AppHeader` + `SovereignSegmented` Upcoming/Past → date-grouped `RowGroup`s (group label = "Today"/"Tomorrow"/"Thu 12 Jun"): each row leading time block (HH:mm bold + duration under), title, meta (TWG · location/Virtual · RSVP state ✓), trailing chevron; the imminent meeting's row carries an inline **Join** pill (the screen's yellow action). RSVP via **bottom sheet** (tap row → detail unchanged; long-press or detail action bar opens `SovereignSheet` with Going/Maybe/No — wire to existing controller).
- **Meeting detail:** keep tabs + pinned action bar; replace serif header block with `AppHeader`-style compact title + status chip; info header becomes a horizontal chip row; attendees/docs already row-based — adopt `ListRow` styling. Join stays the yellow action.
- **Documents:** `AppHeader` + search field + filter chips row (All/PDF/Sheets/Slides + confidentiality) → `RowGroup` rows: type-badge icon container, file name, meta (TWG · date · uploader), trailing chevron; **✦ Summarise** = trailing yellow micro-action on each row or in the doc bottom sheet — ONE pattern, picked consistently (recommend: row tap → existing open; trailing ✦ icon button = Summarise, yellow, that's the screen action).
- **Me:** compact profile header (avatar lg, name 17 w800, role·TWG chip) → 2 StatTiles (Tasks due / Done this week) → `SovereignSegmented` Tasks/Reminders → `RowGroup` with leading checkbox (tasks) or clock icon (reminders); **Add reminder** = yellow action (header + sheet input via `SovereignSheet`).
- **Workspace:** `AppHeader` with TWG name + switcher chip → 3 StatTiles (Members / Open actions / Next meeting) → sections as `RowGroup`s (docs, tasks) → **Ask Martin** row/card = yellow action. Structure/controller unchanged.
- **Login:** the ONE place Fraunces lives — serif welcome; fields; **Sign in** yellow w/ in-button spinner; cascade entrance.
- **Deals / Martin chat:** token-sweep only.

## Motion mapping

CascadeIn: tiles (indices 0–3) then section rows. Skeletons: tile-shaped + row-shaped variants (add `SkeletonTile`, `SkeletonRow` to skeleton.dart). PressableScale on every tile/row/chip. Pull-to-refresh everywhere lists load.

## Testing

Suite stays green; update screen tests for the new structures (header title finder, StatTile values, RowGroup rows, segmented switching, sheet opens + RSVP wires to controller). Component unit tests for StatTile/ListRow/Segmented/CountBadge rendering + 44px constraints.

## Out of scope

Nav/FAB redesign, offline, push, Deal Room content, i18n, backend changes.
