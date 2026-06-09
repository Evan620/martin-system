// lib/features/home/data/briefing_models.dart
//
// Home briefing models — manual fromJson (mirrors features/meetings/data).
// Maps the member-scoped `GET /martin/briefing` payload into a compact
// `Briefing` the Home screen renders: a greeting, the next upcoming meeting,
// and counts for upcoming/overdue items.

class BriefingMeeting {
  const BriefingMeeting({
    required this.title,
    required this.twgName,
    required this.startsAt,
    required this.minutesUntil,
  });

  final String title;
  final String? twgName;
  final DateTime? startsAt; // local time
  final int? minutesUntil;

  factory BriefingMeeting.fromJson(Map<String, dynamic> j) => BriefingMeeting(
        title: (j['title'] ?? '').toString(),
        twgName: j['twg_name']?.toString(),
        startsAt: j['starts_at'] != null
            ? DateTime.tryParse(j['starts_at'].toString())?.toLocal()
            : null,
        minutesUntil: j['minutes_until'] as int?,
      );
}

class Briefing {
  const Briefing({
    required this.greeting,
    required this.nextMeeting,
    required this.overdueCount,
    required this.upcomingCount,
  });

  final String greeting;
  final BriefingMeeting? nextMeeting;
  final int overdueCount;
  final int upcomingCount;

  factory Briefing.fromJson(Map<String, dynamic> j) {
    final ups = (j['upcoming_meetings'] as List?) ?? const [];
    return Briefing(
      greeting: (j['greeting'] ?? 'Hello').toString(),
      nextMeeting: ups.isNotEmpty
          ? BriefingMeeting.fromJson(ups.first as Map<String, dynamic>)
          : null,
      upcomingCount: ups.length,
      overdueCount: ((j['overdue_items'] as List?) ?? const []).length,
    );
  }
}
