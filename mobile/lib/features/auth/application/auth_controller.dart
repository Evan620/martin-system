// lib/features/auth/application/auth_controller.dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import '../../../core/network/api_client.dart';
import '../data/auth_models.dart';
import '../data/auth_repository.dart';
import '../data/biometric_service.dart';
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

final biometricServiceProvider =
    Provider<BiometricService>((_) => BiometricService(LocalAuthentication()));

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
