// integration_test/app_test.dart
//
// Release-bar integration test (gap report P0-8): the end-to-end member
// journey — login -> briefing -> RSVP — driven entirely through the UI of the
// REAL app (the same ProviderScope + go_router router shipped in production),
// with only the data layer faked so the flow is deterministic and offline.
//
// What it proves:
//   1. The unauthenticated app lands on /login.
//   2. Entering creds + tapping "Sign in" authenticates and routes to Home,
//      which renders the live Martin briefing (greeting + next meeting).
//   3. Tapping the Meetings nav pill (key nav-0) shows the member's meeting.
//   4. Opening that meeting and tapping an RSVP chip persists the choice —
//      asserted by verifying the meetings repo's setMyRsvp was called with the
//      right meeting id + RSVP value.
//
// Everything is overridden at the repository boundary, so no real network,
// secure storage, or biometric platform channels are touched.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:member_app/app.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/auth_repository.dart';
import 'package:member_app/features/auth/data/token_storage.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';

// ---------------------------------------------------------------------------
// Fakes / mocks — the only things that differ from the production app.
// ---------------------------------------------------------------------------

class _FakeAuthRepository extends Mock implements AuthRepository {}

class _FakeHomeRepository extends Mock implements HomeRepository {}

class _FakeMeetingsRepository extends Mock implements MeetingsRepository {}

/// A token store that always reports "no session", so the real
/// AuthController.bootstrap() resolves to unauthenticated without ever
/// touching the flutter_secure_storage platform channel (or biometrics).
class _EmptyTokenStorage extends TokenStorage {
  _EmptyTokenStorage() : super(const FlutterSecureStorage());
  @override
  Future<AuthTokens?> read() async => null;
  @override
  Future<void> save(AuthTokens t) async {}
  @override
  Future<void> clear() async {}
}

// The signed-in member: one TWG, so the briefing greeting + "Your TWG" render,
// and a participant on the meeting so the RSVP chips show.
const _member = AppUser(
  id: 'me',
  email: 'amina@africacen.org',
  fullName: 'Amina Diallo',
  role: UserRole.twgMember,
  twgs: [Twg(id: 'twg-energy', name: 'Energy TWG')],
);

// The one upcoming meeting in the member's briefing — carries a video_link.
Briefing _briefing() => Briefing.fromJson({
      'greeting': 'Good morning',
      'upcoming_meetings': [
        {
          'title': 'Energy Sync',
          'twg_name': 'Energy TWG',
          'starts_at': '2031-06-10T14:00:00Z',
          'minutes_until': 45,
          'video_link': 'https://meet.example.org/energy',
          'meeting_id': 'm1',
        },
      ],
      'overdue_items': [
        {'id': 'a1'},
      ],
    });

// The one meeting the member can RSVP to: they are a PENDING participant, so
// the Going/Maybe/No chips render.
Meeting _meeting() => Meeting.fromJson({
      'id': 'm1',
      'title': 'Energy Sync',
      'scheduled_at': '2031-06-10T14:00:00Z',
      'status': 'SCHEDULED',
      'meeting_type': 'virtual',
      'video_link': 'https://meet.example.org/energy',
      'twg': {'name': 'Energy TWG'},
      'participants': [
        {'id': 'p-me', 'user_id': 'me', 'name': 'Amina Diallo', 'rsvp_status': 'PENDING'},
      ],
    });

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    // setMyRsvp takes a MeetingRsvp; register a fallback so any(named:) works.
    registerFallbackValue(MeetingRsvp.going);
  });

  testWidgets('release bar: login -> briefing -> RSVP', (tester) async {
    final auth = _FakeAuthRepository();
    final home = _FakeHomeRepository();
    final meetings = _FakeMeetingsRepository();

    // Auth: "logging in" yields the member; bootstrap() never reaches the repo
    // because the token store is empty, but stub logout for completeness.
    when(() => auth.login(any(), any())).thenAnswer((_) async => _member);
    when(() => auth.logout()).thenAnswer((_) async {});

    // Home: one upcoming meeting with a video link.
    when(() => home.getBriefing()).thenAnswer((_) async => _briefing());

    // Meetings: one RSVP-able meeting; record RSVP writes.
    when(() => meetings.listMeetings()).thenAnswer((_) async => [_meeting()]);
    when(() => meetings.meetingDetail('m1')).thenAnswer((_) async => _meeting());
    when(() => meetings.meetingAgenda(any())).thenAnswer((_) async => null);
    when(() => meetings.meetingMinutes(any())).thenAnswer((_) async => null);
    when(() => meetings.setMyRsvp(any(), any())).thenAnswer((_) async {});

    // The REAL app (MemberApp = MaterialApp.router with the production router),
    // with only the data boundary overridden.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(_EmptyTokenStorage()),
          authRepositoryProvider.overrideWithValue(auth),
          homeRepositoryProvider.overrideWithValue(home),
          meetingsRepositoryProvider.overrideWithValue(meetings),
        ],
        child: const MemberApp(),
      ),
    );

    // Let bootstrap() settle to unauthenticated → router redirects to /login.
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('signin')), findsOneWidget,
        reason: 'unauthenticated app should land on the login screen');

    // --- Login: enter creds + tap Sign in ---
    await tester.enterText(find.byKey(const Key('email')), 'amina@africacen.org');
    await tester.enterText(find.byKey(const Key('password')), 'secret123');
    await tester.tap(find.byKey(const Key('signin')));
    await tester.pumpAndSettle();

    verify(() => auth.login('amina@africacen.org', 'secret123')).called(1);

    // --- Home: the live Martin briefing (greeting + next meeting) ---
    expect(find.text('Good morning,\nAmina'), findsOneWidget,
        reason: 'Home should greet the signed-in member');
    // The briefing card renders the next meeting inside a RichText ("Next up —
    // Energy Sync in 45 min."), so match across spans with findRichText.
    expect(find.textContaining('Energy Sync', findRichText: true), findsWidgets,
        reason: 'briefing should surface the next meeting');

    // --- Navigate to Meetings via the nav pill (key nav-0) ---
    await tester.tap(find.byKey(const Key('nav-0')));
    await tester.pumpAndSettle();

    // The Meetings screen shows its "upcoming sessions" subtitle (unique to the
    // list view; the word "Meetings" alone also matches the active nav pill).
    expect(find.text('Your upcoming sessions'), findsOneWidget,
        reason: 'tapping nav-0 should land on the Meetings list');
    // The meetings list renders the member's meeting.
    expect(find.text('Energy Sync'), findsWidgets);

    // --- Open the meeting (tap the card body) ---
    await tester.tap(find.text('Energy Sync').first);
    await tester.pumpAndSettle();

    verify(() => meetings.meetingDetail('m1')).called(1);
    // Detail shows the pinned RSVP chips for the participant.
    expect(find.text('Going'), findsOneWidget);

    // --- Tap an RSVP chip and assert the repo was called correctly ---
    await tester.tap(find.text('Going'));
    await tester.pumpAndSettle();

    verify(() => meetings.setMyRsvp('m1', MeetingRsvp.going)).called(1);
  });
}
