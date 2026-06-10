// lib/core/theme/sovereign_spacing.dart
import 'package:flutter/widgets.dart';

/// Spacing scale — the only gap/padding values allowed in new layout code.
abstract final class Insets {
  static const xs = 4.0, sm = 8.0, md = 12.0, lg = 16.0, xl = 20.0, xxl = 24.0, huge = 32.0;
  static const gutter = 20.0;     // screen horizontal padding
  static const section = 24.0;    // gap between major sections
}

/// Bottom padding a scrollable needs to clear the floating pill nav.
/// Mirrors AppShell: nav intrinsic height (52+16) + bottom gap (14) + safe inset.
EdgeInsets navClearance(BuildContext context, {double extra = 24}) {
  final bottomInset = MediaQuery.of(context).padding.bottom;
  const navInner = 52 + 16, navBottomGap = 14;
  return EdgeInsets.only(bottom: navInner + navBottomGap + bottomInset + extra);
}
