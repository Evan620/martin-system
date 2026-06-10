// lib/core/motion/pressable.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'motion.dart';

/// Tappable wrapper: scales to 0.97 while pressed + light haptic on tap.
/// Use on cards/chips/pills (NOT the nav pills or ✦ FAB — those are locked).
class PressableScale extends StatefulWidget {
  const PressableScale({super.key, required this.child, required this.onTap, this.haptic = true, this.pressedScale = 0.97});
  final Widget child;
  final VoidCallback onTap;
  final bool haptic;
  final double pressedScale;

  @override
  State<PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<PressableScale> {
  bool _down = false;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _down = true),
      onTapCancel: () => setState(() => _down = false),
      onTapUp: (_) => setState(() => _down = false),
      onTap: () { if (widget.haptic) HapticFeedback.lightImpact(); widget.onTap(); },
      child: AnimatedScale(
        scale: _down ? widget.pressedScale : 1.0,
        duration: Motion.fast,
        curve: Motion.curve,
        child: widget.child,
      ),
    );
  }
}
