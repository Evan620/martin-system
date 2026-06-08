// lib/features/auth/data/token_storage.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'auth_models.dart';

class TokenStorage {
  TokenStorage(this._store);
  final FlutterSecureStorage _store;

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';

  Future<void> save(AuthTokens t) async {
    await _store.write(key: _kAccess, value: t.access);
    await _store.write(key: _kRefresh, value: t.refresh);
  }

  Future<AuthTokens?> read() async {
    final a = await _store.read(key: _kAccess);
    final r = await _store.read(key: _kRefresh);
    if (a == null || r == null) return null;
    return AuthTokens(access: a, refresh: r);
  }

  Future<void> clear() async {
    await _store.delete(key: _kAccess);
    await _store.delete(key: _kRefresh);
  }
}
