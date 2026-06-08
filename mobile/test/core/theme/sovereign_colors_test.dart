// test/core/theme/sovereign_colors_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';

void main() {
  test('Sovereign palette exposes navy and gold', () {
    expect(SovereignColors.navy, const Color(0xFF0A1F44));
    expect(SovereignColors.gold, const Color(0xFFC9A227));
    expect(SovereignColors.ivory, const Color(0xFFF6F1E7));
  });
}
