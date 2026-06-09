// lib/features/home/presentation/martin_chat_placeholder.dart
//
// Martin chat — Phase 4b placeholder. The real streaming, hands-free member
// agent chat replaces this in sub-project 4b. For now: a full-screen Sovereign
// backdrop, a glass back button, a ✦ Martin header, and a centred glass card
// announcing what's coming.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';

/// Coming-soon placeholder for the Martin member-agent chat (replaced in 4b).
class MartinChatPlaceholder extends StatelessWidget {
  const MartinChatPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          const _AmbientBackground(),
          SafeArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header row: glass back button + ✦ Martin serif title.
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 20, 0),
                  child: Row(
                    children: [
                      GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => context.pop(),
                        child: const GlassSurface(
                          borderRadius: 14,
                          padding: EdgeInsets.all(10),
                          child: Icon(
                            Icons.arrow_back_rounded,
                            size: 20,
                            color: SovereignColors.ivory,
                          ),
                        ),
                      ),
                      const SizedBox(width: 14),
                      const Text(
                        '✦ Martin',
                        style: TextStyle(
                          color: SovereignColors.gold,
                          fontFamily: 'Georgia',
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.3,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: GlassCard(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.auto_awesome,
                              color: SovereignColors.gold,
                              size: 28,
                            ),
                            const SizedBox(height: 14),
                            Text(
                              'Martin is coming in the next update — ask about '
                              'your meetings, documents and tasks, hands-free.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: SovereignColors.ivory
                                    .withValues(alpha: 0.85),
                                fontSize: 15.5,
                                height: 1.42,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Atmospheric navy field with a faint gold glow (mirrors the Home backdrop).
class _AmbientBackground extends StatelessWidget {
  const _AmbientBackground();

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              SovereignColors.navy,
              SovereignColors.navyDeep,
            ],
          ),
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(-0.6, -1.0),
              radius: 1.1,
              colors: [
                SovereignColors.gold.withValues(alpha: 0.10),
                SovereignColors.gold.withValues(alpha: 0.0),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
