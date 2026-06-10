// lib/core/ui/header_card.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Houses a screen's header content (title / context, avatar, status) in a
/// raised card surface — the consistent "header in a card" treatment applied
/// across Home, Meetings, the meeting detail, Deals and Me.
class HeaderCard extends StatelessWidget {
  const HeaderCard({super.key, required this.child, this.accent = false, this.padding});

  final Widget child;

  /// Gold-tinted border (vs the default subtle ivory hairline).
  final bool accent;

  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding ?? const EdgeInsets.all(Insets.lg),
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: accent
              ? SovereignColors.gold.withValues(alpha: 0.30)
              : SovereignColors.ivory.withValues(alpha: 0.08),
        ),
      ),
      child: child,
    );
  }
}
