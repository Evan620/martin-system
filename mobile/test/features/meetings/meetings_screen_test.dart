// test/features/meetings/meetings_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/presentation/meetings_screen.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

void main() {
  testWidgets('shows a meeting title from live data', (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson({
            'id': 'm1', 'title': 'Energy Sync',
            'scheduled_at': '2031-06-10T14:00:00Z', 'status': 'SCHEDULED', 'meeting_type': 'virtual',
            'participants': const [],
          }),
        ]);
    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MeetingsScreen()),
    ));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Energy Sync'), findsOneWidget);
  });
}
