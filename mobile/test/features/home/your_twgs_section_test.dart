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
    GoRoute(path: '/', builder: (_, _) => const Scaffold(body: YourTwgsSection())),
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
