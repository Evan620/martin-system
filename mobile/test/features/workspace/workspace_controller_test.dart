// test/features/workspace/workspace_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/profile/data/me_models.dart';
import 'package:member_app/features/profile/data/me_repository.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/workspace/application/workspace_controller.dart';
import 'package:member_app/features/workspace/data/workspace_models.dart';
import 'package:member_app/features/workspace/data/workspace_repository.dart';

class _MockWorkspaceRepo extends Mock implements WorkspaceRepository {}
class _MockMeetingsRepo extends Mock implements MeetingsRepository {}
class _MockMeRepo extends Mock implements MeRepository {}

TwgDetail _detail() => TwgDetail(
      id: 't1', name: 'Energy', pillarLabel: 'Energy & Infrastructure',
      members: const [], documents: const [], openActions: 0,
    );

void main() {
  setUpAll(() {
    registerFallbackValue(MeetingRsvp.pending);
  });

  ProviderContainer makeContainer(_MockWorkspaceRepo ws, _MockMeetingsRepo m, _MockMeRepo me) =>
      ProviderContainer(overrides: [
        workspaceRepositoryProvider.overrideWithValue(ws),
        meetingsRepositoryProvider.overrideWithValue(m),
        meRepositoryProvider.overrideWithValue(me),
      ]);

  test('load() yields WorkspaceData with detail + meetings + tasks', () async {
    final ws = _MockWorkspaceRepo();
    final m = _MockMeetingsRepo();
    final me = _MockMeRepo();
    when(() => ws.twgDetail('t1')).thenAnswer((_) async => _detail());
    when(() => m.listMeetings(twgId: 't1')).thenAnswer((_) async => []);
    when(() => me.listActionItems(twgId: 't1')).thenAnswer((_) async => <ActionItem>[]);

    final c = makeContainer(ws, m, me);
    addTearDown(c.dispose);
    await c.read(workspaceControllerProvider('t1').notifier).load();
    final state = c.read(workspaceControllerProvider('t1'));
    expect(state, isA<WorkspaceData>());
    expect((state as WorkspaceData).detail.name, 'Energy');
  });

  test('a failing section is best-effort (meetings throw -> still WorkspaceData, empty meetings)', () async {
    final ws = _MockWorkspaceRepo();
    final m = _MockMeetingsRepo();
    final me = _MockMeRepo();
    when(() => ws.twgDetail('t1')).thenAnswer((_) async => _detail());
    when(() => m.listMeetings(twgId: 't1')).thenThrow(MeetingException('x'));
    when(() => me.listActionItems(twgId: 't1')).thenAnswer((_) async => <ActionItem>[]);

    final c = makeContainer(ws, m, me);
    addTearDown(c.dispose);
    await c.read(workspaceControllerProvider('t1').notifier).load();
    final state = c.read(workspaceControllerProvider('t1'));
    expect(state, isA<WorkspaceData>());
    expect((state as WorkspaceData).meetings, isEmpty);
  });

  test('twg detail failure -> WorkspaceError', () async {
    final ws = _MockWorkspaceRepo();
    final m = _MockMeetingsRepo();
    final me = _MockMeRepo();
    when(() => ws.twgDetail('t1')).thenThrow(WorkspaceException('nope'));
    when(() => m.listMeetings(twgId: 't1')).thenAnswer((_) async => []);
    when(() => me.listActionItems(twgId: 't1')).thenAnswer((_) async => <ActionItem>[]);

    final c = makeContainer(ws, m, me);
    addTearDown(c.dispose);
    await c.read(workspaceControllerProvider('t1').notifier).load();
    expect(c.read(workspaceControllerProvider('t1')), isA<WorkspaceError>());
  });
}
