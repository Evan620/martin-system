// Smoke test for the member app entry point.
//
// The scaffolded counter test was replaced when Task 13 wired the real app
// entry (ProviderScope + MemberApp). It boots through the router into the
// navigation shell while the session bootstrap runs.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:member_app/app.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

void main() {
  testWidgets('app boots and wires the router into the navigation shell',
      (WidgetTester tester) async {
    // The shell's IndexedStack mounts MeetingsScreen at boot; stub its repo so
    // its initState load() resolves instead of leaving a pending network timer.
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => []);

    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MemberApp(),
    ));
    await tester.pump();

    expect(find.byKey(const Key('martin-center')), findsOneWidget);
  });
}
