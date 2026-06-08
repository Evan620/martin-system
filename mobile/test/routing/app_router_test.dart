// test/routing/app_router_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/routing/app_router.dart';

const _user = AppUser(id: '1', email: 'a@b.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []);

void main() {
  test('redirect: unauthenticated → /login, authenticated → /', () {
    expect(redirectFor(const AuthState.unauthenticated(), '/'), '/login');
    expect(redirectFor(const AuthState.authenticated(_user), '/login'), '/');
    expect(redirectFor(const AuthState.authenticated(_user), '/'), isNull);
    expect(redirectFor(const AuthState.loading(), '/'), isNull);
  });
}
