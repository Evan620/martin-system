// lib/features/profile/data/notification_prefs.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Device-local notification preferences (3 bools), defaulting on/on/off.
/// Used later to choose FCM topics; there is no backend store yet.
class NotificationPrefsData {
  const NotificationPrefsData({
    this.meetingUpdates = true,
    this.newDocuments = true,
    this.announcements = false,
  });
  final bool meetingUpdates;
  final bool newDocuments;
  final bool announcements;

  NotificationPrefsData copyWith({bool? meetingUpdates, bool? newDocuments, bool? announcements}) =>
      NotificationPrefsData(
        meetingUpdates: meetingUpdates ?? this.meetingUpdates,
        newDocuments: newDocuments ?? this.newDocuments,
        announcements: announcements ?? this.announcements,
      );
}

class NotificationPrefs {
  NotificationPrefs(this._prefs);
  final SharedPreferences _prefs;

  static const _kMeetingUpdates = 'notif_meeting_updates';
  static const _kNewDocuments = 'notif_new_documents';
  static const _kAnnouncements = 'notif_announcements';

  NotificationPrefsData read() => NotificationPrefsData(
        meetingUpdates: _prefs.getBool(_kMeetingUpdates) ?? true,
        newDocuments: _prefs.getBool(_kNewDocuments) ?? true,
        announcements: _prefs.getBool(_kAnnouncements) ?? false,
      );

  Future<void> setMeetingUpdates(bool v) => _prefs.setBool(_kMeetingUpdates, v);
  Future<void> setNewDocuments(bool v) => _prefs.setBool(_kNewDocuments, v);
  Future<void> setAnnouncements(bool v) => _prefs.setBool(_kAnnouncements, v);
}

/// Override in `main()` with the resolved `SharedPreferences` instance.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (_) => throw UnimplementedError('sharedPreferencesProvider must be overridden in main()'),
);

final notificationPrefsProvider = Provider<NotificationPrefs>(
  (ref) => NotificationPrefs(ref.watch(sharedPreferencesProvider)),
);
