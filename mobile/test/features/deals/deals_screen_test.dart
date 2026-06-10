// test/features/deals/deals_screen_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/motion/skeleton.dart';
import 'package:member_app/core/ui/app_header.dart';
import 'package:member_app/core/ui/list_row.dart';
import 'package:member_app/core/ui/stat_tile.dart';
import 'package:member_app/features/deals/data/deals_models.dart';
import 'package:member_app/features/deals/data/deals_repository.dart';
import 'package:member_app/features/deals/presentation/deals_screen.dart';

class _MockRepo extends Mock implements DealsRepository {}

Map<String, dynamic> _projectJson({
  String id = 'p1',
  String name = 'Bagre Solar PV',
  String status = 'SUMMIT_READY',
  String? sector = 'energy_infrastructure',
  Object? value = '25000000.00',
  Object? score = 72,
  bool following = false,
}) =>
    {
      'id': id,
      'name': name,
      'status': status,
      'sector': sector,
      'investment_size': value,
      'afcen_score': score,
      'is_following': following,
      'interest_count': following ? 1 : 0,
    };

Widget _app(DealsRepository repo) => ProviderScope(
      overrides: [dealsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: DealsScreen()),
    );

void main() {
  testWidgets('renders header card, the 3 stat tiles and project rows',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects()).thenAnswer((_) async => [
          DealProject.fromJson(_projectJson(following: true)),
          DealProject.fromJson(_projectJson(
              id: 'p2',
              name: 'Tema Grid Upgrade',
              status: 'INCUBATION',
              sector: null,
              value: null,
              score: null)),
        ]);

    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load()
    // Let the skeleton->content AnimatedSwitcher finish dropping the old view.
    await tester.pump(const Duration(milliseconds: 300));

    // HeaderCard + compact AppHeader with the TWG context fallback.
    expect(find.byType(AppHeader), findsOneWidget);
    expect(find.text('Deal Room'), findsOneWidget);
    expect(find.text('Your projects'), findsOneWidget);

    // 3 StatTiles derived from the loaded data: 2 projects, 1 at
    // SUMMIT_READY or beyond, 1 followed by me.
    expect(find.byType(StatTile), findsNWidgets(3));
    expect(find.text('PROJECTS'), findsOneWidget);
    expect(find.text('SUMMIT-READY'), findsOneWidget);
    expect(find.text('FOLLOWING'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('1'), findsNWidgets(2));

    // Rows render inside one RowGroup with the "sector · value · score" meta
    // (missing parts omitted on the second project).
    expect(find.byType(RowGroup), findsOneWidget);
    expect(
      find.descendant(
          of: find.byType(ListRow), matching: find.text('Bagre Solar PV')),
      findsOneWidget,
    );
    expect(find.text('Energy infrastructure · \$25M · 72/100'), findsOneWidget);
    expect(find.text('Tema Grid Upgrade'), findsOneWidget);

    // The filter chips bar offers All + only the buckets present in the data.
    expect(find.text('All'), findsOneWidget);
    expect(find.text('Pipeline'), findsNothing);
    // Present both as a filter chip and as the row's trailing stage chip.
    expect(find.text('Incubation'), findsNWidgets(2));
    expect(find.text('Summit-ready'), findsNWidgets(2));
  });

  testWidgets('stage chips filter the rows; All restores them',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects()).thenAnswer((_) async => [
          DealProject.fromJson(_projectJson()),
          DealProject.fromJson(_projectJson(
              id: 'p2', name: 'Tema Grid Upgrade', status: 'INCUBATION')),
        ]);

    await tester.pumpWidget(_app(repo));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Tap the Incubation filter chip (the first match — the chips bar sits
    // above the rows) → only the incubation project remains listed.
    await tester.tap(find.text('Incubation').first);
    await tester.pump();
    expect(find.text('Tema Grid Upgrade'), findsOneWidget);
    expect(find.text('Bagre Solar PV'), findsNothing);

    // Back to All → both rows return.
    await tester.tap(find.text('All'));
    await tester.pump();
    expect(find.text('Tema Grid Upgrade'), findsOneWidget);
    expect(find.text('Bagre Solar PV'), findsOneWidget);
  });

  testWidgets('loading shows tile + row skeletons, not a spinner',
      (tester) async {
    final repo = _MockRepo();
    final pending = Completer<List<DealProject>>();
    when(() => repo.listMyProjects()).thenAnswer((_) => pending.future);

    await tester.pumpWidget(_app(repo));
    await tester.pump(); // post-frame load() -> still loading

    expect(find.byType(SkeletonTile), findsNWidgets(3));
    expect(find.byType(SkeletonRow), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);

    pending.complete(const []); // settle into the empty state
    await tester.pumpAndSettle();
    expect(find.text('No projects yet'), findsOneWidget);
  });

  testWidgets('tapping a project row pushes /deals/:id', (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMyProjects()).thenAnswer((_) async => [
          DealProject.fromJson(_projectJson()),
        ]);

    final router = GoRouter(
      initialLocation: '/deals',
      routes: [
        GoRoute(
          path: '/deals',
          builder: (_, _) => const DealsScreen(),
          routes: [
            // Probe stand-in for the /deals/:id detail route.
            GoRoute(
              path: ':id',
              builder: (_, st) =>
                  _ProbeDetailScreen(id: st.pathParameters['id']),
            ),
          ],
        ),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [dealsRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.text('Bagre Solar PV'));
    await tester.pumpAndSettle();

    expect(find.text('detail=p1'), findsOneWidget);
  });
}

/// A tiny stand-in for the deal detail route that echoes the path id.
class _ProbeDetailScreen extends StatelessWidget {
  const _ProbeDetailScreen({required this.id});
  final String? id;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('detail=$id')));
}
