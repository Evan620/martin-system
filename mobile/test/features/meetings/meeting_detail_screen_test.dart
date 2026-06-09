// test/features/meetings/meeting_detail_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/presentation/meeting_detail_screen.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

void main() {
  testWidgets('renders meeting detail title', (tester) async {
    final repo = _MockRepo();
    when(() => repo.meetingDetail('m1')).thenAnswer((_) async => Meeting.fromJson({
          'id': 'm1', 'title': 'Steering Committee',
          'scheduled_at': '2031-06-10T10:00:00Z', 'status': 'SCHEDULED', 'meeting_type': 'virtual',
          'participants': const [],
        }));
    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MeetingDetailScreen(meetingId: 'm1')),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Steering Committee'), findsOneWidget);
  });
}
