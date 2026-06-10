// lib/core/theme/sovereign_colors.dart
import 'package:flutter/material.dart';

/// Sovereign palette — Bright Sun on Big Stone: vivid gold accent over deep cool navy.
abstract final class SovereignColors {
  static const navy = Color(0xFF141D38);       // Big Stone — base surface
  static const navyDeep = Color(0xFF0D1426);   // deepest — gradient bottoms / recessed
  static const navyRaised = Color(0xFF1F2A4A); // elevated — glass cards
  static const gold = Color(0xFFFCDB32);       // Bright Sun — the one action / accents
  static const sunDeep = Color(0xFFE6C229);    // deeper sun — gold gradients / pressed / FAB tint
  static const ivory = Color(0xFFF6F1E7);      // primary text/light on navy
  static const danger = Color(0xFF9B3A2E);
  static const success = Color(0xFF2F6B4F);

  /// Text/opacity tokens (AA-safe for body sizes on navy).
  static const double alphaHigh = 0.87; // primary text
  static const double alphaMid = 0.70;  // secondary text (AA floor)
  static const double alphaLow = 0.45;  // decorative only — never body copy
}
