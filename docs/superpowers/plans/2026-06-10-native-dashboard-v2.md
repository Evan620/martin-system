# Native Dashboard V2 Implementation Plan (supersedes Editorial T3–T8)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox steps. Run from `mobile/`; `export PATH="$PATH:/opt/homebrew/bin"`. Commit per task; never push; sequential. Each task ends `flutter analyze` clean + full suite green.

**Goal:** Replace the article-like Editorial screens with a native dashboard language — compact headers, stat tiles, dense list rows, segmented controls, bottom sheets — per the v2 spec.

**Architecture:** A shared component kit in `lib/core/ui/` (AppHeader, StatTile, ListRow/RowGroup, SectionHeader, SovereignSegmented, SovereignSheet, CountBadge) + skeleton variants, then screen-by-screen rework. Controllers/repos/routes unchanged. Motion kit + tokens from the landed T1/T2 are REUSED.

**Spec:** `docs/superpowers/specs/2026-06-10-native-dashboard-v2-design.md` (read it first — it defines per-screen layouts + the one-yellow-action per screen).

**Hard rules:** pill nav + ✦ FAB untouched (colors already tokenized). Martin chat = token-sweep only. Fraunces serif ONLY on Login welcome — remove serif/eyebrow usage from all other screens. Use `SovereignColors`, `Insets`, `navClearance`, `Motion`, `CascadeIn`, `PressableScale`, skeletons — never raw hexes/paddings.

---

## Task 1: Component kit (`lib/core/ui/`) + skeleton variants

**Files:**
- Create: `lib/core/ui/app_header.dart`, `lib/core/ui/stat_tile.dart`, `lib/core/ui/list_row.dart`, `lib/core/ui/section_header.dart`, `lib/core/ui/segmented.dart`, `lib/core/ui/sheet.dart`, `lib/core/ui/count_badge.dart`
- Modify: `lib/core/motion/skeleton.dart` (add `SkeletonTile`, `SkeletonRow`)
- Test: `test/core/ui/components_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/core/ui/components_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/ui/app_header.dart';
import 'package:member_app/core/ui/stat_tile.dart';
import 'package:member_app/core/ui/list_row.dart';
import 'package:member_app/core/ui/section_header.dart';
import 'package:member_app/core/ui/segmented.dart';
import 'package:member_app/core/ui/count_badge.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('AppHeader shows context, title, badge count and initials', (tester) async {
    await tester.pumpWidget(_wrap(const AppHeader(
      context_: 'Tue 10 Jun', title: 'Home', badgeCount: 2, initials: 'AK')));
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Tue 10 Jun'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('AK'), findsOneWidget);
  });

  testWidgets('StatTile renders label/value/sub and taps', (tester) async {
    var tapped = false;
    await tester.pumpWidget(_wrap(StatTile(
      label: 'TASKS DUE', value: '2', sub: '1 overdue', onTap: () => tapped = true)));
    expect(find.text('TASKS DUE'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    await tester.tap(find.text('2'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });

  testWidgets('ListRow renders title/meta and is >=56px tall', (tester) async {
    await tester.pumpWidget(_wrap(RowGroup(children: [
      ListRow(icon: Icons.event, title: 'TWG Energy Sync', meta: '14:00 · Virtual', onTap: () {}),
    ])));
    expect(find.text('TWG Energy Sync'), findsOneWidget);
    final size = tester.getSize(find.byType(ListRow));
    expect(size.height, greaterThanOrEqualTo(56));
  });

  testWidgets('SectionHeader shows title + See all', (tester) async {
    await tester.pumpWidget(_wrap(SectionHeader(title: 'Today', onSeeAll: () {})));
    expect(find.text('Today'), findsOneWidget);
    expect(find.textContaining('See all'), findsOneWidget);
  });

  testWidgets('SovereignSegmented switches selection', (tester) async {
    int sel = 0;
    await tester.pumpWidget(_wrap(StatefulBuilder(builder: (c, set) =>
      SovereignSegmented(options: const ['Upcoming', 'Past'], selected: sel,
        onChanged: (i) => set(() => sel = i)))));
    await tester.tap(find.text('Past'));
    await tester.pumpAndSettle();
    expect(sel, 1);
  });

  testWidgets('CountBadge shows count', (tester) async {
    await tester.pumpWidget(_wrap(const CountBadge(count: 3)));
    expect(find.text('3'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Run — expect FAIL** (files missing): `flutter test test/core/ui/components_test.dart`

- [ ] **Step 3: Implement the components** (exact APIs the test + screens use):

```dart
// lib/core/ui/app_header.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';
import 'count_badge.dart';

/// Compact native-app screen header: small context label over a bold title,
/// trailing notification bell (with optional yellow CountBadge) + avatar chip.
class AppHeader extends StatelessWidget {
  const AppHeader({super.key, required this.title, this.context_, this.badgeCount,
      this.initials, this.onBell, this.onAvatar, this.trailing});
  final String title;
  final String? context_;
  final int? badgeCount;
  final String? initials;
  final VoidCallback? onBell;
  final VoidCallback? onAvatar;
  final Widget? trailing; // overrides bell+avatar when provided

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (context_ != null)
            Text(context_!, style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
          Text(title, style: const TextStyle(fontFamily: 'Inter', fontSize: 19,
              fontWeight: FontWeight.w800, color: SovereignColors.ivory)),
        ]),
      ),
      if (trailing != null) trailing!
      else ...[
        if (onBell != null)
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: onBell,
            child: SizedBox(width: 44, height: 44, child: Stack(alignment: Alignment.center, children: [
              Icon(Icons.notifications_none_rounded, size: 24,
                  color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaHigh)),
              if ((badgeCount ?? 0) > 0)
                Positioned(top: 6, right: 4, child: CountBadge(count: badgeCount!)),
            ])),
          ),
        if (initials != null)
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: onAvatar,
            child: Container(
              width: 30, height: 30,
              decoration: const BoxDecoration(shape: BoxShape.circle,
                  gradient: LinearGradient(colors: [SovereignColors.gold, SovereignColors.sunDeep])),
              alignment: Alignment.center,
              child: Text(initials!, style: const TextStyle(fontFamily: 'Inter', fontSize: 12,
                  fontWeight: FontWeight.w800, color: SovereignColors.navy)),
            ),
          ),
      ],
    ]);
  }
}
```

```dart
// lib/core/ui/count_badge.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';

/// Tiny yellow pill with a bold navy count (notification/unread style).
class CountBadge extends StatelessWidget {
  const CountBadge({super.key, required this.count});
  final int count;
  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 16),
      height: 16,
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(color: SovereignColors.gold, borderRadius: BorderRadius.circular(8)),
      alignment: Alignment.center,
      child: Text('$count', style: const TextStyle(fontFamily: 'Inter', fontSize: 10,
          fontWeight: FontWeight.w800, color: SovereignColors.navy)),
    );
  }
}
```

```dart
// lib/core/ui/stat_tile.dart
import 'package:flutter/material.dart';
import '../motion/pressable.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Dashboard widget tile: uppercase label, big value, sub line, optional
/// embedded action (e.g. the Join pill) and emphasis ring.
class StatTile extends StatelessWidget {
  const StatTile({super.key, required this.label, required this.value, this.sub,
      this.action, this.emphasized = false, this.onTap});
  final String label;
  final String value;
  final String? sub;
  final Widget? action;
  final bool emphasized;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tile = Container(
      padding: const EdgeInsets.all(Insets.md),
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: emphasized
            ? SovereignColors.gold.withValues(alpha: 0.45)
            : SovereignColors.ivory.withValues(alpha: 0.08)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(label.toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontFamily: 'Inter', fontSize: 10, fontWeight: FontWeight.w700,
                letterSpacing: 0.6,
                color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
        const SizedBox(height: Insets.xs),
        Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontFamily: 'Inter', fontSize: 21, fontWeight: FontWeight.w700,
                color: SovereignColors.ivory, height: 1.05)),
        if (sub != null) ...[
          const SizedBox(height: 2),
          Text(sub!, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                  color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
        ],
        if (action != null) ...[const SizedBox(height: Insets.sm), action!],
      ]),
    );
    return onTap == null ? tile : PressableScale(onTap: onTap!, child: tile);
  }
}
```

```dart
// lib/core/ui/list_row.dart
import 'package:flutter/material.dart';
import '../motion/pressable.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Dense native list row: leading icon container, title + meta, trailing
/// chevron / right-meta / custom widget. Use inside [RowGroup].
class ListRow extends StatelessWidget {
  const ListRow({super.key, this.icon, this.leading, required this.title, this.meta,
      this.trailing, this.rightMeta, this.onTap});
  final IconData? icon;
  final Widget? leading; // overrides icon
  final String title;
  final String? meta;
  final Widget? trailing; // overrides chevron
  final String? rightMeta;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final row = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 56),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: Insets.md, vertical: Insets.sm),
        child: Row(children: [
          if (leading != null) leading!
          else if (icon != null)
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                  color: SovereignColors.gold.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(9)),
              child: Icon(icon, size: 17, color: SovereignColors.gold),
            ),
          if (leading != null || icon != null) const SizedBox(width: Insets.md - 2),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(title, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontFamily: 'Inter', fontSize: 14.5,
                      fontWeight: FontWeight.w600, color: SovereignColors.ivory)),
              if (meta != null) ...[
                const SizedBox(height: 2),
                Text(meta!, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                        color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
              ],
            ]),
          ),
          const SizedBox(width: Insets.sm),
          if (trailing != null) trailing!
          else if (rightMeta != null)
            Text(rightMeta!, style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid)))
          else if (onTap != null)
            Icon(Icons.chevron_right, size: 18,
                color: SovereignColors.ivory.withValues(alpha: 0.35)),
        ]),
      ),
    );
    return onTap == null ? row : PressableScale(onTap: onTap!, child: row);
  }
}

/// Groups [ListRow]s in a raised rounded container with hairline dividers.
class RowGroup extends StatelessWidget {
  const RowGroup({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: SovereignColors.ivory.withValues(alpha: 0.07)),
      ),
      child: Column(children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0)
            Divider(height: 1, thickness: 1, indent: Insets.md, endIndent: Insets.md,
                color: SovereignColors.ivory.withValues(alpha: 0.06)),
          children[i],
        ],
      ]),
    );
  }
}
```

```dart
// lib/core/ui/section_header.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';

/// "Today   See all ›" — section title with optional trailing link.
class SectionHeader extends StatelessWidget {
  const SectionHeader({super.key, required this.title, this.onSeeAll, this.seeAllLabel = 'See all ›'});
  final String title;
  final VoidCallback? onSeeAll;
  final String seeAllLabel;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 2, right: 2, bottom: 8),
      child: Row(children: [
        Expanded(child: Text(title, style: const TextStyle(fontFamily: 'Inter',
            fontSize: 15, fontWeight: FontWeight.w700, color: SovereignColors.ivory))),
        if (onSeeAll != null)
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: onSeeAll,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
              child: Text(seeAllLabel, style: const TextStyle(fontFamily: 'Inter',
                  fontSize: 12.5, fontWeight: FontWeight.w700, color: SovereignColors.gold)),
            ),
          ),
      ]),
    );
  }
}
```

```dart
// lib/core/ui/segmented.dart
import 'package:flutter/material.dart';
import '../motion/motion.dart';
import '../theme/sovereign_colors.dart';

/// 2–4 option segmented control on a recessed track; 44px tall.
class SovereignSegmented extends StatelessWidget {
  const SovereignSegmented({super.key, required this.options, required this.selected, required this.onChanged});
  final List<String> options;
  final int selected;
  final ValueChanged<int> onChanged;
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 44,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: SovereignColors.ivory.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(children: [
        for (var i = 0; i < options.length; i++)
          Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => onChanged(i),
              child: AnimatedContainer(
                duration: Motion.fast,
                curve: Motion.curve,
                decoration: BoxDecoration(
                  color: i == selected ? SovereignColors.navyRaised : Colors.transparent,
                  borderRadius: BorderRadius.circular(9),
                  border: i == selected
                      ? Border.all(color: SovereignColors.ivory.withValues(alpha: 0.1))
                      : null,
                ),
                alignment: Alignment.center,
                child: Text(options[i], style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: SovereignColors.ivory.withValues(
                        alpha: i == selected ? SovereignColors.alphaHigh : SovereignColors.alphaMid))),
              ),
            ),
          ),
      ]),
    );
  }
}
```

```dart
// lib/core/ui/sheet.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Sovereign bottom sheet for quick actions (RSVP, add reminder, doc actions).
Future<T?> showSovereignSheet<T>(BuildContext context, {required Widget child}) {
  return showModalBottomSheet<T>(
    context: context,
    backgroundColor: SovereignColors.navyRaised,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (c) => SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
            left: Insets.xl, right: Insets.xl, top: Insets.md,
            bottom: Insets.xl + MediaQuery.of(c).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 36, height: 4,
              decoration: BoxDecoration(
                  color: SovereignColors.ivory.withValues(alpha: 0.25),
                  borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: Insets.lg),
          child,
        ]),
      ),
    ),
  );
}
```

- [ ] **Step 4: Add skeleton variants** to `lib/core/motion/skeleton.dart` (append):

```dart
/// Tile-shaped loading placeholder (pairs with StatTile grids).
class SkeletonTile extends StatelessWidget {
  const SkeletonTile({super.key});
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: SovereignColors.ivory.withValues(alpha: 0.07)),
      ),
      child: const Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        SkeletonBlock(width: 70, height: 9),
        SizedBox(height: 8),
        SkeletonBlock(width: 54, height: 18),
        SizedBox(height: 6),
        SkeletonBlock(width: 90, height: 9),
      ]),
    );
  }
}

/// Row-shaped loading placeholder (pairs with ListRow groups).
class SkeletonRow extends StatelessWidget {
  const SkeletonRow({super.key});
  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      child: Row(children: [
        SkeletonBlock(width: 32, height: 32, radius: 9),
        SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SkeletonBlock(width: 150, height: 12),
          SizedBox(height: 6),
          SkeletonBlock(width: 100, height: 9),
        ])),
      ]),
    );
  }
}
```
(If `SkeletonBlock` lacks a `radius`/width combo used here, adapt to its real signature.)

- [ ] **Step 5: Run the component tests — expect PASS**: `flutter test test/core/ui/components_test.dart`
- [ ] **Step 6: `flutter analyze lib/core test/core` clean → commit** `feat(mobile): native dashboard component kit — AppHeader, StatTile, ListRow, Segmented, Sheet`

---

## Shared screen recipe (T2–T5)

For each screen: read it fully first; keep its controller/repo/route wiring EXACTLY as-is; replace the Editorial layout with the v2 structure from the spec. Always: `AppHeader` (no serif, no eyebrow labels), content per spec, `CascadeIn` entrances (tiles 0–3 then rows), `AnimatedSwitcher` skeleton→content using `SkeletonTile`/`SkeletonRow` shapes, `RefreshIndicator(color: SovereignColors.gold, backgroundColor: SovereignColors.navyRaised)`, `navClearance(context)` bottom padding, exactly ONE filled-yellow action (named per task), `PressableScale` via the kit components. Update the screen's tests for the new structure (header finder, tile values, rows) and keep the whole suite green before committing.

## Task 2: Home — dashboard rework

**Files:** Modify `lib/features/home/presentation/home_screen.dart`; Test `test/features/home/home_screen_test.dart`

- [ ] `AppHeader(context_: '<EEE d MMM>', title: 'Home', initials: <from authed user's fullName>, badgeCount: briefing.overdueCount (hide when 0), onAvatar: → '/me' branch via context.go('/me'))`.
- [ ] **2×2 tile grid** (two `Row`s of two `Expanded` tiles with `Insets.sm` gaps — no GridView needed): ① Next meeting (emphasized, label `NEXT MEETING${relative}`, value = HH:mm of `nextMeeting.startsAt` (fall back to the relative phrase when null), sub = title + ' · N going' if available, action = the **Join pill** (THE yellow action; only when videoLink != null, launches via url_launcher), onTap → `/meetings`); ② Tasks due (value = overdueCount, sub = 'action items', onTap → `/me`); ③ My TWG (value = first TWG name or '—', sub = 'open workspace ›', onTap → `/home/workspace/<id>`; hide-or-dash when no TWG); ④ Ask Martin (value '✦', sub 'ask anything', onTap → `/martin` — NOT yellow-filled, quiet tile).
- [ ] `SectionHeader('Today', onSeeAll: → '/meetings')` + `RowGroup` mixing: the next meeting row (icon event, meta time·location, rightMeta relative), an overdue-tasks row when count>0 (icon flag, → `/me`), and keep the existing Your-TWGs rows if >1 TWG (each as `ListRow` → workspace). The old `_MartinBriefingCard`, serif `_Greeting`, `_Eyebrow`, suggestion chips and `_AskMartinBar` are REMOVED (Martin entry = tile ④ + the FAB).
- [ ] Loading = 4 `SkeletonTile`s + 3 `SkeletonRow`s. Error view unchanged pattern.
- [ ] Tests: header 'Home' renders; tiles show briefing-derived values; Join hidden when no videoLink; loading shows SkeletonTile. Commit `feat(mobile): Home v2 — dashboard tiles + today rows`.

## Task 3: Meetings list + detail header rework

**Files:** Modify `lib/features/meetings/presentation/meetings_screen.dart`, `meeting_detail_screen.dart`; Tests in `test/features/meetings/`

- [ ] **List:** `AppHeader(title: 'Meetings', context_: TWG label)`. `SovereignSegmented(['Upcoming','Past'])` filtering by `scheduledAt` vs now. Group by day (Today/Tomorrow/`EEE d MMM`) — each group: `SectionHeader(label)` + `RowGroup` of meeting rows: leading = a 38px time block (HH:mm bold 13 + duration 10 under, in the icon-container style), title, meta `${twg ?? ''} · ${location/Virtual} · ${rsvp state ✓/?}`, trailing chevron; the SOONEST upcoming row gets an inline **Join pill** trailing (THE yellow action) when it has video. Row tap → detail (route unchanged). Long-press a row → `showSovereignSheet` with three RSVP options wired to the existing controller `setRsvp` (reuse the list screen's existing handler).
- [ ] **Detail:** replace the serif title block with compact header (back button + status chip right, then title 19 w800 sans + meta line); info header chips stay but adopt Inter sizes; tabs/action-bar/Hero/back logic unchanged; Join in the pinned bar stays the yellow action.
- [ ] Update meetings tests (serif-header finders → new header; keep skeleton + RSVP assertions). Commit `feat(mobile): Meetings v2 — segmented day-grouped rows + sheet RSVP; compact detail header`.

## Task 4: Documents + Me rework

**Files:** Modify `lib/features/documents/presentation/documents_screen.dart`, `lib/features/profile/presentation/me_screen.dart`; Tests in respective dirs

- [ ] **Documents:** `AppHeader('Documents', context_: TWG label)`; keep the existing search field (themed); filter chips row stays (44px). Rows → `RowGroup` of `ListRow`s: leading = type badge container (existing kind badge text), title = file name, meta = `${twg ?? 'Global'} · ${date} · ${uploader}`, trailing = **✦ Summarise icon-button (yellow — THE action)** that pushes the existing `/martin?q=Summarise…` route; row tap = existing open behavior. Loading = SkeletonRows. Confidential chip/filter behavior unchanged.
- [ ] **Me:** compact profile header (40px initials avatar, name 17 w800, role·TWG meta) — no serif. Two `StatTile`s (Tasks due / Reminders count). `SovereignSegmented(['Tasks','Reminders'])` switching the list below: Tasks = rows with leading checkbox (existing markDone wiring), Reminders = rows with clock icon + delete affordance (existing wiring). **Add reminder = THE yellow action**: a yellow pill button by the Reminders section header opening `showSovereignSheet` containing the existing add-reminder inputs (message + time picker → existing controller `addReminder`). Notification toggles section stays (44px rows). Sign-out row stays.
- [ ] Update both screens' tests. Commit `feat(mobile): Documents + Me v2 — icon rows, segmented Me, sheet add-reminder`.

## Task 5: Workspace + Login rework

**Files:** Modify `lib/features/workspace/presentation/workspace_screen.dart`, the login screen (find under `lib/features/auth/presentation/`); Tests in respective dirs

- [ ] **Workspace:** `AppHeader(title: <TWG name>, context_: pillarLabel, trailing: existing switcher (restyle trigger as a chip; keep `Key('workspace-switcher')` + replace-navigation))`. Row of 3 `StatTile`s (Members / Open actions / Next mtg HH:mm or '—'). Sections: `SectionHeader('Next meeting')` + meeting `ListRow`; `SectionHeader('Documents')` + `RowGroup` rows (cap 5, '+N more' kept); `SectionHeader('Your tasks')` + rows. **Ask Martin = THE yellow action** — a full-width yellow pill row/button → `/martin?twg=`. Controller/best-effort logic unchanged.
- [ ] **Login:** Fraunces serif welcome stays (the one serif moment), Inter everywhere else; fields themed; **Sign in = yellow** with in-button spinner; CascadeIn entrance; error inline.
- [ ] Update tests (workspace section labels are now SectionHeaders — adjust finders e.g. 'Next meeting' not 'NEXT MEETING'). Commit `feat(mobile): Workspace + Login v2`.

## Task 6: Sweep — kill the article

**Files:** all `lib/features/**` + `lib/shell`

- [ ] Grep sweep and fix every remainder:
```bash
cd mobile
echo "Serif on app screens (only login may match):"; grep -rn "SovereignType.display\|SovereignType.title\|fontFamily: 'Fraunces'\|Georgia" lib/features lib/shell | grep -v login || echo "none ✓"
echo "Eyebrow labels left:"; grep -rn "SovereignType.eyebrow\|letterSpacing: 3" lib/features | grep -v login | head
echo "Old hero/editorial widgets:"; grep -rn "_Eyebrow\|_Greeting\|_MartinBriefingCard\|_AskMartinBar" lib/features | head
echo "Raw hexes:"; grep -rn "0xFF[0-9A-Fa-f]\{6\}" lib/features lib/shell | grep -v sovereign_colors || echo "none ✓"
echo "Hardcoded nav paddings:"; grep -rn "bottom: 104\|bottom: 120\|bottom: 200" lib || echo "none ✓"
```
- [ ] Martin chat + Deals: confirm token-only state (no restructure); fix any straggler raw styles.
- [ ] `flutter analyze` clean + `flutter test` FULL suite green. Commit `chore(mobile): v2 sweep — no editorial remnants`.

## Task 7: Final verification

- [ ] `flutter analyze` → clean. `flutter test` → all green (count reported).
- [ ] Hot-restart the running web preview if alive (`/Users/evan/ravishing-presence-web` worktree is SEPARATE — do not touch it; just note the main checkout is ready) — the lead handles the visual pass.

## Self-review notes
Spec components §→T1 · Home§→T2 · Meetings§→T3 · Docs/Me§→T4 · Workspace/Login§→T5 · one-yellow-action named per screen · motion/skeleton/refresh in the shared recipe · nav/FAB/chat untouched · serif only on Login.
