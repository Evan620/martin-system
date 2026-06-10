// lib/core/motion/cascade_in.dart
import 'package:flutter/material.dart';
import 'motion.dart';

/// Fade + 14px rise entrance, staggered by [index]. Plays once on first build
/// (a screen that rebuilds — e.g. on a state change — should pass replay:false
/// or rebuild the list with the same keys so this does not re-animate).
class CascadeIn extends StatefulWidget {
  const CascadeIn({super.key, required this.index, required this.child, this.replay = false});
  final int index;
  final Widget child;
  final bool replay;

  static Duration staggerDelayFor(int index) {
    final i = index < 0 ? 0 : (index > Motion.maxStagger ? Motion.maxStagger : index);
    return Motion.stagger * i;
  }

  @override
  State<CascadeIn> createState() => _CascadeInState();
}

class _CascadeInState extends State<CascadeIn> with SingleTickerProviderStateMixin {
  // The controller spans the stagger delay PLUS the entrance, so the fade/slide
  // are gated to begin at the staggered start via an Interval. Driving the
  // delay through the controller (rather than a bare Future.delayed timer) keeps
  // a frame scheduled, so the entrance settles deterministically under tests.
  late final Duration _delay = CascadeIn.staggerDelayFor(widget.index);
  late final AnimationController _c =
      AnimationController(vsync: this, duration: _delay + Motion.gentle);
  late final double _start =
      _delay.inMicroseconds / (_delay + Motion.gentle).inMicroseconds;
  late final Animation<double> _fade = CurvedAnimation(
    parent: _c,
    curve: Interval(_start, 1, curve: Motion.curve),
  );
  late final Animation<Offset> _slide =
      Tween(begin: const Offset(0, 0.06), end: Offset.zero).animate(_fade);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _c.forward();
    });
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) =>
      FadeTransition(opacity: _fade, child: SlideTransition(position: _slide, child: widget.child));
}
