// test/core/ui/components_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/ui/app_header.dart';
import 'package:member_app/core/ui/stat_tile.dart';
import 'package:member_app/core/ui/list_row.dart';
import 'package:member_app/core/ui/section_header.dart';
import 'package:member_app/core/ui/segmented.dart';
import 'package:member_app/core/ui/count_badge.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('AppHeader shows context, title, badge count and initials', (tester) async {
    await tester.pumpWidget(_wrap(const AppHeader(
      context_: 'Tue 10 Jun', title: 'Home', badgeCount: 2, initials: 'AK')));
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Tue 10 Jun'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('AK'), findsOneWidget);
  });

  testWidgets('StatTile renders label/value/sub and taps', (tester) async {
    var tapped = false;
    await tester.pumpWidget(_wrap(StatTile(
      label: 'TASKS DUE', value: '2', sub: '1 overdue', onTap: () => tapped = true)));
    expect(find.text('TASKS DUE'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    await tester.tap(find.text('2'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });

  testWidgets('ListRow renders title/meta and is >=56px tall', (tester) async {
    await tester.pumpWidget(_wrap(RowGroup(children: [
      ListRow(icon: Icons.event, title: 'TWG Energy Sync', meta: '14:00 · Virtual', onTap: () {}),
    ])));
    expect(find.text('TWG Energy Sync'), findsOneWidget);
    final size = tester.getSize(find.byType(ListRow));
    expect(size.height, greaterThanOrEqualTo(56));
  });

  testWidgets('SectionHeader shows title + See all', (tester) async {
    await tester.pumpWidget(_wrap(SectionHeader(title: 'Today', onSeeAll: () {})));
    expect(find.text('Today'), findsOneWidget);
    expect(find.textContaining('See all'), findsOneWidget);
  });

  testWidgets('SovereignSegmented switches selection', (tester) async {
    int sel = 0;
    await tester.pumpWidget(_wrap(StatefulBuilder(builder: (c, set) =>
      SovereignSegmented(options: const ['Upcoming', 'Past'], selected: sel,
        onChanged: (i) => set(() => sel = i)))));
    await tester.tap(find.text('Past'));
    await tester.pumpAndSettle();
    expect(sel, 1);
  });

  testWidgets('CountBadge shows count', (tester) async {
    await tester.pumpWidget(_wrap(const CountBadge(count: 3)));
    expect(find.text('3'), findsOneWidget);
  });
}
