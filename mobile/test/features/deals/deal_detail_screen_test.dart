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

    // Score section: big readiness numeral (backend scale is 0-10) plus the
    // AfCEN (WAIIS, 0-100) and strategic (0-10) breakdown rows.
    expect(find.text('7.5'), findsOneWidget);
    expect(find.text('/10'), findsOneWidget);
    expect(find.text('AfCEN (WAIIS)'), findsOneWidget);
    expect(find.text('72/100'), findsOneWidget);
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

  testWidgets('Ask Martin pushes /martin seeded with the project question',
      (tester) async {
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
          builder: (_, st) => _ProbeChatScreen(seed: st.uri.queryParameters['q']),
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

    expect(find.text('seed=Tell me about the project Bagre Solar PV'),
        findsOneWidget);
  });
}

/// A tiny stand-in for the Martin chat route that echoes the ?q= seed.
class _ProbeChatScreen extends StatelessWidget {
  const _ProbeChatScreen({required this.seed});
  final String? seed;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('seed=$seed')));
}
