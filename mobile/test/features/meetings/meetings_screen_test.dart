// test/features/meetings/meetings_screen_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/motion/skeleton.dart';
import 'package:member_app/core/ui/app_header.dart';
import 'package:member_app/core/ui/segmented.dart';
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

Map<String, dynamic> _meetingJson({
  String id = 'm1',
  String title = 'Energy Sync',
  String scheduledAt = '2031-06-10T14:00:00Z',
  String? videoLink,
  List<Map<String, dynamic>> participants = const [],
}) =>
    {
      'id': id,
      'title': title,
      'scheduled_at': scheduledAt,
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

  testWidgets(
      'shows the compact header + a day-grouped row with the inline Join pill',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson(
              _meetingJson(videoLink: 'https://meet.example.org/abc')),
        ]);
    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // Compact AppHeader (no serif): screen title inside the kit header.
    expect(find.byType(AppHeader), findsOneWidget);
    expect(find.text('Meetings'), findsOneWidget);

    // The meeting renders as a dense row under its day group label.
    expect(find.text('Energy Sync'), findsOneWidget);
    final at = DateTime.parse('2031-06-10T14:00:00Z').toLocal();
    expect(find.text(DateFormat('EEE d MMM').format(at)), findsOneWidget);
    expect(find.text(DateFormat('HH:mm').format(at)), findsOneWidget);

    // The soonest upcoming session with video carries the one yellow Join.
    expect(find.text('Join'), findsOneWidget);
  });

  testWidgets('shows row-shaped skeletons while loading (no spinner)',
      (tester) async {
    final repo = _MockRepo();
    final completer = Completer<List<Meeting>>();
    when(() => repo.listMeetings()).thenAnswer((_) => completer.future);
    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load() → MeetingsLoading
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.byType(SkeletonRow), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    // Let the pending future complete so the test tears down cleanly.
    completer.complete(const []);
    await tester.pump();
  });

  testWidgets('segmented control filters Upcoming vs Past by scheduledAt',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson(_meetingJson(id: 'm1', title: 'Future Sync')),
          Meeting.fromJson(_meetingJson(
              id: 'm2',
              title: 'Past Review',
              scheduledAt: '2020-01-01T10:00:00Z')),
        ]);
    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // Upcoming (default): only the future session shows.
    expect(find.byType(SovereignSegmented), findsOneWidget);
    expect(find.text('Future Sync'), findsOneWidget);
    expect(find.text('Past Review'), findsNothing);

    // Past: the segments flip the filter.
    await tester.tap(find.text('Past'));
    await tester.pumpAndSettle();
    expect(find.text('Past Review'), findsOneWidget);
    expect(find.text('Future Sync'), findsNothing);
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
