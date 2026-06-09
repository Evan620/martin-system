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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Let the screen content flow behind the floating nav so the glass blurs it.
      extendBody: true,
      body: Stack(
        children: [
          Positioned.fill(child: navigationShell),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(top: false, child: _glassNav()),
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
  // The raised gold ✦ Martin disc stays the fixed centre.
  Widget _glassNav() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 14),
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
              _martin(),
              _item(Icons.person_rounded, 'Me', 3),
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

  // The glowing gold Martin disc — the fixed centre of the app. Its halo
  // blooms when home is active.
  Widget _martin() {
    final on = navigationShell.currentIndex == 2;
    return Expanded(
      child: GestureDetector(
        key: const Key('martin-center'),
        behavior: HitTestBehavior.opaque,
        onTap: () => _select(2),
        child: Center(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFFE6C766), SovereignColors.gold],
              ),
              boxShadow: [
                BoxShadow(
                  color: SovereignColors.gold.withValues(alpha: on ? 0.60 : 0.38),
                  blurRadius: on ? 22 : 16,
                  spreadRadius: on ? 2 : 1,
                ),
              ],
            ),
            child: const Center(
              child: Text('✦',
                  style: TextStyle(
                      color: SovereignColors.navy,
                      fontSize: 22,
                      fontWeight: FontWeight.bold)),
            ),
          ),
        ),
      ),
    );
  }
}
