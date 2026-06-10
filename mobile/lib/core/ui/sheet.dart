// lib/core/ui/sheet.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';
import '../theme/sovereign_spacing.dart';

/// Sovereign bottom sheet for quick actions (RSVP, add reminder, doc actions).
Future<T?> showSovereignSheet<T>(BuildContext context, {required Widget child}) {
  return showModalBottomSheet<T>(
    context: context,
    backgroundColor: SovereignColors.navyRaised,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (c) => SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
            left: Insets.xl, right: Insets.xl, top: Insets.md,
            bottom: Insets.xl + MediaQuery.of(c).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 36, height: 4,
              decoration: BoxDecoration(
                  color: SovereignColors.ivory.withValues(alpha: 0.25),
                  borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: Insets.lg),
          child,
        ]),
      ),
    ),
  );
}
