// lib/core/ui/segmented.dart
import 'package:flutter/material.dart';
import '../motion/motion.dart';
import '../theme/sovereign_colors.dart';

/// 2–4 option segmented control on a recessed track; 44px tall.
class SovereignSegmented extends StatelessWidget {
  const SovereignSegmented({super.key, required this.options, required this.selected, required this.onChanged});
  final List<String> options;
  final int selected;
  final ValueChanged<int> onChanged;
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 44,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: SovereignColors.ivory.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(children: [
        for (var i = 0; i < options.length; i++)
          Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => onChanged(i),
              child: AnimatedContainer(
                duration: Motion.fast,
                curve: Motion.curve,
                decoration: BoxDecoration(
                  color: i == selected ? SovereignColors.navyRaised : Colors.transparent,
                  borderRadius: BorderRadius.circular(9),
                  border: i == selected
                      ? Border.all(color: SovereignColors.ivory.withValues(alpha: 0.1))
                      : null,
                ),
                alignment: Alignment.center,
                child: Text(options[i], style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: SovereignColors.ivory.withValues(
                        alpha: i == selected ? SovereignColors.alphaHigh : SovereignColors.alphaMid))),
              ),
            ),
          ),
      ]),
    );
  }
}
