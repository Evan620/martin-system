// test/core/config/app_config_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/core/config/app_config.dart';

void main() {
  test('apiBaseUrl defaults and ends without trailing slash', () {
    expect(AppConfig.apiBaseUrl, isNotEmpty);
    expect(AppConfig.apiBaseUrl.endsWith('/'), isFalse);
    expect(AppConfig.apiV1, '${AppConfig.apiBaseUrl}/api/v1');
  });
}
