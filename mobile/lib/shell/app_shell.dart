// lib/shell/app_shell.dart
import 'package:flutter/material.dart';
import '../core/theme/sovereign_colors.dart';
import 'placeholder_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  // 0 Meetings, 1 Documents, 2 Martin(center/home), 3 Me
  int _index = 2;

  static const _screens = [
    PlaceholderScreen('Meetings'),
    PlaceholderScreen('Documents'),
    PlaceholderScreen('Martin'),
    PlaceholderScreen('Me'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _screens),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: FloatingActionButton(
        key: const Key('martin-center'),
        backgroundColor: SovereignColors.gold,
        foregroundColor: SovereignColors.navy,
        onPressed: () => setState(() => _index = 2),
        child: const Text('✦', style: TextStyle(fontSize: 22)),
      ),
      bottomNavigationBar: BottomAppBar(
        color: SovereignColors.navyDeep,
        shape: const CircularNotchedRectangle(),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _tab(icon: Icons.event, label: 'Meetings', i: 0),
            _tab(icon: Icons.description, label: 'Documents', i: 1),
            const SizedBox(width: 48), // notch gap for the Martin FAB
            _tab(icon: Icons.person, label: 'Me', i: 3),
          ],
        ),
      ),
    );
  }

  Widget _tab({required IconData icon, required String label, required int i}) {
    final on = _index == i;
    final color = on ? SovereignColors.gold : SovereignColors.ivory.withValues(alpha: 0.55);
    return InkWell(
      onTap: () => setState(() => _index = i),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, color: color, size: 22),
          Text(label, style: TextStyle(color: color, fontSize: 11)),
        ]),
      ),
    );
  }
}
