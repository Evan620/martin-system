// lib/core/motion/skeleton.dart
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';
import '../glass/glass.dart';

/// A shimmering placeholder block. Compose into content-shaped skeletons that
/// replace CircularProgressIndicator in screen bodies.
class SkeletonBlock extends StatefulWidget {
  const SkeletonBlock({super.key, this.width, this.height = 12, this.radius = 6});
  final double? width;
  final double height;
  final double radius;
  @override
  State<SkeletonBlock> createState() => _SkeletonBlockState();
}

class _SkeletonBlockState extends State<SkeletonBlock> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1300))..repeat();
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final t = _c.value;
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(-1 - 2 * t, 0),
              end: Alignment(1 - 2 * t, 0),
              colors: [
                SovereignColors.ivory.withValues(alpha: 0.06),
                SovereignColors.ivory.withValues(alpha: 0.16),
                SovereignColors.ivory.withValues(alpha: 0.06),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// A glass card filled with skeleton lines — drop-in for a loading list row.
class SkeletonCard extends StatelessWidget {
  const SkeletonCard({super.key, this.lines = 2});
  final int lines;
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const SkeletonBlock(width: 140, height: 14),
        const SizedBox(height: 10),
        for (var i = 0; i < lines; i++) ...[
          if (i > 0) const SizedBox(height: 8),
          SkeletonBlock(width: i.isEven ? double.infinity : 200, height: 11),
        ],
      ]),
    );
  }
}

/// N skeleton cards with spacing — a loading list.
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.count = 4});
  final int count;
  @override
  Widget build(BuildContext context) => Column(children: [
        for (var i = 0; i < count; i++) ...[ if (i > 0) const SizedBox(height: 12), const SkeletonCard() ],
      ]);
}
