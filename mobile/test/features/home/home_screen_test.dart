// test/features/home/home_screen_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/motion/skeleton.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';
import 'package:member_app/features/home/presentation/home_screen.dart';

class _MockRepo extends Mock implements HomeRepository {}

class _AuthedController extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(AppUser(
        id: 'me',
        email: 'amina@x.org',
        fullName: 'Amina Diallo',
        role: UserRole.twgMember,
        twgs: [Twg(id: 't1', name: 'Energy TWG')],
      ));
}

Briefing _briefing() => Briefing.fromJson({
      'greeting': 'Good morning',
      'upcoming_meetings': [
        {
          'title': 'TWG Energy Sync',
          'twg_name': 'Energy',
          'starts_at': '2031-06-10T14:00:00Z',
          'minutes_until': 120,
        },
      ],
      'overdue_items': [
        {'title': 'Send notes', 'days_overdue': 2},
      ],
    });

void main() {
  testWidgets('renders greeting (with first name) + next meeting title',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // Gold WAIIS eyebrow (now carries today's date: "WAIIS · <weekday, d MMM>").
    expect(find.textContaining('WAIIS'), findsOneWidget);
    // Greeting uses briefing.greeting + the member's first name.
    expect(find.textContaining('Good morning'), findsOneWidget);
    expect(find.textContaining('Amina'), findsOneWidget);
    // Martin briefing card shows the next meeting title (in a RichText span).
    expect(
      find.textContaining('TWG Energy Sync', findRichText: true),
      findsOneWidget,
    );
    // "N action items due" derived from overdueCount.
    expect(find.textContaining('1 action item'), findsOneWidget);
  });

  testWidgets('gold-outline Ask Martin bar pushes /martin', (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    final router = GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
        // Probe stand-in for the canonical full-screen /martin chat route.
        GoRoute(
          path: '/martin',
          builder: (_, st) =>
              _ProbeChatScreen(seed: st.uri.queryParameters['q']),
        ),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // Tapping the (gold-outline) Ask Martin bar opens the chat with no seed.
    await tester.tap(find.text('Ask Martin…'));
    await tester.pumpAndSettle();

    expect(find.text('seed=null'), findsOneWidget);
  });

  testWidgets('Join pill is hidden when the briefing has no video link',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // No video_link in the briefing → no Join pill on Home.
    expect(find.text('Join'), findsNothing);
  });

  testWidgets('Join pill shows when the briefing carries a video link',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => Briefing.fromJson({
          'greeting': 'Good morning',
          'upcoming_meetings': [
            {
              'title': 'TWG Energy Sync',
              'minutes_until': 30,
              'video_link': 'https://meet.example.org/abc',
              'meeting_id': 'm-42',
            },
          ],
          'overdue_items': const [],
        }));

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Join'), findsOneWidget);
  });

  testWidgets('hero card shows the big serif relative time when a meeting exists',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // 120 minutes until → "in 2h" big serif hero time.
    expect(find.text('in 2h'), findsOneWidget);
  });

  testWidgets('calm card + no Join when there is no next meeting',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => Briefing.fromJson({
          'greeting': 'Good evening',
          'upcoming_meetings': const [],
          'overdue_items': const [],
        }));

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.textContaining('Nothing on your calendar'), findsOneWidget);
    expect(find.text('Join'), findsNothing);
  });

  testWidgets('loading state shows a skeleton (not a spinner)', (tester) async {
    final repo = _MockRepo();
    // Never completes → controller stays in HomeLoading.
    final pending = Completer<Briefing>();
    when(() => repo.getBriefing()).thenAnswer((_) => pending.future);

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump(); // post-frame load() → still loading

    expect(find.byType(SkeletonList), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);

    pending.complete(_briefing()); // let the future settle
    await tester.pumpAndSettle();
  });
}

/// A tiny stand-in for the chat screen that just echoes the seed it received,
/// so the Home wiring test can assert the route + query param without pulling
/// in the chat controller / Dio.
class _ProbeChatScreen extends StatelessWidget {
  const _ProbeChatScreen({required this.seed});
  final String? seed;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('seed=$seed')));
}
