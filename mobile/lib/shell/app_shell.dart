// lib/shell/app_shell.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/glass/glass.dart';
import '../core/theme/sovereign_colors.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});
  final StatefulNavigationShell navigationShell;

  void _select(int i) =>
      navigationShell.goBranch(i, initialLocation: i == navigationShell.currentIndex);

  // The glass nav pill's intrinsic height (SizedBox 52 + 2×8 vertical padding).
  static const double _navInner = 52 + 16;
  // The bottom padding under the pill (the _glassNav Padding bottom).
  static const double _navBottomGap = 14;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).padding.bottom;
    // Where the top edge of the nav pill sits, measured from the screen bottom.
    final navTop = _navInner + _navBottomGap + bottomInset;

    return Scaffold(
      // Let the screen content flow behind the floating nav so the glass blurs it.
      extendBody: true,
      body: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned.fill(child: navigationShell),

          // The floating glass nav bar (with a centre gap for the Home disc).
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(top: false, child: _glassNav()),
          ),

          // Raised Home centre — rendered OUTSIDE the glass so it can protrude
          // above the bar's top edge. Horizontally centred; sits raised so the
          // disc overlaps/rises above the nav.
          Positioned(
            left: 0,
            right: 0,
            // Lift the disc so roughly its lower half overlaps the bar.
            bottom: navTop - 28,
            child: Center(child: _homeCenter()),
          ),

          // Floating Martin ✦ FAB — bottom-right, floating just over the bar's
          // right end. Pushes the /martin chat route (covers the nav).
          Positioned(
            right: 18,
            bottom: navTop + 18,
            child: _martinFab(context),
          ),
        ],
      ),
    );
  }

  // Floating, pill-shaped, glassmorphic bottom nav — Sovereign navy glass + gold.
  //
  // No highlight pill: the active destination is shown by the icon itself
  // *growing* and turning gold. Tapping another tab smoothly hands the emphasis
  // over — the old icon shrinks back to ivory as the new one grows to gold.
  // The CENTRE slot is an empty spacer: the raised gold Home disc lives in the
  // AppShell Stack so it can protrude above this bar.
  Widget _glassNav() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, _navBottomGap),
      child: GlassSurface(
        borderRadius: 34,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        goldGlow: true, // faint gold halo so it reads as Sovereign, not generic
        child: SizedBox(
          height: 52,
          child: Row(
            children: [
              _item(Icons.event_rounded, 'Meetings', 0),
              _item(Icons.description_rounded, 'Documents', 1),
              // Centre spacer — the raised Home disc sits above this gap.
              const Expanded(child: SizedBox()),
              _item(Icons.handshake_outlined, 'Deals', 3),
              _item(Icons.person_rounded, 'Me', 4),
            ],
          ),
        ),
      ),
    );
  }

  Widget _item(IconData icon, String label, int i) {
    final on = navigationShell.currentIndex == i;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => _select(i),
        // A single tween drives the whole transition: as `on` flips, the icon
        // grows (24→30) and crossfades ivory→gold, and the label follows. The
        // de-selected tab runs the same tween in reverse at the same time, so
        // the emphasis appears to glide smoothly from one icon to the next.
        child: TweenAnimationBuilder<double>(
          tween: Tween(end: on ? 1.0 : 0.0),
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
          builder: (context, t, _) {
            final color = Color.lerp(
              SovereignColors.ivory.withValues(alpha: 0.5),
              SovereignColors.gold,
              t,
            )!;
            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 24 + 6 * t, color: color),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: TextStyle(
                    color: color,
                    fontSize: 10.5,
                    fontWeight: FontWeight.lerp(FontWeight.w400, FontWeight.w700, t),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  // The raised Home centre — a gold gradient disc with a navy home glyph that
  // sits raised above the nav's top edge. Its gold halo blooms when Home is
  // the active branch.
  Widget _homeCenter() {
    final on = navigationShell.currentIndex == 2;
    return GestureDetector(
      key: const Key('home-center'),
      behavior: HitTestBehavior.opaque,
      onTap: () => _select(2),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFE6C766), SovereignColors.gold],
          ),
          boxShadow: [
            BoxShadow(
              color: SovereignColors.gold.withValues(alpha: on ? 0.62 : 0.40),
              blurRadius: on ? 24 : 16,
              spreadRadius: on ? 2 : 1,
            ),
          ],
        ),
        child: const Center(
          child: Icon(Icons.home_rounded, color: SovereignColors.navy, size: 26),
        ),
      ),
    );
  }

  // The floating gold ✦ Martin disc — bottom-right, above the nav. Pushes the
  // /martin chat route (covers the bar).
  Widget _martinFab(BuildContext context) {
    return GestureDetector(
      key: const Key('martin-fab'),
      behavior: HitTestBehavior.opaque,
      onTap: () => context.push('/martin'),
      child: Container(
        width: 54,
        height: 54,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFE6C766), SovereignColors.gold],
          ),
          boxShadow: [
            BoxShadow(
              color: SovereignColors.gold.withValues(alpha: 0.50),
              blurRadius: 20,
              spreadRadius: 1,
            ),
          ],
        ),
        child: const Center(
          child: Text(
            '✦',
            style: TextStyle(
              color: SovereignColors.navy,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }
}
