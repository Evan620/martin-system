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
import 'package:table_calendar/table_calendar.dart';
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
  /// The month the calendar is showing, and the day whose meetings are listed
  /// below it. Both default to today.
  DateTime _focusedDay = DateTime.now();
  DateTime _selectedDay = DateTime.now();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(meetingsControllerProvider.notifier).load();
    });
  }

  void _onDaySelected(DateTime selected, DateTime focused) {
    setState(() {
      _selectedDay = selected;
      _focusedDay = focused;
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
                  focusedDay: _focusedDay,
                  selectedDay: _selectedDay,
                  onDaySelected: _onDaySelected,
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

/// A day key normalised to a date-only UTC value, so meetings group by calendar
/// day regardless of their local time-of-day (used for calendar markers).
DateTime _dayKey(DateTime at) => DateTime.utc(at.year, at.month, at.day);

/// Loaded state: header, a month calendar with markers on days that have
/// meetings, then the selected day's meetings (today by default).
class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.meetings,
    required this.focusedDay,
    required this.selectedDay,
    required this.onDaySelected,
    required this.userId,
    required this.twgLabel,
    required this.onJoin,
    required this.onLongPress,
    required this.onOpen,
  });

  final List<Meeting> meetings;
  final DateTime focusedDay;
  final DateTime selectedDay;
  final void Function(DateTime selected, DateTime focused) onDaySelected;
  final String userId;
  final String twgLabel;
  final ValueChanged<Meeting> onJoin;
  final ValueChanged<Meeting> onLongPress;
  final ValueChanged<Meeting> onOpen;

  @override
  Widget build(BuildContext context) {
    // Bucket every meeting by its calendar day (for the marker dots) and find
    // the calendar's bounds (pad a year either side so paging always works).
    final byDay = <DateTime, List<Meeting>>{};
    for (final m in meetings) {
      byDay.putIfAbsent(_dayKey(m.scheduledAt), () => []).add(m);
    }
    final now = DateTime.now();
    final first = DateTime.utc(now.year - 1, 1, 1);
    final last = DateTime.utc(now.year + 2, 12, 31);

    List<Meeting> eventsFor(DateTime day) => byDay[_dayKey(day)] ?? const [];

    // The selected day's meetings, soonest first; the soonest still-upcoming
    // one with video carries the inline Join pill (the screen's yellow action).
    final dayMeetings = eventsFor(selectedDay).toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
    Meeting? soonest;
    for (final m in dayMeetings) {
      if (!m.isPast && m.hasVideo) {
        soonest = m;
        break;
      }
    }

    final dayTitle = _dayLabel(selectedDay);

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
            child: _CalendarCard(
              meetings: meetings,
              focusedDay: focusedDay,
              selectedDay: selectedDay,
              firstDay: first,
              lastDay: last,
              eventsFor: eventsFor,
              onDaySelected: onDaySelected,
            ),
          ),
          const SizedBox(height: Insets.section),
          CascadeIn(index: 2, child: SectionHeader(title: dayTitle)),
          CascadeIn(
            index: 3,
            child: RowGroup(children: [
              if (dayMeetings.isEmpty)
                const ListRow(
                  icon: Icons.event_busy_rounded,
                  title: 'No meetings this day',
                  meta: 'Pick another day on the calendar above.',
                )
              else
                for (final m in dayMeetings)
                  _MeetingRow(
                    meeting: m,
                    userId: userId,
                    showJoin: identical(m, soonest),
                    onJoin: () => onJoin(m),
                    onLongPress: () => onLongPress(m),
                    onOpen: () => onOpen(m),
                  ),
            ]),
          ),
        ],
      ),
    );
  }
}

/// The month calendar, themed Bright Sun on Big Stone: gold dot markers on days
/// with meetings, a gold filled selected day, a subtle ring on today.
class _CalendarCard extends StatelessWidget {
  const _CalendarCard({
    required this.meetings,
    required this.focusedDay,
    required this.selectedDay,
    required this.firstDay,
    required this.lastDay,
    required this.eventsFor,
    required this.onDaySelected,
  });

  final List<Meeting> meetings;
  final DateTime focusedDay;
  final DateTime selectedDay;
  final DateTime firstDay;
  final DateTime lastDay;
  final List<Meeting> Function(DateTime) eventsFor;
  final void Function(DateTime selected, DateTime focused) onDaySelected;

  @override
  Widget build(BuildContext context) {
    final ivory = SovereignColors.ivory;
    final dim = ivory.withValues(alpha: SovereignColors.alphaMid);
    return Container(
      padding: const EdgeInsets.fromLTRB(Insets.sm, Insets.sm, Insets.sm, Insets.md),
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ivory.withValues(alpha: 0.07)),
      ),
      child: TableCalendar<Meeting>(
        firstDay: firstDay,
        lastDay: lastDay,
        focusedDay: focusedDay,
        currentDay: DateTime.now(),
        selectedDayPredicate: (d) => isSameDay(selectedDay, d),
        onDaySelected: onDaySelected,
        eventLoader: eventsFor,
        calendarFormat: CalendarFormat.month,
        availableCalendarFormats: const {CalendarFormat.month: 'Month'},
        startingDayOfWeek: StartingDayOfWeek.monday,
        daysOfWeekHeight: 22,
        rowHeight: 44,
        headerStyle: HeaderStyle(
          formatButtonVisible: false,
          titleCentered: true,
          titleTextStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: SovereignColors.ivory,
          ),
          leftChevronIcon:
              const Icon(Icons.chevron_left_rounded, color: SovereignColors.gold),
          rightChevronIcon:
              const Icon(Icons.chevron_right_rounded, color: SovereignColors.gold),
          headerPadding: const EdgeInsets.symmetric(vertical: Insets.xs),
        ),
        daysOfWeekStyle: DaysOfWeekStyle(
          weekdayStyle: TextStyle(
              fontFamily: 'Inter', fontSize: 11, fontWeight: FontWeight.w600, color: dim),
          weekendStyle: TextStyle(
              fontFamily: 'Inter',
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: ivory.withValues(alpha: SovereignColors.alphaLow)),
        ),
        calendarStyle: CalendarStyle(
          isTodayHighlighted: true,
          defaultTextStyle: TextStyle(fontFamily: 'Inter', fontSize: 13.5, color: ivory),
          weekendTextStyle: TextStyle(fontFamily: 'Inter', fontSize: 13.5, color: dim),
          outsideTextStyle: TextStyle(
              fontFamily: 'Inter',
              fontSize: 13.5,
              color: ivory.withValues(alpha: SovereignColors.alphaLow)),
          todayDecoration: BoxDecoration(
            color: SovereignColors.gold.withValues(alpha: 0.14),
            shape: BoxShape.circle,
            border: Border.all(color: SovereignColors.gold.withValues(alpha: 0.6)),
          ),
          todayTextStyle: const TextStyle(
              fontFamily: 'Inter', fontSize: 13.5, fontWeight: FontWeight.w700, color: SovereignColors.ivory),
          selectedDecoration:
              const BoxDecoration(color: SovereignColors.gold, shape: BoxShape.circle),
          selectedTextStyle: const TextStyle(
              fontFamily: 'Inter', fontSize: 13.5, fontWeight: FontWeight.w800, color: SovereignColors.navy),
          markerDecoration:
              const BoxDecoration(color: SovereignColors.gold, shape: BoxShape.circle),
          markerSize: 5,
          markersMaxCount: 3,
          markerMargin: const EdgeInsets.symmetric(horizontal: 1),
        ),
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
