// test/features/deals/deal_detail_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/deals/data/deals_models.dart';
import 'package:member_app/features/deals/data/deals_repository.dart';
import 'package:member_app/features/deals/presentation/deal_detail_screen.dart';

class _MockRepo extends Mock implements DealsRepository {}

Map<String, dynamic> _projectJson({
  String id = 'p1',
  String name = 'Bagre Solar PV',
  String status = 'SUMMIT_READY',
  bool following = false,
}) =>
    {
      'id': id,
      'name': name,
      'status': status,
      'sector': 'energy_infrastructure',
      'investment_size': '25000000.00',
      'readiness_score': 7.5,
      'afcen_score': 72,
      'strategic_alignment_score': 8,
      'location': 'Burkina Faso',
      'description': 'A 50MW grid-connected solar plant.',
      'is_following': following,
      'interest_count': following ? 1 : 0,
      'twg_id': 'twg-energy',
    };

Widget _app(DealsRepository repo, {String id = 'p1'}) => ProviderScope(
      overrides: [dealsRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(home: DealDetailScreen(projectId: id)),
    );

void main() {
  testWidgets('renders name, stage chip, scores and facts from loaded state',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects())
        .thenAnswer((_) async => [DealProject.fromJson(_projectJson())]);

    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // HeaderCard: name + sector meta + trailing stage chip.
    expect(find.text('Bagre Solar PV'), findsOneWidget);
    expect(find.text('Energy infrastructure'), findsOneWidget);
    expect(find.text('Summit-ready'), findsOneWidget);

    // Info chips: value + location (present fields only).
    expect(find.text(r'$25M'), findsOneWidget);
    expect(find.text('Burkina Faso'), findsOneWidget);

    // Score section: the big numeral leads with the AfCEN WAIIS score (/100,
    // matching the list rows' meta) under a "WAIIS score" header, with the
    // readiness (0-10 on the backend) and strategic breakdown rows below.
    expect(find.text('WAIIS score'), findsOneWidget);
    expect(find.text('72'), findsOneWidget);
    expect(find.text('/100'), findsOneWidget);
    expect(find.text('Readiness'), findsOneWidget);
    expect(find.text('7.5/10'), findsOneWidget);
    expect(find.text('Strategic alignment'), findsOneWidget);
    expect(find.text('8/10'), findsOneWidget);

    // Description card-in-card section.
    expect(find.text('A 50MW grid-connected solar plant.'), findsOneWidget);

    // Pinned action bar: Follow (the yellow action), Ask Martin, Share.
    expect(find.text('Follow'), findsOneWidget);
    expect(find.text('✦ Ask Martin'), findsOneWidget);
    expect(find.bySemanticsLabel('Share'), findsOneWidget);
  });

  testWidgets('Follow tap toggles to Following ✓ via the controller',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects())
        .thenAnswer((_) async => [DealProject.fromJson(_projectJson())]);
    when(() => repo.follow('p1')).thenAnswer((_) async =>
        DealInterestState.fromJson(
            {'project_id': 'p1', 'is_following': true, 'interest_count': 3}));

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await tester.tap(find.text('Follow'));
    await tester.pump(); // optimistic flip is immediate

    expect(find.text('Following ✓'), findsOneWidget);
    expect(find.text('Follow'), findsNothing);

    await tester.pump(const Duration(milliseconds: 50)); // reconcile settles
    verify(() => repo.follow('p1')).called(1);
  });

  testWidgets(
      'Ask Martin pushes /martin seeded with the project question, scoped to '
      "the project's TWG", (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects())
        .thenAnswer((_) async => [DealProject.fromJson(_projectJson())]);

    final router = GoRouter(
      initialLocation: '/deals/p1',
      routes: [
        GoRoute(
          path: '/deals/:id',
          builder: (_, st) =>
              DealDetailScreen(projectId: st.pathParameters['id']!),
        ),
        // Probe stand-in for the canonical full-screen /martin chat route.
        GoRoute(
          path: '/martin',
          builder: (_, st) => _ProbeChatScreen(
            seed: st.uri.queryParameters['q'],
            twg: st.uri.queryParameters['twg'],
          ),
        ),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [dealsRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await tester.tap(find.text('✦ Ask Martin'));
    await tester.pumpAndSettle();

    expect(
      find.text(
          'seed=Tell me about the project Bagre Solar PV twg=twg-energy'),
      findsOneWidget,
    );
  });

  testWidgets('Ask Martin omits ?twg= when the project has no TWG id',
      (tester) async {
    final repo = _MockRepo();
    final json = _projectJson()..remove('twg_id');
    when(() => repo.listMyProjects())
        .thenAnswer((_) async => [DealProject.fromJson(json)]);

    final router = GoRouter(
      initialLocation: '/deals/p1',
      routes: [
        GoRoute(
          path: '/deals/:id',
          builder: (_, st) =>
              DealDetailScreen(projectId: st.pathParameters['id']!),
        ),
        GoRoute(
          path: '/martin',
          builder: (_, st) => _ProbeChatScreen(
            seed: st.uri.queryParameters['q'],
            twg: st.uri.queryParameters['twg'],
          ),
        ),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [dealsRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await tester.tap(find.text('✦ Ask Martin'));
    await tester.pumpAndSettle();

    expect(
      find.text('seed=Tell me about the project Bagre Solar PV twg=null'),
      findsOneWidget,
    );
  });

  testWidgets('Share hands the text brief to the system share invoker',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects())
        .thenAnswer((_) async => [DealProject.fromJson(_projectJson())]);

    // Swap the share seam so the test observes the call instead of hitting
    // the real share_plus platform channel.
    final shared = <String>[];
    final original = shareInvoker;
    shareInvoker = (text) async => shared.add(text);
    addTearDown(() => shareInvoker = original);

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await tester.tap(find.bySemanticsLabel('Share'));
    await tester.pump();

    expect(shared, [
      r'Bagre Solar PV · Energy infrastructure · Summit-ready · $25M · '
          'WAIIS 72/100',
    ]);
  });

  testWidgets('score falls back to readiness /10 when afcen_score is absent',
      (tester) async {
    final repo = _MockRepo();
    final json = _projectJson()..['afcen_score'] = null;
    when(() => repo.listMyProjects())
        .thenAnswer((_) async => [DealProject.fromJson(json)]);

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Readiness'), findsOneWidget); // section header
    expect(find.text('7.5'), findsOneWidget);
    expect(find.text('/10'), findsOneWidget);
    expect(find.text('WAIIS score'), findsNothing);
    expect(find.text('Strategic alignment'), findsOneWidget);
    expect(find.text('8/10'), findsOneWidget);
  });
}

/// A tiny stand-in for the Martin chat route that echoes the ?q= and ?twg=
/// query params.
class _ProbeChatScreen extends StatelessWidget {
  const _ProbeChatScreen({required this.seed, required this.twg});
  final String? seed;
  final String? twg;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('seed=$seed twg=$twg')));
}
