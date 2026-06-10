// test/core/theme/sovereign_colors_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';

void main() {
  test('Sovereign palette exposes navy and gold', () {
    // New palette — Bright Sun on Big Stone (names kept, values redefined in WF-E).
    expect(SovereignColors.navy, const Color(0xFF141D38));
    expect(SovereignColors.gold, const Color(0xFFFCDB32));
    expect(SovereignColors.ivory, const Color(0xFFF6F1E7));
  });
}
