// lib/features/meetings/application/meetings_controller.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/application/auth_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';

sealed class MeetingsState {
  const MeetingsState();
}

class MeetingsLoading extends MeetingsState {
  const MeetingsLoading();
}

class MeetingsEmpty extends MeetingsState {
  const MeetingsEmpty();
}

class MeetingsError extends MeetingsState {
  const MeetingsError(this.message);
  final String message;
}

class MeetingsData extends MeetingsState {
  const MeetingsData(this.meetings);
  final List<Meeting> meetings;
}

final meetingsRepositoryProvider = Provider<MeetingsRepository>(
  (ref) => MeetingsRepository(dio: ref.watch(dioProvider)),
);

class MeetingsController extends Notifier<MeetingsState> {
  @override
  MeetingsState build() => const MeetingsLoading();

  MeetingsRepository get _repo => ref.read(meetingsRepositoryProvider);

  Future<void> load() async {
    state = const MeetingsLoading();
    try {
      final list = await _repo.listMeetings();
      state = list.isEmpty ? const MeetingsEmpty() : MeetingsData(list);
    } on MeetingException catch (e) {
      state = MeetingsError(e.message);
    }
  }

  /// Optimistically flip the RSVP, then persist; roll back on failure.
  Future<void> setRsvp(String meetingId, MeetingRsvp rsvp, String userId) async {
    final current = state;
    if (current is! MeetingsData) return;
    final previous = current.meetings;

    // Optimistic: rebuild the list with the new local rsvp for this meeting.
    state = MeetingsData(_withRsvp(previous, meetingId, rsvp, userId));
    try {
      await _repo.setMyRsvp(meetingId, rsvp);
    } on MeetingException {
      state = MeetingsData(previous); // rollback
      rethrow;
    }
  }

  List<Meeting> _withRsvp(List<Meeting> list, String meetingId, MeetingRsvp rsvp, String userId) {
    return [
      for (final m in list)
        if (m.id == meetingId)
          Meeting(
            id: m.id, title: m.title, scheduledAt: m.scheduledAt,
            durationMinutes: m.durationMinutes, status: m.status, meetingType: m.meetingType,
            location: m.location, videoLink: m.videoLink, twgName: m.twgName,
            participants: [
              for (final p in m.participants)
                if (p.userId == userId)
                  MeetingParticipant(id: p.id, userId: p.userId, name: p.name, rsvp: rsvp)
                else
                  p,
            ],
          )
        else
          m,
    ];
  }
}

final meetingsControllerProvider =
    NotifierProvider<MeetingsController, MeetingsState>(MeetingsController.new);

/// Convenience: the current member's user id (empty if not authed).
final currentUserIdProvider = Provider<String>((ref) {
  final s = ref.watch(authControllerProvider);
  return s is AuthAuthenticated ? s.user.id : '';
});
