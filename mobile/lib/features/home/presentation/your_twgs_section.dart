// lib/features/home/presentation/your_twgs_section.dart
//
// The "Your TWGs" section on Home. Reads AppUser.twgs (already in auth state —
// no fetch). One TWG -> a single card under a "Your TWG" label; 2+ -> a list
// under "Your TWGs". Each card pushes /home/workspace/<id>. Hidden entirely
// when the member is in no TWG.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';

class YourTwgsSection extends ConsumerWidget {
  const YourTwgsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final twgs = auth is AuthAuthenticated ? auth.user.twgs : const <Twg>[];
    if (twgs.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(twgs.length == 1 ? 'YOUR TWG' : 'YOUR TWGS',
              style: const TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 10,
                  letterSpacing: 2.6,
                  fontWeight: FontWeight.w600)),
        ),
        for (var i = 0; i < twgs.length; i++) ...[
          if (i > 0) const SizedBox(height: 10),
          _TwgCard(twg: twgs[i]),
        ],
      ],
    );
  }
}

class _TwgCard extends StatelessWidget {
  const _TwgCard({required this.twg});
  final Twg twg;
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      onTap: () => context.push('/home/workspace/${twg.id}'),
      borderRadius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(children: [
        Expanded(
          child: Text(twg.name,
              style: const TextStyle(
                  color: SovereignColors.ivory, fontSize: 15, fontWeight: FontWeight.w700)),
        ),
        Text('Open workspace',
            style: TextStyle(
                color: SovereignColors.gold.withValues(alpha: 0.85), fontSize: 12)),
        const SizedBox(width: 6),
        Icon(Icons.chevron_right, color: SovereignColors.gold.withValues(alpha: 0.85), size: 18),
      ]),
    );
  }
}
