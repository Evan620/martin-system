// test/core/network/api_client_test.dart
import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/network/api_client.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/token_storage.dart';

class _MockTokenStorage extends Mock implements TokenStorage {}

void main() {
  test('interceptor attaches Bearer access token when present', () async {
    final store = _MockTokenStorage();
    when(() => store.read())
        .thenAnswer((_) async => const AuthTokens(access: 'abc', refresh: 'r'));

    final dio = buildAuthInterceptedDio(store);
    final options = RequestOptions(path: '/x');

    final handler = _CapturingRequestHandler();
    final interceptor = dio.interceptors
        .whereType<QueuedInterceptorsWrapper>()
        .first;
    interceptor.onRequest(options, handler);
    await handler.done;

    expect(options.headers['Authorization'], 'Bearer abc');
  });
}

class _CapturingRequestHandler extends RequestInterceptorHandler {
  final _c = Completer<void>();
  Future<void> get done => _c.future;
  @override
  void next(RequestOptions requestOptions) => _c.complete();
}
