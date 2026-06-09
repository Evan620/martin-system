// lib/routing/app_router.dart
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/application/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/deals/presentation/deals_screen.dart';
import '../features/documents/presentation/documents_screen.dart';
import '../features/documents/presentation/pdf_viewer_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/home/presentation/martin_chat_placeholder.dart';
import '../features/meetings/presentation/meetings_screen.dart';
import '../features/meetings/presentation/meeting_detail_screen.dart';
import '../features/profile/presentation/me_screen.dart';
import '../shell/app_shell.dart';
import 'sovereign_page.dart';

/// Pure redirect logic — unit-testable without a widget tree.
String? redirectFor(AuthState state, String location) {
  final authed = state is AuthAuthenticated;
  if (!authed && state is! AuthLoading && state is! AuthUnknown && location != '/login') {
    return '/login';
  }
  if (authed && location == '/login') return '/home';
  return null;
}

final goRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/home',
    redirect: (context, st) => redirectFor(ref.read(authControllerProvider), st.matchedLocation),
    refreshListenable: _AuthRefresh(ref),
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      // Martin chat — a top-level pushed route (NOT a shell branch), so it
      // covers the nav. Reached via the floating ✦ Martin FAB (context.push).
      GoRoute(
        path: '/martin',
        pageBuilder: (context, st) => sovereignPage(child: const MartinChatPlaceholder()),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => AppShell(navigationShell: navigationShell),
        branches: [
          // 0 Meetings (with nested detail)
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/meetings',
              builder: (_, __) => const MeetingsScreen(),
              routes: [
                GoRoute(
                  path: ':id',
                  pageBuilder: (context, st) =>
                      sovereignPage(child: MeetingDetailScreen(meetingId: st.pathParameters['id']!)),
                ),
              ],
            ),
          ]),
          // 1 Documents (with nested in-app PDF viewer)
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/documents',
              builder: (_, __) => const DocumentsScreen(),
              routes: [
                GoRoute(
                  path: ':id/pdf',
                  pageBuilder: (context, st) => sovereignPage(
                    child: PdfViewerScreen(
                      documentId: st.pathParameters['id']!,
                      title: st.uri.queryParameters['name'] ?? 'Document',
                    ),
                  ),
                ),
              ],
            ),
          ]),
          // 2 Home (the raised centre)
          StatefulShellBranch(routes: [GoRoute(path: '/home', builder: (_, __) => const HomeScreen())]),
          // 3 Deals (Phase 2)
          StatefulShellBranch(routes: [GoRoute(path: '/deals', builder: (_, __) => const DealsScreen())]),
          // 4 Me
          StatefulShellBranch(routes: [GoRoute(path: '/me', builder: (_, __) => const MeScreen())]),
        ],
      ),
    ],
  );
});

/// Bridges Riverpod auth changes into go_router refreshes.
class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh(Ref ref) {
    ref.listen(authControllerProvider, (_, __) => notifyListeners());
  }
}
