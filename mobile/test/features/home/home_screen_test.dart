// test/features/home/home_screen_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/motion/skeleton.dart';
import 'package:member_app/core/ui/stat_tile.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';
import 'package:member_app/features/home/presentation/home_screen.dart';

class _MockRepo extends Mock implements HomeRepository {}

class _AuthedController extends AuthController {
  _AuthedController([this._twgs = const [Twg(id: 't1', name: 'Energy TWG')]]);
  final List<Twg> _twgs;
  @override
  AuthState build() => AuthAuthenticated(AppUser(
        id: 'me',
        email: 'amina@x.org',
        fullName: 'Amina Diallo',
        role: UserRole.twgMember,
        twgs: _twgs,
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

Widget _app(HomeRepository repo, {List<Twg>? twgs}) => ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(() => _AuthedController(
            twgs ?? const [Twg(id: 't1', name: 'Energy TWG')])),
      ],
      child: const MaterialApp(home: HomeScreen()),
    );

void main() {
  testWidgets('renders compact header + briefing-derived stat tiles',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // Compact AppHeader: 'Home' title + initials avatar (Amina Diallo -> AD).
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('AD'), findsOneWidget);

    // Next-meeting tile: relative label + HH:mm value + title sub.
    expect(find.textContaining('NEXT MEETING'), findsOneWidget);
    final expectedTime = DateFormat('HH:mm')
        .format(DateTime.parse('2031-06-10T14:00:00Z').toLocal());
    expect(find.text(expectedTime), findsWidgets);

    // Tasks-due tile derives its count from overdue_items.
    expect(
      find.descendant(of: find.byType(StatTile), matching: find.text('1')),
      findsOneWidget,
    );
    expect(find.text('action items'), findsOneWidget);

    // My-TWG tile + quiet Ask-Martin tile.
    expect(find.text('Energy TWG'), findsOneWidget);
    expect(find.text('✦'), findsOneWidget);

    // Today section: the next meeting row (title appears in tile sub + row).
    expect(find.text('Today'), findsOneWidget);
    expect(find.text('TWG Energy Sync'), findsNWidgets(2));

    // Editorial remnants are gone: no eyebrow, serif greeting or ask bar.
    expect(find.textContaining('WAIIS'), findsNothing);
    expect(find.textContaining('Good morning'), findsNothing);
    expect(find.text('Ask Martin…'), findsNothing);
  });

  testWidgets('Ask Martin tile pushes /martin', (tester) async {
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

    // Tapping the quiet Ask-Martin tile opens the chat with no seed.
    await tester.tap(find.text('✦'));
    await tester.pumpAndSettle();

    expect(find.text('seed=null'), findsOneWidget);
  });

  testWidgets('Join pill is hidden when the briefing has no video link',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // No video_link in the briefing -> no Join pill on Home.
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

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Join'), findsOneWidget);
  });

  testWidgets('empty briefing shows tile 0-states, never blank',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => Briefing.fromJson({
          'greeting': 'Good evening',
          'upcoming_meetings': const [],
          'overdue_items': const [],
        }));

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // Next-meeting tile dashes out; tasks tile shows 0; Today has a calm row.
    expect(find.text('—'), findsOneWidget);
    expect(find.text('nothing scheduled'), findsOneWidget);
    expect(
      find.descendant(of: find.byType(StatTile), matching: find.text('0')),
      findsOneWidget,
    );
    expect(find.text('All clear today'), findsOneWidget);
    expect(find.text('Join'), findsNothing);
  });

  testWidgets('multiple TWGs -> Today rows per TWG, tap opens its workspace',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    String? navId;
    final router = GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(path: '/home', builder: (_, _) => const HomeScreen(), routes: [
          GoRoute(
              path: 'workspace/:twgId',
              builder: (_, st) {
                navId = st.pathParameters['twgId'];
                return const Scaffold(body: Text('WORKSPACE'));
              }),
        ]),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(() => _AuthedController(const [
              Twg(id: 't1', name: 'Energy TWG'),
              Twg(id: 't2', name: 'Trade TWG'),
            ])),
      ],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // Tile shows the first TWG; the Today group lists a row per TWG.
    expect(find.text('Energy TWG'), findsNWidgets(2)); // tile + row
    expect(find.text('Trade TWG'), findsOneWidget);

    await tester.tap(find.text('Trade TWG'));
    await tester.pumpAndSettle();
    expect(navId, 't2');
    expect(find.text('WORKSPACE'), findsOneWidget);
  });

  testWidgets('loading state shows tile/row skeletons (not a spinner)',
      (tester) async {
    final repo = _MockRepo();
    // Never completes -> controller stays in HomeLoading.
    final pending = Completer<Briefing>();
    when(() => repo.getBriefing()).thenAnswer((_) => pending.future);

    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load() -> still loading

    expect(find.byType(SkeletonTile), findsNWidgets(4));
    expect(find.byType(SkeletonRow), findsNWidgets(3));
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
