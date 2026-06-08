// test/features/auth/auth_controller_test.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/auth_repository.dart';

class _MockRepo extends Mock implements AuthRepository {}

const _user = AppUser(id: '1', email: 'a@b.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []);

void main() {
  late _MockRepo repo;
  ProviderContainer makeContainer() => ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(repo)],
      );

  setUp(() => repo = _MockRepo());

  test('signIn success → AuthState.authenticated(user)', () async {
    when(() => repo.login(any(), any())).thenAnswer((_) async => _user);
    final c = makeContainer();
    addTearDown(c.dispose);

    await c.read(authControllerProvider.notifier).signIn('a@b.org', 'secret123');

    expect(c.read(authControllerProvider), AuthState.authenticated(_user));
  });

  test('signIn failure → AuthState.error with message', () async {
    when(() => repo.login(any(), any())).thenThrow(AuthException('Wrong email or password.'));
    final c = makeContainer();
    addTearDown(c.dispose);

    await c.read(authControllerProvider.notifier).signIn('a@b.org', 'bad');

    final s = c.read(authControllerProvider);
    expect(s, isA<AuthError>());
    expect((s as AuthError).message, 'Wrong email or password.');
  });
}
