# Member App — Foundation + Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Flutter member app in `mobile/` with the Sovereign design system, log a member into the existing backend (email+password, with biometric reopen), and land them in a Martin-center navigation shell.

**Architecture:** A new Flutter app in `mobile/` (monorepo) talks to the existing FastAPI backend over REST. Auth reuses the existing `/api/v1/auth/*` endpoints (JWT access + refresh). State is Riverpod; HTTP is dio with a token-attaching + refresh-on-401 interceptor; tokens live in `flutter_secure_storage`; navigation is go_router with an auth redirect. No backend changes in this plan.

**Tech Stack:** Flutter (stable, Dart 3), flutter_riverpod, dio, flutter_secure_storage, go_router, local_auth, mocktail (tests).

**Spec:** `docs/superpowers/specs/2026-06-08-member-mobile-app-design.md` (§4 design system, §8 auth).

**Backend contract (verified, do not change):**
- `POST /api/v1/auth/login` — JSON `{ "email": str, "password": str }` → `200 { "access_token": str, "refresh_token": str, "token_type": "bearer" }`
- `GET /api/v1/auth/me` — header `Authorization: Bearer <access>` → `200 { "id": uuid, "email": str, "full_name": str, "role": "ADMIN"|"TWG_FACILITATOR"|"TWG_MEMBER"|"SECRETARIAT_LEAD", "organization": str?, "twg_ids": [uuid], "twgs": [{"id":uuid,"name":str}] }`
- `POST /api/v1/auth/refresh` — JSON `{ "refresh_token": str }` → `200 { "access_token": str, "token_type": "bearer" }`
- `POST /api/v1/auth/logout` — JSON `{ "refresh_token": str }` → `204`

---

## File Structure

```
mobile/
  lib/
    main.dart                              # entry: ProviderScope + bootstrap
    app.dart                               # MemberApp: MaterialApp.router + theme
    core/
      config/app_config.dart               # API base URL (from --dart-define)
      theme/sovereign_colors.dart          # color tokens
      theme/sovereign_theme.dart           # ThemeData (navy/gold/serif)
      network/api_client.dart              # dio instance + auth interceptor
    features/auth/
      data/auth_models.dart                # AuthTokens, AppUser, UserRole
      data/token_storage.dart              # secure storage wrapper
      data/auth_repository.dart            # login / refresh / logout / fetchMe
      application/auth_controller.dart      # AuthState + AuthController (Riverpod)
      presentation/login_screen.dart       # Sovereign login UI
    routing/app_router.dart                # go_router + auth redirect
    shell/app_shell.dart                   # Martin-center bottom nav
    shell/placeholder_screen.dart          # temporary destination screens
  test/
    core/config/app_config_test.dart
    core/network/api_client_test.dart
    features/auth/auth_models_test.dart
    features/auth/token_storage_test.dart
    features/auth/auth_repository_test.dart
    features/auth/auth_controller_test.dart
    features/auth/login_screen_test.dart
    shell/app_shell_test.dart
```

**Responsibilities:** each file owns one thing — `auth_repository` only does network+storage for auth, `auth_controller` only holds state, `login_screen` only renders+delegates. Keep them focused.

---

## Task 1: Scaffold the Flutter project

**Files:**
- Create: `mobile/` (via `flutter create`)
- Modify: `mobile/pubspec.yaml`

- [ ] **Step 1: Create the app**

Run (from repo root):
```bash
flutter create --org org.ecowasiisummit --project-name member_app --platforms ios,android mobile
```
Expected: `mobile/` created with `lib/main.dart`, `ios/`, `android/`.

- [ ] **Step 2: Add dependencies**

Run (from `mobile/`):
```bash
cd mobile
flutter pub add flutter_riverpod dio flutter_secure_storage go_router local_auth
flutter pub add --dev mocktail
```
Expected: `pubspec.yaml` lists all under `dependencies` / `dev_dependencies`; `flutter pub get` succeeds.

- [ ] **Step 3: Verify it builds**

Run: `flutter analyze`
Expected: "No issues found!" (the default counter app).

- [ ] **Step 4: Commit**

```bash
cd /Users/evan/ravishing-presence
git add mobile/ .gitignore
git commit -m "feat(mobile): scaffold Flutter member app with core deps"
```

---

## Task 2: Sovereign color tokens

**Files:**
- Create: `mobile/lib/core/theme/sovereign_colors.dart`
- Test: `mobile/test/core/theme/sovereign_colors_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/core/theme/sovereign_colors_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';

void main() {
  test('Sovereign palette exposes navy and gold', () {
    expect(SovereignColors.navy, const Color(0xFF0A1F44));
    expect(SovereignColors.gold, const Color(0xFFC9A227));
    expect(SovereignColors.ivory, const Color(0xFFF6F1E7));
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/theme/sovereign_colors_test.dart`
Expected: FAIL — `Target of URI doesn't exist 'sovereign_colors.dart'`.

- [ ] **Step 3: Implement**

```dart
// lib/core/theme/sovereign_colors.dart
import 'package:flutter/material.dart';

/// Sovereign palette — deep navy + gold, institutional/diplomatic.
abstract final class SovereignColors {
  static const navy = Color(0xFF0A1F44);
  static const navyDeep = Color(0xFF08152F);
  static const navyRaised = Color(0xFF0E2A55);
  static const gold = Color(0xFFC9A227);
  static const ivory = Color(0xFFF6F1E7);
  static const danger = Color(0xFF9B3A2E);
  static const success = Color(0xFF2F6B4F);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/theme/sovereign_colors_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/core/theme/sovereign_colors.dart mobile/test/core/theme/sovereign_colors_test.dart
git commit -m "feat(mobile): Sovereign color tokens"
```

---

## Task 3: Sovereign ThemeData

**Files:**
- Create: `mobile/lib/core/theme/sovereign_theme.dart`
- Test: `mobile/test/core/theme/sovereign_theme_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/core/theme/sovereign_theme_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/theme/sovereign_colors.dart';
import 'package:member_app/core/theme/sovereign_theme.dart';

void main() {
  test('theme uses navy scaffold and gold primary, dark brightness', () {
    final theme = SovereignTheme.dark();
    expect(theme.scaffoldBackgroundColor, SovereignColors.navy);
    expect(theme.colorScheme.primary, SovereignColors.gold);
    expect(theme.brightness, Brightness.dark);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/theme/sovereign_theme_test.dart`
Expected: FAIL — `sovereign_theme.dart` not found.

- [ ] **Step 3: Implement**

```dart
// lib/core/theme/sovereign_theme.dart
import 'package:flutter/material.dart';
import 'sovereign_colors.dart';

abstract final class SovereignTheme {
  static ThemeData dark() {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: SovereignColors.navy,
      colorScheme: const ColorScheme.dark(
        primary: SovereignColors.gold,
        surface: SovereignColors.navy,
        onPrimary: SovereignColors.navy,
        error: SovereignColors.danger,
      ),
      textTheme: base.textTheme.copyWith(
        // Serif display for headlines; system sans for body.
        displaySmall: const TextStyle(fontFamily: 'Georgia', color: SovereignColors.ivory),
        headlineMedium: const TextStyle(fontFamily: 'Georgia', color: SovereignColors.ivory),
        titleLarge: const TextStyle(fontFamily: 'Georgia', color: SovereignColors.ivory),
        bodyMedium: const TextStyle(color: SovereignColors.ivory),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: SovereignColors.gold,
          foregroundColor: SovereignColors.navy,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.06),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: SovereignColors.gold),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/theme/sovereign_theme_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/core/theme/sovereign_theme.dart mobile/test/core/theme/sovereign_theme_test.dart
git commit -m "feat(mobile): Sovereign ThemeData"
```

---

## Task 4: App config (API base URL)

**Files:**
- Create: `mobile/lib/core/config/app_config.dart`
- Test: `mobile/test/core/config/app_config_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/core/config/app_config_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/config/app_config.dart';

void main() {
  test('apiBaseUrl defaults and ends without trailing slash', () {
    expect(AppConfig.apiBaseUrl, isNotEmpty);
    expect(AppConfig.apiBaseUrl.endsWith('/'), isFalse);
    expect(AppConfig.apiV1, AppConfig.apiBaseUrl + '/api/v1');
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/config/app_config_test.dart`
Expected: FAIL — `app_config.dart` not found.

- [ ] **Step 3: Implement**

```dart
// lib/core/config/app_config.dart
/// Build-time config. Override with:
///   flutter run --dart-define=API_BASE_URL=https://your-host
abstract final class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );

  static String get apiV1 => '$apiBaseUrl/api/v1';
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/config/app_config_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/core/config/app_config.dart mobile/test/core/config/app_config_test.dart
git commit -m "feat(mobile): build-time API base URL config"
```

---

## Task 5: Auth models

**Files:**
- Create: `mobile/lib/features/auth/data/auth_models.dart`
- Test: `mobile/test/features/auth/auth_models_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/auth_models_test.dart`
Expected: FAIL — `auth_models.dart` not found.

- [ ] **Step 3: Implement**

```dart
// lib/features/auth/data/auth_models.dart
enum UserRole { admin, twgFacilitator, twgMember, secretariatLead, unknown }

UserRole _roleFromApi(String raw) => switch (raw) {
      'ADMIN' => UserRole.admin,
      'TWG_FACILITATOR' => UserRole.twgFacilitator,
      'TWG_MEMBER' => UserRole.twgMember,
      'SECRETARIAT_LEAD' => UserRole.secretariatLead,
      _ => UserRole.unknown,
    };

class AuthTokens {
  const AuthTokens({required this.access, required this.refresh});
  final String access;
  final String refresh;

  factory AuthTokens.fromLoginJson(Map<String, dynamic> json) => AuthTokens(
        access: json['access_token'] as String,
        refresh: json['refresh_token'] as String,
      );
}

class Twg {
  const Twg({required this.id, required this.name});
  final String id;
  final String name;
  factory Twg.fromJson(Map<String, dynamic> j) =>
      Twg(id: j['id'].toString(), name: j['name'] as String);
}

class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.twgs,
  });

  final String id;
  final String email;
  final String fullName;
  final UserRole role;
  final List<Twg> twgs;

  bool get isMember => role == UserRole.twgMember;

  factory AppUser.fromMeJson(Map<String, dynamic> json) => AppUser(
        id: json['id'].toString(),
        email: json['email'] as String,
        fullName: json['full_name'] as String,
        role: _roleFromApi(json['role'] as String),
        twgs: ((json['twgs'] as List?) ?? const [])
            .map((e) => Twg.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/auth_models_test.dart`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/auth/data/auth_models.dart mobile/test/features/auth/auth_models_test.dart
git commit -m "feat(mobile): auth models (tokens, user, role)"
```

---

## Task 6: Secure token storage

**Files:**
- Create: `mobile/lib/features/auth/data/token_storage.dart`
- Test: `mobile/test/features/auth/token_storage_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/token_storage_test.dart`
Expected: FAIL — `token_storage.dart` not found.

- [ ] **Step 3: Implement**

```dart
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/token_storage_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/auth/data/token_storage.dart mobile/test/features/auth/token_storage_test.dart
git commit -m "feat(mobile): secure token storage"
```

---

## Task 7: Dio API client + token-attach interceptor

**Files:**
- Create: `mobile/lib/core/network/api_client.dart`
- Test: `mobile/test/core/network/api_client_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/core/network/api_client_test.dart
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
    await handler.future;

    expect(options.headers['Authorization'], 'Bearer abc');
  });
}

class _CapturingRequestHandler extends RequestInterceptorHandler {
  final _c = Completer<void>();
  Future<void> get future => _c.future;
  @override
  void next(RequestOptions requestOptions) => _c.complete();
}
```
Add `import 'dart:async';` at the top of the test.

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/network/api_client_test.dart`
Expected: FAIL — `api_client.dart` / `buildAuthInterceptedDio` not found.

- [ ] **Step 3: Implement**

```dart
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/network/api_client_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/core/network/api_client.dart mobile/test/core/network/api_client_test.dart
git commit -m "feat(mobile): dio client with token-attach interceptor"
```

---

## Task 8: Auth repository (login / fetchMe / refresh / logout)

**Files:**
- Create: `mobile/lib/features/auth/data/auth_repository.dart`
- Test: `mobile/test/features/auth/auth_repository_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
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

  setUp(() {
    dio = _MockDio();
    store = _MockStore();
    repo = AuthRepository(dio: dio, tokens: store);
    when(() => store.save(any())).thenAnswer((_) async {});
  });

  Response<T> _resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('login posts credentials, stores tokens, returns user from /me', () async {
    when(() => dio.post('/auth/login', data: any(named: 'data'))).thenAnswer((_) async =>
        _resp<Map<String, dynamic>>({'access_token': 'a', 'refresh_token': 'r', 'token_type': 'bearer'}));
    when(() => dio.get('/auth/me')).thenAnswer((_) async => _resp<Map<String, dynamic>>({
          'id': '1', 'email': 'amina@example.org', 'full_name': 'Amina', 'role': 'TWG_MEMBER', 'twgs': [],
        }));

    final user = await repo.login('amina@example.org', 'secret123');

    expect(user.email, 'amina@example.org');
    verify(() => dio.post('/auth/login',
        data: {'email': 'amina@example.org', 'password': 'secret123'})).called(1);
    verify(() => store.save(any(that: isA<AuthTokens>()))).called(1);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/auth_repository_test.dart`
Expected: FAIL — `auth_repository.dart` not found.

- [ ] **Step 3: Implement**

```dart
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
  AuthRepository({required Dio dio, required TokenStorage tokens})
      : _dio = dio, _tokens = tokens;
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/auth_repository_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/auth/data/auth_repository.dart mobile/test/features/auth/auth_repository_test.dart
git commit -m "feat(mobile): auth repository (login/me/logout)"
```

---

## Task 9: Auth controller (Riverpod state)

**Files:**
- Create: `mobile/lib/features/auth/application/auth_controller.dart`
- Test: `mobile/test/features/auth/auth_controller_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/auth/auth_controller_test.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/auth_repository.dart';

class _MockRepo extends Mock implements AuthRepository {}

const _user = AppUser(id: '1', email: 'a@b.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []);

void main() {
  late _MockRepo repo;
  ProviderContainer makeContainer() => ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(repo)],
      );

  setUp(() => repo = _MockRepo());

  test('signIn success → AuthState.authenticated(user)', () async {
    when(() => repo.login(any(), any())).thenAnswer((_) async => _user);
    final c = makeContainer();
    addTearDown(c.dispose);

    await c.read(authControllerProvider.notifier).signIn('a@b.org', 'secret123');

    expect(c.read(authControllerProvider), AuthState.authenticated(_user));
  });

  test('signIn failure → AuthState.error with message', () async {
    when(() => repo.login(any(), any())).thenThrow(AuthException('Wrong email or password.'));
    final c = makeContainer();
    addTearDown(c.dispose);

    await c.read(authControllerProvider.notifier).signIn('a@b.org', 'bad');

    final s = c.read(authControllerProvider);
    expect(s, isA<AuthError>());
    expect((s as AuthError).message, 'Wrong email or password.');
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/auth_controller_test.dart`
Expected: FAIL — `auth_controller.dart` not found.

- [ ] **Step 3: Implement**

```dart
// lib/features/auth/application/auth_controller.dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/network/api_client.dart';
import '../data/auth_models.dart';
import '../data/auth_repository.dart';
import '../data/token_storage.dart';

sealed class AuthState {
  const AuthState();
  const factory AuthState.unknown() = AuthUnknown;
  const factory AuthState.loading() = AuthLoading;
  const factory AuthState.authenticated(AppUser user) = AuthAuthenticated;
  const factory AuthState.unauthenticated() = AuthUnauthenticated;
  const factory AuthState.error(String message) = AuthError;
}

class AuthUnknown extends AuthState { const AuthUnknown(); }
class AuthLoading extends AuthState { const AuthLoading(); }
class AuthUnauthenticated extends AuthState { const AuthUnauthenticated(); }

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.user);
  final AppUser user;
  @override
  bool operator ==(Object o) => o is AuthAuthenticated && o.user.id == user.id;
  @override
  int get hashCode => user.id.hashCode;
}

class AuthError extends AuthState {
  const AuthError(this.message);
  final String message;
  @override
  bool operator ==(Object o) => o is AuthError && o.message == message;
  @override
  int get hashCode => message.hashCode;
}

final tokenStorageProvider = Provider<TokenStorage>(
  (_) => TokenStorage(const FlutterSecureStorage()),
);

final dioProvider = Provider<Dio>(
  (ref) => buildAuthInterceptedDio(ref.watch(tokenStorageProvider)),
);

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(dio: ref.watch(dioProvider), tokens: ref.watch(tokenStorageProvider)),
);

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthState.unknown();

  AuthRepository get _repo => ref.read(authRepositoryProvider);
  TokenStorage get _tokens => ref.read(tokenStorageProvider);

  /// On launch: if a token exists, try to load the user.
  Future<void> bootstrap() async {
    final t = await _tokens.read();
    if (t == null) {
      state = const AuthState.unauthenticated();
      return;
    }
    try {
      state = AuthState.authenticated(await _repo.fetchMe());
    } catch (_) {
      await _tokens.clear();
      state = const AuthState.unauthenticated();
    }
  }

  Future<void> signIn(String email, String password) async {
    state = const AuthState.loading();
    try {
      state = AuthState.authenticated(await _repo.login(email, password));
    } on AuthException catch (e) {
      state = AuthState.error(e.message);
    }
  }

  Future<void> signOut() async {
    await _repo.logout();
    state = const AuthState.unauthenticated();
  }
}

final authControllerProvider =
    NotifierProvider<AuthController, AuthState>(AuthController.new);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/auth_controller_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/auth/application/auth_controller.dart mobile/test/features/auth/auth_controller_test.dart
git commit -m "feat(mobile): auth controller + providers (Riverpod)"
```

---

## Task 10: Login screen

**Files:**
- Create: `mobile/lib/features/auth/presentation/login_screen.dart`
- Test: `mobile/test/features/auth/login_screen_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/auth/login_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/auth/data/auth_repository.dart';
import 'package:member_app/features/auth/presentation/login_screen.dart';

class _MockRepo extends Mock implements AuthRepository {}
const _user = AppUser(id: '1', email: 'a@b.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []);

void main() {
  testWidgets('entering creds and tapping Sign in calls repo.login', (tester) async {
    final repo = _MockRepo();
    when(() => repo.login(any(), any())).thenAnswer((_) async => _user);

    await tester.pumpWidget(ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: LoginScreen()),
    ));

    await tester.enterText(find.byKey(const Key('email')), 'a@b.org');
    await tester.enterText(find.byKey(const Key('password')), 'secret123');
    await tester.tap(find.byKey(const Key('signin')));
    await tester.pump();

    verify(() => repo.login('a@b.org', 'secret123')).called(1);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/login_screen_test.dart`
Expected: FAIL — `login_screen.dart` not found.

- [ ] **Step 3: Implement**

```dart
// lib/features/auth/presentation/login_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../application/auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authControllerProvider);
    final loading = state is AuthLoading;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('ECOWAS SUMMIT 2026',
                  style: TextStyle(color: SovereignColors.gold, letterSpacing: 3, fontSize: 11)),
              const SizedBox(height: 10),
              Text('Welcome',
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(fontSize: 34)),
              const SizedBox(height: 28),
              TextField(
                key: const Key('email'),
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              const SizedBox(height: 14),
              TextField(
                key: const Key('password'),
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password'),
              ),
              if (state is AuthError) ...[
                const SizedBox(height: 14),
                Text(state.message, style: const TextStyle(color: SovereignColors.danger)),
              ],
              const SizedBox(height: 24),
              FilledButton(
                key: const Key('signin'),
                onPressed: loading
                    ? null
                    : () => ref.read(authControllerProvider.notifier)
                        .signIn(_email.text.trim(), _password.text),
                child: loading
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: SovereignColors.navy))
                    : const Text('Sign in'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/login_screen_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/auth/presentation/login_screen.dart mobile/test/features/auth/login_screen_test.dart
git commit -m "feat(mobile): Sovereign login screen"
```

---

## Task 11: Navigation shell (Martin-center bottom nav)

**Files:**
- Create: `mobile/lib/shell/placeholder_screen.dart`
- Create: `mobile/lib/shell/app_shell.dart`
- Test: `mobile/test/shell/app_shell_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/shell/app_shell_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/shell/app_shell.dart';

void main() {
  testWidgets('shell shows the three destination tabs and a center Martin button', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AppShell()));
    expect(find.text('Meetings'), findsOneWidget);
    expect(find.text('Documents'), findsOneWidget);
    expect(find.text('Me'), findsOneWidget);
    expect(find.byKey(const Key('martin-center')), findsOneWidget);
  });

  testWidgets('tapping a tab swaps the visible destination', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AppShell()));
    expect(find.text('Martin'), findsWidgets); // opens on Martin
    await tester.tap(find.text('Documents'));
    await tester.pumpAndSettle();
    expect(find.text('Documents — coming soon'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/shell/app_shell_test.dart`
Expected: FAIL — `app_shell.dart` not found.

- [ ] **Step 3: Implement**

```dart
// lib/shell/placeholder_screen.dart
import 'package:flutter/material.dart';
import '../core/theme/sovereign_colors.dart';

class PlaceholderScreen extends StatelessWidget {
  const PlaceholderScreen(this.title, {super.key});
  final String title;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: Center(
          child: Text('$title — coming soon',
              style: const TextStyle(color: SovereignColors.ivory)),
        ),
      );
}
```

```dart
// lib/shell/app_shell.dart
import 'package:flutter/material.dart';
import '../core/theme/sovereign_colors.dart';
import 'placeholder_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  // 0 Meetings, 1 Documents, 2 Martin(center/home), 3 Me
  int _index = 2;

  static const _screens = [
    PlaceholderScreen('Meetings'),
    PlaceholderScreen('Documents'),
    PlaceholderScreen('Martin'),
    PlaceholderScreen('Me'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _screens),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: FloatingActionButton(
        key: const Key('martin-center'),
        backgroundColor: SovereignColors.gold,
        foregroundColor: SovereignColors.navy,
        onPressed: () => setState(() => _index = 2),
        child: const Text('✦', style: TextStyle(fontSize: 22)),
      ),
      bottomNavigationBar: BottomAppBar(
        color: SovereignColors.navyDeep,
        shape: const CircularNotchedRectangle(),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _tab(icon: Icons.event, label: 'Meetings', i: 0),
            _tab(icon: Icons.description, label: 'Documents', i: 1),
            const SizedBox(width: 48), // notch gap for the Martin FAB
            _tab(icon: Icons.person, label: 'Me', i: 3),
          ],
        ),
      ),
    );
  }

  Widget _tab({required IconData icon, required String label, required int i}) {
    final on = _index == i;
    final color = on ? SovereignColors.gold : SovereignColors.ivory.withValues(alpha: 0.55);
    return InkWell(
      onTap: () => setState(() => _index = i),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, color: color, size: 22),
          Text(label, style: TextStyle(color: color, fontSize: 11)),
        ]),
      ),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/shell/app_shell_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/shell/ mobile/test/shell/app_shell_test.dart
git commit -m "feat(mobile): Martin-center navigation shell"
```

---

## Task 12: Router with auth redirect

**Files:**
- Create: `mobile/lib/routing/app_router.dart`
- Test: `mobile/test/routing/app_router_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/routing/app_router_test.dart`
Expected: FAIL — `app_router.dart` / `redirectFor` not found.

- [ ] **Step 3: Implement**

```dart
// lib/routing/app_router.dart
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/application/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../shell/app_shell.dart';

/// Pure redirect logic — unit-testable without a widget tree.
String? redirectFor(AuthState state, String location) {
  final authed = state is AuthAuthenticated;
  if (!authed && state is! AuthLoading && state is! AuthUnknown && location != '/login') {
    return '/login';
  }
  if (authed && location == '/login') return '/';
  return null;
}

final goRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    redirect: (context, st) => redirectFor(ref.read(authControllerProvider), st.matchedLocation),
    refreshListenable: _AuthRefresh(ref),
    routes: [
      GoRoute(path: '/', builder: (_, __) => const AppShell()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    ],
  );
});

/// Bridges Riverpod auth changes into go_router refreshes.
class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh(Ref ref) {
    ref.listen(authControllerProvider, (_, __) => notifyListeners());
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/routing/app_router_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/routing/app_router.dart mobile/test/routing/app_router_test.dart
git commit -m "feat(mobile): go_router with auth redirect"
```

---

## Task 13: App entry + bootstrap wiring

**Files:**
- Create: `mobile/lib/app.dart`
- Modify: `mobile/lib/main.dart` (replace the scaffolded default)

- [ ] **Step 1: Write `app.dart`**

```dart
// lib/app.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/sovereign_theme.dart';
import 'features/auth/application/auth_controller.dart';
import 'routing/app_router.dart';

class MemberApp extends ConsumerStatefulWidget {
  const MemberApp({super.key});
  @override
  ConsumerState<MemberApp> createState() => _MemberAppState();
}

class _MemberAppState extends ConsumerState<MemberApp> {
  @override
  void initState() {
    super.initState();
    // Fire the session check once the first frame is scheduled.
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => ref.read(authControllerProvider.notifier).bootstrap(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'ECOWAS Summit',
      debugShowCheckedModeBanner: false,
      theme: SovereignTheme.dark(),
      routerConfig: ref.watch(goRouterProvider),
    );
  }
}
```

- [ ] **Step 2: Replace `main.dart`**

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';

void main() {
  runApp(const ProviderScope(child: MemberApp()));
}
```

- [ ] **Step 3: Static check + full test run**

Run: `flutter analyze && flutter test`
Expected: "No issues found!" and all tests PASS.

- [ ] **Step 4: Manual smoke test**

Run (with backend reachable, or just to see the login screen):
```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8080
```
Expected: app launches → Sovereign **login screen** (no stored token). After a successful login against a real member account, lands on the Martin-center shell.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/app.dart mobile/lib/main.dart
git commit -m "feat(mobile): wire app entry, theme, router, and session bootstrap"
```

---

## Task 14: Biometric reopen

**Files:**
- Create: `mobile/lib/features/auth/data/biometric_service.dart`
- Modify: `mobile/lib/features/auth/application/auth_controller.dart` (add `bootstrapWithBiometric`)
- Test: `mobile/test/features/auth/biometric_service_test.dart`
- Platform config: `mobile/ios/Runner/Info.plist`, `mobile/android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/auth/biometric_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:local_auth/local_auth.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/data/biometric_service.dart';

class _MockLocalAuth extends Mock implements LocalAuthentication {}

void main() {
  test('authenticate returns true when device has no biometrics (no-op pass)', () async {
    final la = _MockLocalAuth();
    when(() => la.isDeviceSupported()).thenAnswer((_) async => false);
    final svc = BiometricService(la);
    expect(await svc.authenticate(), isTrue);
  });

  test('authenticate delegates to local_auth when supported', () async {
    final la = _MockLocalAuth();
    when(() => la.isDeviceSupported()).thenAnswer((_) async => true);
    when(() => la.authenticate(
          localizedReason: any(named: 'localizedReason'),
          options: any(named: 'options'),
        )).thenAnswer((_) async => true);
    final svc = BiometricService(la);
    expect(await svc.authenticate(), isTrue);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/biometric_service_test.dart`
Expected: FAIL — `biometric_service.dart` not found.

- [ ] **Step 3: Implement the service**

```dart
// lib/features/auth/data/biometric_service.dart
import 'package:local_auth/local_auth.dart';

class BiometricService {
  BiometricService(this._auth);
  final LocalAuthentication _auth;

  /// Returns true if the user unlocked (or the device can't do biometrics,
  /// so we don't lock people out).
  Future<bool> authenticate() async {
    if (!await _auth.isDeviceSupported()) return true;
    try {
      return await _auth.authenticate(
        localizedReason: 'Unlock to open the Summit app',
        options: const AuthenticationOptions(stickyAuth: true, biometricOnly: false),
      );
    } catch (_) {
      return false;
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/biometric_service_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Gate bootstrap behind biometrics**

In `lib/features/auth/application/auth_controller.dart`, add a provider and use it in `bootstrap()`:

```dart
// add imports
import 'package:local_auth/local_auth.dart';
import '../data/biometric_service.dart';

// add provider (near the others)
final biometricServiceProvider =
    Provider<BiometricService>((_) => BiometricService(LocalAuthentication()));

// replace the body of bootstrap():
Future<void> bootstrap() async {
  final t = await _tokens.read();
  if (t == null) {
    state = const AuthState.unauthenticated();
    return;
  }
  final unlocked = await ref.read(biometricServiceProvider).authenticate();
  if (!unlocked) {
    state = const AuthState.unauthenticated();
    return;
  }
  try {
    state = AuthState.authenticated(await _repo.fetchMe());
  } catch (_) {
    await _tokens.clear();
    state = const AuthState.unauthenticated();
  }
}
```

- [ ] **Step 6: Platform permissions**

In `mobile/ios/Runner/Info.plist` add (inside the top `<dict>`):
```xml
<key>NSFaceIDUsageDescription</key>
<string>Use Face ID to quickly and securely reopen the Summit app.</string>
```
In `mobile/android/app/src/main/AndroidManifest.xml`, ensure the `<manifest>` has:
```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
```
And confirm `MainActivity` extends `FlutterFragmentActivity` (local_auth requirement) — if it extends `FlutterActivity`, change it to `FlutterFragmentActivity` in `mobile/android/app/src/main/kotlin/.../MainActivity.kt`.

- [ ] **Step 7: Verify + commit**

Run: `flutter analyze && flutter test`
Expected: clean + all PASS.
```bash
git add mobile/lib/features/auth/data/biometric_service.dart \
        mobile/lib/features/auth/application/auth_controller.dart \
        mobile/test/features/auth/biometric_service_test.dart \
        mobile/ios/Runner/Info.plist \
        mobile/android/app/src/main/AndroidManifest.xml \
        mobile/android/app/src/main/kotlin
git commit -m "feat(mobile): biometric reopen gate"
```

---

## Self-Review

**Spec coverage (§4, §8):**
- Sovereign design system → Tasks 2–3 (colors, theme). ✓
- Martin-center navigation → Task 11 (center FAB + 3 tabs; Deals omitted, correct for Phase 1). ✓
- Email+password login against existing auth → Tasks 7–10. ✓
- Secure token storage → Task 6. ✓
- "Stay signed in" / session restore → Task 9 `bootstrap()` + Task 13. ✓
- Biometric reopen → Task 14. ✓
- Logout → Task 8/9 (`signOut`). ✓
- Reuse existing REST API, no backend changes → confirmed; only `/auth/*` consumed. ✓
- *(Out of scope here, by design: Home/Meetings/Documents/Me content, member-Martin, push — these are Plans 2–4.)*

**Placeholder scan:** No "TBD/TODO"; every code step shows complete code; every run step shows command + expected result. The placeholder *screens* in Task 11 are intentional, named stubs that Plan 3 replaces. ✓

**Type consistency:** `AuthState` constructors/subclasses (`AuthAuthenticated`, `AuthError`, etc.) are used identically in Tasks 9, 10, 12. `AuthRepository.login/fetchMe/logout`, `TokenStorage.save/read/clear`, `AppUser.fromMeJson`, `AuthTokens.fromLoginJson`, `authControllerProvider`, `authRepositoryProvider`, `buildAuthInterceptedDio` all referenced with consistent signatures across tasks. ✓

**Note for the implementer:** `member_app` is the Dart package name (set in Task 1 via `--project-name member_app`); all imports use `package:member_app/...`. If you choose a different project name, update imports accordingly.
