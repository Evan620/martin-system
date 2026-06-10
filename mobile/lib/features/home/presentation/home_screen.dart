// lib/features/home/presentation/home_screen.dart
//
// Home · native dashboard (v2) — wired to the live member-scoped briefing
// (`GET /martin/briefing`).
//
// Layout (top -> bottom), per the Native Dashboard v2 spec:
//   - compact `AppHeader`: "<EEE d MMM>" context over "Home", overdue-count
//     badge (hidden at 0) + initials avatar (-> /me).
//   - a 2x2 `StatTile` grid: ① Next meeting (emphasized; the embedded Join
//     pill is THE one filled-yellow action, hidden without a video link),
//     ② Tasks due (-> /me), ③ My TWG (-> workspace), ④ Ask Martin (quiet
//     tile -> /martin).
//   - "Today" `SectionHeader` + a `RowGroup` mixing the next meeting row, an
//     overdue-tasks row (when count > 0) and the member's TWG rows (when in
//     more than one TWG). Empty briefing -> tiles show 0-states, never blank.
//
// Loads via homeControllerProvider.load() (post-frame), renders by sealed
// state (loading -> tile/row-shaped skeleton / error / data). Tiles cascade in
// (indices 0–3) then the Today section; pull-to-refresh re-runs load().
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/glass/glass.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/motion/motion.dart';
import '../../../core/motion/pressable.dart';
import '../../../core/motion/skeleton.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/app_header.dart';
import '../../../core/ui/list_row.dart';
import '../../../core/ui/section_header.dart';
import '../../../core/ui/stat_tile.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/home_controller.dart';
import '../data/briefing_models.dart';

/// The member dashboard. A compact header, four stat tiles and the Today row
/// group — dense, glanceable, exactly one filled-yellow action (Join).
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(homeControllerProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(homeControllerProvider);

    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          // Atmospheric navy field with a faint gold glow, so raised surfaces
          // have something rich to sit on (never sky-blue).
          const _AmbientBackground(),
          SafeArea(
            bottom: false,
            child: RefreshIndicator(
              color: SovereignColors.gold,
              backgroundColor: SovereignColors.navyRaised,
              onRefresh: () => ref.read(homeControllerProvider.notifier).load(),
              child: AnimatedSwitcher(
                duration: Motion.base,
                child: switch (state) {
                  HomeLoading() => const _LoadingView(key: ValueKey('loading')),
                  HomeError(:final message) => _ErrorView(
                      key: const ValueKey('error'),
                      message: message,
                      onRetry: () =>
                          ref.read(homeControllerProvider.notifier).load(),
                    ),
                  HomeData(:final briefing) => _DataView(
                      key: const ValueKey('data'),
                      briefing: briefing,
                      initials: _initials(ref),
                      twgs: _twgs(ref),
                    ),
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The member's initials from the authed user's full name ("Amina Diallo" ->
/// "AD"); null when unknown, which hides the header avatar.
String? _initials(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  if (auth is! AuthAuthenticated) return null;
  final words = auth.user.fullName.trim().split(RegExp(r'\s+'))
    ..removeWhere((w) => w.isEmpty);
  if (words.isEmpty) return null;
  return words.take(2).map((w) => w[0].toUpperCase()).join();
}

/// The member's TWGs from auth state (already loaded — no fetch).
List<Twg> _twgs(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  return auth is AuthAuthenticated ? auth.user.twgs : const <Twg>[];
}

// ---------------------------------------------------------------------------
// Loaded state — header, 2x2 tile grid, Today rows.
// ---------------------------------------------------------------------------

class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.briefing,
    required this.initials,
    required this.twgs,
  });

  final Briefing briefing;
  final String? initials;
  final List<Twg> twgs;

  @override
  Widget build(BuildContext context) {
    final next = briefing.nextMeeting;
    final firstTwg = twgs.isNotEmpty ? twgs.first : null;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
          .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppHeader(
            context_: DateFormat('EEE d MMM').format(DateTime.now()),
            title: 'Home',
            badgeCount: briefing.overdueCount,
            initials: initials,
            onAvatar: () => context.go('/me'),
          ),
          const SizedBox(height: Insets.lg),

          // 2x2 stat tile grid — tiles cascade in at indices 0–3.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: CascadeIn(index: 0, child: _NextMeetingTile(next: next)),
              ),
              const SizedBox(width: Insets.sm),
              Expanded(
                child: CascadeIn(
                  index: 1,
                  child: StatTile(
                    label: 'Tasks due',
                    value: '${briefing.overdueCount}',
                    sub: 'action items',
                    onTap: () => context.go('/me'),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: Insets.sm),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: CascadeIn(
                  index: 2,
                  child: StatTile(
                    label: 'My TWG',
                    value: firstTwg?.name ?? '—',
                    sub: firstTwg != null ? 'open workspace ›' : 'no TWG yet',
                    onTap: firstTwg != null
                        ? () => context.push('/home/workspace/${firstTwg.id}')
                        : null,
                  ),
                ),
              ),
              const SizedBox(width: Insets.sm),
              Expanded(
                child: CascadeIn(
                  index: 3,
                  child: StatTile(
                    label: 'Ask Martin',
                    value: '✦',
                    sub: 'ask anything',
                    onTap: () => context.push('/martin'),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: Insets.section),

          // Today — up to 5 mixed rows, each navigating to its feature.
          CascadeIn(
            index: 4,
            child: SectionHeader(
              title: 'Today',
              onSeeAll: () => context.go('/meetings'),
            ),
          ),
          CascadeIn(
            index: 5,
            child: RowGroup(children: _todayRows(context, next)),
          ),
        ],
      ),
    );
  }

  /// The Today rows: next meeting, overdue tasks (when any), the member's TWG
  /// rows (when in more than one TWG); a calm all-clear row when empty.
  List<Widget> _todayRows(BuildContext context, BriefingMeeting? next) {
    final rows = <Widget>[
      if (next != null)
        ListRow(
          icon: Icons.event_rounded,
          title: next.title,
          meta: _meetingMeta(next),
          rightMeta: _relativeTime(next),
          onTap: () => context.go('/meetings'),
        ),
      if (briefing.overdueCount > 0)
        ListRow(
          icon: Icons.flag_rounded,
          title: '${briefing.overdueCount} action '
              '${briefing.overdueCount == 1 ? 'item' : 'items'} due',
          meta: 'Review in Me',
          onTap: () => context.go('/me'),
        ),
      if (twgs.length > 1)
        for (final twg in twgs)
          ListRow(
            icon: Icons.groups_rounded,
            title: twg.name,
            meta: 'Open workspace',
            onTap: () => context.push('/home/workspace/${twg.id}'),
          ),
    ];
    if (rows.isEmpty) {
      return const [
        ListRow(
          icon: Icons.check_circle_outline_rounded,
          title: 'All clear today',
          meta: 'Nothing scheduled',
        ),
      ];
    }
    return rows.take(5).toList();
  }
}

/// The emphasized Next-meeting tile: relative-time label, HH:mm value (falls
/// back to the relative phrase when the start time is unknown), title sub and
/// the embedded Join pill — THE screen's one filled-yellow action.
class _NextMeetingTile extends StatelessWidget {
  const _NextMeetingTile({required this.next});

  final BriefingMeeting? next;

  @override
  Widget build(BuildContext context) {
    final m = next;
    if (m == null) {
      return StatTile(
        emphasized: true,
        label: 'Next meeting',
        value: '—',
        sub: 'nothing scheduled',
        onTap: () => context.go('/meetings'),
      );
    }
    return StatTile(
      emphasized: true,
      label: 'Next meeting · ${_relativeTime(m)}',
      value: m.startsAt != null
          ? DateFormat('HH:mm').format(m.startsAt!)
          : _relativeTime(m),
      sub: m.title,
      action: m.videoLink != null ? _JoinPill(videoLink: m.videoLink!) : null,
      onTap: () => context.go('/meetings'),
    );
  }
}

/// A friendly relative time for the next meeting, derived from `minutesUntil`
/// (falls back to a generic phrase when unknown).
String _relativeTime(BriefingMeeting m) {
  final mins = m.minutesUntil;
  if (mins == null) return 'Soon';
  if (mins <= 0) return 'Now';
  if (mins < 60) return 'in $mins min';
  final hours = mins ~/ 60;
  if (hours < 24) {
    final rem = mins % 60;
    return rem == 0 ? 'in ${hours}h' : 'in ${hours}h ${rem}m';
  }
  final days = hours ~/ 24;
  return days == 1 ? 'Tomorrow' : 'in $days days';
}

/// The Today-row meta line: clock time when known, plus "Virtual" when the
/// meeting carries a video link, else the TWG name.
String _meetingMeta(BriefingMeeting m) {
  final parts = <String>[
    if (m.startsAt != null) DateFormat('HH:mm').format(m.startsAt!),
    if (m.videoLink != null) 'Virtual' else if (m.twgName != null) m.twgName!,
  ];
  return parts.isEmpty ? 'Today' : parts.join(' · ');
}

/// The yellow "Join" pill embedded in the Next-meeting tile — the screen's ONE
/// filled-yellow action. Launches the meeting's [videoLink] externally.
class _JoinPill extends StatelessWidget {
  const _JoinPill({required this.videoLink});

  final String videoLink;

  Future<void> _launch() async {
    final uri = Uri.tryParse(videoLink);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Join meeting',
      child: PressableScale(
        onTap: _launch,
        child: Container(
          padding: const EdgeInsets.symmetric(
              horizontal: Insets.md, vertical: Insets.xs + 2),
          decoration: BoxDecoration(
            color: SovereignColors.gold,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.videocam_rounded,
                  size: 14, color: SovereignColors.navy),
              SizedBox(width: Insets.xs),
              Text(
                'Join',
                style: TextStyle(
                  fontFamily: 'Inter',
                  color: SovereignColors.navy,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Loading — tile/row-shaped skeleton (4 tiles + 3 rows), no spinner.
// ---------------------------------------------------------------------------

class _LoadingView extends StatelessWidget {
  const _LoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
          .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(children: [
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
          ]),
          SizedBox(height: Insets.sm),
          Row(children: [
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
          ]),
          SizedBox(height: Insets.section),
          RowGroup(children: [SkeletonRow(), SkeletonRow(), SkeletonRow()]),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Background
// ---------------------------------------------------------------------------

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
          // A soft gold halo up top — the Sovereign signature, kept subtle.
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

// ---------------------------------------------------------------------------
// Error state — a glass message + a Retry button.
// ---------------------------------------------------------------------------

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
              const Icon(Icons.cloud_off,
                  color: SovereignColors.gold, size: 28),
              const SizedBox(height: Insets.md),
              Text(
                message,
                textAlign: TextAlign.center,
                style: SovereignType.body.copyWith(
                  color: SovereignColors.ivory.withValues(
                    alpha: SovereignColors.alphaHigh,
                  ),
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
