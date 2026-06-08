// test/features/auth/login_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/auth_repository.dart';
import 'package:member_app/features/auth/presentation/login_screen.dart';

class _MockRepo extends Mock implements AuthRepository {}
const _user = AppUser(id: '1', email: 'a@b.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []);

void main() {
  testWidgets('entering creds and tapping Sign in calls repo.login', (tester) async {
    final repo = _MockRepo();
    when(() => repo.login(any(), any())).thenAnswer((_) async => _user);

    await tester.pumpWidget(ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: LoginScreen()),
    ));

    await tester.enterText(find.byKey(const Key('email')), 'a@b.org');
    await tester.enterText(find.byKey(const Key('password')), 'secret123');
    await tester.tap(find.byKey(const Key('signin')));
    await tester.pump();

    verify(() => repo.login('a@b.org', 'secret123')).called(1);
  });
}
