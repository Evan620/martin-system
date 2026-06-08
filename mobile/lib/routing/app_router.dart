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
