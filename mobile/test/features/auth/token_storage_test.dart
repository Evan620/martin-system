// test/features/auth/token_storage_test.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/token_storage.dart';

class _MockStore extends Mock implements FlutterSecureStorage {}

void main() {
  late _MockStore store;
  late TokenStorage tokens;

  setUp(() {
    store = _MockStore();
    tokens = TokenStorage(store);
  });

  test('save writes access and refresh keys', () async {
    when(() => store.write(key: any(named: 'key'), value: any(named: 'value')))
        .thenAnswer((_) async {});
    await tokens.save(const AuthTokens(access: 'a', refresh: 'r'));
    verify(() => store.write(key: 'access_token', value: 'a')).called(1);
    verify(() => store.write(key: 'refresh_token', value: 'r')).called(1);
  });

  test('read returns null when no access token stored', () async {
    when(() => store.read(key: any(named: 'key'))).thenAnswer((_) async => null);
    expect(await tokens.read(), isNull);
  });
}
