// test/features/meetings/meetings_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';

void main() {
  group('MeetingRsvp', () {
    test('parses api names + maps to api', () {
      expect(MeetingRsvpX.fromApi('ACCEPTED'), MeetingRsvp.going);
      expect(MeetingRsvpX.fromApi('TENTATIVE'), MeetingRsvp.maybe);
      expect(MeetingRsvpX.fromApi('DECLINED'), MeetingRsvp.no);
      expect(MeetingRsvpX.fromApi('PENDING'), MeetingRsvp.pending);
      expect(MeetingRsvp.going.toApi, 'ACCEPTED');
      expect(MeetingRsvp.maybe.toApi, 'TENTATIVE');
      expect(MeetingRsvp.no.toApi, 'DECLINED');
    });
  });

  test('Meeting.fromJson parses fields + derives myRsvp by user id', () {
    final json = {
      'id': 'm1',
      'title': 'Energy Sync',
      'scheduled_at': '2026-06-10T14:00:00Z',
      'duration_minutes': 60,
      'status': 'SCHEDULED',
      'meeting_type': 'virtual',
      'location': 'Virtual',
      'video_link': 'https://meet.example/abc',
      'twg': {'id': 't1', 'name': 'Energy TWG'},
      'participants': [
        {'id': 'p1', 'user_id': 'u1', 'rsvp_status': 'ACCEPTED'},
        {'id': 'p2', 'user_id': 'u2', 'rsvp_status': 'PENDING'},
      ],
    };
    final m = Meeting.fromJson(json);
    expect(m.id, 'm1');
    expect(m.title, 'Energy Sync');
    expect(m.twgName, 'Energy TWG');
    expect(m.videoLink, 'https://meet.example/abc');
    expect(m.scheduledAt.isUtc, isFalse); // converted to local
    expect(m.myRsvp('u1'), MeetingRsvp.going);
    expect(m.isParticipant('u1'), isTrue);
    expect(m.myRsvp('u2'), MeetingRsvp.pending);
    expect(m.isParticipant('zzz'), isFalse);
  });

  test('Meeting.fromJson parses attached documents', () {
    final m = Meeting.fromJson({
      'id': 'm1', 'title': 'T', 'scheduled_at': '2026-06-10T14:00:00Z',
      'status': 'SCHEDULED', 'meeting_type': 'virtual',
      'participants': const [],
      'documents': [
        {'id': 'd1', 'file_name': 'Policy.pdf', 'file_type': 'application/pdf', 'file_path': '/uploads/policy.pdf'},
      ],
    });
    expect(m.documents.single.name, 'Policy.pdf');
    expect(m.documents.single.id, 'd1');
  });
}
