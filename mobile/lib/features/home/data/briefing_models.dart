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
    this.videoLink,
    this.meetingId,
  });

  final String title;
  final String? twgName;
  final DateTime? startsAt; // local time
  final int? minutesUntil;

  /// The meeting's video/conference URL, when the briefing carries one
  /// (`video_link`). Null until the WF-A prod deploy populates it; the Home
  /// Join pill is hidden while null.
  final String? videoLink;

  /// The backend meeting id (`meeting_id`), when present — lets the Home
  /// briefing deep-link into the meeting if needed.
  final String? meetingId;

  factory BriefingMeeting.fromJson(Map<String, dynamic> j) => BriefingMeeting(
        title: (j['title'] ?? '').toString(),
        twgName: j['twg_name']?.toString(),
        startsAt: j['starts_at'] != null
            ? DateTime.tryParse(j['starts_at'].toString())?.toLocal()
            : null,
        minutesUntil: j['minutes_until'] as int?,
        videoLink: (j['video_link']?.toString().isNotEmpty ?? false)
            ? j['video_link'].toString()
            : null,
        meetingId: (j['meeting_id']?.toString().isNotEmpty ?? false)
            ? j['meeting_id'].toString()
            : null,
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
