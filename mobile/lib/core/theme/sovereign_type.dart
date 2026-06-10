// lib/core/theme/sovereign_type.dart
import 'package:flutter/widgets.dart';
import 'sovereign_colors.dart';

/// The ONE type scale. No screen should declare a TextStyle for anything this
/// covers — use these (or .copyWith on these for one-off color/weight tweaks).
abstract final class SovereignType {
  static const _serif = 'Fraunces';
  static const _sans = 'Inter';
  static const _ivory = SovereignColors.ivory;

  static const display = TextStyle(fontFamily: _serif, fontSize: 34, fontWeight: FontWeight.w600, height: 1.06, color: _ivory);
  static const title = TextStyle(fontFamily: _serif, fontSize: 26, fontWeight: FontWeight.w500, height: 1.1, color: _ivory);
  static const heading = TextStyle(fontFamily: _serif, fontSize: 20, fontWeight: FontWeight.w500, height: 1.15, color: _ivory);
  static const section = TextStyle(fontFamily: _sans, fontSize: 16, fontWeight: FontWeight.w600, height: 1.25, color: _ivory);
  static const body = TextStyle(fontFamily: _sans, fontSize: 14.5, fontWeight: FontWeight.w400, height: 1.42, color: _ivory);
  static const secondary = TextStyle(fontFamily: _sans, fontSize: 13, fontWeight: FontWeight.w400, height: 1.4, color: _ivory);
  static const caption = TextStyle(fontFamily: _sans, fontSize: 12, fontWeight: FontWeight.w500, height: 1.3, color: _ivory);
  static const eyebrow = TextStyle(fontFamily: _sans, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 3.0, color: SovereignColors.gold);
}

/// Tiny holder so `context.stext.display` reads ergonomically, mirroring
/// `Theme.of(context).textTheme`. (`SovereignType` is non-instantiable.)
class SovereignTextScale {
  const SovereignTextScale();
  TextStyle get display => SovereignType.display;
  TextStyle get title => SovereignType.title;
  TextStyle get heading => SovereignType.heading;
  TextStyle get section => SovereignType.section;
  TextStyle get body => SovereignType.body;
  TextStyle get secondary => SovereignType.secondary;
  TextStyle get caption => SovereignType.caption;
  TextStyle get eyebrow => SovereignType.eyebrow;
}

/// `context.stext.display` ergonomic access (mirrors Theme.of(context).textTheme).
extension SovereignTextX on BuildContext {
  SovereignTextScale get stext => const SovereignTextScale();
}
