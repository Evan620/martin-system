// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'app.dart';
import 'features/profile/data/notification_prefs.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Resolve SharedPreferences once at startup and inject it, so the local
  // notification-preference toggles (Me screen) have a real backing store.
  final prefs = await SharedPreferences.getInstance();
  runApp(
    ProviderScope(
      overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
      child: const MemberApp(),
    ),
  );
}
