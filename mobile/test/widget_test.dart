// Smoke test for the member app entry point.
//
// The scaffolded counter test was replaced when Task 13 wired the real app
// entry (ProviderScope + MemberApp). It boots through the router into the
// navigation shell while the session bootstrap runs.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:member_app/app.dart';

void main() {
  testWidgets('app boots and wires the router into the navigation shell',
      (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: MemberApp()));
    await tester.pump();

    expect(find.byKey(const Key('martin-center')), findsOneWidget);
  });
}
