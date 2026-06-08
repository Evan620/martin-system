// lib/core/theme/sovereign_theme.dart
import 'package:flutter/material.dart';
import 'sovereign_colors.dart';

abstract final class SovereignTheme {
  static ThemeData dark() {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: SovereignColors.navy,
      colorScheme: const ColorScheme.dark(
        primary: SovereignColors.gold,
        surface: SovereignColors.navy,
        onPrimary: SovereignColors.navy,
        error: SovereignColors.danger,
      ),
      textTheme: base.textTheme.copyWith(
        // Serif display for headlines; system sans for body.
        displaySmall: const TextStyle(fontFamily: 'Georgia', color: SovereignColors.ivory),
        headlineMedium: const TextStyle(fontFamily: 'Georgia', color: SovereignColors.ivory),
        titleLarge: const TextStyle(fontFamily: 'Georgia', color: SovereignColors.ivory),
        bodyMedium: const TextStyle(color: SovereignColors.ivory),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: SovereignColors.gold,
          foregroundColor: SovereignColors.navy,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.06),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: SovereignColors.gold),
        ),
      ),
    );
  }
}
