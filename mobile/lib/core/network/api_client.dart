// lib/core/network/api_client.dart
import 'package:dio/dio.dart';
import '../config/app_config.dart';
import '../../features/auth/data/auth_models.dart';
import '../../features/auth/data/token_storage.dart';

/// Marks a request that has already been retried once after a token refresh,
/// so a second 401 cannot trigger an infinite refresh loop.
const _kRetriedFlag = 'auth_retried';

/// Endpoints that must NOT trigger a refresh-and-retry: a 401 here means the
/// credentials/refresh token themselves are bad, so retrying would loop or be
/// pointless.
bool _isAuthExemptPath(String path) =>
    path.endsWith('/auth/refresh') ||
    path.endsWith('/auth/login') ||
    path.endsWith('/auth/google') ||
    path.endsWith('/auth/logout');

/// Builds a Dio configured for the backend.
///
/// - Attaches the stored access token as a Bearer header on every request.
/// - Applies connect/receive/send timeouts so a dead network fails fast.
/// - On a 401 from a protected endpoint it transparently refreshes the access
///   token once (POST /auth/refresh with the stored refresh token via a bare,
///   interceptor-free Dio to avoid recursion), saves the new access token,
///   re-attaches it, and replays the original request exactly once. If refresh
///   fails it clears the stored tokens and lets the 401 surface so the app can
///   fall back to the login screen. Requests to the auth endpoints themselves
///   are exempt, and each request is retried at most once.
///
/// [refresherBuilder] creates the bare, interceptor-free Dio used for the
/// refresh call; the default is a fresh Dio with the same timeouts. It exists
/// so tests can inject an adapter — production code should not pass it.
Dio buildAuthInterceptedDio(
  TokenStorage tokens, {
  Dio? inner,
  Dio Function()? refresherBuilder,
}) {
  final dio = inner ??
      Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 12),
        receiveTimeout: const Duration(seconds: 20),
        sendTimeout: const Duration(seconds: 20),
      ));
  if (inner != null) {
    dio.options
      ..connectTimeout = const Duration(seconds: 12)
      ..receiveTimeout = const Duration(seconds: 20)
      ..sendTimeout = const Duration(seconds: 20);
  }

  dio.interceptors.add(QueuedInterceptorsWrapper(
    onRequest: (options, handler) async {
      final t = await tokens.read();
      if (t != null) {
        options.headers['Authorization'] = 'Bearer ${t.access}';
      }
      handler.next(options);
    },
    onError: (error, handler) async {
      final req = error.requestOptions;
      final is401 = error.response?.statusCode == 401;
      final alreadyRetried = req.extra[_kRetriedFlag] == true;

      if (!is401 || alreadyRetried || _isAuthExemptPath(req.path)) {
        handler.next(error);
        return;
      }

      final current = await tokens.read();
      if (current == null) {
        handler.next(error);
        return;
      }

      // Refresh via a bare Dio (no interceptors) to avoid re-entering this
      // onError handler and looping.
      final refresher = refresherBuilder?.call() ??
          Dio(BaseOptions(
            baseUrl: AppConfig.apiV1,
            connectTimeout: const Duration(seconds: 12),
            receiveTimeout: const Duration(seconds: 20),
            sendTimeout: const Duration(seconds: 20),
          ));

      String? newAccess;
      try {
        final res = await refresher.post<Map<String, dynamic>>(
          '/auth/refresh',
          data: {'refresh_token': current.refresh},
        );
        newAccess = res.data?['access_token'] as String?;
      } on DioException {
        newAccess = null;
      } finally {
        refresher.close(force: true);
      }

      if (newAccess == null) {
        // Refresh failed -> drop tokens so the app routes back to login.
        await tokens.clear();
        handler.next(error);
        return;
      }

      // The backend's /auth/refresh returns only a new access token; the
      // refresh token is unchanged.
      await tokens.save(AuthTokens(access: newAccess, refresh: current.refresh));

      req.extra[_kRetriedFlag] = true;
      req.headers['Authorization'] = 'Bearer $newAccess';

      try {
        final retried = await dio.fetch<dynamic>(req);
        handler.resolve(retried);
      } on DioException catch (e) {
        handler.next(e);
      }
    },
  ));
  return dio;
}
