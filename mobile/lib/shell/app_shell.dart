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

          // The floating glass nav bar — Dribbble-style expanding pills.
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(top: false, child: _glassNav()),
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
  // Dribbble-style expanding pills: every destination is icon-only when
  // inactive; the active one expands into a gold pill that reveals its label.
  // Tapping another tab hands the emphasis over — the old pill collapses back to
  // an icon as the new one expands. The Martin ✦ FAB floats separately, above
  // the bar's right end (see [_martinFab]).
  Widget _glassNav() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, _navBottomGap),
      child: GlassSurface(
        borderRadius: 34,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        goldGlow: true, // faint gold halo so it reads as Sovereign, not generic
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _pillItem(Icons.event_rounded, 'Meetings', 0),
            _pillItem(Icons.description_rounded, 'Documents', 1),
            _pillItem(Icons.home_rounded, 'Home', 2),
            _pillItem(Icons.handshake_outlined, 'Deals', 3),
            _pillItem(Icons.person_rounded, 'Me', 4),
          ],
        ),
      ),
    );
  }

  // A Dribbble-style nav item: icon-only when inactive; when active it expands
  // into a gold pill that reveals its label (navy icon + text). One tween drives
  // the whole morph — the pill fill fades in, the icon recolours ivory→navy, and
  // the label slides open from zero width.
  Widget _pillItem(IconData icon, String label, int i) {
    final on = navigationShell.currentIndex == i;
    return GestureDetector(
      key: Key('nav-$i'),
      behavior: HitTestBehavior.opaque,
      onTap: () => _select(i),
      child: TweenAnimationBuilder<double>(
        tween: Tween(end: on ? 1.0 : 0.0),
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeOutCubic,
        builder: (context, t, _) {
          return Container(
            padding: EdgeInsets.symmetric(horizontal: 11 + 7 * t, vertical: 10),
            decoration: BoxDecoration(
              color: Color.lerp(Colors.transparent, SovereignColors.gold, t),
              borderRadius: BorderRadius.circular(20),
              boxShadow: t < 0.5
                  ? null
                  : [
                      BoxShadow(
                        color: SovereignColors.gold.withValues(alpha: 0.28 * t),
                        blurRadius: 12,
                        offset: const Offset(0, 3),
                      ),
                    ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  icon,
                  size: 22,
                  color: Color.lerp(
                      SovereignColors.ivory.withValues(alpha: 0.6),
                      SovereignColors.navy,
                      t),
                ),
                // Label reveals: width 0→full (ClipRect + Align widthFactor) and
                // fades transparent→navy as the pill opens.
                ClipRect(
                  child: Align(
                    alignment: Alignment.centerLeft,
                    widthFactor: t,
                    child: Padding(
                      padding: const EdgeInsets.only(left: 7),
                      child: Text(
                        label,
                        maxLines: 1,
                        softWrap: false,
                        overflow: TextOverflow.clip,
                        style: TextStyle(
                          color: Color.lerp(
                              Colors.transparent, SovereignColors.navy, t),
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
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
            colors: [SovereignColors.sunDeep, SovereignColors.gold],
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
