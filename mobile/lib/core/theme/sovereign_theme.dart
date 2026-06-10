// lib/core/theme/sovereign_theme.dart
import 'package:flutter/material.dart';
import 'sovereign_colors.dart';
import 'sovereign_type.dart';

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
        displaySmall: SovereignType.display,
        displayMedium: SovereignType.title,
        headlineMedium: SovereignType.heading,
        titleLarge: SovereignType.heading,
        titleMedium: SovereignType.section,
        bodyLarge: SovereignType.body,
        bodyMedium: SovereignType.body,
        bodySmall: SovereignType.secondary,
        labelLarge: SovereignType.caption,
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
