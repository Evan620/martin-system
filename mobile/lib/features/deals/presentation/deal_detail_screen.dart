// lib/features/deals/presentation/deal_detail_screen.dart
//
// Deal detail — the /deals/:id route shell. A minimal kit-consistent
// placeholder so the list's row navigation compiles and lands somewhere; M3
// replaces this with the full project detail (info chips, WAIIS score card,
// description, Follow / Ask-Martin / Share).
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/app_header.dart';
import '../../../core/ui/header_card.dart';

/// Placeholder detail view for one Deal Room project, addressed by [projectId].
class DealDetailScreen extends StatelessWidget {
  const DealDetailScreen({super.key, required this.projectId});

  final String projectId;

  void _back(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/deals');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
                  Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _BackButton(onTap: () => _back(context)),
              const SizedBox(height: Insets.lg),
              const HeaderCard(
                child: AppHeader(context_: 'Deal Room', title: 'Project'),
              ),
              const SizedBox(height: Insets.section),
              GlassCard(
                child: Text(
                  'The full project detail is on its way.',
                  style: SovereignType.body.copyWith(
                    color: SovereignColors.ivory
                        .withValues(alpha: SovereignColors.alphaHigh),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Glass back button (mirrors the meeting detail's treatment).
class _BackButton extends StatelessWidget {
  const _BackButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Back',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: const GlassSurface(
          borderRadius: 14,
          padding: EdgeInsets.all(10),
          child:
              Icon(Icons.arrow_back, size: 18, color: SovereignColors.ivory),
        ),
      ),
    );
  }
}
