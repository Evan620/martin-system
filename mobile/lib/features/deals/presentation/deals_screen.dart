// lib/features/deals/presentation/deals_screen.dart
//
// Deal Room (Phase 2 placeholder) — the future home for following a pillar's
// projects and their readiness scores. For now it sits on the Sovereign ambient
// navy+gold backdrop with a serif title, a gold "PHASE 2" eyebrow, and a single
// glass card explaining what's coming. Reuses the Sovereign glass system.
import 'package:flutter/material.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';

/// The Deals tab — a Phase 2 placeholder until the real Deal Room ships.
class DealsScreen extends StatelessWidget {
  const DealsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          const _AmbientBackground(),
          SafeArea(
            bottom: false,
            child: SingleChildScrollView(
              // Bottom padding so the floating nav clears the content.
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'PHASE 2',
                    style: TextStyle(
                      color: SovereignColors.gold.withValues(alpha: 0.85),
                      fontSize: 11,
                      letterSpacing: 4,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Deal Room',
                    style: (Theme.of(context).textTheme.displaySmall ??
                            const TextStyle())
                        .copyWith(
                      color: SovereignColors.ivory,
                      fontFamily: 'Georgia',
                      fontSize: 38,
                      height: 1.08,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 24),
                  GlassCard(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.handshake_outlined,
                          color: SovereignColors.gold,
                          size: 22,
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            "Follow your pillar's projects and readiness "
                            'scores here — arriving in Phase 2.',
                            style: TextStyle(
                              color: SovereignColors.ivory.withValues(alpha: 0.85),
                              fontSize: 15.5,
                              height: 1.42,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Atmospheric navy field with a faint gold glow (mirrors the Home backdrop) so
/// the Sovereign look stays consistent across tabs.
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
