// test/features/workspace/workspace_switch_test.dart
//
// Regression: switching TWG re-uses the WorkspaceScreen State (same widget
// type, no key) — load() must re-run for the NEW twgId or the screen hangs on
// the skeleton forever.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/profile/data/me_models.dart';
import 'package:member_app/features/profile/data/me_repository.dart';
import 'package:member_app/features/workspace/data/workspace_models.dart';
import 'package:member_app/features/workspace/data/workspace_repository.dart';
import 'package:member_app/features/workspace/presentation/workspace_screen.dart';

class _MockWs extends Mock implements WorkspaceRepository {}
class _MockMeetings extends Mock implements MeetingsRepository {}
class _MockMe extends Mock implements MeRepository {}

TwgDetail _detail(String id, String name) => TwgDetail(
    id: id, name: name, pillarLabel: 'Pillar',
    members: const [], documents: const [], openActions: 0);

void main() {
  testWidgets('switching twgId on a live screen loads the NEW workspace',
      (tester) async {
    final ws = _MockWs();
    final meetings = _MockMeetings();
    final me = _MockMe();
    when(() => ws.twgDetail('t1')).thenAnswer((_) async => _detail('t1', 'Energy'));
    when(() => ws.twgDetail('t2')).thenAnswer((_) async => _detail('t2', 'Trade'));
    when(() => meetings.listMeetings(twgId: any(named: 'twgId')))
        .thenAnswer((_) async => []);
    when(() => me.listActionItems(twgId: any(named: 'twgId')))
        .thenAnswer((_) async => <ActionItem>[]);

    final overrides = [
      workspaceRepositoryProvider.overrideWithValue(ws),
      meetingsRepositoryProvider.overrideWithValue(meetings),
      meRepositoryProvider.overrideWithValue(me),
    ];

    Widget app(String twgId) => ProviderScope(
        overrides: overrides,
        child: MaterialApp(home: WorkspaceScreen(twgId: twgId)));

    await tester.pumpWidget(app('t1'));
    await tester.pumpAndSettle();
    expect(find.text('Energy'), findsWidgets);

    // Same widget type at the same position, no key → the State is REUSED.
    // The screen must still load + show the NEW TWG (this is the switcher's
    // context.replace path).
    await tester.pumpWidget(app('t2'));
    await tester.pumpAndSettle();
    expect(find.text('Trade'), findsWidgets);
  });
}
