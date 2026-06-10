// test/core/network/api_client_test.dart
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/network/api_client.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/token_storage.dart';

class _MockTokenStorage extends Mock implements TokenStorage {}

/// Programmable adapter: each call to [fetch] consumes the next queued handler
/// keyed by request path, so we can script 401 -> refresh -> retry flows.
class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.handler);

  /// Returns a [ResponseBody] for the given options. Receives the request
  /// (already mutated by interceptors) so tests can assert on headers.
  final Future<ResponseBody> Function(RequestOptions options) handler;

  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Object body, int code) => ResponseBody.fromString(
      jsonEncode(body),
      code,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );

void main() {
  setUpAll(() {
    registerFallbackValue(const AuthTokens(access: 'a', refresh: 'r'));
  });

  test('interceptor attaches Bearer access token when present', () async {
    final store = _MockTokenStorage();
    when(() => store.read())
        .thenAnswer((_) async => const AuthTokens(access: 'abc', refresh: 'r'));

    final dio = buildAuthInterceptedDio(store);
    final options = RequestOptions(path: '/x');

    final handler = _CapturingRequestHandler();
    final interceptor =
        dio.interceptors.whereType<QueuedInterceptorsWrapper>().first;
    interceptor.onRequest(options, handler);
    await handler.done;

    expect(options.headers['Authorization'], 'Bearer abc');
  });

  test('sets sane timeouts on the dio instance', () {
    final store = _MockTokenStorage();
    final dio = buildAuthInterceptedDio(store);
    expect(dio.options.connectTimeout, const Duration(seconds: 12));
    expect(dio.options.receiveTimeout, const Duration(seconds: 20));
    expect(dio.options.sendTimeout, const Duration(seconds: 20));
  });

  test('401 triggers refresh once, retries original with new bearer, succeeds',
      () async {
    final store = _MockTokenStorage();
    var stored = const AuthTokens(access: 'old', refresh: 'r1');
    when(() => store.read()).thenAnswer((_) async => stored);
    when(() => store.save(any())).thenAnswer((invocation) async {
      stored = invocation.positionalArguments.first as AuthTokens;
    });
    when(() => store.clear()).thenAnswer((_) async {});

    var meCalls = 0;
    var refreshCalls = 0;
    Object? refreshBody;
    String? firstMeAuth;
    String? retryMeAuth;

    final adapter = _FakeAdapter((options) async {
      if (options.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        refreshBody = options.data;
        return _json({'access_token': 'new', 'token_type': 'bearer'}, 200);
      }
      if (options.path.endsWith('/auth/me')) {
        meCalls++;
        if (meCalls == 1) {
          // First attempt uses the stale access token -> 401.
          firstMeAuth = options.headers['Authorization'] as String?;
          return _json({'detail': 'expired'}, 401);
        }
        // Retry must carry the refreshed bearer.
        retryMeAuth = options.headers['Authorization'] as String?;
        return _json({'id': '1', 'email': 'a@b.org'}, 200);
      }
      return _json({}, 404);
    });

    final dio = buildAuthInterceptedDio(
      store,
      refresherBuilder: () => Dio()..httpClientAdapter = adapter,
    );
    dio.httpClientAdapter = adapter;

    final res = await dio.get<Map<String, dynamic>>('/auth/me');

    expect(res.statusCode, 200);
    expect(res.data?['email'], 'a@b.org');
    expect(refreshCalls, 1);
    expect(meCalls, 2);
    // First /me used the stale token; the refresh sent the stored refresh
    // token; the retry carried the freshly refreshed bearer.
    expect(firstMeAuth, 'Bearer old');
    expect(retryMeAuth, 'Bearer new');
    final decodedRefresh = refreshBody is String
        ? jsonDecode(refreshBody as String)
        : refreshBody;
    expect((decodedRefresh as Map)['refresh_token'], 'r1');
    // New access token persisted; refresh token unchanged.
    expect(stored.access, 'new');
    expect(stored.refresh, 'r1');
    verify(() => store.save(any())).called(1);
  });

  test('refresh failure clears tokens and surfaces the original 401', () async {
    final store = _MockTokenStorage();
    when(() => store.read())
        .thenAnswer((_) async => const AuthTokens(access: 'old', refresh: 'r1'));
    when(() => store.save(any())).thenAnswer((_) async {});
    when(() => store.clear()).thenAnswer((_) async {});

    var refreshCalls = 0;

    final adapter = _FakeAdapter((options) async {
      if (options.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        return _json({'detail': 'refresh expired'}, 401);
      }
      if (options.path.endsWith('/auth/me')) {
        return _json({'detail': 'expired'}, 401);
      }
      return _json({}, 404);
    });

    final dio = buildAuthInterceptedDio(
      store,
      refresherBuilder: () => Dio()..httpClientAdapter = adapter,
    );
    dio.httpClientAdapter = adapter;

    await expectLater(
      dio.get<Map<String, dynamic>>('/auth/me'),
      throwsA(isA<DioException>()),
    );

    expect(refreshCalls, 1);
    verify(() => store.clear()).called(1);
    verifyNever(() => store.save(any()));
  });

  test('a 401 on the refresh endpoint itself does not loop', () async {
    final store = _MockTokenStorage();
    when(() => store.read())
        .thenAnswer((_) async => const AuthTokens(access: 'old', refresh: 'r1'));
    when(() => store.save(any())).thenAnswer((_) async {});
    when(() => store.clear()).thenAnswer((_) async {});

    var refreshCalls = 0;

    final adapter = _FakeAdapter((options) async {
      if (options.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        return _json({'detail': 'no'}, 401);
      }
      return _json({}, 404);
    });

    final dio = buildAuthInterceptedDio(store);
    dio.httpClientAdapter = adapter;

    // Hitting refresh directly with a 401 must NOT recurse into another refresh.
    await expectLater(
      dio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': 'r1'},
      ),
      throwsA(isA<DioException>()),
    );

    // Only the single direct call; no interceptor-driven refresh attempt.
    expect(refreshCalls, 1);
  });

  test('a 401 on login does not attempt a refresh', () async {
    final store = _MockTokenStorage();
    when(() => store.read()).thenAnswer((_) async => null);
    when(() => store.clear()).thenAnswer((_) async {});

    var loginCalls = 0;
    var refreshCalls = 0;

    final adapter = _FakeAdapter((options) async {
      if (options.path.endsWith('/auth/refresh')) {
        refreshCalls++;
        return _json({}, 200);
      }
      if (options.path.endsWith('/auth/login')) {
        loginCalls++;
        return _json({'detail': 'bad creds'}, 401);
      }
      return _json({}, 404);
    });

    final dio = buildAuthInterceptedDio(store);
    dio.httpClientAdapter = adapter;

    await expectLater(
      dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'email': 'a@b.org', 'password': 'x'},
      ),
      throwsA(isA<DioException>()),
    );

    expect(loginCalls, 1);
    expect(refreshCalls, 0);
  });
}

class _CapturingRequestHandler extends RequestInterceptorHandler {
  final _c = Completer<void>();
  Future<void> get done => _c.future;
  @override
  void next(RequestOptions requestOptions) => _c.complete();
}
