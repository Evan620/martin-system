// test/features/meetings/meetings_screen_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:mocktail/mocktail.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:member_app/core/motion/skeleton.dart';
import 'package:member_app/core/ui/app_header.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/presentation/meetings_screen.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

class _MeController extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(AppUser(
      id: 'me',
      email: 'me@x.org',
      fullName: 'Me',
      role: UserRole.twgMember,
      twgs: []));
}

/// A meeting moment that always lands on *today* in local time: [offset] from
/// now, clamped to 23:59 so late-evening test runs don't roll into tomorrow.
DateTime _todayAt({Duration offset = const Duration(hours: 2)}) {
  final now = DateTime.now();
  final t = now.add(offset);
  return DateUtils.isSameDay(t, now)
      ? t
      : DateTime(now.year, now.month, now.day, 23, 59);
}

/// ISO-UTC string for [_todayAt], so the calendar shows it by default.
String _todayIso({Duration offset = const Duration(hours: 2)}) =>
    _todayAt(offset: offset).toUtc().toIso8601String();

Map<String, dynamic> _meetingJson({
  String id = 'm1',
  String title = 'Energy Sync',
  String? scheduledAt,
  int durationMinutes = 60,
  String? videoLink,
  List<Map<String, dynamic>> participants = const [],
}) =>
    {
      'id': id,
      'title': title,
      'scheduled_at': scheduledAt ?? _todayIso(),
      'duration_minutes': durationMinutes,
      'status': 'SCHEDULED',
      'meeting_type': 'virtual',
      'video_link': ?videoLink,
      'participants': participants,
    };

Widget _app(MeetingsRepository repo, {bool authed = false}) => ProviderScope(
      overrides: [
        meetingsRepositoryProvider.overrideWithValue(repo),
        if (authed) authControllerProvider.overrideWith(_MeController.new),
      ],
      child: const MaterialApp(home: MeetingsScreen()),
    );

void main() {
  setUpAll(() {
    registerFallbackValue(MeetingRsvp.going);
  });

  testWidgets('shows the compact header + a month calendar + today\'s row',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson(
              _meetingJson(videoLink: 'https://meet.example.org/abc')),
        ]);
    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // Compact AppHeader + the month calendar.
    expect(find.byType(AppHeader), findsOneWidget);
    expect(find.text('Meetings'), findsOneWidget);
    expect(find.byType(TableCalendar<Meeting>), findsOneWidget);

    // Today's section + the meeting row (today is selected by default).
    expect(find.text('Today'), findsOneWidget);
    expect(find.text('Energy Sync'), findsOneWidget);
    expect(find.text(DateFormat('HH:mm').format(_todayAt())), findsOneWidget);

    // The soonest upcoming session with video carries the one yellow Join.
    expect(find.text('Join'), findsOneWidget);
  });

  testWidgets('shows row-shaped skeletons while loading (no spinner)',
      (tester) async {
    final repo = _MockRepo();
    final completer = Completer<List<Meeting>>();
    when(() => repo.listMeetings()).thenAnswer((_) => completer.future);
    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.byType(SkeletonRow), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    completer.complete(const []);
    await tester.pump();
  });

  testWidgets('defaults to today: a meeting on another day is not listed',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson(_meetingJson(id: 'm1', title: 'Today Sync')),
          // A meeting on a clearly different day must not show in today's list.
          Meeting.fromJson(_meetingJson(
              id: 'm2',
              title: 'Other Day Sync',
              scheduledAt: '2031-06-10T14:00:00Z')),
        ]);
    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // Today is selected by default → only today's meeting is listed.
    expect(find.text('Today Sync'), findsOneWidget);
    expect(find.text('Other Day Sync'), findsNothing);
  });

  testWidgets('an in-progress meeting (today) shows with the Join pill',
      (tester) async {
    final repo = _MockRepo();
    final started = DateTime.now().subtract(const Duration(minutes: 10));
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          // Started 10 min ago, runs 60 → in progress (not past): keeps Join.
          Meeting.fromJson(_meetingJson(
              id: 'live',
              title: 'Live Now',
              scheduledAt: started.toUtc().toIso8601String(),
              videoLink: 'https://meet.example.org/live')),
        ]);
    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Live Now'), findsOneWidget);
    expect(find.text('Join'), findsOneWidget);
  });

  testWidgets(
      'long-pressing a row opens the RSVP sheet and wires the choice to the controller',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson(_meetingJson(participants: [
            {'id': 'p', 'user_id': 'me', 'rsvp_status': 'PENDING'},
          ])),
        ]);
    when(() => repo.setMyRsvp(any(), any())).thenAnswer((_) async {});

    await tester.pumpWidget(_app(repo, authed: true));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // Long-press the row → the SovereignSheet with the three RSVP options.
    await tester.longPress(find.text('Energy Sync'));
    await tester.pumpAndSettle();
    expect(find.text('Going'), findsOneWidget);
    expect(find.text('Maybe'), findsOneWidget);
    expect(find.text('No'), findsOneWidget);

    // Choosing an option persists through the existing controller path.
    await tester.tap(find.text('Going'));
    await tester.pumpAndSettle();
    verify(() => repo.setMyRsvp('m1', MeetingRsvp.going)).called(1);
  });
}
