// test/features/workspace/workspace_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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
  _DataController(super.twgId);
  @override
  WorkspaceState build() => WorkspaceData(
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
        workspaceControllerProvider.overrideWith2(_DataController.new),
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

  testWidgets('Ask Martin card pushes /martin scoped to this TWG',
      (tester) async {
    final router = GoRouter(
      initialLocation: '/home/workspace/t1',
      routes: [
        GoRoute(
          path: '/home/workspace/:twgId',
          builder: (_, st) =>
              WorkspaceScreen(twgId: st.pathParameters['twgId']!),
        ),
        // Probe stand-in for the canonical full-screen /martin chat route.
        GoRoute(
          path: '/martin',
          builder: (_, st) =>
              _ProbeChatScreen(twg: st.uri.queryParameters['twg']),
        ),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(_OneTwgAuth.new),
        workspaceControllerProvider.overrideWith2(_DataController.new),
      ],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pumpAndSettle();

    final card = find.textContaining('Ask Martin about');
    await tester.ensureVisible(card);
    await tester.tap(card);
    await tester.pumpAndSettle();

    expect(find.text('twg=t1'), findsOneWidget);
  });
}

/// A tiny stand-in for the chat screen that echoes the `?twg=` scope it
/// received, so the workspace wiring test can assert the route + query param
/// without pulling in the chat controller / Dio.
class _ProbeChatScreen extends StatelessWidget {
  const _ProbeChatScreen({required this.twg});
  final String? twg;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('twg=$twg')));
}
