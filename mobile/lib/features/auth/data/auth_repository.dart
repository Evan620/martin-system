// lib/features/auth/data/auth_repository.dart
import 'package:dio/dio.dart';
import 'auth_models.dart';
import 'token_storage.dart';

class AuthException implements Exception {
  AuthException(this.message);
  final String message;
  @override
  String toString() => message;
}

class AuthRepository {
  AuthRepository({required this._dio, required this._tokens});
  final Dio _dio;
  final TokenStorage _tokens;

  Future<AppUser> login(String email, String password) async {
    try {
      final res = await _dio.post('/auth/login', data: {'email': email, 'password': password});
      final t = AuthTokens.fromLoginJson(res.data as Map<String, dynamic>);
      await _tokens.save(t);
      return await fetchMe();
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) throw AuthException('Wrong email or password.');
      throw AuthException('Could not sign in. Check your connection and try again.');
    }
  }

  Future<AppUser> fetchMe() async {
    final res = await _dio.get('/auth/me');
    return AppUser.fromMeJson(res.data as Map<String, dynamic>);
  }

  Future<void> logout() async {
    final t = await _tokens.read();
    if (t != null) {
      try {
        await _dio.post('/auth/logout', data: {'refresh_token': t.refresh});
      } catch (_) {/* best-effort */}
    }
    await _tokens.clear();
  }
}
