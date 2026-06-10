// lib/core/ui/stat_tile.dart
import 'package:flutter/material.dart';
import '../motion/pressable.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Dashboard widget tile: uppercase label, big value, sub line, optional
/// embedded action (e.g. the Join pill) and emphasis ring.
class StatTile extends StatelessWidget {
  const StatTile({super.key, required this.label, required this.value, this.sub,
      this.action, this.emphasized = false, this.onTap});
  final String label;
  final String value;
  final String? sub;
  final Widget? action;
  final bool emphasized;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tile = Container(
      padding: const EdgeInsets.all(Insets.md),
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: emphasized
            ? SovereignColors.gold.withValues(alpha: 0.45)
            : SovereignColors.ivory.withValues(alpha: 0.08)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(label.toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontFamily: 'Inter', fontSize: 10, fontWeight: FontWeight.w700,
                letterSpacing: 0.6,
                color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
        const SizedBox(height: Insets.xs),
        Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontFamily: 'Inter', fontSize: 21, fontWeight: FontWeight.w700,
                color: SovereignColors.ivory, height: 1.05)),
        if (sub != null) ...[
          const SizedBox(height: 2),
          Text(sub!, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                  color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
        ],
        if (action != null) ...[const SizedBox(height: Insets.sm), action!],
      ]),
    );
    return onTap == null ? tile : PressableScale(onTap: onTap!, child: tile);
  }
}
