// lib/core/ui/list_row.dart
import 'package:flutter/material.dart';
import '../motion/pressable.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Dense native list row: leading icon container, title + meta, trailing
/// chevron / right-meta / custom widget. Use inside [RowGroup].
class ListRow extends StatelessWidget {
  const ListRow({super.key, this.icon, this.leading, required this.title, this.meta,
      this.trailing, this.rightMeta, this.onTap});
  final IconData? icon;
  final Widget? leading; // overrides icon
  final String title;
  final String? meta;
  final Widget? trailing; // overrides chevron
  final String? rightMeta;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final row = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 56),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: Insets.md, vertical: Insets.sm),
        child: Row(children: [
          if (leading != null) leading!
          else if (icon != null)
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                  color: SovereignColors.gold.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(9)),
              child: Icon(icon, size: 17, color: SovereignColors.gold),
            ),
          if (leading != null || icon != null) const SizedBox(width: Insets.md - 2),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(title, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontFamily: 'Inter', fontSize: 14.5,
                      fontWeight: FontWeight.w600, color: SovereignColors.ivory)),
              if (meta != null) ...[
                const SizedBox(height: 2),
                Text(meta!, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                        color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid))),
              ],
            ]),
          ),
          const SizedBox(width: Insets.sm),
          if (trailing != null) trailing!
          else if (rightMeta != null)
            Text(rightMeta!, style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                color: SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid)))
          else if (onTap != null)
            Icon(Icons.chevron_right, size: 18,
                color: SovereignColors.ivory.withValues(alpha: 0.35)),
        ]),
      ),
    );
    return onTap == null ? row : PressableScale(onTap: onTap!, child: row);
  }
}

/// Groups [ListRow]s in a raised rounded container with hairline dividers.
class RowGroup extends StatelessWidget {
  const RowGroup({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: SovereignColors.ivory.withValues(alpha: 0.07)),
      ),
      child: Column(children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0)
            Divider(height: 1, thickness: 1, indent: Insets.md, endIndent: Insets.md,
                color: SovereignColors.ivory.withValues(alpha: 0.06)),
          children[i],
        ],
      ]),
    );
  }
}
