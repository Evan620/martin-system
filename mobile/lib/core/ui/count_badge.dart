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
