// lib/shell/app_shell.dart
import 'package:flutter/material.dart';
import '../core/glass/glass.dart';
import '../core/theme/sovereign_colors.dart';
import '../features/documents/presentation/documents_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/meetings/presentation/meetings_screen.dart';
import '../features/profile/presentation/me_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  // 0 Meetings, 1 Documents, 2 Martin (home), 3 Me
  int _index = 2;

  static const _screens = [
    MeetingsScreen(),
    DocumentsScreen(),
    HomeScreen(),
    MeScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Let the screen content flow behind the floating nav so the glass blurs it.
      extendBody: true,
      body: Stack(
        children: [
          Positioned.fill(child: IndexedStack(index: _index, children: _screens)),
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
  // Rendered via the shared GlassSurface so the look stays DRY across the app.
  Widget _glassNav() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 14),
      child: GlassSurface(
        borderRadius: 34,
        height: 68,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        goldGlow: true, // faint gold halo so it reads as Sovereign, not generic
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _item(Icons.event_rounded, 'Meetings', 0),
            _item(Icons.description_rounded, 'Documents', 1),
            _martin(),
            _item(Icons.person_rounded, 'Me', 3),
          ],
        ),
      ),
    );
  }

  Widget _item(IconData icon, String label, int i) {
    final on = _index == i;
    final color = on ? SovereignColors.gold : SovereignColors.ivory.withValues(alpha: 0.55);
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => setState(() => _index = i),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 3),
          Text(label,
              style: TextStyle(
                color: color,
                fontSize: 10.5,
                fontWeight: on ? FontWeight.w600 : FontWeight.w400,
              )),
        ],
      ),
    );
  }

  // The glowing gold Martin disc — the centre of the app.
  Widget _martin() {
    final on = _index == 2;
    return GestureDetector(
      key: const Key('martin-center'),
      behavior: HitTestBehavior.opaque,
      onTap: () => setState(() => _index = 2),
      child: Container(
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
              color: SovereignColors.gold.withValues(alpha: on ? 0.55 : 0.38),
              blurRadius: 16,
              spreadRadius: 1,
            ),
          ],
        ),
        child: const Center(
          child: Text('✦',
              style: TextStyle(color: SovereignColors.navy, fontSize: 22, fontWeight: FontWeight.bold)),
        ),
      ),
    );
  }
}
