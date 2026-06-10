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
        if (onBell != null || (badgeCount ?? 0) > 0)
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
