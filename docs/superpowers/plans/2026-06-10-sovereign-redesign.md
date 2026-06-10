# Sovereign Redesign (WF-E) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Run from `mobile/`; `export PATH="$PATH:/opt/homebrew/bin"` so `flutter` resolves. Commit per task; never push; sequential. Each task ends `flutter analyze` clean + suite green before its commit.

**Goal:** Lift the member app to senior-level: real type hierarchy (bundled serif + scale), a motion system (cascade entrances, skeletons, press feedback, hero transitions, pull-to-refresh), and finish polish — zero regressions, the pill nav + ✦ FAB untouched.

**Architecture:** Add `lib/core/theme/` tokens (type scale, spacing, alpha) wired into `ThemeData`, a `lib/core/motion/` kit (reusable entrance/press/skeleton widgets), and a nav-clearance helper — then migrate each screen to tokens + the motion patterns, one screen per task. One solid-gold action per screen.

**Tech Stack:** Flutter, flutter_riverpod, go_router, intl, gpt_markdown (already added). New bundled fonts: Fraunces (serif display), Inter (UI sans). No new runtime packages except dev/build tooling (flutter_native_splash, flutter_launcher_icons) installed in T1.

**Spec:** `docs/superpowers/specs/2026-06-10-sovereign-redesign-design.md`

**Conventions (verified):** `SovereignColors` (navy 0xFF0A1F44, navyDeep 0x08152F, navyRaised 0x0E2A55, gold 0xFFC9A227, ivory 0xFFF6F1E7, danger 0x9B3A2E, success 0x2F6B4F) in `lib/core/theme/sovereign_colors.dart`. `SovereignTheme.dark()` in `sovereign_theme.dart` currently maps displaySmall/headlineMedium/titleLarge to **unbundled** 'Georgia'. Nav constants in `lib/shell/app_shell.dart`: `_navInner = 52 + 16`, `_navBottomGap = 14`. Page transition: `sovereignPage()` in `lib/routing/sovereign_page.dart`. `main.dart` runs `runApp` with a ProviderScope override.

**Sequencing:** This is WF-E; it runs **after** WF-B (client P0) merges and **after** the Martin-chat consolidation workflow merges. The Martin chat screen is therefore OWNED by that workflow — this plan only token-sweeps it (T6), never restructures it.

---

## File Structure

**Create:**
- `lib/core/theme/sovereign_type.dart` — type scale + `BuildContext.stext` extension
- `lib/core/theme/sovereign_spacing.dart` — spacing constants + `navClearance(context)`
- `lib/core/motion/motion.dart` — duration/curve tokens
- `lib/core/motion/cascade_in.dart` — staggered entrance widget
- `lib/core/motion/pressable.dart` — `PressableScale` (scale + haptic)
- `lib/core/motion/skeleton.dart` — shimmer skeleton widgets
- `assets/fonts/*.ttf` — Fraunces (500,600), Inter (400,500,600,700)
- tests under `test/core/theme/`, `test/core/motion/`

**Modify:** `pubspec.yaml` (fonts + assets + splash/icon dev deps), `sovereign_theme.dart`, `sovereign_colors.dart` (alpha tokens), `main.dart` (system chrome), `sovereign_page.dart` (motion tokens), `lib/core/glass/glass.dart` (RepaintBoundary), and each screen under `lib/features/*/presentation/`.

---

## Task 1: Foundation — fonts, type scale, spacing, alpha, system chrome

**Files:**
- Modify: `pubspec.yaml`
- Create: `assets/fonts/` (.ttf files), `lib/core/theme/sovereign_type.dart`, `lib/core/theme/sovereign_spacing.dart`
- Modify: `lib/core/theme/sovereign_colors.dart`, `lib/core/theme/sovereign_theme.dart`, `lib/main.dart`
- Test: `test/core/theme/sovereign_type_test.dart`

- [ ] **Step 1: Fetch the fonts** (static weights, offline-safe, from the fontsource jsDelivr CDN)

```bash
cd mobile && mkdir -p assets/fonts
base="https://cdn.jsdelivr.net/fontsource/fonts"
curl -fsSL "$base/inter@latest/latin-400-normal.ttf"     -o assets/fonts/Inter-Regular.ttf
curl -fsSL "$base/inter@latest/latin-500-normal.ttf"     -o assets/fonts/Inter-Medium.ttf
curl -fsSL "$base/inter@latest/latin-600-normal.ttf"     -o assets/fonts/Inter-SemiBold.ttf
curl -fsSL "$base/inter@latest/latin-700-normal.ttf"     -o assets/fonts/Inter-Bold.ttf
curl -fsSL "$base/fraunces@latest/latin-500-normal.ttf"  -o assets/fonts/Fraunces-Medium.ttf
curl -fsSL "$base/fraunces@latest/latin-600-normal.ttf"  -o assets/fonts/Fraunces-SemiBold.ttf
ls -lh assets/fonts/   # expect 6 non-empty .ttf files
```
Expected: six `.ttf` files, each > 50 KB. (If the CDN path 404s, fall back to `https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf` and `.../ofl/fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf` as single variable fonts, declaring one asset per family without weight descriptors.)

- [ ] **Step 2: Declare fonts + assets in `pubspec.yaml`** — replace the commented `# fonts:` block (lines ~73-102) and the `uses-material-design: true` flutter section tail with:

```yaml
  uses-material-design: true

  assets:
    - assets/fonts/

  fonts:
    - family: Fraunces
      fonts:
        - asset: assets/fonts/Fraunces-Medium.ttf
          weight: 500
        - asset: assets/fonts/Fraunces-SemiBold.ttf
          weight: 600
    - family: Inter
      fonts:
        - asset: assets/fonts/Inter-Regular.ttf
          weight: 400
        - asset: assets/fonts/Inter-Medium.ttf
          weight: 500
        - asset: assets/fonts/Inter-SemiBold.ttf
          weight: 600
        - asset: assets/fonts/Inter-Bold.ttf
          weight: 700
```
Run `flutter pub get`.

- [ ] **Step 3: Add alpha tokens to `sovereign_colors.dart`** — append inside the class:

```dart
  /// Text/opacity tokens (AA-safe for body sizes on navy).
  static const double alphaHigh = 0.87; // primary text
  static const double alphaMid = 0.70;  // secondary text (AA floor)
  static const double alphaLow = 0.45;  // decorative only — never body copy
```

- [ ] **Step 4: Write the failing test** `test/core/theme/sovereign_type_test.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_type.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';

void main() {
  test('SovereignType exposes the scale with the right fonts/sizes', () {
    expect(SovereignType.display.fontFamily, 'Fraunces');
    expect(SovereignType.display.fontSize, 34);
    expect(SovereignType.title.fontFamily, 'Fraunces');
    expect(SovereignType.heading.fontFamily, 'Fraunces');
    expect(SovereignType.section.fontFamily, 'Inter');
    expect(SovereignType.body.fontFamily, 'Inter');
    expect(SovereignType.body.fontSize, 14.5);
    expect(SovereignType.eyebrow.letterSpacing, 3.0);
    expect(SovereignType.eyebrow.color, SovereignColors.gold);
  });

  testWidgets('context.stext returns scale styles', (tester) async {
    late BuildContext ctx;
    await tester.pumpWidget(MaterialApp(home: Builder(builder: (c) { ctx = c; return const SizedBox(); })));
    expect(ctx.stext.display.fontSize, 34);
    expect(ctx.stext.body.fontSize, 14.5);
  });
}
```

- [ ] **Step 5: Run it — expect FAIL** (`sovereign_type.dart` missing): `flutter test test/core/theme/sovereign_type_test.dart`

- [ ] **Step 6: Create `lib/core/theme/sovereign_type.dart`**

```dart
// lib/core/theme/sovereign_type.dart
import 'package:flutter/widgets.dart';
import 'sovereign_colors.dart';

/// The ONE type scale. No screen should declare a TextStyle for anything this
/// covers — use these (or .copyWith on these for one-off color/weight tweaks).
abstract final class SovereignType {
  static const _serif = 'Fraunces';
  static const _sans = 'Inter';
  static const _ivory = SovereignColors.ivory;

  static const display = TextStyle(fontFamily: _serif, fontSize: 34, fontWeight: FontWeight.w600, height: 1.06, color: _ivory);
  static const title = TextStyle(fontFamily: _serif, fontSize: 26, fontWeight: FontWeight.w500, height: 1.1, color: _ivory);
  static const heading = TextStyle(fontFamily: _serif, fontSize: 20, fontWeight: FontWeight.w500, height: 1.15, color: _ivory);
  static const section = TextStyle(fontFamily: _sans, fontSize: 16, fontWeight: FontWeight.w600, height: 1.25, color: _ivory);
  static const body = TextStyle(fontFamily: _sans, fontSize: 14.5, fontWeight: FontWeight.w400, height: 1.42, color: _ivory);
  static const secondary = TextStyle(fontFamily: _sans, fontSize: 13, fontWeight: FontWeight.w400, height: 1.4, color: _ivory);
  static const caption = TextStyle(fontFamily: _sans, fontSize: 12, fontWeight: FontWeight.w500, height: 1.3, color: _ivory);
  static const eyebrow = TextStyle(fontFamily: _sans, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 3.0, color: SovereignColors.gold);
}

/// `context.stext.display` ergonomic access (mirrors Theme.of(context).textTheme).
extension SovereignTextX on BuildContext {
  SovereignType get stext => const SovereignType._();
}

extension on SovereignType {
  const SovereignType._();
  TextStyle get display => SovereignType.display;
  TextStyle get title => SovereignType.title;
  TextStyle get heading => SovereignType.heading;
  TextStyle get section => SovereignType.section;
  TextStyle get body => SovereignType.body;
  TextStyle get secondary => SovereignType.secondary;
  TextStyle get caption => SovereignType.caption;
  TextStyle get eyebrow => SovereignType.eyebrow;
}
```
> Note: `abstract final class` can't be instantiated; replace the `extension on SovereignType` + `context.stext` approach with a concrete tiny holder if the analyzer objects — define `class _Stext { const _Stext(); TextStyle get display => SovereignType.display; ... }` and `extension SovereignTextX on BuildContext { _Stext get stext => const _Stext(); }`. Pick whichever compiles; the test only needs `context.stext.display`/`.body` and the static `SovereignType.*` getters.

- [ ] **Step 7: Run the test — expect PASS.** If the `extension on SovereignType` form fails to compile, switch to the `_Stext` holder noted above, re-run.

- [ ] **Step 8: Wire the scale into `sovereign_theme.dart`** — replace the `textTheme: base.textTheme.copyWith(...)` block so Material defaults use the new fonts (so stray `Theme.of(context).textTheme` and Material widgets inherit correctly):

```dart
      textTheme: base.textTheme.copyWith(
        displaySmall: SovereignType.display,
        displayMedium: SovereignType.title,
        headlineMedium: SovereignType.heading,
        titleLarge: SovereignType.heading,
        titleMedium: SovereignType.section,
        bodyLarge: SovereignType.body,
        bodyMedium: SovereignType.body,
        bodySmall: SovereignType.secondary,
        labelLarge: SovereignType.caption,
      ),
```
Add `import 'sovereign_type.dart';` at the top. Remove all 'Georgia' references.

- [ ] **Step 9: Create `lib/core/theme/sovereign_spacing.dart`**

```dart
// lib/core/theme/sovereign_spacing.dart
import 'package:flutter/widgets.dart';

/// Spacing scale — the only gap/padding values allowed in new layout code.
abstract final class Insets {
  static const xs = 4.0, sm = 8.0, md = 12.0, lg = 16.0, xl = 20.0, xxl = 24.0, huge = 32.0;
  static const gutter = 20.0;     // screen horizontal padding
  static const section = 24.0;    // gap between major sections
}

/// Bottom padding a scrollable needs to clear the floating pill nav.
/// Mirrors AppShell: nav intrinsic height (52+16) + bottom gap (14) + safe inset.
EdgeInsets navClearance(BuildContext context, {double extra = 24}) {
  final bottomInset = MediaQuery.of(context).padding.bottom;
  const navInner = 52 + 16, navBottomGap = 14;
  return EdgeInsets.only(bottom: navInner + navBottomGap + bottomInset + extra);
}
```

- [ ] **Step 10: Add system chrome to `main.dart`** — add imports `package:flutter/services.dart` + the colors, and inside `main()` after `ensureInitialized()`:

```dart
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Color(0x00000000),
    statusBarIconBrightness: Brightness.light,
    statusBarBrightness: Brightness.dark,
    systemNavigationBarColor: SovereignColors.navyDeep,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
```

- [ ] **Step 11: Verify + commit**

Run: `flutter analyze lib/core test/core` (clean) and `flutter test test/core/theme/sovereign_type_test.dart` (pass) and a quick `flutter test` (suite green — existing tests that referenced 'Georgia' indirectly should be unaffected; if any golden/style test asserted Georgia, update it to Fraunces).
```bash
git add pubspec.yaml assets/fonts lib/core/theme/sovereign_type.dart lib/core/theme/sovereign_spacing.dart lib/core/theme/sovereign_colors.dart lib/core/theme/sovereign_theme.dart lib/main.dart test/core/theme/sovereign_type_test.dart
git commit -m "feat(mobile): design tokens — bundled Fraunces/Inter, type scale, spacing, alpha, system chrome"
```

---

## Task 2: Motion kit — tokens, CascadeIn, PressableScale, skeletons

**Files:**
- Create: `lib/core/motion/motion.dart`, `lib/core/motion/cascade_in.dart`, `lib/core/motion/pressable.dart`, `lib/core/motion/skeleton.dart`
- Test: `test/core/motion/cascade_in_test.dart`, `test/core/motion/pressable_test.dart`

- [ ] **Step 1: Create `lib/core/motion/motion.dart`**

```dart
// lib/core/motion/motion.dart
import 'package:flutter/animation.dart';

abstract final class Motion {
  static const fast = Duration(milliseconds: 150);
  static const base = Duration(milliseconds: 250);
  static const gentle = Duration(milliseconds: 400);
  static const stagger = Duration(milliseconds: 70); // per-index entrance delay
  static const Curve curve = Curves.easeOutCubic;
  static const Curve emphasis = Curves.easeOutBack;
  static const int maxStagger = 8; // items past this share the last delay
}
```

- [ ] **Step 2: Write the failing test** `test/core/motion/cascade_in_test.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/motion/cascade_in.dart';
import 'package:member_app/core/motion/motion.dart';

void main() {
  test('staggerDelayFor caps at maxStagger', () {
    expect(CascadeIn.staggerDelayFor(0), Duration.zero);
    expect(CascadeIn.staggerDelayFor(3), Motion.stagger * 3);
    expect(CascadeIn.staggerDelayFor(20), Motion.stagger * Motion.maxStagger);
  });

  testWidgets('CascadeIn renders its child and settles fully opaque', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: CascadeIn(index: 2, child: Text('hi')))));
    expect(find.text('hi'), findsOneWidget);
    await tester.pumpAndSettle();
    final op = tester.widget<FadeTransition>(find.ancestor(of: find.text('hi'), matching: find.byType(FadeTransition)).first);
    expect(op.opacity.value, 1.0);
  });
}
```

- [ ] **Step 3: Run — expect FAIL** (missing file): `flutter test test/core/motion/cascade_in_test.dart`

- [ ] **Step 4: Create `lib/core/motion/cascade_in.dart`**

```dart
// lib/core/motion/cascade_in.dart
import 'package:flutter/material.dart';
import 'motion.dart';

/// Fade + 14px rise entrance, staggered by [index]. Plays once on first build
/// (a screen that rebuilds — e.g. on a state change — should pass replay:false
/// or rebuild the list with the same keys so this does not re-animate).
class CascadeIn extends StatefulWidget {
  const CascadeIn({super.key, required this.index, required this.child, this.replay = false});
  final int index;
  final Widget child;
  final bool replay;

  static Duration staggerDelayFor(int index) {
    final i = index < 0 ? 0 : (index > Motion.maxStagger ? Motion.maxStagger : index);
    return Motion.stagger * i;
  }

  @override
  State<CascadeIn> createState() => _CascadeInState();
}

class _CascadeInState extends State<CascadeIn> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: Motion.gentle);
  late final Animation<double> _fade = CurvedAnimation(parent: _c, curve: Motion.curve);
  late final Animation<Offset> _slide = Tween(begin: const Offset(0, 0.06), end: Offset.zero).animate(_fade);

  @override
  void initState() {
    super.initState();
    Future.delayed(CascadeIn.staggerDelayFor(widget.index), () { if (mounted) _c.forward(); });
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) =>
      FadeTransition(opacity: _fade, child: SlideTransition(position: _slide, child: widget.child));
}
```

- [ ] **Step 5: Run — expect PASS.**

- [ ] **Step 6: Write the failing test** `test/core/motion/pressable_test.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/motion/pressable.dart';

void main() {
  testWidgets('PressableScale fires onTap', (tester) async {
    var tapped = false;
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Center(
      child: PressableScale(onTap: () => tapped = true, child: const Text('go')),
    ))));
    await tester.tap(find.text('go'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });
}
```

- [ ] **Step 7: Run — expect FAIL.**

- [ ] **Step 8: Create `lib/core/motion/pressable.dart`**

```dart
// lib/core/motion/pressable.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'motion.dart';

/// Tappable wrapper: scales to 0.97 while pressed + light haptic on tap.
/// Use on cards/chips/pills (NOT the nav pills or ✦ FAB — those are locked).
class PressableScale extends StatefulWidget {
  const PressableScale({super.key, required this.child, required this.onTap, this.haptic = true, this.pressedScale = 0.97});
  final Widget child;
  final VoidCallback onTap;
  final bool haptic;
  final double pressedScale;

  @override
  State<PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<PressableScale> {
  bool _down = false;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _down = true),
      onTapCancel: () => setState(() => _down = false),
      onTapUp: (_) => setState(() => _down = false),
      onTap: () { if (widget.haptic) HapticFeedback.lightImpact(); widget.onTap(); },
      child: AnimatedScale(
        scale: _down ? widget.pressedScale : 1.0,
        duration: Motion.fast,
        curve: Motion.curve,
        child: widget.child,
      ),
    );
  }
}
```

- [ ] **Step 9: Run — expect PASS.**

- [ ] **Step 10: Create `lib/core/motion/skeleton.dart`**

```dart
// lib/core/motion/skeleton.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';
import '../glass/glass.dart';

/// A shimmering placeholder block. Compose into content-shaped skeletons that
/// replace CircularProgressIndicator in screen bodies.
class SkeletonBlock extends StatefulWidget {
  const SkeletonBlock({super.key, this.width, this.height = 12, this.radius = 6});
  final double? width;
  final double height;
  final double radius;
  @override
  State<SkeletonBlock> createState() => _SkeletonBlockState();
}

class _SkeletonBlockState extends State<SkeletonBlock> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1300))..repeat();
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) {
        final t = _c.value;
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(-1 - 2 * t, 0),
              end: Alignment(1 - 2 * t, 0),
              colors: [
                SovereignColors.ivory.withValues(alpha: 0.06),
                SovereignColors.ivory.withValues(alpha: 0.16),
                SovereignColors.ivory.withValues(alpha: 0.06),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// A glass card filled with skeleton lines — drop-in for a loading list row.
class SkeletonCard extends StatelessWidget {
  const SkeletonCard({super.key, this.lines = 2});
  final int lines;
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const SkeletonBlock(width: 140, height: 14),
        const SizedBox(height: 10),
        for (var i = 0; i < lines; i++) ...[
          if (i > 0) const SizedBox(height: 8),
          SkeletonBlock(width: i.isEven ? double.infinity : 200, height: 11),
        ],
      ]),
    );
  }
}

/// N skeleton cards with spacing — a loading list.
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.count = 4});
  final int count;
  @override
  Widget build(BuildContext context) => Column(children: [
        for (var i = 0; i < count; i++) ...[ if (i > 0) const SizedBox(height: 12), const SkeletonCard() ],
      ]);
}
```
> If `GlassCard`'s required params differ, adapt `SkeletonCard` to the real `GlassCard` signature (it takes an optional `child`).

- [ ] **Step 11: Verify + commit**

Run: `flutter analyze lib/core/motion test/core/motion` (clean) + `flutter test test/core/motion/` (pass).
```bash
git add lib/core/motion test/core/motion
git commit -m "feat(mobile): motion kit — CascadeIn, PressableScale, skeleton loaders, motion tokens"
```

---

## Shared migration recipe (applies to every screen task T3–T6)

Each screen task performs the SAME transformation; the per-task notes only list what's screen-specific. Before editing a screen, **read it fully**. For each screen:

1. **Tokens:** replace inline `TextStyle(...)` with `SovereignType.*` (or `.copyWith` for one-off color/weight). Replace decorative alphas with `SovereignColors.alphaHigh/.alphaMid/.alphaLow`. Replace magic paddings with `Insets.*`; replace the hardcoded bottom padding (104/120/200) on the scroll view with `navClearance(context)`.
2. **Hierarchy:** the screen's header uses `SovereignType.display`/`title` (serif); section labels use `SovereignType.eyebrow`; body uses `body`/`secondary`. Ensure visible size contrast top→down.
3. **One gold action:** exactly one solid-gold filled element (named per task). Demote any other gold fills to outline/text.
4. **Entrance:** wrap the top-level section children in `CascadeIn(index: i, child: …)` (i increments down the column). For list bodies, wrap each item in `CascadeIn(index: i)`.
5. **Loading:** replace the body `CircularProgressIndicator` with a `SkeletonList`/content-shaped skeleton inside `AnimatedSwitcher(duration: Motion.base, child: …)` keyed by state so it cross-fades to content.
6. **Press feedback:** wrap tappable cards/rows/chips in `PressableScale` (leave nav + FAB alone).
7. **Pull-to-refresh:** wrap the scroll body in `RefreshIndicator(color: SovereignColors.gold, backgroundColor: SovereignColors.navyRaised, onRefresh: () => ref.read(controller.notifier).load())` — `load()` must return a Future (it does).
8. **Test:** add/extend the screen's widget test to assert the header renders from stubbed data, skeleton shows on loading state, and the gold action is present; keep existing assertions green (update spinner finders → `find.byType(SkeletonList)` etc.).

---

## Task 3: Home redesign (flagship — Editorial hero)

**Files:** Modify `lib/features/home/presentation/home_screen.dart`; Test `test/features/home/home_screen_test.dart`

Apply the recipe. Screen-specifics:
- [ ] **Header:** eyebrow `WAIIS · <weekday, d MMM>` (use `intl` `DateFormat('EEEE, d MMM')`); greeting in `SovereignType.display` (`'${briefing.greeting},\n$firstName'`).
- [ ] **Hero next-meeting card:** when `briefing.nextMeeting != null`, render a prominent `GlassCard` (goldGlow) with: eyebrow `NEXT · ${twgName ?? meeting}`, a **big serif time** (`SovereignType.title` showing the relative/clock time), `secondary` line (`location/Virtual · attending`), and the **gold Join pill** (the screen's ONE solid-gold action) — only when a join link exists (uses the new `video_link` from WF-A's briefing payload; guard null). When no next meeting: a calm `body` "Nothing on your calendar right now." card (no gold).
- [ ] **"THEN" section:** eyebrow `THEN`; an action-items summary row (`overdueCount`) + the existing Your-TWGs section, each a `PressableScale` quiet glass row (navy-raised, no gold fill) that pushes its destination.
- [ ] **Ask-Martin bar:** gold **outline** (not filled — the hero owns the gold), pushes `/martin` (per the Martin consolidation).
- [ ] **Entrance:** CascadeIn the eyebrow/greeting/hero/then/ask in order. **Loading:** skeleton hero + two skeleton rows. **Refresh:** RefreshIndicator → `homeControllerProvider.notifier.load()`.
- [ ] **Test:** stub a briefing with a next meeting → assert greeting text (display) + hero time + Join present; stub no-meeting → assert calm card + no Join; loading state → `SkeletonList`/skeleton present. Run `flutter test test/features/home/home_screen_test.dart` green; commit `feat(mobile): Home editorial redesign — hero meeting, type scale, motion`.

## Task 4: Meetings list + meeting detail

**Files:** Modify `lib/features/meetings/presentation/meetings_screen.dart`, `lib/features/meetings/presentation/meeting_detail_screen.dart`; Tests in `test/features/meetings/`

- [ ] **Meetings list:** apply recipe. Serif `SovereignType.title` screen header; group meetings by day with `eyebrow` day labels; render the **soonest upcoming** meeting as an emphasized card (serif time ~`title`, others `body`). RSVP chips: bump to ≥44px tall (`Insets` vertical padding). Gold action = **Join** on a card that has video; RSVP chips use gold-outline-when-selected (not multiple gold fills competing — only the imminent card's Join is the solid gold). Use `ListView.builder` if the list is long. Hero tag on each card's title block keyed by meeting id. CascadeIn per card (first load). Skeleton list on loading. RefreshIndicator.
- [ ] **Meeting detail:** keep the tabbed structure + info header from the prior rework. Token-migrate it; make the back/title header the `Hero` destination (same tag by id); CascadeIn the active tab's content; the pinned action bar's **Join** is the gold action (RSVP chips gold-outline). Replace its loading spinner with a skeleton header+card.
- [ ] **Tests:** meetings list renders header + a meeting card from stubbed repo, skeleton on loading; detail renders title + tabs + Join. Keep existing meeting tests green (update finders). Commit `feat(mobile): Meetings + detail — hero list, tokens, motion, 44px targets`.

## Task 5: Documents + Me

**Files:** Modify `lib/features/documents/presentation/documents_screen.dart`, `lib/features/profile/presentation/me_screen.dart`; Tests in `test/features/documents/`, `test/features/profile/`

- [ ] **Documents:** recipe. Serif title + `secondary` "Shared with you"; search field uses the themed `InputDecoration`; doc rows = `PressableScale` glass rows with a type-badge (inner glass), name (`body`), meta (`secondary`, alphaMid). Filter chips ≥44px. Gold action = the **✦ Summarise** affordance (WF-B wires its target; here just make it the single gold element). Skeleton list on loading; RefreshIndicator; CascadeIn per row; Hero badge → PDF viewer.
- [ ] **Me:** recipe. Serif profile header (name `display`/`title`, role·TWG `secondary` alphaMid); sectioned `eyebrow` labels for Action Items / Reminders; rows as quiet glass with `PressableScale`; toggles ≥44px. Gold action = **Add reminder**. Skeleton on loading; RefreshIndicator → `meControllerProvider.notifier.load()`.
- [ ] **Tests:** documents renders header + a doc row + skeleton-on-loading; Me renders profile header + sections. Keep existing green. Commit `feat(mobile): Documents + Me — tokens, hierarchy, motion, targets`.

## Task 6: Workspace + Login + token-sweep (chat, deals)

**Files:** Modify `lib/features/workspace/presentation/workspace_screen.dart`, `lib/features/auth/presentation/login_screen.dart` (find exact path), `lib/features/home/presentation/martin_chat_screen.dart` (tokens ONLY), `lib/features/deals/presentation/deals_screen.dart`; Tests in respective dirs

- [ ] **Workspace:** recipe (TWG name already serif → switch to `SovereignType.title`; sections to eyebrow/tokens). Gold action = the **Ask Martin** card. CascadeIn sections; skeleton on loading; RefreshIndicator → `workspaceControllerProvider(twgId).notifier.load()`. Keep the existing `navClearance` swap (currently hardcoded 120).
- [ ] **Login:** recipe. Serif welcome (`display`); CascadeIn the form fields; the **Sign in** button (gold) shows an in-button loading spinner while authenticating (replace any full-screen spinner); error renders inline with a gentle shake (`TweenAnimationBuilder` offset, `Motion.fast`). Gold action = Sign in.
- [ ] **Martin chat:** TOKENS ONLY — swap inline TextStyles to `SovereignType.*` and alphas to tokens; do NOT restructure bubbles/markdown/streaming (owned by the consolidation workflow). If a token swap risks colliding, skip the file and note it.
- [ ] **Deals:** token pass on the Phase-2 placeholder (serif title, eyebrow, body); no new gold beyond a single CTA if present.
- [ ] **Tests:** workspace renders TWG name + sections + skeleton; login renders welcome + Sign in. Keep existing green. Commit `feat(mobile): Workspace + Login + chat/deals token sweep`.

## Task 7: Performance & accessibility riders

**Files:** Modify `lib/core/glass/glass.dart`; sweep `lib/shell/app_shell.dart` + screens for Semantics; Test `test/core/glass/glass_perf_test.dart` (light)

- [ ] **Glass perf:** wrap the `BackdropFilter` in `GlassSurface` with a `RepaintBoundary` (isolates blur repaints). For `GlassSurface.inner`, render as a **tinted opaque** surface (no second `BackdropFilter`) so nested glass never stacks blurs — confirm `.inner` does not create a new BackdropFilter; if it does, change it to a solid translucent fill. Add a doc note: ≤6 live blur layers per screen.
- [ ] **Semantics:** add `Semantics(label: …, button: true)` to the nav pills (label only — `'<Destination> tab'`, no visual change), the ✦ FAB (`'Ask Martin'`), the Home ask bar, RSVP chips (`'RSVP <state>'`), and doc rows (`'<filename>'`). The pill/FAB visuals + behavior stay byte-for-byte; only Semantics wrappers added.
- [ ] **Touch targets:** audit RSVP chips, filter chips, the workspace switcher, Me toggles → min 44px height (wrap content in a `SizedBox(height: 44)` / vertical `Insets` padding).
- [ ] **Test:** a light widget test pumping the shell asserts the nav Semantics labels exist (`find.bySemanticsLabel(RegExp('tab'))`) and the FAB label exists. Run; commit `perf+a11y(mobile): RepaintBoundary glass, Semantics labels, 44px targets`.

## Task 8: Global sweep + final verification

**Files:** any stragglers; Test: full suite

- [ ] **Grep sweep — no stragglers:**
```bash
cd mobile
echo "Hardcoded nav paddings (expect 0):"; grep -rn "bottom: 104\|bottom: 120\|bottom: 200\|fromLTRB(.*, 104\|fromLTRB(.*, 120\|fromLTRB(.*, 200" lib/features lib/shell || echo "none ✓"
echo "Stray 'Georgia' (expect 0):"; grep -rn "Georgia" lib || echo "none ✓"
echo "Inline TextStyle count (should be far lower; remaining are one-off copyWith):"; grep -rn "TextStyle(" lib/features | grep -v "copyWith" | wc -l
```
Fix any hardcoded nav padding or 'Georgia' still present (migrate to `navClearance`/`SovereignType`).
- [ ] **Full verify:** `flutter analyze` (whole project, clean) + `flutter test` (full suite green).
- [ ] **Commit** any stragglers: `chore(mobile): redesign sweep — kill hardcoded nav paddings + Georgia fallbacks`.

---

## Final verification (whole plan)

- [ ] `flutter analyze` clean; `flutter test` fully green.
- [ ] Manual smoke (Chrome or device): each screen shows the serif hero + cascade entrance + skeletons on load + pull-to-refresh + press feedback; exactly one gold action per screen; nav pills + ✦ FAB visually unchanged.
- [ ] `grep -rn "Georgia" lib` → none; no `CircularProgressIndicator` left in a screen *body* (button spinners ok); no hardcoded 104/120/200 nav paddings.

## Self-review notes (coverage)

Spec §1 foundation → T1; §2 motion → T2; §3 screens → T3 (Home), T4 (Meetings+detail), T5 (Documents+Me), T6 (Workspace+Login+chat/deals); §4 perf/a11y → T7; §5 testing → per-task + T8; §6 sequencing → this plan = WF-E after WF-B + Martin merge. One-gold-action rule enforced per screen task. Nav/FAB locked (only Semantics labels added in T7). Out-of-scope items (offline, push, Deal Room content, i18n, goldens) excluded.

