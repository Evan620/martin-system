// lib/features/meetings/presentation/meetings_screen.dart
//
// Meetings — Sovereign glass list of the member's sessions, wired to live data.
//
// Loads via meetingsControllerProvider.load() (post-frame), renders by sealed
// state (loading / error / empty / data) inside an AnimatedSwitcher so the
// skeleton cross-fades to content. An Upcoming|Past toggle filters the list;
// meetings are grouped by day under gold eyebrow labels, and the soonest
// upcoming session is rendered as an emphasized hero card (big serif time).
//
// One gold action per screen: the Join pill on the imminent (hero) card that
// carries a video link. RSVP chips are gold-outline-when-selected (≥44px tall)
// so they don't compete with the hero's solid gold. Tapping a card body pushes
// /meetings/:id with a Hero transition keyed by meeting id.
//
// Motion: each card cascades in on first load; loading shows a SkeletonList;
// pull-to-refresh re-runs load(); cards/chips give press feedback.
//
// Reuses the Sovereign glass design system (lib/core/glass/glass.dart) with
// glass-inside-glass: each outer GlassCard holds lighter GlassSurface.inner
// panels (the RSVP chips).
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
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/meetings_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';

/// Hero tag for a meeting's title block — shared between this list and the
/// detail screen so the title morphs across the push.
String meetingHeroTag(String id) => 'meeting-title-$id';

/// Meetings screen: serif title + a scrollable list of glass meeting cards,
/// rendered from live data with an Upcoming|Past toggle.
class MeetingsScreen extends ConsumerStatefulWidget {
  const MeetingsScreen({super.key});

  @override
  ConsumerState<MeetingsScreen> createState() => _MeetingsScreenState();
}

class _MeetingsScreenState extends ConsumerState<MeetingsScreen> {
  /// Upcoming (false) vs Past (true) filter for the segmented toggle.
  bool _showPast = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(meetingsControllerProvider.notifier).load();
    });
  }

  Future<void> _setRsvp(Meeting m, MeetingRsvp rsvp, String userId) async {
    try {
      await ref
          .read(meetingsControllerProvider.notifier)
          .setRsvp(m.id, rsvp, userId);
    } on MeetingException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _join(Meeting m) async {
    final link = m.videoLink;
    if (link == null || link.isEmpty) return;
    await launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(meetingsControllerProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          color: SovereignColors.gold,
          backgroundColor: SovereignColors.navyRaised,
          onRefresh: () => ref.read(meetingsControllerProvider.notifier).load(),
          child: AnimatedSwitcher(
            duration: Motion.base,
            child: switch (state) {
              MeetingsLoading() => const _LoadingView(key: ValueKey('loading')),
              MeetingsError(:final message) => _ErrorView(
                  key: const ValueKey('error'),
                  message: message,
                  onRetry: () =>
                      ref.read(meetingsControllerProvider.notifier).load(),
                ),
              MeetingsEmpty() => const _EmptyView(key: ValueKey('empty')),
              MeetingsData(:final meetings) => _DataView(
                  key: const ValueKey('data'),
                  meetings: meetings,
                  showPast: _showPast,
                  onToggle: (past) => setState(() => _showPast = past),
                  userId: ref.watch(currentUserIdProvider),
                  twgName: _headerSubtitle(ref),
                  onJoin: _join,
                  onRsvp: _setRsvp,
                  onOpen: (m) => context.push('/meetings/${m.id}'),
                ),
            },
          ),
        ),
      ),
    );
  }
}

/// The member's TWG label, used as the header eyebrow (one TWG → its name,
/// several → a compact multi-TWG label; falls back to a neutral label when
/// unknown).
String _headerSubtitle(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  if (auth is AuthAuthenticated) {
    final label = auth.user.twgs.headerLabel;
    if (label != null) return label;
  }
  return 'Your sessions';
}

/// Loaded list state: header, Upcoming|Past toggle, then day-grouped cards with
/// the soonest upcoming session emphasized.
class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.meetings,
    required this.showPast,
    required this.onToggle,
    required this.userId,
    required this.twgName,
    required this.onJoin,
    required this.onRsvp,
    required this.onOpen,
  });

  final List<Meeting> meetings;
  final bool showPast;
  final ValueChanged<bool> onToggle;
  final String userId;
  final String twgName;
  final ValueChanged<Meeting> onJoin;
  final void Function(Meeting, MeetingRsvp, String) onRsvp;
  final ValueChanged<Meeting> onOpen;

  static final _dayFmt = DateFormat('EEEE, d MMMM');

  @override
  Widget build(BuildContext context) {
    final shown = meetings.where((m) => showPast ? m.isPast : !m.isPast).toList()
      ..sort((a, b) => showPast
          ? b.scheduledAt.compareTo(a.scheduledAt)
          : a.scheduledAt.compareTo(b.scheduledAt));

    // The soonest upcoming session is the imminent hero (first of the sorted
    // Upcoming list). In Past, nothing is emphasized.
    final Meeting? hero = (!showPast && shown.isNotEmpty) ? shown.first : null;

    // Build the column children: header, toggle, then day-grouped cards. A
    // running index drives the cascade entrance across all cards.
    final children = <Widget>[];
    var cascade = 0;

    if (shown.isEmpty) {
      children.add(_InlineEmpty(showPast: showPast));
    } else {
      String? lastDayLabel;
      for (final meeting in shown) {
        final dayLabel = _dayFmt.format(meeting.scheduledAt).toUpperCase();
        if (dayLabel != lastDayLabel) {
          lastDayLabel = dayLabel;
          children.add(Padding(
            padding: EdgeInsets.only(
              top: children.isEmpty ? 0 : Insets.lg,
              bottom: Insets.sm,
            ),
            child: CascadeIn(
              index: cascade++,
              child: Text(dayLabel, style: SovereignType.eyebrow),
            ),
          ));
        }
        final isHero = identical(meeting, hero);
        children.add(CascadeIn(
          index: cascade++,
          child: _MeetingCard(
            meeting: meeting,
            userId: userId,
            emphasized: isHero,
            onJoin: () => onJoin(meeting),
            onRsvp: (rsvp) => onRsvp(meeting, rsvp, userId),
            onOpen: () => onOpen(meeting),
          ),
        ));
        children.add(const SizedBox(height: Insets.md));
      }
    }

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
          .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CascadeIn(
            index: 0,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(twgName.toUpperCase(), style: SovereignType.eyebrow),
                const SizedBox(height: Insets.xs),
                Text('Meetings', style: SovereignType.display),
                const SizedBox(height: Insets.xs),
                Text(
                  showPast ? 'Your past sessions' : 'Your upcoming sessions',
                  style: SovereignType.secondary.copyWith(
                    color: SovereignColors.ivory
                        .withValues(alpha: SovereignColors.alphaMid),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 1,
            child: _UpcomingPastToggle(showPast: showPast, onToggle: onToggle),
          ),
          const SizedBox(height: Insets.lg),
          ...children,
        ],
      ),
    );
  }
}

/// Loading — content-shaped skeleton list (no spinner), cross-fades to content.
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
          SkeletonBlock(width: 140, height: 12),
          SizedBox(height: Insets.md),
          SkeletonBlock(width: 200, height: 34),
          SizedBox(height: Insets.section),
          SkeletonList(count: 4),
        ],
      ),
    );
  }
}

/// Segmented Upcoming | Past control built from two inner-glass tabs.
class _UpcomingPastToggle extends StatelessWidget {
  const _UpcomingPastToggle({required this.showPast, required this.onToggle});

  final bool showPast;
  final ValueChanged<bool> onToggle;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      borderRadius: 14,
      padding: const EdgeInsets.all(4),
      child: Row(
        children: [
          _ToggleTab(
            label: 'Upcoming',
            selected: !showPast,
            onTap: () => onToggle(false),
          ),
          const SizedBox(width: Insets.xs),
          _ToggleTab(
            label: 'Past',
            selected: showPast,
            onTap: () => onToggle(true),
          ),
        ],
      ),
    );
  }
}

class _ToggleTab extends StatelessWidget {
  const _ToggleTab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: PressableScale(
        onTap: onTap,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: selected ? SovereignColors.gold : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Center(
              child: Text(
                label,
                style: SovereignType.caption.copyWith(
                  color: selected
                      ? SovereignColors.navy
                      : SovereignColors.ivory
                          .withValues(alpha: SovereignColors.alphaHigh),
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A single meeting rendered as a tappable raised GlassCard. The imminent
/// (soonest upcoming) card is [emphasized]: a gold glow, a serif relative-time
/// line, and — when it carries video — the screen's ONE solid-gold Join pill.
/// Glass-inside-glass: the RSVP chip row is a lighter GlassSurface.inner layer.
class _MeetingCard extends StatelessWidget {
  const _MeetingCard({
    required this.meeting,
    required this.userId,
    required this.emphasized,
    required this.onJoin,
    required this.onRsvp,
    required this.onOpen,
  });

  final Meeting meeting;
  final String userId;
  final bool emphasized;
  final VoidCallback onJoin;
  final ValueChanged<MeetingRsvp> onRsvp;
  final VoidCallback onOpen;

  static final _dateFmt = DateFormat('EEE d MMM · HH:mm');

  @override
  Widget build(BuildContext context) {
    final isParticipant = meeting.isParticipant(userId);
    final myRsvp = meeting.myRsvp(userId);
    final location = (meeting.location ?? '').trim();
    final subtitle = [
      _dateFmt.format(meeting.scheduledAt),
      if (location.isNotEmpty) location else if (meeting.hasVideo) 'Virtual',
    ].join(' · ');

    // Only the emphasized (imminent) card may carry the solid-gold Join — that
    // is the screen's single gold action.
    final showJoin = emphasized && meeting.hasVideo;

    return PressableScale(
      onTap: onOpen,
      child: GlassCard(
        goldGlow: emphasized,
        borderRadius: emphasized ? 22 : 20,
        padding: EdgeInsets.all(emphasized ? Insets.xl : Insets.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // The emphasized card leads with an eyebrow + a big serif relative
            // time so the soonest session reads as the focal point.
            if (emphasized) ...[
              Text('NEXT UP', style: SovereignType.eyebrow),
              const SizedBox(height: Insets.sm),
              Text(_relativeTime(meeting), style: SovereignType.title),
              const SizedBox(height: Insets.xs),
            ],
            // Title block (Hero destination keyed by id) + Join (emphasized only).
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Hero(
                    tag: meetingHeroTag(meeting.id),
                    flightShuttleBuilder: _heroShuttle,
                    child: Material(
                      type: MaterialType.transparency,
                      child: Text(
                        meeting.title,
                        style: emphasized
                            ? SovereignType.heading
                            : SovereignType.section,
                      ),
                    ),
                  ),
                ),
                if (showJoin) ...[
                  const SizedBox(width: Insets.md),
                  _JoinPill(onTap: onJoin),
                ],
              ],
            ),
            const SizedBox(height: Insets.sm),
            Row(
              children: [
                const Icon(Icons.schedule, size: 13, color: SovereignColors.gold),
                const SizedBox(width: Insets.sm),
                Expanded(
                  child: Text(
                    subtitle,
                    style: SovereignType.secondary.copyWith(
                      color: SovereignColors.ivory
                          .withValues(alpha: SovereignColors.alphaMid),
                    ),
                  ),
                ),
              ],
            ),

            // RSVP row — shown only to participants. Three inner-glass chips,
            // the selected one gold-outline (so it doesn't compete with Join).
            if (isParticipant) ...[
              const SizedBox(height: Insets.lg),
              Text('RSVP', style: SovereignType.eyebrow),
              const SizedBox(height: Insets.sm),
              Row(
                children: [
                  _RsvpChip(
                    label: 'Going',
                    selected: myRsvp == MeetingRsvp.going,
                    onTap: () => onRsvp(MeetingRsvp.going),
                  ),
                  const SizedBox(width: Insets.sm),
                  _RsvpChip(
                    label: 'Maybe',
                    selected: myRsvp == MeetingRsvp.maybe,
                    onTap: () => onRsvp(MeetingRsvp.maybe),
                  ),
                  const SizedBox(width: Insets.sm),
                  _RsvpChip(
                    label: 'No',
                    selected: myRsvp == MeetingRsvp.no,
                    onTap: () => onRsvp(MeetingRsvp.no),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Keeps the title legible (not double-shadowed) mid-flight.
  static Widget _heroShuttle(
    BuildContext flightContext,
    Animation<double> animation,
    HeroFlightDirection flightDirection,
    BuildContext fromHeroContext,
    BuildContext toHeroContext,
  ) {
    return DefaultTextStyle(
      style: DefaultTextStyle.of(toHeroContext).style,
      child: toHeroContext.widget,
    );
  }
}

/// A friendly relative time for an upcoming meeting (mirrors Home's hero copy).
String _relativeTime(Meeting m) {
  final mins = m.scheduledAt.difference(DateTime.now()).inMinutes;
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

/// The gold "Join" call-to-action pill — the imminent card's single gold action.
class _JoinPill extends StatelessWidget {
  const _JoinPill({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Join meeting',
      child: PressableScale(
        onTap: onTap,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: SovereignColors.gold,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: SovereignColors.gold.withValues(alpha: 0.28),
                blurRadius: 14,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 9),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.videocam, size: 14, color: SovereignColors.navy),
                SizedBox(width: 6),
                Text(
                  'Join',
                  style: TextStyle(
                    fontFamily: 'Inter',
                    color: SovereignColors.navy,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// One RSVP option as a ≥44px tappable chip. When [selected], the chip reads as
/// a gold-OUTLINE pill (gold ring + gold label) — not a solid fill — so the
/// imminent card's Join stays the only solid gold on the screen.
class _RsvpChip extends StatelessWidget {
  const _RsvpChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final labelStyle = SovereignType.caption.copyWith(
      color: selected
          ? SovereignColors.gold
          : SovereignColors.ivory.withValues(alpha: SovereignColors.alphaHigh),
      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
    );

    final content = SizedBox(
      height: 44, // ≥44px touch target
      child: Center(child: Text(label, style: labelStyle)),
    );

    final Widget chip = selected
        ? DecoratedBox(
            decoration: BoxDecoration(
              color: SovereignColors.gold.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: SovereignColors.gold.withValues(alpha: 0.85),
                width: 1.4,
              ),
            ),
            child: content,
          )
        : GlassSurface.inner(borderRadius: 12, child: content);

    return Expanded(
      child: Semantics(
        button: true,
        label: 'RSVP $label${selected ? ', selected' : ''}',
        child: PressableScale(onTap: onTap, child: chip),
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

/// Full-screen empty state (no meetings at all).
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
              const Icon(Icons.event_available,
                  color: SovereignColors.gold, size: 30),
              const SizedBox(height: Insets.md),
              Text(
                'No meetings scheduled yet',
                textAlign: TextAlign.center,
                style: SovereignType.section,
              ),
              const SizedBox(height: Insets.xs),
              Text(
                "When your TWG schedules a session, it'll appear here.",
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

/// Inline empty state shown under the toggle when one side has no meetings.
class _InlineEmpty extends StatelessWidget {
  const _InlineEmpty({required this.showPast});

  final bool showPast;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: Insets.sm),
          child: Text(
            showPast ? 'No past meetings.' : 'No upcoming meetings.',
            style: SovereignType.secondary.copyWith(
              color: SovereignColors.ivory
                  .withValues(alpha: SovereignColors.alphaMid),
            ),
          ),
        ),
      ),
    );
  }
}
