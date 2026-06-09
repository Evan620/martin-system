// test/shell/app_shell_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/shell/app_shell.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

/// The IndexedStack mounts MeetingsScreen on boot; stub its repo so its
/// initState load() resolves immediately instead of hitting the network.
Widget _shell() {
  final repo = _MockRepo();
  when(() => repo.listMeetings()).thenAnswer((_) async => []);
  return ProviderScope(
    overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
    child: const MaterialApp(home: AppShell()),
  );
}

void main() {
  testWidgets('shell shows the three destination tabs and a center Martin button', (tester) async {
    await tester.pumpWidget(_shell());

    // The glass nav exposes the three destination labels and the gold
    // Martin disc. (The 'Meetings'/'Documents' strings also appear as titles on
    // their real screens inside the IndexedStack, so assert at-least-one.)
    expect(find.text('Meetings'), findsWidgets);
    expect(find.text('Documents'), findsWidgets);
    expect(find.text('Me'), findsOneWidget);
    expect(find.byKey(const Key('martin-center')), findsOneWidget);
  });

  testWidgets('tapping a tab swaps the visible destination', (tester) async {
    await tester.pumpWidget(_shell());

    // Opens on the Martin home, whose gold disc is keyed 'martin-center'.
    expect(find.byKey(const Key('martin-center')), findsOneWidget);

    // Switch to the Documents tab and confirm the real DocumentsScreen is shown
    // (its subtitle is unique to that screen and absent from the home/nav).
    await tester.tap(find.text('Documents').last);
    await tester.pumpAndSettle();
    expect(find.text('Shared with you'), findsOneWidget);
  });
}
