# Meeting Detail Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. *(Executed via a dynamic Workflow at the user's request; same task order + gates.)*

**Goal:** Finish the meeting detail screen (dense-data Layout B), keep the floating nav persistent on it, and give the app a Sovereign page transition — Flutter-only, reusing existing backend reads.

**Architecture:** Refactor routing to `StatefulShellRoute.indexedStack` (the floating grow-gold nav becomes the shell that wraps four branch navigators, so a meeting-detail route pushed inside the Meetings branch keeps the nav). A shared `sovereignPage()` `CustomTransitionPage` replaces the default slide. The detail body becomes a `CustomScrollView` with a collapsing header, expandable sections (Agenda/Attendees/Documents/Minutes) and a pinned Join+RSVP bar.

**Tech Stack:** Flutter, flutter_riverpod, go_router (StatefulShellRoute), dio, intl, url_launcher, mocktail.

**Spec:** `docs/superpowers/specs/2026-06-09-meeting-detail-polish-design.md`

**Environment:** Flutter from `mobile/` (`export PATH="$PATH:/opt/homebrew/bin"`). Tests `flutter test <path>`, analyze `flutter analyze <path>`. Package `member_app`. Commit per task; never `git push`.

**Verified current state:**
- `lib/shell/app_shell.dart` — StatefulWidget owning `int _index=2`, an `IndexedStack` of 4 const screens, and the floating glass nav with the grow-gold `_item` (icon 24→30, ivory→gold, `FontWeight.lerp`), the `_martin()` ✦ centre (`Key('martin-center')`), `_glassNav()`. **Must preserve these visuals.**
- `lib/routing/app_router.dart` — flat GoRouter: `/`→AppShell, `/login`, `/meetings/:id`→MeetingDetailScreen (plain builder). `redirectFor(state, location)` sends authed users at `/login`→`/`.
- `lib/features/meetings/data/meetings_models.dart` — `Meeting.fromJson` parses participants, NOT documents/agenda/minutes. `MeetingRead` (backend) includes `documents[]` but NOT agenda/minutes (those are separate `GET /meetings/{id}/agenda` and `/minutes`, which 404 when absent).
- `lib/features/meetings/data/meetings_repository.dart` — `listMeetings()`, `meetingDetail(id)`, `setMyRsvp(...)`.
- `lib/features/meetings/presentation/meeting_detail_screen.dart` — current detail with `_JoinPill`, `_RsvpChip`, `_AttendeeRow`, `_RsvpBadge`, `_SectionLabel`, `_BackButton`, `_IconRow`, `_DetailError` (reuse these).
- `test/shell/app_shell_test.dart` + `test/widget_test.dart` were patched to wrap AppShell in `ProviderScope` + stub `meetingsRepositoryProvider`. They will be rewritten here for the shell-route shape.

---

## Task 1: Sovereign page transition

**Files:**
- Create: `mobile/lib/routing/sovereign_page.dart`
- Test: `mobile/test/routing/sovereign_page_test.dart`

- [ ] **Step 1: Write the failing test**
```dart
// test/routing/sovereign_page_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:member_app/routing/sovereign_page.dart';

void main() {
  test('sovereignPage returns a CustomTransitionPage with the child + 280ms', () {
    const child = Text('x');
    final page = sovereignPage<void>(child: child);
    expect(page, isA<CustomTransitionPage<void>>());
    expect(page.child, same(child));
    expect(page.transitionDuration, const Duration(milliseconds: 280));
  });
}
```
- [ ] **Step 2: Run it — FAIL** (`cd mobile && flutter test test/routing/sovereign_page_test.dart`) — file not found.
- [ ] **Step 3: Implement**
```dart
// lib/routing/sovereign_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Sovereign page transition: a gentle fade + slight upward rise.
CustomTransitionPage<T> sovereignPage<T>({required Widget child, LocalKey? key}) {
  return CustomTransitionPage<T>(
    key: key,
    transitionDuration: const Duration(milliseconds: 280),
    reverseTransitionDuration: const Duration(milliseconds: 220),
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final curved = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
      return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position: Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero).animate(curved),
          child: child,
        ),
      );
    },
  );
}
```
- [ ] **Step 4: Run it — PASS.**
- [ ] **Step 5: Commit** — `git add mobile/lib/routing/sovereign_page.dart mobile/test/routing/sovereign_page_test.dart && git commit -m "feat(mobile): sovereign page transition"`

---

## Task 2: Extend the meetings model + repository for detail content

**Files:**
- Modify: `mobile/lib/features/meetings/data/meetings_models.dart`
- Modify: `mobile/lib/features/meetings/data/meetings_repository.dart`
- Test: `mobile/test/features/meetings/meetings_models_test.dart` (extend), `mobile/test/features/meetings/meetings_repository_test.dart` (extend)

- [ ] **Step 1: Write failing tests** (append to the existing files)
```dart
// in meetings_models_test.dart — add:
  test('Meeting.fromJson parses attached documents', () {
    final m = Meeting.fromJson({
      'id': 'm1', 'title': 'T', 'scheduled_at': '2026-06-10T14:00:00Z',
      'status': 'SCHEDULED', 'meeting_type': 'virtual',
      'participants': const [],
      'documents': [
        {'id': 'd1', 'file_name': 'Policy.pdf', 'file_type': 'application/pdf', 'file_path': '/uploads/policy.pdf'},
      ],
    });
    expect(m.documents.single.name, 'Policy.pdf');
    expect(m.documents.single.id, 'd1');
  });
```
```dart
// in meetings_repository_test.dart — add (inside main(), after existing tests):
  test('meetingAgenda returns content, null on 404', () async {
    when(() => dio.get('/meetings/m1/agenda'))
        .thenAnswer((_) async => _resp<Map<String, dynamic>>({'content': '1. Open\n2. Close'}));
    expect(await repo.meetingAgenda('m1'), '1. Open\n2. Close');

    when(() => dio.get('/meetings/m2/agenda')).thenThrow(DioException(
      requestOptions: RequestOptions(path: '/meetings/m2/agenda'),
      response: Response(statusCode: 404, requestOptions: RequestOptions(path: '/meetings/m2/agenda')),
    ));
    expect(await repo.meetingAgenda('m2'), isNull);
  });
```
(Note: the repo test's response helper is named `_resp` or `resp` in the existing file — match whichever is there.)

- [ ] **Step 2: Run — FAIL** (`flutter test test/features/meetings/`).
- [ ] **Step 3: Implement** — in `meetings_models.dart` add the document model + parse it on `Meeting`:
```dart
class MeetingDocument {
  const MeetingDocument({required this.id, required this.name, required this.type, required this.url});
  final String id;
  final String name;
  final String? type;
  final String? url;
  factory MeetingDocument.fromJson(Map<String, dynamic> j) => MeetingDocument(
        id: j['id'].toString(),
        name: (j['file_name'] ?? j['name'] ?? 'Document').toString(),
        type: j['file_type']?.toString(),
        url: (j['file_path'] ?? j['url'])?.toString(),
      );
}
```
Add to `Meeting`: a `final List<MeetingDocument> documents;` field (default `const []`), include it in the constructor, and in `fromJson`:
```dart
        documents: ((json['documents'] as List?) ?? const [])
            .map((e) => MeetingDocument.fromJson(e as Map<String, dynamic>))
            .toList(),
```
In `meetings_repository.dart` add two tolerant fetchers:
```dart
  /// Agenda markdown for a meeting; null when there is none (404).
  Future<String?> meetingAgenda(String id) async {
    try {
      final res = await _dio.get('/meetings/$id/agenda');
      return (res.data as Map<String, dynamic>)['content']?.toString();
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      throw MeetingException('Could not load the agenda.');
    }
  }

  /// Minutes/summary text for a meeting; null when there is none (404).
  Future<String?> meetingMinutes(String id) async {
    try {
      final res = await _dio.get('/meetings/$id/minutes');
      final data = res.data as Map<String, dynamic>;
      final content = data['content']?.toString();
      final decisions = data['key_decisions']?.toString();
      return [if (content != null && content.isNotEmpty) content,
              if (decisions != null && decisions.isNotEmpty) 'Decisions: $decisions']
          .join('\n\n');
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      throw MeetingException('Could not load the minutes.');
    }
  }
```
- [ ] **Step 4: Run — PASS.**
- [ ] **Step 5: Commit** — `git add mobile/lib/features/meetings/data mobile/test/features/meetings && git commit -m "feat(mobile): parse meeting documents + agenda/minutes fetchers"`

---

## Task 3: StatefulShellRoute — persistent nav

**Files:**
- Modify: `mobile/lib/routing/app_router.dart` (full rewrite below)
- Modify: `mobile/lib/shell/app_shell.dart` (full rewrite below — preserve nav visuals)
- Modify: `mobile/test/routing/app_router_test.dart`, `mobile/test/shell/app_shell_test.dart`, `mobile/test/widget_test.dart`

- [ ] **Step 1: Write/adjust the failing tests**

`test/routing/app_router_test.dart` — the redirect target changes `/`→`/home`. Update the relevant assertion:
```dart
// authed user at /login is sent to the home branch
expect(redirectFor(const AuthAuthenticated(_u), '/login'), '/home');
```
(Keep the other redirect cases; `_u` is the existing test AppUser. If the test builds users differently, match it.)

`test/shell/app_shell_test.dart` — rewrite to pump the **router** (AppShell now needs a navigation shell, so test through GoRouter):
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/routing/app_router.dart';

class _MockMeetingsRepo extends Mock implements MeetingsRepository {}

class _AuthedController extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(
      AppUser(id: 'u1', email: 'a@x.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []));
}

void main() {
  testWidgets('shell shows destination tabs + martin centre; tab switch works', (tester) async {
    final repo = _MockMeetingsRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => []);
    final container = ProviderContainer(overrides: [
      authControllerProvider.overrideWith(_AuthedController.new),
      meetingsRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);
    final router = container.read(goRouterProvider);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Meetings'), findsWidgets);
    expect(find.text('Documents'), findsWidgets);
    expect(find.text('Me'), findsWidgets);
    expect(find.byKey(const Key('martin-center')), findsOneWidget);

    await tester.tap(find.text('Documents').first);
    await tester.pumpAndSettle();
    expect(find.text('Shared with you'), findsWidgets); // DocumentsScreen subtitle
  });
}
```
`test/widget_test.dart` — if it pumps `AppShell()` directly, switch it to pump `MaterialApp.router` the same way (authed controller + mock repo), or simplify it to assert the app boots to the login or home. Keep it green.

- [ ] **Step 2: Run — FAIL** (`flutter test test/shell/app_shell_test.dart test/routing/app_router_test.dart`).

- [ ] **Step 3: Rewrite `app_router.dart`**
```dart
// lib/routing/app_router.dart
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/application/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/documents/presentation/documents_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/meetings/presentation/meetings_screen.dart';
import '../features/meetings/presentation/meeting_detail_screen.dart';
import '../features/profile/presentation/me_screen.dart';
import '../shell/app_shell.dart';
import 'sovereign_page.dart';

/// Pure redirect logic — unit-testable without a widget tree.
String? redirectFor(AuthState state, String location) {
  final authed = state is AuthAuthenticated;
  if (!authed && state is! AuthLoading && state is! AuthUnknown && location != '/login') {
    return '/login';
  }
  if (authed && location == '/login') return '/home';
  return null;
}

final goRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/home',
    redirect: (context, st) => redirectFor(ref.read(authControllerProvider), st.matchedLocation),
    refreshListenable: _AuthRefresh(ref),
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => AppShell(navigationShell: navigationShell),
        branches: [
          // 0 Meetings (with nested detail)
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/meetings',
              builder: (_, __) => const MeetingsScreen(),
              routes: [
                GoRoute(
                  path: ':id',
                  pageBuilder: (context, st) =>
                      sovereignPage(child: MeetingDetailScreen(meetingId: st.pathParameters['id']!)),
                ),
              ],
            ),
          ]),
          // 1 Documents
          StatefulShellBranch(routes: [GoRoute(path: '/documents', builder: (_, __) => const DocumentsScreen())]),
          // 2 Home / Martin (centre)
          StatefulShellBranch(routes: [GoRoute(path: '/home', builder: (_, __) => const HomeScreen())]),
          // 3 Me
          StatefulShellBranch(routes: [GoRoute(path: '/me', builder: (_, __) => const MeScreen())]),
        ],
      ),
    ],
  );
});

class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh(Ref ref) {
    ref.listen(authControllerProvider, (_, __) => notifyListeners());
  }
}
```
Note: meeting cards now navigate with `context.go('/meetings/${m.id}')` — confirm `meetings_screen.dart` pushes there (it already uses `/meetings/:id`; `context.push` also works within the branch).

- [ ] **Step 4: Rewrite `app_shell.dart`** — driven by the navigation shell, nav visuals unchanged:
```dart
// lib/shell/app_shell.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/glass/glass.dart';
import '../core/theme/sovereign_colors.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});
  final StatefulNavigationShell navigationShell;

  void _select(int i) =>
      navigationShell.goBranch(i, initialLocation: i == navigationShell.currentIndex);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: Stack(
        children: [
          Positioned.fill(child: navigationShell),
          Positioned(left: 0, right: 0, bottom: 0, child: SafeArea(top: false, child: _glassNav())),
        ],
      ),
    );
  }

  Widget _glassNav() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 14),
      child: GlassSurface(
        borderRadius: 34,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        goldGlow: true,
        child: SizedBox(
          height: 52,
          child: Row(
            children: [
              _item(Icons.event_rounded, 'Meetings', 0),
              _item(Icons.description_rounded, 'Documents', 1),
              _martin(),
              _item(Icons.person_rounded, 'Me', 3),
            ],
          ),
        ),
      ),
    );
  }

  Widget _item(IconData icon, String label, int i) {
    final on = navigationShell.currentIndex == i;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => _select(i),
        child: TweenAnimationBuilder<double>(
          tween: Tween(end: on ? 1.0 : 0.0),
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
          builder: (context, t, _) {
            final color = Color.lerp(
                SovereignColors.ivory.withValues(alpha: 0.5), SovereignColors.gold, t)!;
            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 24 + 6 * t, color: color),
                const SizedBox(height: 4),
                Text(label,
                    style: TextStyle(
                        color: color,
                        fontSize: 10.5,
                        fontWeight: FontWeight.lerp(FontWeight.w400, FontWeight.w700, t))),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _martin() {
    final on = navigationShell.currentIndex == 2;
    return Expanded(
      child: GestureDetector(
        key: const Key('martin-center'),
        behavior: HitTestBehavior.opaque,
        onTap: () => _select(2),
        child: Center(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const LinearGradient(
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                  colors: [Color(0xFFE6C766), SovereignColors.gold]),
              boxShadow: [
                BoxShadow(
                    color: SovereignColors.gold.withValues(alpha: on ? 0.60 : 0.38),
                    blurRadius: on ? 22 : 16, spreadRadius: on ? 2 : 1),
              ],
            ),
            child: const Center(
              child: Text('✦',
                  style: TextStyle(color: SovereignColors.navy, fontSize: 22, fontWeight: FontWeight.bold)),
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: Run the tests — PASS** (`flutter test test/shell/app_shell_test.dart test/routing/app_router_test.dart test/widget_test.dart`). Then `flutter analyze lib` (no errors).

- [ ] **Step 6: Commit** — `git add mobile/lib/routing/app_router.dart mobile/lib/shell/app_shell.dart mobile/test && git commit -m "feat(mobile): StatefulShellRoute — persistent nav across detail"`

---

## Task 4: Layout B detail body

**Files:**
- Modify: `mobile/lib/features/meetings/presentation/meeting_detail_screen.dart` (rewrite the body to Layout B)
- Test: `mobile/test/features/meetings/meeting_detail_screen_test.dart` (extend)

Build a `CustomScrollView` detail with an ambient backdrop, a collapsing `SliverAppBar` and expandable sections + a pinned bottom action bar. Reuse the existing `_JoinPill`, `_RsvpChip`, `_AttendeeRow`, `_RsvpBadge`, `_SectionLabel`, `_DetailError` already in the file.

- [ ] **Step 1: Fetch agenda + minutes alongside the meeting.** Change the state's load to gather all three (agenda/minutes tolerate null):
```dart
  late Future<_DetailData> _future;
  Future<_DetailData> _load() async {
    final repo = ref.read(meetingsRepositoryProvider);
    final meeting = await repo.meetingDetail(widget.meetingId);
    final agenda = await repo.meetingAgenda(widget.meetingId);
    final minutes = await repo.meetingMinutes(widget.meetingId);
    return _DetailData(meeting: meeting, agenda: agenda, minutes: minutes);
  }
```
with a small record/class `class _DetailData { final Meeting meeting; final String? agenda; final String? minutes; const _DetailData({required this.meeting, this.agenda, this.minutes}); }`. The `FutureBuilder<_DetailData>` keeps the existing loading/error states.

- [ ] **Step 2: Add an ambient backdrop + Layout B body.** Wrap the body in a `DecoratedBox` with the Sovereign ambient gradient (navyRaised→navy→navyDeep + a top-right gold radial glow via a `Stack` + `RadialGradient` container), then a `CustomScrollView`:
  - `SliverAppBar(pinned: true, expandedHeight: 150, backgroundColor: Colors.transparent, leading: glass back button, flexibleSpace: FlexibleSpaceBar(title: serif title, background: TWG eyebrow + status badge))`. Use the existing `_BackButton`. Add a `_StatusBadge(status)` (gold-outline pill mapping SCHEDULED/IN_PROGRESS/COMPLETED/CANCELLED → label).
  - A `SliverList`/`SliverToBoxAdapter` of `_ExpandableSection` cards (new widget below):
    - `Agenda · N` — open by default; renders the agenda markdown as numbered/という lines (split on newlines). Hidden if agenda null.
    - `Attendees · ${participants.length}` — rows via existing `_AttendeeRow`.
    - `Documents · ${documents.length}` — rows: type badge + name (display-only this pass; tapping shows a SnackBar "Opens in Documents" — full open/preview ships with sub-project #2). Hidden if empty.
    - `Minutes` — the minutes text. Hidden if null.
  - Bottom padding so content clears the pinned bar + floating nav (e.g., 150).
  - A **pinned bottom action bar** (a `Positioned`/`bottomNavigationBar`-style row above the floating nav): the `_JoinPill` (when `meeting.hasVideo`) + the three `_RsvpChip`s (participants only) calling the existing `_setRsvp`. Render it as the Scaffold's body `Stack` bottom layer (above content, below the global floating nav) using a `GlassSurface` bar; give it `SafeArea`/padding so it sits above the floating nav (which is ~92px tall).

- [ ] **Step 3: Add `_ExpandableSection`** (tap header toggles, `AnimatedSize`):
```dart
class _ExpandableSection extends StatefulWidget {
  const _ExpandableSection({required this.label, required this.count, required this.child, this.initiallyOpen = false});
  final String label; final int? count; final Widget child; final bool initiallyOpen;
  @override State<_ExpandableSection> createState() => _ExpandableSectionState();
}
class _ExpandableSectionState extends State<_ExpandableSection> {
  late bool _open = widget.initiallyOpen;
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => setState(() => _open = !_open),
          child: Row(children: [
            _SectionLabel(widget.count == null ? widget.label : '${widget.label} · ${widget.count}'),
            const Spacer(),
            AnimatedRotation(turns: _open ? 0.25 : 0, duration: const Duration(milliseconds: 200),
              child: const Icon(Icons.chevron_right, color: SovereignColors.gold, size: 18)),
          ]),
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic,
          alignment: Alignment.topCenter,
          child: _open ? Padding(padding: const EdgeInsets.only(top: 10), child: widget.child) : const SizedBox(width: double.infinity),
        ),
      ]),
    );
  }
}
```

- [ ] **Step 4: Widget test** — extend `meeting_detail_screen_test.dart`:
```dart
  testWidgets('detail shows title, an expandable section, and pinned RSVP', (tester) async {
    final repo = _MockRepo();
    when(() => repo.meetingDetail('m1')).thenAnswer((_) async => Meeting.fromJson({
      'id': 'm1', 'title': 'Steering Committee', 'scheduled_at': '2031-06-10T10:00:00Z',
      'status': 'SCHEDULED', 'meeting_type': 'virtual',
      'participants': [{'id':'p','user_id':'me','rsvp_status':'PENDING'}],
    }));
    when(() => repo.meetingAgenda('m1')).thenAnswer((_) async => '1. Open\n2. Close');
    when(() => repo.meetingMinutes('m1')).thenAnswer((_) async => null);
    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MeetingDetailScreen(meetingId: 'm1')),
    ));
    await tester.pump(); await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Steering Committee'), findsOneWidget);
    expect(find.textContaining('Agenda'), findsWidgets);
    expect(find.text('Going'), findsOneWidget); // pinned RSVP (participant)
  });
```
(Add `when(() => repo.meetingAgenda(any())).thenAnswer((_) async => null);` / `meetingMinutes` stubs to the existing detail test so it keeps passing.)

- [ ] **Step 5: Run** — `flutter test test/features/meetings/meeting_detail_screen_test.dart` PASS; `flutter analyze lib` clean.
- [ ] **Step 6: Commit** — `git add mobile/lib/features/meetings/presentation/meeting_detail_screen.dart mobile/test/features/meetings && git commit -m "feat(mobile): meeting detail Layout B — collapsing header, sections, pinned actions"`

---

## Final verification
- [ ] `cd mobile && export PATH="$PATH:/opt/homebrew/bin" && flutter analyze && flutter test` → analyze clean (pre-existing info-lints OK), all tests pass.
- [ ] On device: open a meeting → it rises/fades in **with the nav still visible**; header collapses on scroll; sections expand/collapse; Join + RSVP pinned at the bottom; tabs still switch with the grow-gold animation.

## Notes
- Documents rows in the detail are display-only this pass; full open/preview lands with sub-project #2 (Documents).
- No backend changes. The detail makes 3 GETs (meeting + agenda + minutes); agenda/minutes 404s are treated as "none."
