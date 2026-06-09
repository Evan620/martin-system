// lib/features/meetings/data/meetings_models.dart
//
// Meetings data models — manual fromJson (mirrors features/auth/data/auth_models.dart).
// MeetingRsvp maps the member UI states (Going/Maybe/No) to the backend
// RsvpStatus enum (ACCEPTED/TENTATIVE/DECLINED, plus PENDING = no response).

enum MeetingRsvp { going, maybe, no, pending }

extension MeetingRsvpX on MeetingRsvp {
  /// Backend RsvpStatus value for this UI state.
  String get toApi => switch (this) {
        MeetingRsvp.going => 'ACCEPTED',
        MeetingRsvp.maybe => 'TENTATIVE',
        MeetingRsvp.no => 'DECLINED',
        MeetingRsvp.pending => 'PENDING',
      };

  static MeetingRsvp fromApi(String? raw) => switch (raw) {
        'ACCEPTED' => MeetingRsvp.going,
        'TENTATIVE' => MeetingRsvp.maybe,
        'DECLINED' => MeetingRsvp.no,
        _ => MeetingRsvp.pending,
      };
}

class MeetingParticipant {
  const MeetingParticipant({
    required this.id,
    required this.userId,
    required this.name,
    required this.rsvp,
  });

  final String id;
  final String? userId;
  final String? name;
  final MeetingRsvp rsvp;

  factory MeetingParticipant.fromJson(Map<String, dynamic> j) => MeetingParticipant(
        id: j['id'].toString(),
        userId: j['user_id']?.toString(),
        name: (j['name'] ?? (j['user'] as Map?)?['full_name'])?.toString(),
        rsvp: MeetingRsvpX.fromApi(j['rsvp_status'] as String?),
      );
}

class Meeting {
  const Meeting({
    required this.id,
    required this.title,
    required this.scheduledAt,
    required this.durationMinutes,
    required this.status,
    required this.meetingType,
    required this.location,
    required this.videoLink,
    required this.twgName,
    required this.participants,
  });

  final String id;
  final String title;
  final DateTime scheduledAt; // local time
  final int durationMinutes;
  final String status;
  final String meetingType;
  final String? location;
  final String? videoLink;
  final String? twgName;
  final List<MeetingParticipant> participants;

  bool get isPast => scheduledAt.isBefore(DateTime.now());
  bool get hasVideo => (videoLink ?? '').isNotEmpty;

  MeetingParticipant? _me(String userId) {
    for (final p in participants) {
      if (p.userId == userId) return p;
    }
    return null;
  }

  bool isParticipant(String userId) => _me(userId) != null;
  MeetingRsvp myRsvp(String userId) => _me(userId)?.rsvp ?? MeetingRsvp.pending;

  factory Meeting.fromJson(Map<String, dynamic> json) => Meeting(
        id: json['id'].toString(),
        title: json['title'] as String,
        scheduledAt: DateTime.parse(json['scheduled_at'] as String).toLocal(),
        durationMinutes: (json['duration_minutes'] as int?) ?? 60,
        status: (json['status'] ?? 'SCHEDULED').toString(),
        meetingType: (json['meeting_type'] ?? 'virtual').toString(),
        location: json['location']?.toString(),
        videoLink: json['video_link']?.toString(),
        twgName: (json['twg'] as Map?)?['name']?.toString(),
        participants: ((json['participants'] as List?) ?? const [])
            .map((e) => MeetingParticipant.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
