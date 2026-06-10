// lib/core/motion/motion.dart
import 'package:flutter/animation.dart';

abstract final class Motion {
  static const fast = Duration(milliseconds: 150);
  static const base = Duration(milliseconds: 250);
  static const gentle = Duration(milliseconds: 400);
  static const stagger = Duration(milliseconds: 70); // per-index entrance delay
  static const Curve curve = Curves.easeOutCubic;
  static const Curve emphasis = Curves.easeOutBack;
  static const int maxStagger = 8; // items past this share the last delay
}
