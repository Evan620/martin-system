// test/shell/app_shell_test.dart
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
