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
          persistAcrossBackgrounding: any(named: 'persistAcrossBackgrounding'),
          biometricOnly: any(named: 'biometricOnly'),
        )).thenAnswer((_) async => true);
    final svc = BiometricService(la);
    expect(await svc.authenticate(), isTrue);
  });
}
