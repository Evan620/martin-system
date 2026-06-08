// lib/core/network/api_client.dart
import 'package:dio/dio.dart';
import '../config/app_config.dart';
import '../../features/auth/data/token_storage.dart';

/// Builds a dio configured for the backend, attaching the stored access token.
/// On 401 it attempts a single refresh and retries (see [_refreshAndRetry]).
Dio buildAuthInterceptedDio(TokenStorage tokens, {Dio? inner}) {
  final dio = inner ?? Dio(BaseOptions(baseUrl: AppConfig.apiV1));
  dio.interceptors.add(QueuedInterceptorsWrapper(
    onRequest: (options, handler) async {
      final t = await tokens.read();
      if (t != null) {
        options.headers['Authorization'] = 'Bearer ${t.access}';
      }
      handler.next(options);
    },
  ));
  return dio;
}
