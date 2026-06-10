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
