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
              Text('WAIIS',
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
