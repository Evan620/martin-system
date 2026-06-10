import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/home/data/briefing_models.dart';

void main() {
  test('Briefing.fromJson parses greeting + next meeting + counts', () {
    final b = Briefing.fromJson({
      'greeting': 'Good morning',
      'upcoming_meetings': [
        {
          'title': 'Energy Sync',
          'twg_name': 'Energy',
          'starts_at': '2031-06-10T14:00:00Z',
          'minutes_until': 120,
        },
      ],
      'overdue_items': [
        {'title': 'Send notes', 'days_overdue': 2},
      ],
    });
    expect(b.greeting, 'Good morning');
    expect(b.nextMeeting?.title, 'Energy Sync');
    expect(b.nextMeeting?.minutesUntil, 120);
    expect(b.overdueCount, 1);
  });

  test('BriefingMeeting parses video_link + meeting_id when present', () {
    final m = BriefingMeeting.fromJson({
      'title': 'Energy Sync',
      'twg_name': 'Energy',
      'starts_at': '2031-06-10T14:00:00Z',
      'minutes_until': 30,
      'video_link': 'https://meet.example.org/abc',
      'meeting_id': 'm-42',
    });
    expect(m.videoLink, 'https://meet.example.org/abc');
    expect(m.meetingId, 'm-42');
  });

  test('BriefingMeeting leaves video_link/meeting_id null when absent', () {
    final m = BriefingMeeting.fromJson({
      'title': 'Energy Sync',
      'minutes_until': 30,
    });
    expect(m.videoLink, isNull);
    expect(m.meetingId, isNull);
  });
}
