// test/features/auth/auth_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/auth/data/auth_models.dart';

void main() {
  test('AuthTokens.fromLoginJson parses access + refresh', () {
    final t = AuthTokens.fromLoginJson({
      'access_token': 'a', 'refresh_token': 'r', 'token_type': 'bearer',
    });
    expect(t.access, 'a');
    expect(t.refresh, 'r');
  });

  test('AppUser.fromMeJson parses fields and role; isMember reflects TWG_MEMBER', () {
    final u = AppUser.fromMeJson({
      'id': '11111111-1111-1111-1111-111111111111',
      'email': 'amina@example.org',
      'full_name': 'Amina Diallo',
      'role': 'TWG_MEMBER',
      'twgs': [{'id': '22222222-2222-2222-2222-222222222222', 'name': 'Energy TWG'}],
    });
    expect(u.fullName, 'Amina Diallo');
    expect(u.role, UserRole.twgMember);
    expect(u.isMember, isTrue);
    expect(u.twgs.single.name, 'Energy TWG');
  });

  test('unknown role falls back to UserRole.unknown', () {
    final u = AppUser.fromMeJson({
      'id': 'x', 'email': 'e', 'full_name': 'n', 'role': 'SOMETHING_NEW', 'twgs': [],
    });
    expect(u.role, UserRole.unknown);
  });
}
