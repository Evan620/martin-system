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
