// test/features/auth/auth_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/auth_repository.dart';
import 'package:member_app/features/auth/data/token_storage.dart';

class _MockDio extends Mock implements Dio {}
class _MockStore extends Mock implements TokenStorage {}

void main() {
  late _MockDio dio;
  late _MockStore store;
  late AuthRepository repo;

  setUpAll(() {
    registerFallbackValue(const AuthTokens(access: 'a', refresh: 'r'));
  });

  setUp(() {
    dio = _MockDio();
    store = _MockStore();
    repo = AuthRepository(dio: dio, tokens: store);
    when(() => store.save(any())).thenAnswer((_) async {});
  });

  Response<T> resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('login posts credentials, stores tokens, returns user from /me', () async {
    when(() => dio.post('/auth/login', data: any(named: 'data'))).thenAnswer((_) async =>
        resp<Map<String, dynamic>>({'access_token': 'a', 'refresh_token': 'r', 'token_type': 'bearer'}));
    when(() => dio.get('/auth/me')).thenAnswer((_) async => resp<Map<String, dynamic>>({
          'id': '1', 'email': 'amina@example.org', 'full_name': 'Amina', 'role': 'TWG_MEMBER', 'twgs': [],
        }));

    final user = await repo.login('amina@example.org', 'secret123');

    expect(user.email, 'amina@example.org');
    verify(() => dio.post('/auth/login',
        data: {'email': 'amina@example.org', 'password': 'secret123'})).called(1);
    verify(() => store.save(any(that: isA<AuthTokens>()))).called(1);
  });
}
