// test/shell/app_shell_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/shell/app_shell.dart';

void main() {
  testWidgets('shell shows the three destination tabs and a center Martin button', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AppShell()));
    expect(find.text('Meetings'), findsOneWidget);
    expect(find.text('Documents'), findsOneWidget);
    expect(find.text('Me'), findsOneWidget);
    expect(find.byKey(const Key('martin-center')), findsOneWidget);
  });

  testWidgets('tapping a tab swaps the visible destination', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AppShell()));
    expect(find.text('Martin'), findsWidgets); // opens on Martin
    await tester.tap(find.text('Documents'));
    await tester.pumpAndSettle();
    expect(find.text('Documents — coming soon'), findsOneWidget);
  });
}
