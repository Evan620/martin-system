import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/motion/pressable.dart';

void main() {
  testWidgets('PressableScale fires onTap', (tester) async {
    var tapped = false;
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Center(
      child: PressableScale(onTap: () => tapped = true, child: const Text('go')),
    ))));
    await tester.tap(find.text('go'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });
}
