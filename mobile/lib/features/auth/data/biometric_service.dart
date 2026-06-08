// lib/features/auth/data/biometric_service.dart
import 'package:local_auth/local_auth.dart';

class BiometricService {
  BiometricService(this._auth);
  final LocalAuthentication _auth;

  /// Returns true if the user unlocked (or the device can't do biometrics,
  /// so we don't lock people out).
  Future<bool> authenticate() async {
    if (!await _auth.isDeviceSupported()) return true;
    try {
      return await _auth.authenticate(
        localizedReason: 'Unlock to open the Summit app',
        persistAcrossBackgrounding: true,
        biometricOnly: false,
      );
    } catch (_) {
      return false;
    }
  }
}
