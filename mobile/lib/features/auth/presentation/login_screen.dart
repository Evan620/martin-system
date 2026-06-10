// lib/features/auth/presentation/login_screen.dart
//
// Login — the ONE screen where the Fraunces serif lives (the Welcome moment).
// Everything else is Inter via the type tokens. Sign in is the screen's single
// filled-yellow action (in-button spinner while authenticating); fields, keys
// and controller wiring unchanged; the column cascades in; errors stay inline.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
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
          padding: const EdgeInsets.symmetric(horizontal: Insets.xxl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const CascadeIn(
                index: 0,
                child: Text('WAIIS', style: SovereignType.eyebrow),
              ),
              const SizedBox(height: Insets.sm),
              // The one Fraunces serif moment in the app.
              const CascadeIn(
                index: 1,
                child: Text('Welcome', style: SovereignType.display),
              ),
              const SizedBox(height: Insets.section),
              CascadeIn(
                index: 2,
                child: TextField(
                  key: const Key('email'),
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
              ),
              const SizedBox(height: Insets.md),
              CascadeIn(
                index: 3,
                child: TextField(
                  key: const Key('password'),
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Password'),
                ),
              ),
              if (state is AuthError) ...[
                const SizedBox(height: Insets.md),
                Text(
                  state.message,
                  style: SovereignType.secondary
                      .copyWith(color: SovereignColors.danger),
                ),
              ],
              const SizedBox(height: Insets.xxl),
              CascadeIn(
                index: 4,
                child: FilledButton(
                  key: const Key('signin'),
                  // Stays gold while the in-button spinner runs.
                  style: FilledButton.styleFrom(
                    disabledBackgroundColor:
                        SovereignColors.gold.withValues(alpha: 0.45),
                  ),
                  onPressed: loading
                      ? null
                      : () => ref
                          .read(authControllerProvider.notifier)
                          .signIn(_email.text.trim(), _password.text),
                  child: loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: SovereignColors.navy))
                      : const Text('Sign in'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
