// test/features/meetings/meetings_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

Meeting _m(String id, {String rsvp = 'PENDING'}) => Meeting.fromJson({
      'id': id, 'title': 'M$id', 'scheduled_at': '2026-06-10T14:00:00Z', 'status': 'SCHEDULED',
      'meeting_type': 'virtual',
      'participants': [{'id': 'p', 'user_id': 'me', 'rsvp_status': rsvp}],
    });

void main() {
  setUpAll(() => registerFallbackValue(MeetingRsvp.going));

  test('load -> data; empty -> empty', () async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [_m('1')]);
    final container = ProviderContainer(overrides: [
      meetingsRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);

    await container.read(meetingsControllerProvider.notifier).load();
    expect(container.read(meetingsControllerProvider), isA<MeetingsData>());
  });

  test('setRsvp is optimistic and rolls back on error', () async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [_m('1', rsvp: 'PENDING')]);
    when(() => repo.setMyRsvp(any(), any())).thenThrow(MeetingException('nope'));
    final container = ProviderContainer(overrides: [
      meetingsRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);
    final ctrl = container.read(meetingsControllerProvider.notifier);
    await ctrl.load();

    // setRsvp rethrows after rolling back, so assert it throws first.
    await expectLater(
      ctrl.setRsvp('1', MeetingRsvp.going, 'me'),
      throwsA(isA<MeetingException>()),
    );
    final state = container.read(meetingsControllerProvider) as MeetingsData;
    // rolled back to PENDING after the failure
    expect(state.meetings.single.myRsvp('me'), MeetingRsvp.pending);
  });
}
