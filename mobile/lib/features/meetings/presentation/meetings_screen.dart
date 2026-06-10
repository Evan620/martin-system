// lib/features/meetings/presentation/meetings_screen.dart
//
// Meetings — native dashboard (v2) list of the member's sessions, wired to
// live data.
//
// Layout (top -> bottom), per the Native Dashboard v2 spec:
//   - compact `AppHeader`: TWG label context over "Meetings" (no serif).
//   - `SovereignSegmented` Upcoming | Past, filtering by `scheduledAt` vs now.
//   - day-grouped rows (Today / Tomorrow / "EEE d MMM"): each group is a
//     `SectionHeader` + `RowGroup` of dense rows — a 38px HH:mm time block,
//     title, "TWG · location/Virtual · RSVP state" meta, trailing chevron.
//     The SOONEST upcoming session carries the inline Join pill when it has
//     video — THE screen's one filled-yellow action.
//   - tapping a row pushes /meetings/:id (route unchanged); long-pressing it
//     opens a `SovereignSheet` with the three RSVP options, wired to the
//     existing controller `setRsvp` (optimistic; rolls back + snackbar on
//     failure).
//
// Loads via meetingsControllerProvider.load() (post-frame), renders by sealed
// state (loading / error / empty / data) inside an AnimatedSwitcher so the
// row-shaped skeleton cross-fades to content; pull-to-refresh re-runs load().
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
import '../../../core/ui/segmented.dart';
import '../../../core/ui/sheet.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/meetings_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';

/// Hero tag for a meeting's title — the detail screen's title Hero still keys
/// off this (kept public for meeting_detail_screen.dart).
String meetingHeroTag(String id) => 'meeting-title-$id';

/// Meetings screen: compact header, Upcoming|Past segmented control, then
/// day-grouped dense meeting rows rendered from live data.
class MeetingsScreen extends ConsumerStatefulWidget {
  const MeetingsScreen({super.key});

  @override
  ConsumerState<MeetingsScreen> createState() => _MeetingsScreenState();
}

class _MeetingsScreenState extends ConsumerState<MeetingsScreen> {
  /// 0 = Upcoming, 1 = Past — the segmented control's selection.
  int _segment = 0;

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

  /// Long-press affordance: a bottom sheet with the three RSVP options. The
  /// chosen option flows through the same controller path as before.
  Future<void> _openRsvpSheet(Meeting m) async {
    final userId = ref.read(currentUserIdProvider);
    final choice = await showSovereignSheet<MeetingRsvp>(
      context,
      child: _RsvpSheetBody(meeting: m, current: m.myRsvp(userId)),
    );
    if (choice == null || !mounted) return;
    await _setRsvp(m, choice, userId);
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
                  segment: _segment,
                  onSegment: (i) => setState(() => _segment = i),
                  userId: ref.watch(currentUserIdProvider),
                  twgLabel: _headerSubtitle(ref),
                  onJoin: _join,
                  onLongPress: _openRsvpSheet,
                  onOpen: (m) => context.push('/meetings/${m.id}'),
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
  return 'Your sessions';
}

/// "Today" / "Tomorrow" / "EEE d MMM" group label for a meeting's day.
String _dayLabel(DateTime at) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(at.year, at.month, at.day);
  final diff = day.difference(today).inDays;
  if (diff == 0) return 'Today';
  if (diff == 1) return 'Tomorrow';
  return DateFormat('EEE d MMM').format(at);
}

/// Compact RSVP state for the row meta line (✓ / ? / ✗ per the v2 spec).
String _rsvpMark(MeetingRsvp rsvp) => switch (rsvp) {
      MeetingRsvp.going => '✓ Going',
      MeetingRsvp.maybe => '? Maybe',
      MeetingRsvp.no => '✗ No',
      MeetingRsvp.pending => '? RSVP',
    };

/// Loaded list state: header, segmented control, then day-grouped row groups.
class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.meetings,
    required this.segment,
    required this.onSegment,
    required this.userId,
    required this.twgLabel,
    required this.onJoin,
    required this.onLongPress,
    required this.onOpen,
  });

  final List<Meeting> meetings;
  final int segment;
  final ValueChanged<int> onSegment;
  final String userId;
  final String twgLabel;
  final ValueChanged<Meeting> onJoin;
  final ValueChanged<Meeting> onLongPress;
  final ValueChanged<Meeting> onOpen;

  @override
  Widget build(BuildContext context) {
    final showPast = segment == 1;
    final shown = meetings.where((m) => showPast ? m.isPast : !m.isPast).toList()
      ..sort((a, b) => showPast
          ? b.scheduledAt.compareTo(a.scheduledAt)
          : a.scheduledAt.compareTo(b.scheduledAt));

    // The soonest upcoming session (first of the sorted Upcoming list) may
    // carry the inline Join pill. In Past, nothing does.
    final Meeting? soonest = (!showPast && shown.isNotEmpty) ? shown.first : null;

    // Day groups, preserving the sorted order.
    final groups = <String, List<Meeting>>{};
    for (final m in shown) {
      groups.putIfAbsent(_dayLabel(m.scheduledAt), () => []).add(m);
    }

    // Header (0) and segmented (1) lead the cascade; groups follow.
    final children = <Widget>[];
    var cascade = 2;

    if (shown.isEmpty) {
      children.add(CascadeIn(
        index: cascade++,
        child: RowGroup(children: [
          ListRow(
            icon: Icons.event_available_rounded,
            title: showPast ? 'No past meetings' : 'No upcoming meetings',
            meta: "When your TWG schedules a session, it'll appear here.",
          ),
        ]),
      ));
    } else {
      groups.forEach((label, items) {
        children.add(CascadeIn(
          index: cascade++,
          child: SectionHeader(title: label),
        ));
        children.add(CascadeIn(
          index: cascade++,
          child: RowGroup(children: [
            for (final m in items)
              _MeetingRow(
                meeting: m,
                userId: userId,
                showJoin: identical(m, soonest) && m.hasVideo,
                onJoin: () => onJoin(m),
                onLongPress: () => onLongPress(m),
                onOpen: () => onOpen(m),
              ),
          ]),
        ));
        children.add(const SizedBox(height: Insets.lg));
      });
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
            child: AppHeader(title: 'Meetings', context_: twgLabel),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 1,
            child: SovereignSegmented(
              options: const ['Upcoming', 'Past'],
              selected: segment,
              onChanged: onSegment,
            ),
          ),
          const SizedBox(height: Insets.lg),
          ...children,
        ],
      ),
    );
  }
}

/// One dense meeting row: leading HH:mm time block, title, meta, trailing
/// chevron (or the inline Join pill on the soonest upcoming session with
/// video). Tap opens the detail; long-press opens the RSVP sheet.
class _MeetingRow extends StatelessWidget {
  const _MeetingRow({
    required this.meeting,
    required this.userId,
    required this.showJoin,
    required this.onJoin,
    required this.onLongPress,
    required this.onOpen,
  });

  final Meeting meeting;
  final String userId;
  final bool showJoin;
  final VoidCallback onJoin;
  final VoidCallback onLongPress;
  final VoidCallback onOpen;

  String get _meta {
    final location = (meeting.location ?? '').trim();
    final parts = <String>[
      if ((meeting.twgName ?? '').isNotEmpty) meeting.twgName!,
      if (location.isNotEmpty)
        location
      else if (meeting.hasVideo)
        'Virtual',
      if (meeting.isParticipant(userId)) _rsvpMark(meeting.myRsvp(userId)),
    ];
    if (parts.isEmpty) return meeting.isPast ? 'Past session' : 'Upcoming';
    return parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onLongPress: onLongPress,
      child: ListRow(
        leading: _TimeBlock(meeting: meeting),
        title: meeting.title,
        meta: _meta,
        trailing: showJoin ? _JoinPill(onTap: onJoin) : null,
        onTap: onOpen,
      ),
    );
  }
}

/// The row's leading 38px time block — HH:mm bold over the duration, in the
/// kit's gold icon-container style.
class _TimeBlock extends StatelessWidget {
  const _TimeBlock({required this.meeting});

  final Meeting meeting;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      padding: const EdgeInsets.symmetric(vertical: Insets.xs),
      decoration: BoxDecoration(
        color: SovereignColors.gold.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(9),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            DateFormat('HH:mm').format(meeting.scheduledAt),
            style: const TextStyle(
              fontFamily: 'Inter',
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: SovereignColors.gold,
              height: 1.1,
            ),
          ),
          Text(
            '${meeting.durationMinutes}m',
            style: TextStyle(
              fontFamily: 'Inter',
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: SovereignColors.gold
                  .withValues(alpha: SovereignColors.alphaMid),
              height: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

/// The yellow "Join" pill — the screen's ONE filled-yellow action, inline on
/// the soonest upcoming row that carries video.
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

/// The long-press RSVP sheet body: the meeting name over the three RSVP
/// options; each option pops the sheet with its [MeetingRsvp] choice (the
/// caller then routes it through the existing controller).
class _RsvpSheetBody extends StatelessWidget {
  const _RsvpSheetBody({required this.meeting, required this.current});

  final Meeting meeting;
  final MeetingRsvp current;

  @override
  Widget build(BuildContext context) {
    Widget mark(MeetingRsvp option) => option == current
        ? const Icon(Icons.check_rounded, size: 18, color: SovereignColors.gold)
        : const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        SectionHeader(title: meeting.title),
        RowGroup(children: [
          ListRow(
            icon: Icons.check_circle_outline_rounded,
            title: 'Going',
            trailing: mark(MeetingRsvp.going),
            onTap: () => Navigator.of(context).pop(MeetingRsvp.going),
          ),
          ListRow(
            icon: Icons.help_outline_rounded,
            title: 'Maybe',
            trailing: mark(MeetingRsvp.maybe),
            onTap: () => Navigator.of(context).pop(MeetingRsvp.maybe),
          ),
          ListRow(
            icon: Icons.close_rounded,
            title: 'No',
            trailing: mark(MeetingRsvp.no),
            onTap: () => Navigator.of(context).pop(MeetingRsvp.no),
          ),
        ]),
      ],
    );
  }
}

/// Loading — header/segmented/row-shaped skeletons (no spinner), cross-fading
/// to content.
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
          SkeletonBlock(width: 90, height: 12),
          SizedBox(height: Insets.sm),
          SkeletonBlock(width: 150, height: 22),
          SizedBox(height: Insets.lg),
          SkeletonBlock(width: double.infinity, height: 44, radius: 12),
          SizedBox(height: Insets.lg),
          SkeletonBlock(width: 70, height: 12),
          SizedBox(height: Insets.sm),
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
