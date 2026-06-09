# Home TWG + Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the member's TWG membership(s) on Home (a "Your TWGs" section) and give each TWG a dedicated Workspace hub (meetings · documents · your tasks · members · Ask-Martin), reusing existing models, repos, glass components, and the 4b chat.

**Architecture:** Home reads `AppUser.twgs` (already in auth state — no fetch) and renders 1 card or N. Each card pushes `/home/workspace/:twgId` (nested under the Home branch so the floating nav persists). A `WorkspaceController` family keyed by `twgId` fans out three **best-effort** reads — `GET /twgs/{id}` (name, pillar, members, documents, stats), `GET /meetings/?twg_id=` (next meeting), `GET /action-items/?twg_id=&mine_only=true` (your tasks) — so one failing endpoint never blanks the hub. Ask-Martin opens the 4b `MartinChatScreen` scoped to the workspace `twgId`.

**Tech Stack:** Flutter, flutter_riverpod (Notifier + NotifierProvider.family), dio, go_router, mocktail, intl. Package `member_app`. `export PATH="$PATH:/opt/homebrew/bin"` so `flutter` resolves; run from `mobile/`.

**Spec:** `docs/superpowers/specs/2026-06-09-home-twg-workspace-design.md`

**Conventions (verified):** `dioProvider` is in `lib/features/auth/application/auth_controller.dart`. `currentUserIdProvider` is in `lib/features/meetings/application/meetings_controller.dart`. `Twg {id, name}` and `AppUser {…, List<Twg> twgs}` are in `lib/features/auth/data/auth_models.dart`. Commit per task; never push; sequential.

---

## File Structure

- **Create** `lib/features/workspace/data/workspace_models.dart` — `TwgMember`, `TwgDetail` (parses `GET /twgs/{id}`), pillar label helper. One responsibility: the workspace data shapes.
- **Modify** `lib/features/meetings/data/meetings_repository.dart` — add optional `twgId` to `listMeetings`.
- **Modify** `lib/features/profile/data/me_repository.dart` — add optional `twgId` to `listActionItems`.
- **Create** `lib/features/workspace/data/workspace_repository.dart` — `WorkspaceRepository.twgDetail(id)` + `workspaceRepositoryProvider`.
- **Create** `lib/features/workspace/application/workspace_controller.dart` — sealed `WorkspaceState`, `WorkspaceData` bundle, `WorkspaceController` (`NotifierProvider.family` by `twgId`).
- **Create** `lib/features/workspace/presentation/workspace_screen.dart` — the hub UI (header + switcher + sections), reusing glass + the existing row patterns.
- **Modify** `lib/features/home/application/chat_controller.dart` — `send(text, {String? overrideTwgId})`.
- **Modify** `lib/features/home/presentation/martin_chat_screen.dart` — accept `twgId`, pass to `send`.
- **Modify** `lib/routing/app_router.dart` — nested `workspace/:twgId` under `/home`; `/martin` + `/home/chat` read `?twg=`.
- **Create** `lib/features/home/presentation/your_twgs_section.dart` — the "Your TWGs" Home section widget.
- **Modify** `lib/features/home/presentation/home_screen.dart` — render the section in `_DataView`.

---

## Task 1: Workspace data models

**Files:**
- Create: `lib/features/workspace/data/workspace_models.dart`
- Test: `test/features/workspace/workspace_models_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/workspace/workspace_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/workspace/data/workspace_models.dart';

void main() {
  test('TwgDetail.fromJson parses name, pillar label, members, docs', () {
    final d = TwgDetail.fromJson({
      'id': 't1',
      'name': 'Energy',
      'pillar': 'energy_infrastructure',
      'status': 'active',
      'members': [
        {'id': 'u1', 'full_name': 'Amina Diallo', 'email': 'a@x.org', 'role': 'TWG_MEMBER'},
        {'id': 'u2', 'full_name': 'Kofi Mensah', 'email': 'k@x.org', 'role': 'TWG_FACILITATOR'},
      ],
      'documents': [
        {'id': 'd1', 'file_name': 'Grid brief.pdf', 'file_type': 'application/pdf', 'is_confidential': false},
      ],
      'stats': {'meetings_held': 5, 'open_actions': 2, 'pipeline_projects': 3, 'resources_count': 12},
    });
    expect(d.id, 't1');
    expect(d.name, 'Energy');
    expect(d.pillarLabel, 'Energy & Infrastructure');
    expect(d.members.length, 2);
    expect(d.members.first.name, 'Amina Diallo');
    expect(d.documents.single.name, 'Grid brief.pdf');
    expect(d.openActions, 2);
  });

  test('TwgDetail.fromJson tolerates missing members/documents/stats', () {
    final d = TwgDetail.fromJson({'id': 't2', 'name': 'Trade', 'pillar': 'protocol_logistics'});
    expect(d.members, isEmpty);
    expect(d.documents, isEmpty);
    expect(d.openActions, 0);
    expect(d.pillarLabel, 'Protocol & Logistics');
  });

  test('unknown pillar falls back to a humanized string', () {
    final d = TwgDetail.fromJson({'id': 't3', 'name': 'X', 'pillar': 'something_new'});
    expect(d.pillarLabel, 'Something New');
  });
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `flutter test test/features/workspace/workspace_models_test.dart`
Expected: FAIL — `workspace_models.dart` does not exist (compile error).

- [ ] **Step 3: Write the implementation**

```dart
// lib/features/workspace/data/workspace_models.dart
//
// Shapes for the TWG Workspace, parsed from GET /twgs/{id} (TWGRead). The
// response already carries members, documents, and stats, so one call feeds the
// header + the documents section + the "open actions" count. Reuses the
// Documents feature's Document model for the docs array (same JSON keys).
import '../../documents/data/documents_models.dart';

/// One TWG member (from TWGRead.members -> UserSimple).
class TwgMember {
  const TwgMember({required this.id, required this.name, required this.role});
  final String id;
  final String name;
  final String role;

  factory TwgMember.fromJson(Map<String, dynamic> j) => TwgMember(
        id: j['id'].toString(),
        name: (j['full_name'] ?? '').toString(),
        role: (j['role'] ?? 'TWG_MEMBER').toString(),
      );
}

/// A TWG's detail bundle for the workspace header + docs section.
class TwgDetail {
  const TwgDetail({
    required this.id,
    required this.name,
    required this.pillarLabel,
    required this.members,
    required this.documents,
    required this.openActions,
  });

  final String id;
  final String name;
  final String pillarLabel;
  final List<TwgMember> members;
  final List<Document> documents;
  final int openActions;

  factory TwgDetail.fromJson(Map<String, dynamic> j) {
    final stats = (j['stats'] as Map?)?.cast<String, dynamic>();
    return TwgDetail(
      id: j['id'].toString(),
      name: (j['name'] ?? 'TWG').toString(),
      pillarLabel: _pillarLabel(j['pillar']?.toString()),
      members: ((j['members'] as List?) ?? const [])
          .map((e) => TwgMember.fromJson(e as Map<String, dynamic>))
          .toList(),
      documents: ((j['documents'] as List?) ?? const [])
          .map((e) => Document.fromJson(e as Map<String, dynamic>))
          .toList(),
      openActions: (stats?['open_actions'] as int?) ?? 0,
    );
  }
}

/// Maps the backend TWGPillar enum string to a member-facing label; falls back
/// to a humanized version of any unknown value.
String _pillarLabel(String? pillar) {
  switch (pillar) {
    case 'energy_infrastructure':
      return 'Energy & Infrastructure';
    case 'agriculture_food_systems':
      return 'Agriculture & Food Systems';
    case 'critical_minerals_industrialization':
      return 'Critical Minerals & Industrialization';
    case 'digital_economy_transformation':
      return 'Digital Economy & Transformation';
    case 'protocol_logistics':
      return 'Protocol & Logistics';
    case 'resource_mobilization':
      return 'Resource Mobilization';
    default:
      final raw = (pillar ?? '').replaceAll('_', ' ').trim();
      if (raw.isEmpty) return 'Working Group';
      return raw
          .split(' ')
          .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
          .join(' ');
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `flutter test test/features/workspace/workspace_models_test.dart`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/features/workspace/data/workspace_models.dart test/features/workspace/workspace_models_test.dart
git commit -m "feat(mobile): TWG workspace models (TwgDetail/TwgMember)"
```

---

## Task 2: Add `twgId` scoping to the meetings + action-items repos

**Files:**
- Modify: `lib/features/meetings/data/meetings_repository.dart` (the `listMeetings` method)
- Modify: `lib/features/profile/data/me_repository.dart` (the `listActionItems` method)
- Test: `test/features/meetings/meetings_repository_test.dart` (add a case)
- Test: `test/features/profile/me_repository_test.dart` (add a case)

- [ ] **Step 1: Write the failing tests**

Add to `test/features/meetings/meetings_repository_test.dart` inside `main()` (the file already mocks `Dio` as `dio` and builds `MeetingsRepository(dio: dio)` — match the existing setup; if the existing test uses a different mock variable name, reuse it):

```dart
  test('listMeetings(twgId:) passes ?twg_id=', () async {
    when(() => dio.get('/meetings/', queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async => Response(
              data: <dynamic>[],
              statusCode: 200,
              requestOptions: RequestOptions(path: '/meetings/'),
            ));
    await repo.listMeetings(twgId: 't1');
    verify(() => dio.get('/meetings/', queryParameters: {'twg_id': 't1'})).called(1);
  });
```

Add to `test/features/profile/me_repository_test.dart` inside `main()`:

```dart
  test('listActionItems(twgId:) adds twg_id alongside mine_only', () async {
    when(() => dio.get('/action-items/', queryParameters: any(named: 'queryParameters')))
        .thenAnswer((_) async => resp<List<dynamic>>([]));
    await repo.listActionItems(twgId: 't1');
    verify(() => dio.get('/action-items/', queryParameters: {'mine_only': true, 'twg_id': 't1'})).called(1);
  });
```

- [ ] **Step 2: Run them to verify they fail**

Run: `flutter test test/features/meetings/meetings_repository_test.dart test/features/profile/me_repository_test.dart`
Expected: FAIL — `listMeetings`/`listActionItems` don't accept a `twgId` argument (compile error).

- [ ] **Step 3: Edit `meetings_repository.dart`**

Replace the existing `listMeetings()` method body with:

```dart
  Future<List<Meeting>> listMeetings({String? twgId}) async {
    try {
      final res = await _dio.get(
        '/meetings/',
        queryParameters: twgId == null ? null : {'twg_id': twgId},
      );
      final data = (res.data as List).cast<Map<String, dynamic>>();
      return data.map(Meeting.fromJson).toList();
    } on DioException {
      throw MeetingException('Could not load meetings. Check your connection and try again.');
    }
  }
```

- [ ] **Step 4: Edit `me_repository.dart`**

Replace the existing `listActionItems()` method body with:

```dart
  Future<List<ActionItem>> listActionItems({String? twgId}) async {
    try {
      final res = await _dio.get('/action-items/', queryParameters: {
        'mine_only': true,
        if (twgId != null) 'twg_id': twgId,
      });
      return (res.data as List).cast<Map<String, dynamic>>().map(ActionItem.fromJson).toList();
    } on DioException {
      throw MeException('Could not load your tasks.');
    }
  }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `flutter test test/features/meetings/meetings_repository_test.dart test/features/profile/me_repository_test.dart`
Expected: PASS (existing cases still green — `listMeetings()`/`listActionItems()` with no arg send `null`/`{'mine_only': true}` exactly as before).

- [ ] **Step 6: Commit**

```bash
git add lib/features/meetings/data/meetings_repository.dart lib/features/profile/data/me_repository.dart test/features/meetings/meetings_repository_test.dart test/features/profile/me_repository_test.dart
git commit -m "feat(mobile): optional twgId scoping on listMeetings + listActionItems"
```

---

## Task 3: WorkspaceRepository

**Files:**
- Create: `lib/features/workspace/data/workspace_repository.dart`
- Test: `test/features/workspace/workspace_repository_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/workspace/workspace_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/workspace/data/workspace_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio;
  late WorkspaceRepository repo;
  setUp(() {
    dio = _MockDio();
    repo = WorkspaceRepository(dio: dio);
  });
  Response<T> resp<T>(T data) =>
      Response<T>(data: data, statusCode: 200, requestOptions: RequestOptions(path: '/'));

  test('twgDetail GETs /twgs/{id} and parses', () async {
    when(() => dio.get('/twgs/t1')).thenAnswer((_) async => resp<Map<String, dynamic>>({
          'id': 't1',
          'name': 'Energy',
          'pillar': 'energy_infrastructure',
          'members': [
            {'id': 'u1', 'full_name': 'Amina', 'email': 'a@x.org', 'role': 'TWG_MEMBER'}
          ],
          'documents': [],
          'stats': {'open_actions': 1},
        }));
    final d = await repo.twgDetail('t1');
    expect(d.name, 'Energy');
    expect(d.members.single.name, 'Amina');
    expect(d.openActions, 1);
  });

  test('twgDetail wraps DioException in WorkspaceException', () async {
    when(() => dio.get('/twgs/bad')).thenThrow(
      DioException(requestOptions: RequestOptions(path: '/twgs/bad')),
    );
    expect(() => repo.twgDetail('bad'), throwsA(isA<WorkspaceException>()));
  });
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `flutter test test/features/workspace/workspace_repository_test.dart`
Expected: FAIL — `workspace_repository.dart` does not exist.

- [ ] **Step 3: Write the implementation**

```dart
// lib/features/workspace/data/workspace_repository.dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart'; // dioProvider
import 'workspace_models.dart';

class WorkspaceException implements Exception {
  WorkspaceException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Reads a single TWG's detail (name, pillar, members, documents, stats).
/// Scoped meetings + tasks are fetched by the controller via the existing
/// MeetingsRepository / MeRepository with a twgId.
class WorkspaceRepository {
  WorkspaceRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<TwgDetail> twgDetail(String twgId) async {
    try {
      final res = await _dio.get('/twgs/$twgId');
      return TwgDetail.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw WorkspaceException('Could not open this workspace.');
    }
  }
}

final workspaceRepositoryProvider = Provider<WorkspaceRepository>(
  (ref) => WorkspaceRepository(dio: ref.watch(dioProvider)),
);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `flutter test test/features/workspace/workspace_repository_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/features/workspace/data/workspace_repository.dart test/features/workspace/workspace_repository_test.dart
git commit -m "feat(mobile): WorkspaceRepository (GET /twgs/{id})"
```

---

## Task 4: WorkspaceController (family by twgId)

**Files:**
- Create: `lib/features/workspace/application/workspace_controller.dart`
- Test: `test/features/workspace/workspace_controller_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `flutter test test/features/workspace/workspace_controller_test.dart`
Expected: FAIL — `workspace_controller.dart` does not exist.

- [ ] **Step 3: Write the implementation**

```dart
// lib/features/workspace/application/workspace_controller.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../meetings/application/meetings_controller.dart'; // meetingsRepositoryProvider
import '../../meetings/data/meetings_models.dart';
import '../../meetings/data/meetings_repository.dart';
import '../../profile/application/me_controller.dart'; // meRepositoryProvider
import '../../profile/data/me_models.dart';
import '../../profile/data/me_repository.dart';
import '../data/workspace_models.dart';
import '../data/workspace_repository.dart';

sealed class WorkspaceState {
  const WorkspaceState();
}

class WorkspaceLoading extends WorkspaceState {
  const WorkspaceLoading();
}

class WorkspaceError extends WorkspaceState {
  const WorkspaceError(this.message);
  final String message;
}

class WorkspaceData extends WorkspaceState {
  const WorkspaceData({
    required this.detail,
    required this.meetings,
    required this.tasks,
  });
  final TwgDetail detail;
  final List<Meeting> meetings; // upcoming, soonest-first
  final List<ActionItem> tasks; // the member's tasks in this TWG
}

class WorkspaceController extends FamilyNotifier<WorkspaceState, String> {
  late String _twgId;

  @override
  WorkspaceState build(String twgId) {
    _twgId = twgId;
    return const WorkspaceLoading();
  }

  Future<void> load() async {
    state = const WorkspaceLoading();
    final WorkspaceRepository ws = ref.read(workspaceRepositoryProvider);
    final MeetingsRepository meetingsRepo = ref.read(meetingsRepositoryProvider);
    final MeRepository meRepo = ref.read(meRepositoryProvider);

    // TWG detail is required — its failure is the only fatal one.
    final TwgDetail detail;
    try {
      detail = await ws.twgDetail(_twgId);
    } on WorkspaceException catch (e) {
      state = WorkspaceError(e.message);
      return;
    }

    // Meetings + tasks are best-effort: a failure shows an empty section.
    List<Meeting> meetings = const [];
    try {
      final all = await meetingsRepo.listMeetings(twgId: _twgId);
      final upcoming = all.where((m) => !m.isPast).toList()
        ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
      meetings = upcoming;
    } on MeetingException {
      meetings = const [];
    }

    List<ActionItem> tasks = const [];
    try {
      tasks = await meRepo.listActionItems(twgId: _twgId);
    } on MeException {
      tasks = const [];
    }

    state = WorkspaceData(detail: detail, meetings: meetings, tasks: tasks);
  }
}

final workspaceControllerProvider =
    NotifierProvider.family<WorkspaceController, WorkspaceState, String>(
  WorkspaceController.new,
);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `flutter test test/features/workspace/workspace_controller_test.dart`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/features/workspace/application/workspace_controller.dart test/features/workspace/workspace_controller_test.dart
git commit -m "feat(mobile): WorkspaceController (family by twgId, best-effort sections)"
```

---

## Task 5: Ask-Martin scoped to a TWG (chat plumbing)

This wires the 4b chat to accept a specific `twgId`, so the workspace's Ask-Martin (and any future caller) can scope the chat. Do this before the screen so the screen can call it.

**Files:**
- Modify: `lib/features/home/application/chat_controller.dart` (`send` signature)
- Modify: `lib/features/home/presentation/martin_chat_screen.dart` (constructor + `_send` call)
- Modify: `lib/routing/app_router.dart` (`/martin` and `/home/chat` read `?twg=`)
- Test: `test/features/home/chat_controller_test.dart` (add a case)

- [ ] **Step 1: Write the failing test**

Add to `test/features/home/chat_controller_test.dart` inside `main()` (reuse the file's existing fake client + auth setup; the fake client records the `twgId` it was called with — if the existing fake doesn't expose it, add a captured field to it):

```dart
  test('send(overrideTwgId:) uses the override instead of the first TWG', () async {
    // Arrange the existing container/fake-client setup used by other tests in
    // this file, with the authed user in TWG 'first-twg'.
    await controller.send('hi', overrideTwgId: 'other-twg');
    expect(fakeClient.lastTwgId, 'other-twg');
  });
```

- [ ] **Step 2: Run it to verify it fails**

Run: `flutter test test/features/home/chat_controller_test.dart`
Expected: FAIL — `send` has no `overrideTwgId` parameter.

- [ ] **Step 3: Edit `chat_controller.dart`**

Change the `send` signature + the `twgId` resolution. Replace the method header and the `final twgId = _twgId;` line:

```dart
  Future<void> send(String text, {String? overrideTwgId}) async {
    final message = text.trim();
    if (message.isEmpty || state.streaming) return;

    final twgId = overrideTwgId ?? _twgId;
    if (twgId == null) {
      state = state.copyWith(
        error: "You're not assigned to a TWG yet, so Martin can't help here.",
      );
      return;
    }
    // …rest of the method unchanged…
```

- [ ] **Step 4: Edit `martin_chat_screen.dart`**

Add the `twgId` field to the constructor:

```dart
  const MartinChatScreen({super.key, this.seed, this.twgId});

  /// Optional prompt to auto-send once when the screen first appears.
  final String? seed;

  /// Optional TWG to scope this chat to (workspace Ask-Martin). When null the
  /// controller falls back to the member's first TWG.
  final String? twgId;
```

In the screen's `_send` handler (and the seed auto-send post-frame callback), pass the override — change the `chatController.send(...)` call(s) to:

```dart
ref.read(chatControllerProvider.notifier).send(text, overrideTwgId: widget.twgId);
```

- [ ] **Step 5: Edit `app_router.dart`**

Update both chat routes to read `?twg=` and forward it. Replace the `/martin` route and the nested `chat` route page builders:

```dart
// top-level /martin
GoRoute(
  path: '/martin',
  pageBuilder: (context, st) => sovereignPage(
    child: MartinChatScreen(
      seed: st.uri.queryParameters['q'],
      twgId: st.uri.queryParameters['twg'],
    ),
  ),
),
```

```dart
// nested under /home
GoRoute(
  path: 'chat',
  pageBuilder: (context, st) => sovereignPage(
    child: MartinChatScreen(
      seed: st.uri.queryParameters['q'],
      twgId: st.uri.queryParameters['twg'],
    ),
  ),
),
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `flutter test test/features/home/chat_controller_test.dart`
Expected: PASS (existing cases still green; the new override case passes).

- [ ] **Step 7: Verify analyze + commit**

Run: `flutter analyze lib/features/home lib/routing`
Expected: No issues found.

```bash
git add lib/features/home/application/chat_controller.dart lib/features/home/presentation/martin_chat_screen.dart lib/routing/app_router.dart test/features/home/chat_controller_test.dart
git commit -m "feat(mobile): Martin chat accepts an overrideTwgId (scoped Ask-Martin)"
```

---

## Task 6: Workspace screen + route

**Files:**
- Create: `lib/features/workspace/presentation/workspace_screen.dart`
- Modify: `lib/routing/app_router.dart` (nested `workspace/:twgId` under `/home`)
- Test: `test/features/workspace/workspace_screen_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/workspace/workspace_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/workspace/application/workspace_controller.dart';
import 'package:member_app/features/workspace/data/workspace_models.dart';
import 'package:member_app/features/workspace/presentation/workspace_screen.dart';

class _OneTwgAuth extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(AppUser(
      id: 'u1', email: 'a@x.org', fullName: 'Amina', role: UserRole.twgMember,
      twgs: [Twg(id: 't1', name: 'Energy')]));
}

class _DataController extends WorkspaceController {
  @override
  WorkspaceState build(String twgId) => WorkspaceData(
        detail: TwgDetail(
            id: 't1', name: 'Energy', pillarLabel: 'Energy & Infrastructure',
            members: const [TwgMember(id: 'u1', name: 'Amina', role: 'TWG_MEMBER')],
            documents: const [], openActions: 0),
        meetings: const [],
        tasks: const [],
      );
  @override
  Future<void> load() async {}
}

void main() {
  testWidgets('renders the TWG name + section headers', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(_OneTwgAuth.new),
        workspaceControllerProvider.overrideWith(_DataController.new),
      ],
      child: const MaterialApp(home: WorkspaceScreen(twgId: 't1')),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Energy'), findsWidgets);
    expect(find.text('NEXT MEETING'), findsOneWidget);
    expect(find.text('DOCUMENTS'), findsOneWidget);
    expect(find.text('YOUR TASKS'), findsOneWidget);
    // Single-TWG member: no switcher.
    expect(find.byKey(const Key('workspace-switcher')), findsNothing);
  });
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `flutter test test/features/workspace/workspace_screen_test.dart`
Expected: FAIL — `workspace_screen.dart` does not exist.

- [ ] **Step 3: Write the implementation**

```dart
// lib/features/workspace/presentation/workspace_screen.dart
//
// The per-TWG Workspace hub: an ambient navy/gold backdrop, a header (back +
// TWG name + pillar chip + member count + a switcher when the member is in 2+
// TWGs), then glass-inside-glass sections — next meeting, documents, your
// tasks — and an Ask-Martin card scoped to this TWG. Best-effort: empty
// sections show a gentle empty state.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../../meetings/data/meetings_models.dart';
import '../../profile/data/me_models.dart';
import '../application/workspace_controller.dart';
import '../data/workspace_models.dart';

class WorkspaceScreen extends ConsumerStatefulWidget {
  const WorkspaceScreen({super.key, required this.twgId});
  final String twgId;

  @override
  ConsumerState<WorkspaceScreen> createState() => _WorkspaceScreenState();
}

class _WorkspaceScreenState extends ConsumerState<WorkspaceScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(workspaceControllerProvider(widget.twgId).notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(workspaceControllerProvider(widget.twgId));
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          const _Backdrop(),
          SafeArea(
            child: switch (state) {
              WorkspaceLoading() => const Center(
                  child: CircularProgressIndicator(color: SovereignColors.gold)),
              WorkspaceError(:final message) => _ErrorView(
                  message: message,
                  onRetry: () => ref
                      .read(workspaceControllerProvider(widget.twgId).notifier)
                      .load()),
              WorkspaceData() => _Body(twgId: widget.twgId, data: state),
            },
          ),
        ],
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.twgId, required this.data});
  final String twgId;
  final WorkspaceData data;

  static final _fmt = DateFormat('EEE d MMM · HH:mm');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final myTwgs = auth is AuthAuthenticated ? auth.user.twgs : const <Twg>[];
    final detail = data.detail;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row: back + (switcher when 2+ TWGs).
          Row(
            children: [
              _GlassIconButton(
                icon: Icons.arrow_back_rounded,
                onTap: () => context.canPop() ? context.pop() : context.go('/home'),
              ),
              const Spacer(),
              if (myTwgs.length > 1)
                _Switcher(current: twgId, twgs: myTwgs),
            ],
          ),
          const SizedBox(height: 12),
          Text(detail.pillarLabel.toUpperCase(),
              style: TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 10,
                  letterSpacing: 3,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(detail.name,
              style: const TextStyle(
                  color: SovereignColors.ivory,
                  fontFamily: 'Georgia',
                  fontSize: 30,
                  fontWeight: FontWeight.w500)),
          const SizedBox(height: 6),
          Text('${detail.members.length} member${detail.members.length == 1 ? '' : 's'}',
              style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.6), fontSize: 13)),
          const SizedBox(height: 18),

          // Next meeting.
          _Section(
            label: 'NEXT MEETING',
            child: data.meetings.isEmpty
                ? const _Empty('No upcoming meetings.')
                : _NextMeeting(meeting: data.meetings.first, fmt: _fmt),
          ),
          const SizedBox(height: 14),

          // Documents.
          _Section(
            label: 'DOCUMENTS',
            child: detail.documents.isEmpty
                ? const _Empty('No documents yet.')
                : Column(
                    children: [
                      for (var i = 0; i < detail.documents.length && i < 5; i++) ...[
                        if (i > 0) const SizedBox(height: 10),
                        GlassSurface.inner(
                          borderRadius: 12,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                          child: Row(children: [
                            const Icon(Icons.insert_drive_file_outlined,
                                size: 16, color: SovereignColors.gold),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(detail.documents[i].name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                      color: SovereignColors.ivory.withValues(alpha: 0.9),
                                      fontSize: 13.5)),
                            ),
                          ]),
                        ),
                      ],
                    ],
                  ),
          ),
          const SizedBox(height: 14),

          // Your tasks.
          _Section(
            label: 'YOUR TASKS',
            child: data.tasks.isEmpty
                ? const _Empty('No tasks for you here.')
                : Column(
                    children: [
                      for (var i = 0; i < data.tasks.length; i++) ...[
                        if (i > 0) const SizedBox(height: 10),
                        _TaskRow(item: data.tasks[i]),
                      ],
                    ],
                  ),
          ),
          const SizedBox(height: 14),

          // Ask Martin (scoped to this TWG).
          GlassCard(
            onTap: () => context.push('/home/chat?twg=$twgId'),
            child: Row(children: [
              const Text('✦',
                  style: TextStyle(color: SovereignColors.gold, fontSize: 18)),
              const SizedBox(width: 10),
              Expanded(
                child: Text('Ask Martin about ${detail.name}',
                    style: TextStyle(
                        color: SovereignColors.ivory.withValues(alpha: 0.9),
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600)),
              ),
              Icon(Icons.chevron_right, color: SovereignColors.gold.withValues(alpha: 0.8)),
            ]),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.label, required this.child});
  final String label;
  final Widget child;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(label,
              style: const TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 9,
                  letterSpacing: 2.4,
                  fontWeight: FontWeight.w600)),
        ),
        GlassCard(child: child),
      ],
    );
  }
}

class _NextMeeting extends StatelessWidget {
  const _NextMeeting({required this.meeting, required this.fmt});
  final Meeting meeting;
  final DateFormat fmt;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(meeting.title,
            style: const TextStyle(
                color: SovereignColors.ivory, fontSize: 15, fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Row(children: [
          const Icon(Icons.schedule, size: 14, color: SovereignColors.gold),
          const SizedBox(width: 6),
          Text(fmt.format(meeting.scheduledAt),
              style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.82), fontSize: 13)),
        ]),
      ],
    );
  }
}

class _TaskRow extends StatelessWidget {
  const _TaskRow({required this.item});
  final ActionItem item;
  @override
  Widget build(BuildContext context) {
    final done = item.isDone;
    return GlassSurface.inner(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
      child: Row(children: [
        Icon(done ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded,
            size: 18, color: SovereignColors.gold),
        const SizedBox(width: 10),
        Expanded(
          child: Text(item.description,
              style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: done ? 0.5 : 0.9),
                  fontSize: 13.5,
                  decoration: done ? TextDecoration.lineThrough : null)),
        ),
      ]),
    );
  }
}

class _Switcher extends StatelessWidget {
  const _Switcher({required this.current, required this.twgs});
  final String current;
  final List<Twg> twgs;
  @override
  Widget build(BuildContext context) {
    final currentName =
        twgs.firstWhere((t) => t.id == current, orElse: () => twgs.first).name;
    return PopupMenuButton<String>(
      key: const Key('workspace-switcher'),
      color: SovereignColors.navyRaised,
      onSelected: (id) => context.replace('/home/workspace/$id'),
      itemBuilder: (_) => [
        for (final t in twgs)
          PopupMenuItem<String>(
            value: t.id,
            child: Text(t.name,
                style: TextStyle(
                    color: t.id == current ? SovereignColors.gold : SovereignColors.ivory)),
          ),
      ],
      child: GlassSurface(
        borderRadius: 12,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ringColor: SovereignColors.gold,
        ringOpacity: 0.5,
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(currentName,
              style: const TextStyle(
                  color: SovereignColors.gold, fontSize: 13, fontWeight: FontWeight.w700)),
          const Icon(Icons.arrow_drop_down, color: SovereignColors.gold, size: 18),
        ]),
      ),
    );
  }
}

class _GlassIconButton extends StatelessWidget {
  const _GlassIconButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: GlassSurface(
        borderRadius: 14,
        padding: const EdgeInsets.all(10),
        child: Icon(icon, size: 18, color: SovereignColors.ivory),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Text(text,
        style: TextStyle(color: SovereignColors.ivory.withValues(alpha: 0.5), fontSize: 13));
  }
}

class _Backdrop extends StatelessWidget {
  const _Backdrop();
  @override
  Widget build(BuildContext context) {
    return const Positioned.fill(
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [SovereignColors.navyRaised, SovereignColors.navy, SovereignColors.navyDeep],
            stops: [0, 0.5, 1],
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: GlassCard(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.cloud_off, color: SovereignColors.gold, size: 28),
            const SizedBox(height: 12),
            Text(message,
                textAlign: TextAlign.center,
                style: TextStyle(color: SovereignColors.ivory.withValues(alpha: 0.85))),
            const SizedBox(height: 12),
            TextButton(
              onPressed: onRetry,
              child: const Text('Retry',
                  style: TextStyle(color: SovereignColors.gold, fontWeight: FontWeight.w700)),
            ),
          ]),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Run the screen test to verify it passes**

Run: `flutter test test/features/workspace/workspace_screen_test.dart`
Expected: PASS.

- [ ] **Step 5: Add the route in `app_router.dart`**

Inside the `/home` branch's `routes:` list (the same list that holds the `chat` route from 4b), add a sibling route:

```dart
GoRoute(
  path: 'workspace/:twgId',
  pageBuilder: (context, st) => sovereignPage(
    child: WorkspaceScreen(twgId: st.pathParameters['twgId']!),
  ),
),
```

Add the import at the top of `app_router.dart`:

```dart
import '../features/workspace/presentation/workspace_screen.dart';
```

- [ ] **Step 6: Verify analyze + commit**

Run: `flutter analyze lib/features/workspace lib/routing`
Expected: No issues found.

```bash
git add lib/features/workspace/presentation/workspace_screen.dart lib/routing/app_router.dart test/features/workspace/workspace_screen_test.dart
git commit -m "feat(mobile): TWG Workspace screen + /home/workspace/:twgId route"
```

---

## Task 7: Home "Your TWGs" section

**Files:**
- Create: `lib/features/home/presentation/your_twgs_section.dart`
- Modify: `lib/features/home/presentation/home_screen.dart` (insert into `_DataView`)
- Test: `test/features/home/your_twgs_section_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/home/your_twgs_section_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/presentation/your_twgs_section.dart';

class _Auth extends AuthController {
  _Auth(this._twgs);
  final List<Twg> _twgs;
  @override
  AuthState build() => AuthAuthenticated(AppUser(
      id: 'u1', email: 'a@x.org', fullName: 'Amina', role: UserRole.twgMember, twgs: _twgs));
}

Widget _harness(List<Twg> twgs, {required void Function(String) onNav}) {
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (_, __) => const Scaffold(body: YourTwgsSection())),
    GoRoute(
        path: '/home/workspace/:id',
        builder: (_, st) {
          onNav(st.pathParameters['id']!);
          return const Scaffold(body: Text('WORKSPACE'));
        }),
  ]);
  return ProviderScope(
    overrides: [authControllerProvider.overrideWith(() => _Auth(twgs))],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('single TWG -> one card, "Your TWG" label', (tester) async {
    await tester.pumpWidget(_harness(const [Twg(id: 't1', name: 'Energy')], onNav: (_) {}));
    await tester.pumpAndSettle();
    expect(find.text('YOUR TWG'), findsOneWidget);
    expect(find.text('Energy'), findsOneWidget);
  });

  testWidgets('multiple TWGs -> N cards, "Your TWGs" label, tap navigates', (tester) async {
    String? navId;
    await tester.pumpWidget(_harness(
      const [Twg(id: 't1', name: 'Energy'), Twg(id: 't2', name: 'Trade')],
      onNav: (id) => navId = id,
    ));
    await tester.pumpAndSettle();
    expect(find.text('YOUR TWGS'), findsOneWidget);
    expect(find.text('Energy'), findsOneWidget);
    expect(find.text('Trade'), findsOneWidget);
    await tester.tap(find.text('Trade'));
    await tester.pumpAndSettle();
    expect(navId, 't2');
  });

  testWidgets('no TWGs -> renders nothing', (tester) async {
    await tester.pumpWidget(_harness(const [], onNav: (_) {}));
    await tester.pumpAndSettle();
    expect(find.byType(SizedBox), findsWidgets); // the shrink
    expect(find.textContaining('YOUR TWG'), findsNothing);
  });
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `flutter test test/features/home/your_twgs_section_test.dart`
Expected: FAIL — `your_twgs_section.dart` does not exist.

- [ ] **Step 3: Write the implementation**

```dart
// lib/features/home/presentation/your_twgs_section.dart
//
// The "Your TWGs" section on Home. Reads AppUser.twgs (already in auth state —
// no fetch). One TWG -> a single card under a "Your TWG" label; 2+ -> a list
// under "Your TWGs". Each card pushes /home/workspace/<id>. Hidden entirely
// when the member is in no TWG.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';

class YourTwgsSection extends ConsumerWidget {
  const YourTwgsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final twgs = auth is AuthAuthenticated ? auth.user.twgs : const <Twg>[];
    if (twgs.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(twgs.length == 1 ? 'YOUR TWG' : 'YOUR TWGS',
              style: const TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 10,
                  letterSpacing: 2.6,
                  fontWeight: FontWeight.w600)),
        ),
        for (var i = 0; i < twgs.length; i++) ...[
          if (i > 0) const SizedBox(height: 10),
          _TwgCard(twg: twgs[i]),
        ],
      ],
    );
  }
}

class _TwgCard extends StatelessWidget {
  const _TwgCard({required this.twg});
  final Twg twg;
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      onTap: () => context.push('/home/workspace/${twg.id}'),
      borderRadius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(children: [
        Expanded(
          child: Text(twg.name,
              style: const TextStyle(
                  color: SovereignColors.ivory, fontSize: 15, fontWeight: FontWeight.w700)),
        ),
        Text('Open workspace',
            style: TextStyle(
                color: SovereignColors.gold.withValues(alpha: 0.85), fontSize: 12)),
        const SizedBox(width: 6),
        Icon(Icons.chevron_right, color: SovereignColors.gold.withValues(alpha: 0.85), size: 18),
      ]),
    );
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `flutter test test/features/home/your_twgs_section_test.dart`
Expected: PASS (3 tests).

- [ ] **Step 5: Insert the section into `home_screen.dart`**

Add the import at the top:

```dart
import 'your_twgs_section.dart';
```

In `_DataView.build()`'s `Column` children, insert the section after `_MartinBriefingCard` and before `_SuggestionChips`:

```dart
          _MartinBriefingCard(briefing: briefing),
          const SizedBox(height: 22),
          const YourTwgsSection(),
          const SizedBox(height: 22),
          _SuggestionChips(onTap: onAsk),
```

(Replace the single `const SizedBox(height: 20)` that previously sat between the briefing card and the chips with the two SizedBoxes + the section above.)

- [ ] **Step 6: Verify analyze + run the home suite + commit**

Run: `flutter analyze lib/features/home`
Expected: No issues found.

Run: `flutter test test/features/home/`
Expected: PASS (existing home_screen test still green — the section renders the member's TWGs; the existing test's authed user determines whether cards appear).

```bash
git add lib/features/home/presentation/your_twgs_section.dart lib/features/home/presentation/home_screen.dart test/features/home/your_twgs_section_test.dart
git commit -m "feat(mobile): Home Your-TWGs section -> workspace"
```

---

## Final verification

- [ ] `cd mobile && export PATH="$PATH:/opt/homebrew/bin" && flutter analyze` → No issues found.
- [ ] `flutter test` → full suite green (the new workspace + home tests plus all prior).
- [ ] Manual (Chrome/phone): Home shows a "Your TWG(s)" card; tapping opens the Workspace (name · pillar · members · next meeting · documents · your tasks · Ask-Martin); a multi-TWG member sees a list + a working header switcher; Ask-Martin opens the chat scoped to that TWG.

## Notes

- **No backend changes.** All endpoints exist with member access checks (`GET /twgs/{id}`, `GET /meetings/?twg_id=`, `GET /action-items/?twg_id=&mine_only=true`).
- **Documents** come from the `GET /twgs/{id}` response (`documents` array, parsed with the existing `Document.fromJson`) — no documents-list twg filter needed.
- **Reuse:** `Document` model, `Meeting` model, `ActionItem` model, the glass system, `dioProvider`, the 4b `MartinChatScreen`. The task rows mirror Me's `_ActionItemRow` styling (re-implemented compactly rather than extracted, since the originals are private and tied to mark-done callbacks the workspace doesn't need).
- **Switcher** uses `context.replace` so Back returns to Home rather than stacking workspaces.
```
