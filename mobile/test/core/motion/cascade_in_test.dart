import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/motion/cascade_in.dart';
import 'package:member_app/core/motion/motion.dart';

void main() {
  test('staggerDelayFor caps at maxStagger', () {
    expect(CascadeIn.staggerDelayFor(0), Duration.zero);
    expect(CascadeIn.staggerDelayFor(3), Motion.stagger * 3);
    expect(CascadeIn.staggerDelayFor(20), Motion.stagger * Motion.maxStagger);
  });

  testWidgets('CascadeIn renders its child and settles fully opaque', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: CascadeIn(index: 2, child: Text('hi')))));
    expect(find.text('hi'), findsOneWidget);
    await tester.pumpAndSettle();
    final op = tester.widget<FadeTransition>(find.ancestor(of: find.text('hi'), matching: find.byType(FadeTransition)).first);
    expect(op.opacity.value, 1.0);
  });
}
