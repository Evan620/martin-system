// lib/shell/placeholder_screen.dart
import 'package:flutter/material.dart';
import '../core/theme/sovereign_colors.dart';

class PlaceholderScreen extends StatelessWidget {
  const PlaceholderScreen(this.title, {super.key});
  final String title;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: Center(
          child: Text('$title — coming soon',
              style: const TextStyle(color: SovereignColors.ivory)),
        ),
      );
}
