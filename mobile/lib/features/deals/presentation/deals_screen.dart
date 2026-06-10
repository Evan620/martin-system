// lib/features/deals/presentation/deals_screen.dart
//
// Deal Room — native dashboard (v2) list of the member's TWG projects, wired
// to live data (replaces the Phase-2 placeholder).
//
// Layout (top -> bottom), per the Deal Room design spec:
//   - `HeaderCard` + compact `AppHeader`: TWG context label over "Deal Room".
//   - 3 `StatTile`s, all derived from the loaded list: Projects (count) ·
//     Summit-ready (count at SUMMIT_READY or beyond) · Following (count
//     followed by me).
//   - 44px stage filter chips: All + one per `DealStage` bucket present in
//     the data (mirrors the Documents filter chips; selected state stays the
//     subtle navy+gold-ring treatment — this screen has NO filled-yellow
//     action; Follow lives in the detail).
//   - one `RowGroup` of project rows: leading icon container, project name,
//     "sector · value · score/100" meta (missing parts omitted), trailing
//     compact stage chip whose tint advances muted ivory → gold with funnel
//     progress. Tap pushes /deals/:id.
//
// Loads via dealsControllerProvider.load() (post-frame), renders by sealed
// state (loading -> tile+row skeletons / error / empty / data) inside an
// AnimatedSwitcher; pull-to-refresh re-runs load().
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/glass/glass.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/motion/motion.dart';
import '../../../core/motion/pressable.dart';
import '../../../core/motion/skeleton.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/app_header.dart';
import '../../../core/ui/header_card.dart';
import '../../../core/ui/list_row.dart';
import '../../../core/ui/stat_tile.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/deals_controller.dart';
import '../data/deals_models.dart';

/// The Deal Room screen: header card, stat tiles, stage filter chips and one
/// row group of the member's TWG projects.
class DealsScreen extends ConsumerStatefulWidget {
  const DealsScreen({super.key});

  @override
  ConsumerState<DealsScreen> createState() => _DealsScreenState();
}

class _DealsScreenState extends ConsumerState<DealsScreen> {
  /// Selected stage filter (null = All).
  DealStage? _stage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(dealsControllerProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(dealsControllerProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          color: SovereignColors.gold,
          backgroundColor: SovereignColors.navyRaised,
          onRefresh: () => ref.read(dealsControllerProvider.notifier).load(),
          child: AnimatedSwitcher(
            duration: Motion.base,
            child: switch (state) {
              DealsLoading() => const _LoadingView(key: ValueKey('loading')),
              DealsError(:final message) => _ErrorView(
                  key: const ValueKey('error'),
                  message: message,
                  onRetry: () =>
                      ref.read(dealsControllerProvider.notifier).load(),
                ),
              DealsData(:final projects) when projects.isEmpty =>
                const _EmptyView(key: ValueKey('empty')),
              DealsData(:final projects) => _DataView(
                  key: const ValueKey('data'),
                  projects: projects,
                  stage: _stage,
                  twgLabel: _headerSubtitle(ref),
                  onStageChanged: (s) => setState(() => _stage = s),
                  onOpen: (p) => context.push('/deals/${p.id}'),
                ),
            },
          ),
        ),
      ),
    );
  }
}

/// The member's TWG label, used as the header context line (one TWG → its
/// name, several → a compact multi-TWG label; falls back to a neutral label
/// when unknown).
String _headerSubtitle(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  if (auth is AuthAuthenticated) {
    final label = auth.user.twgs.headerLabel;
    if (label != null) return label;
  }
  return 'Your projects';
}

/// "energy_infrastructure" → "Energy infrastructure" (null/blank → null).
String? _sectorLabel(String? raw) {
  final s = (raw ?? '').trim();
  if (s.isEmpty) return null;
  final words = s.replaceAll('_', ' ').toLowerCase();
  return words[0].toUpperCase() + words.substring(1);
}

/// The row meta line: "sector · value · score/100", omitting missing parts
/// (null when nothing is known so the row stays title-only).
String? _projectMeta(DealProject p) {
  final parts = <String>[
    ?_sectorLabel(p.sector),
    if (p.value != null)
      NumberFormat.compactCurrency(symbol: r'$').format(p.value),
    if (p.afcenScore != null) '${p.afcenScore!.round()}/100',
  ];
  return parts.isEmpty ? null : parts.join(' · ');
}

/// Loaded state: header card, the 3 stat tiles, stage filter chips, then the
/// filtered project rows in one RowGroup.
class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.projects,
    required this.stage,
    required this.twgLabel,
    required this.onStageChanged,
    required this.onOpen,
  });

  final List<DealProject> projects;
  final DealStage? stage;
  final String twgLabel;
  final ValueChanged<DealStage?> onStageChanged;
  final ValueChanged<DealProject> onOpen;

  @override
  Widget build(BuildContext context) {
    // Distinct stage buckets present in the data, in funnel order, for the
    // filter chips; then the rows the selected chip leaves visible.
    final present =
        DealStage.values.where((s) => projects.any((p) => p.stage == s)).toList();
    final shown =
        stage == null ? projects : projects.where((p) => p.stage == stage).toList();

    final summitReady = projects.where((p) => p.isSummitReadyPlus).length;
    final following = projects.where((p) => p.isFollowing).length;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CascadeIn(
            index: 0,
            child: HeaderCard(
              child: AppHeader(title: 'Deal Room', context_: twgLabel),
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 1,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: StatTile(
                    label: 'Projects',
                    value: '${projects.length}',
                    sub: 'in your TWG',
                  ),
                ),
                const SizedBox(width: Insets.sm),
                Expanded(
                  child: StatTile(
                    label: 'Summit-ready',
                    value: '$summitReady',
                    sub: 'or beyond',
                  ),
                ),
                const SizedBox(width: Insets.sm),
                Expanded(
                  child: StatTile(
                    label: 'Following',
                    value: '$following',
                    sub: 'by you',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 2,
            child: _FilterChips(
              present: present,
              selected: stage,
              onChanged: onStageChanged,
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 3,
            child: RowGroup(children: [
              if (shown.isEmpty)
                const ListRow(
                  icon: Icons.filter_alt_off_rounded,
                  title: 'No projects in this stage',
                  meta: 'Pick another stage chip above.',
                )
              else
                for (final p in shown)
                  ListRow(
                    icon: Icons.handshake_outlined,
                    title: p.name,
                    meta: _projectMeta(p),
                    trailing: _StageChip(stage: p.stage),
                    onTap: () => onOpen(p),
                  ),
            ]),
          ),
        ],
      ),
    );
  }
}

/// Horizontal row of stage filter chips: an "All" chip plus one chip per
/// distinct [DealStage] bucket present in the data. 44px tall, segmented-style
/// fills — this screen keeps every chip subtle (no filled yellow).
class _FilterChips extends StatelessWidget {
  const _FilterChips({
    required this.present,
    required this.selected,
    required this.onChanged,
  });

  final List<DealStage> present;
  final DealStage? selected;
  final ValueChanged<DealStage?> onChanged;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _Chip(
            label: 'All',
            selected: selected == null,
            onTap: () => onChanged(null),
          ),
          for (final s in present) ...[
            const SizedBox(width: Insets.sm),
            _Chip(
              label: s.label,
              selected: selected == s,
              onTap: () => onChanged(s),
            ),
          ],
        ],
      ),
    );
  }
}

/// One filter chip on the segmented-control language: selected = raised navy
/// with a gold ring, unselected = recessed ivory track. 44px tap target.
class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return PressableScale(
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 44),
        padding: const EdgeInsets.symmetric(horizontal: Insets.lg),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected
              ? SovereignColors.navyRaised
              : SovereignColors.ivory.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected
                ? SovereignColors.gold.withValues(alpha: 0.45)
                : SovereignColors.ivory.withValues(alpha: 0.08),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: SovereignColors.ivory.withValues(
              alpha: selected
                  ? SovereignColors.alphaHigh
                  : SovereignColors.alphaMid,
            ),
          ),
        ),
      ),
    );
  }
}

/// The row's trailing compact stage chip. Its tint lerps muted ivory → gold as
/// the bucket advances through the funnel, so late-stage projects read warmer
/// without ever becoming a filled-yellow action.
class _StageChip extends StatelessWidget {
  const _StageChip({required this.stage});

  final DealStage stage;

  @override
  Widget build(BuildContext context) {
    final t = stage.index / (DealStage.values.length - 1);
    final tint = Color.lerp(SovereignColors.ivory, SovereignColors.gold, t)!;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Insets.sm, vertical: 3),
      decoration: BoxDecoration(
        color: tint.withValues(alpha: 0.07 + 0.07 * t),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tint.withValues(alpha: 0.22 + 0.23 * t)),
      ),
      child: Text(
        stage.label,
        style: TextStyle(
          fontFamily: 'Inter',
          fontSize: 10.5,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.2,
          color: tint.withValues(alpha: 0.65 + 0.30 * t),
        ),
      ),
    );
  }
}

/// Loading — header/tile/chip/row-shaped skeletons (no spinner), cross-fading
/// to content.
class _LoadingView extends StatelessWidget {
  const _LoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          SkeletonBlock(width: 90, height: 12),
          SizedBox(height: Insets.sm),
          SkeletonBlock(width: 170, height: 22),
          SizedBox(height: Insets.lg),
          Row(children: [
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
          ]),
          SizedBox(height: Insets.lg),
          SkeletonBlock(width: 220, height: 36, radius: 12),
          SizedBox(height: Insets.lg),
          RowGroup(children: [
            SkeletonRow(),
            SkeletonRow(),
            SkeletonRow(),
            SkeletonRow(),
          ]),
        ],
      ),
    );
  }
}

/// Error state: a glass message + a Retry button.
class _ErrorView extends StatelessWidget {
  const _ErrorView({super.key, required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(Insets.xxl),
      children: [
        const SizedBox(height: 80),
        GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, color: SovereignColors.gold, size: 28),
              const SizedBox(height: Insets.md),
              Text(
                message,
                textAlign: TextAlign.center,
                style: SovereignType.body.copyWith(
                  color: SovereignColors.ivory
                      .withValues(alpha: SovereignColors.alphaHigh),
                ),
              ),
              const SizedBox(height: Insets.md),
              TextButton(
                onPressed: onRetry,
                child: Text(
                  'Retry',
                  style: SovereignType.caption.copyWith(
                    color: SovereignColors.gold,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Full-screen empty state (no projects linked to the member's TWGs at all).
class _EmptyView extends StatelessWidget {
  const _EmptyView({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(Insets.xxl),
      children: [
        const SizedBox(height: 80),
        GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.handshake_outlined,
                  color: SovereignColors.gold, size: 30),
              const SizedBox(height: Insets.md),
              const Text(
                'No projects yet',
                textAlign: TextAlign.center,
                style: SovereignType.section,
              ),
              const SizedBox(height: Insets.xs),
              Text(
                "When a project is linked to your TWG, it'll appear here.",
                textAlign: TextAlign.center,
                style: SovereignType.secondary.copyWith(
                  color: SovereignColors.ivory
                      .withValues(alpha: SovereignColors.alphaMid),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
