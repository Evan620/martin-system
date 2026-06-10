import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_type.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';

void main() {
  test('SovereignType exposes the scale with the right fonts/sizes', () {
    expect(SovereignType.display.fontFamily, 'Fraunces');
    expect(SovereignType.display.fontSize, 34);
    expect(SovereignType.title.fontFamily, 'Fraunces');
    expect(SovereignType.heading.fontFamily, 'Fraunces');
    expect(SovereignType.section.fontFamily, 'Inter');
    expect(SovereignType.body.fontFamily, 'Inter');
    expect(SovereignType.body.fontSize, 14.5);
    expect(SovereignType.eyebrow.letterSpacing, 3.0);
    expect(SovereignType.eyebrow.color, SovereignColors.gold);
  });

  testWidgets('context.stext returns scale styles', (tester) async {
    late BuildContext ctx;
    await tester.pumpWidget(MaterialApp(home: Builder(builder: (c) { ctx = c; return const SizedBox(); })));
    expect(ctx.stext.display.fontSize, 34);
    expect(ctx.stext.body.fontSize, 14.5);
  });
}
