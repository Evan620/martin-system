// lib/features/deals/presentation/deal_detail_screen.dart
//
// Deal detail — the /deals/:id full project view (mirrors the meeting detail's
// structure: back button above a HeaderCard, info chip row, card-in-card
// sections, pinned action bar at bottom: 92).
//
// Reads its project out of the already-loaded dealsController state by id; on
// a deep link (state never loaded) it triggers controller.load() post-frame —
// the controller design has no single-project fetch, so the list load IS the
// fallback. Renders by sealed state: loading -> content-shaped skeleton,
// error -> retry card, data -> the detail (or a "no longer available" card
// when the id isn't in the member's portfolio).
//
// Sections, top -> bottom:
//   * HeaderCard: project name (19 w800) + sector meta, trailing stage chip
//     (same muted-ivory -> gold funnel tint as the list rows).
//   * Info chips: value · location (only the fields the API actually has —
//     the member read carries no sponsor field today, so none is shown).
//   * Score: the big numeral leads with the AfCEN WAIIS score ("/100", header
//     "WAIIS score" — matching the list rows' meta) and falls back to
//     readiness ("/10", header "Readiness" — the backend scores readiness
//     0-10 per pipeline_schemas' Field(ge=0, le=10)); the other present
//     scores render as breakdown rows.
//   * Description in a card-in-card "About" section.
//
// Pinned actions: Follow is THE one filled-yellow action (optimistic toggle
// via dealsController.toggleFollow; errors roll back + toast), ✦ Ask Martin
// pushes the canonical /martin route seeded with the project question (and
// ?twg=<project.twgId> so multi-TWG members get a chat grounded in the
// project's own TWG), and Share hands the text brief to the OS share sheet
// via share_plus (supported on mobile, web and desktop; [shareInvoker] is the
// test seam).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../../core/glass/glass.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/motion/pressable.dart';
import '../../../core/motion/skeleton.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/header_card.dart';
import '../../../core/ui/section_header.dart';
import '../application/deals_controller.dart';
import '../data/deals_models.dart';
import '../data/deals_repository.dart';

/// Invokes the platform share sheet — a swap-out seam so widget tests can
/// observe the share without hitting the real plugin's platform channel.
@visibleForTesting
Future<void> Function(String text) shareInvoker =
    (text) => SharePlus.instance.share(ShareParams(text: text));

/// Full detail view for one Deal Room project, addressed by [projectId].
class DealDetailScreen extends ConsumerStatefulWidget {
  const DealDetailScreen({super.key, required this.projectId});

  final String projectId;

  @override
  ConsumerState<DealDetailScreen> createState() => _DealDetailScreenState();
}

class _DealDetailScreenState extends ConsumerState<DealDetailScreen> {
  @override
  void initState() {
    super.initState();
    // Deep-link fallback: when the list was never loaded, fetch it — that is
    // the controller's only read path, and this screen reads from its state.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (ref.read(dealsControllerProvider) is! DealsData) {
        ref.read(dealsControllerProvider.notifier).load();
      }
    });
  }

  void _back() {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/deals');
    }
  }

  Future<void> _toggleFollow(DealProject p) async {
    try {
      await ref.read(dealsControllerProvider.notifier).toggleFollow(p.id);
    } on DealsException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  void _askMartin(DealProject p) {
    final q = Uri.encodeQueryComponent('Tell me about the project ${p.name}');
    // Ground the chat in the project's own TWG when known — for multi-TWG
    // members the unscoped chat would otherwise default to their first TWG.
    final twg = p.twgId;
    context.push(twg == null ? '/martin?q=$q' : '/martin?q=$q&twg=$twg');
  }

  void _share(DealProject p) {
    shareInvoker(_briefText(p));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(dealsControllerProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: _AmbientBackdrop(
        child: switch (state) {
          DealsLoading() =>
            const SafeArea(bottom: false, child: _DetailSkeleton()),
          DealsError(:final message) => SafeArea(
              child: _DetailError(
                message: message,
                onRetry: () =>
                    ref.read(dealsControllerProvider.notifier).load(),
              ),
            ),
          DealsData(:final projects) => _bodyFor(projects),
        },
      ),
    );
  }

  Widget _bodyFor(List<DealProject> projects) {
    DealProject? project;
    for (final p in projects) {
      if (p.id == widget.projectId) {
        project = p;
        break;
      }
    }
    if (project == null) {
      // Stale deep link or a project that left the member's portfolio.
      return SafeArea(
        child: _DetailError(
          message: 'This project is no longer available.',
          onRetry: () => ref.read(dealsControllerProvider.notifier).load(),
        ),
      );
    }
    final p = project;
    return _DetailBody(
      project: p,
      onBack: _back,
      onFollow: () => _toggleFollow(p),
      onAskMartin: () => _askMartin(p),
      onShare: () => _share(p),
    );
  }
}

/// "energy_infrastructure" -> "Energy infrastructure" (null/blank -> null).
String? _sectorLabel(String? raw) {
  final s = (raw ?? '').trim();
  if (s.isEmpty) return null;
  final words = s.replaceAll('_', ' ').toLowerCase();
  return words[0].toUpperCase() + words.substring(1);
}

/// "7.5" / "72" — one decimal at most, no trailing ".0".
String _fmtScore(double v) {
  final r = (v * 10).round() / 10;
  return r % 1 == 0 ? r.toStringAsFixed(0) : r.toString();
}

String? _valueLabel(DealProject p) => p.value == null
    ? null
    : NumberFormat.compactCurrency(symbol: r'$').format(p.value);

/// The share text: "name · sector · stage · value · score" (missing parts
/// omitted), per the design spec.
String _briefText(DealProject p) => [
      p.name,
      ?_sectorLabel(p.sector),
      p.stageLabel,
      ?_valueLabel(p),
      if (p.afcenScore != null)
        'WAIIS ${_fmtScore(p.afcenScore!)}/100'
      else if (p.readinessScore != null)
        'Readiness ${_fmtScore(p.readinessScore!)}/10',
    ].join(' · ');

/// The loaded detail content — scrollable sections under the back button +
/// header card, with the pinned Follow / Ask Martin / Share bar at bottom: 92.
class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.project,
    required this.onBack,
    required this.onFollow,
    required this.onAskMartin,
    required this.onShare,
  });

  final DealProject project;
  final VoidCallback onBack;
  final VoidCallback onFollow;
  final VoidCallback onAskMartin;
  final VoidCallback onShare;

  @override
  Widget build(BuildContext context) {
    final p = project;
    final sector = _sectorLabel(p.sector);
    final value = _valueLabel(p);
    final location = (p.location ?? '').trim();
    final hasChips = value != null || location.isNotEmpty;
    final hasScore = p.readinessScore != null ||
        p.afcenScore != null ||
        p.strategicScore != null;
    final description = (p.description ?? '').trim();

    return Stack(
      children: [
        Positioned.fill(
          child: SafeArea(
            bottom: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                      Insets.gutter, Insets.sm, Insets.gutter, 0)
                  .add(navClearance(context, extra: 96)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Back button (chrome) above the header card.
                  _BackButton(onTap: onBack),
                  const SizedBox(height: Insets.md),
                  CascadeIn(
                    index: 0,
                    child: HeaderCard(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  p.name,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontFamily: 'Inter',
                                    fontSize: 19,
                                    fontWeight: FontWeight.w800,
                                    height: 1.2,
                                    color: SovereignColors.ivory,
                                  ),
                                ),
                                if (sector != null)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 2),
                                    child: Text(
                                      sector,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontFamily: 'Inter',
                                        fontSize: 12,
                                        color: SovereignColors.ivory.withValues(
                                            alpha: SovereignColors.alphaMid),
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          const SizedBox(width: Insets.md),
                          _StageBadge(stage: p.stage),
                        ],
                      ),
                    ),
                  ),
                  if (hasChips) ...[
                    const SizedBox(height: Insets.md),
                    CascadeIn(
                      index: 1,
                      child: GlassCard(
                        padding: const EdgeInsets.all(Insets.md),
                        child: Wrap(
                          spacing: Insets.sm,
                          runSpacing: Insets.sm,
                          children: [
                            if (value != null)
                              _FactChip(
                                  icon: Icons.payments_outlined, text: value),
                            if (location.isNotEmpty)
                              _FactChip(
                                  icon: Icons.place_outlined, text: location),
                          ],
                        ),
                      ),
                    ),
                  ],
                  if (hasScore) ...[
                    const SizedBox(height: Insets.section),
                    CascadeIn(index: 2, child: _ScoreSection(project: p)),
                  ],
                  const SizedBox(height: Insets.section),
                  CascadeIn(
                    index: 3,
                    child: _OuterSection(
                      label: 'About',
                      children: [
                        _InnerPanel(
                          child: Text(
                            description.isNotEmpty
                                ? description
                                : 'No description yet.',
                            style: SovereignType.body.copyWith(
                              color: SovereignColors.ivory.withValues(
                                alpha: description.isNotEmpty
                                    ? SovereignColors.alphaHigh
                                    : SovereignColors.alphaLow,
                              ),
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
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 92, // sit above the floating nav
          child: _ActionBar(
            isFollowing: p.isFollowing,
            onFollow: onFollow,
            onAskMartin: onAskMartin,
            onShare: onShare,
          ),
        ),
      ],
    );
  }
}

/// Score card-in-card: the big numeral leads with the AfCEN WAIIS score
/// (/100 — the same number the list rows' meta shows) and falls back to
/// readiness (/10, the backend's 0-10 scale — see the header comment); the
/// other present scores render as breakdown rows. The section header tracks
/// whichever metric the numeral shows.
class _ScoreSection extends StatelessWidget {
  const _ScoreSection({required this.project});

  final DealProject project;

  /// (label, value, suffix) for the big numeral — AfCEN (WAIIS) first to
  /// match the list meta, otherwise the next score the API sent.
  (String, double, String) get _primary {
    final p = project;
    if (p.afcenScore != null) return ('WAIIS score', p.afcenScore!, '/100');
    if (p.readinessScore != null) return ('Readiness', p.readinessScore!, '/10');
    return ('Strategic alignment', p.strategicScore!, '/10');
  }

  /// The component rows that are present and not already the big numeral.
  List<(String, String)> get _breakdown {
    final p = project;
    return [
      if (p.afcenScore != null && p.readinessScore != null)
        ('Readiness', '${_fmtScore(p.readinessScore!)}/10'),
      if (p.strategicScore != null &&
          (p.readinessScore != null || p.afcenScore != null))
        ('Strategic alignment', '${_fmtScore(p.strategicScore!)}/10'),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final (label, value, suffix) = _primary;
    return _OuterSection(
      label: label,
      children: [
        _InnerPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label.toUpperCase(), style: SovereignType.eyebrow),
              const SizedBox(height: Insets.xs),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(_fmtScore(value), style: SovereignType.display),
                  const SizedBox(width: Insets.xs),
                  Text(
                    suffix,
                    style: SovereignType.section.copyWith(
                      color: SovereignColors.ivory
                          .withValues(alpha: SovereignColors.alphaMid),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        for (final (rowLabel, rowValue) in _breakdown)
          _InnerPanel(
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    rowLabel,
                    style: SovereignType.body.copyWith(
                      color: SovereignColors.ivory
                          .withValues(alpha: SovereignColors.alphaHigh),
                    ),
                  ),
                ),
                Text(
                  rowValue,
                  style: SovereignType.body.copyWith(
                    fontWeight: FontWeight.w700,
                    color: SovereignColors.gold,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// The pinned bottom action bar: Follow (THE filled-yellow action), the
/// gold-outline ✦ Ask Martin chip, and a compact Share button — one glass
/// surface above the floating nav.
class _ActionBar extends StatelessWidget {
  const _ActionBar({
    required this.isFollowing,
    required this.onFollow,
    required this.onAskMartin,
    required this.onShare,
  });

  final bool isFollowing;
  final VoidCallback onFollow;
  final VoidCallback onAskMartin;
  final VoidCallback onShare;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 18),
      child: GlassSurface(
        borderRadius: 24,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        goldGlow: true,
        child: Row(
          children: [
            Expanded(
              child: _FollowPill(isFollowing: isFollowing, onTap: onFollow),
            ),
            const SizedBox(width: Insets.sm),
            _AskMartinChip(onTap: onAskMartin),
            const SizedBox(width: Insets.sm),
            _ShareButton(onTap: onShare),
          ],
        ),
      ),
    );
  }
}

/// The screen's ONE filled-yellow action. Stays solid gold in both states;
/// the label flips Follow <-> "Following ✓" with the optimistic toggle.
class _FollowPill extends StatelessWidget {
  const _FollowPill({required this.isFollowing, required this.onTap});

  final bool isFollowing;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: isFollowing ? 'Unfollow project' : 'Follow project',
      child: PressableScale(
        onTap: onTap,
        child: Container(
          height: 44,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: SovereignColors.gold,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: SovereignColors.gold.withValues(alpha: 0.28),
                blurRadius: 14,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Text(
            isFollowing ? 'Following ✓' : 'Follow',
            style: const TextStyle(
              fontFamily: 'Inter',
              color: SovereignColors.navy,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}

/// Gold-outline "✦ Ask Martin" chip — never filled (Follow owns the yellow).
class _AskMartinChip extends StatelessWidget {
  const _AskMartinChip({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Ask Martin about this project',
      child: PressableScale(
        onTap: onTap,
        child: Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: Insets.md),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: SovereignColors.gold.withValues(alpha: 0.55)),
          ),
          child: Text(
            '✦ Ask Martin',
            style: SovereignType.caption.copyWith(
              color: SovereignColors.gold,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}

/// Compact share button — hands the text brief to the OS share sheet.
class _ShareButton extends StatelessWidget {
  const _ShareButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Share',
      child: PressableScale(
        onTap: onTap,
        child: Container(
          width: 44,
          height: 44,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: SovereignColors.ivory.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: SovereignColors.ivory.withValues(alpha: 0.10)),
          ),
          child: const Icon(Icons.ios_share,
              size: 18, color: SovereignColors.ivory),
        ),
      ),
    );
  }
}

/// The trailing stage chip — same muted-ivory -> gold funnel-tint treatment
/// as the list rows, so the stage reads identically in both places.
class _StageBadge extends StatelessWidget {
  const _StageBadge({required this.stage});

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

/// A compact glass-inside-glass fact chip: small gold icon + short text
/// (mirrors the meeting detail's info chips).
class _FactChip extends StatelessWidget {
  const _FactChip({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: SovereignColors.gold),
          const SizedBox(width: 6),
          Text(text, style: SovereignType.caption),
        ],
      ),
    );
  }
}

/// Card-in-card outer frame: a [SectionHeader] above a raised card holding one
/// [_InnerPanel] per logical item (mirrors the meeting detail's sections).
class _OuterSection extends StatelessWidget {
  const _OuterSection({required this.label, required this.children});

  final String label;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(title: label),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(Insets.md),
          decoration: BoxDecoration(
            color: SovereignColors.navyRaised,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: SovereignColors.ivory.withValues(alpha: 0.08)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < children.length; i++) ...[
                if (i > 0) const SizedBox(height: Insets.sm),
                children[i],
              ],
            ],
          ),
        ),
      ],
    );
  }
}

/// A single recessed inner panel inside an [_OuterSection] (or the sheet).
class _InnerPanel extends StatelessWidget {
  const _InnerPanel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(Insets.md),
      decoration: BoxDecoration(
        color: SovereignColors.navyDeep,
        borderRadius: BorderRadius.circular(12),
        border:
            Border.all(color: SovereignColors.ivory.withValues(alpha: 0.06)),
      ),
      child: child,
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

/// Loading — a content-shaped skeleton (no spinner), mirroring the meeting
/// detail: header block + two card shapes.
class _DetailSkeleton extends StatelessWidget {
  const _DetailSkeleton();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.xl, Insets.gutter, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          SkeletonBlock(width: 120, height: 12),
          SizedBox(height: Insets.md),
          SkeletonBlock(width: 240, height: 26),
          SizedBox(height: Insets.section),
          SkeletonCard(lines: 3),
          SizedBox(height: Insets.md),
          SkeletonCard(lines: 2),
        ],
      ),
    );
  }
}

/// Ambient Sovereign backdrop — navy gradient + top-right gold radial glow
/// (the same treatment as the meeting detail).
class _AmbientBackdrop extends StatelessWidget {
  const _AmbientBackdrop({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            SovereignColors.navyRaised,
            SovereignColors.navy,
            SovereignColors.navyDeep,
          ],
          stops: [0, 0.45, 1],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: -120,
            right: -90,
            child: Container(
              width: 320,
              height: 320,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    SovereignColors.gold.withValues(alpha: 0.18),
                    SovereignColors.gold.withValues(alpha: 0),
                  ],
                ),
              ),
            ),
          ),
          child,
        ],
      ),
    );
  }
}

/// Error state with a Retry action (also covers "project not found").
class _DetailError extends StatelessWidget {
  const _DetailError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Insets.xxl),
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off,
                  color: SovereignColors.gold, size: 28),
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
      ),
    );
  }
}
