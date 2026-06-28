// lib/core/config/app_config.dart
/// Build-time config. Override with:
///   flutter run --dart-define=API_BASE_URL=https://your-host
abstract final class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    // Default to the production martin-system backend so release/beta APKs
    // never fall back to localhost (Bug Queue #9). Override for local dev with
    //   flutter run --dart-define=API_BASE_URL=http://localhost:8080
    defaultValue: 'https://martin-system-production-bb2f.up.railway.app',
  );

  static String get apiV1 => '$apiBaseUrl/api/v1';
}
