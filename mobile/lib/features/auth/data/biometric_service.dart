// lib/features/auth/data/biometric_service.dart
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:local_auth/local_auth.dart';

class BiometricService {
  BiometricService(this._auth);
  final LocalAuthentication _auth;

  /// Returns true if the user unlocked (or the device can't do biometrics,
  /// so we don't lock people out).
  Future<bool> authenticate() async {
    // No biometric hardware on web/desktop — local_auth has no implementation
    // there (calling it throws MissingPluginException), so never lock out.
    if (kIsWeb) return true;
    bool supported;
    try {
      supported = await _auth.isDeviceSupported();
    } catch (_) {
      // Plugin/platform unavailable → don't lock the user out.
      return true;
    }
    if (!supported) return true;
    try {
      return await _auth.authenticate(
        localizedReason: 'Unlock to open the Summit app',
        persistAcrossBackgrounding: true,
        biometricOnly: false,
      );
    } catch (_) {
      // A real auth failure/cancel stays locked (security preserved).
      return false;
    }
  }
}
