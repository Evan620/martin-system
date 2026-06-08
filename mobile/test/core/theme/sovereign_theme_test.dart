// test/core/theme/sovereign_theme_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';
import 'package:member_app/core/theme/sovereign_theme.dart';

void main() {
  test('theme uses navy scaffold and gold primary, dark brightness', () {
    final theme = SovereignTheme.dark();
    expect(theme.scaffoldBackgroundColor, SovereignColors.navy);
    expect(theme.colorScheme.primary, SovereignColors.gold);
    expect(theme.brightness, Brightness.dark);
  });
}
