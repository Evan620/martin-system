// lib/features/meetings/presentation/meetings_screen.dart
//
// Meetings — Sovereign glass list of the member's sessions, wired to live data.
//
// Loads via meetingsControllerProvider.load() (post-frame), renders by sealed
// state (loading / error / empty / data), an Upcoming|Past toggle, a gold Join
// pill (url_launcher) when a video_link is present, and member RSVP chips
// (Going/Maybe/No) that call meetingsController.setRsvp — surfacing a SnackBar
// on MeetingException. Tapping a card body pushes /meetings/:id.
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
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/meetings_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';

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
        child: switch (state) {
          MeetingsLoading() => const Center(
              child: CircularProgressIndicator(color: SovereignColors.gold),
            ),
          MeetingsError(:final message) => _ErrorView(
              message: message,
              onRetry: () =>
                  ref.read(meetingsControllerProvider.notifier).load(),
            ),
          MeetingsEmpty() => const _EmptyView(),
          MeetingsData(:final meetings) => _DataView(
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

/// Loaded list state: header, Upcoming|Past toggle, then filtered cards.
class _DataView extends StatelessWidget {
  const _DataView({
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final shown = meetings.where((m) => showPast ? m.isPast : !m.isPast).toList()
      ..sort((a, b) => showPast
          ? b.scheduledAt.compareTo(a.scheduledAt)
          : a.scheduledAt.compareTo(b.scheduledAt));

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            twgName.toUpperCase(),
            style: theme.textTheme.bodySmall?.copyWith(
              color: SovereignColors.gold,
              letterSpacing: 3,
              fontSize: 10,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Meetings',
            style: theme.textTheme.displaySmall?.copyWith(fontSize: 34),
          ),
          const SizedBox(height: 4),
          Text(
            showPast ? 'Your past sessions' : 'Your upcoming sessions',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: SovereignColors.ivory.withValues(alpha: 0.65),
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 18),
          _UpcomingPastToggle(showPast: showPast, onToggle: onToggle),
          const SizedBox(height: 18),
          if (shown.isEmpty)
            _InlineEmpty(showPast: showPast)
          else
            for (final meeting in shown) ...[
              _MeetingCard(
                meeting: meeting,
                userId: userId,
                onJoin: () => onJoin(meeting),
                onRsvp: (rsvp) => onRsvp(meeting, rsvp, userId),
                onOpen: () => onOpen(meeting),
              ),
              const SizedBox(height: 14),
            ],
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
          const SizedBox(width: 4),
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
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: selected ? SovereignColors.gold : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 9),
            child: Center(
              child: Text(
                label,
                style: TextStyle(
                  color: selected
                      ? SovereignColors.navy
                      : SovereignColors.ivory.withValues(alpha: 0.85),
                  fontSize: 12.5,
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

/// A single meeting rendered as a tappable raised GlassCard. Glass-inside-glass:
/// the RSVP chip row is a lighter GlassSurface.inner layer.
class _MeetingCard extends StatelessWidget {
  const _MeetingCard({
    required this.meeting,
    required this.userId,
    required this.onJoin,
    required this.onRsvp,
    required this.onOpen,
  });

  final Meeting meeting;
  final String userId;
  final VoidCallback onJoin;
  final ValueChanged<MeetingRsvp> onRsvp;
  final VoidCallback onOpen;

  static final _fmt = DateFormat('EEE d MMM · HH:mm');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isParticipant = meeting.isParticipant(userId);
    final myRsvp = meeting.myRsvp(userId);
    final subtitle = [
      _fmt.format(meeting.scheduledAt),
      if ((meeting.location ?? '').isNotEmpty) meeting.location!,
    ].join(' · ');

    return GlassCard(
      onTap: onOpen,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title + Join pill.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  meeting.title,
                  style: theme.textTheme.titleLarge?.copyWith(fontSize: 19),
                ),
              ),
              if (meeting.hasVideo) ...[
                const SizedBox(width: 12),
                _JoinPill(onTap: onJoin),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(
                Icons.schedule,
                size: 13,
                color: SovereignColors.gold,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  subtitle,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: SovereignColors.ivory.withValues(alpha: 0.72),
                    fontSize: 12.5,
                  ),
                ),
              ),
            ],
          ),

          // RSVP row — shown only to participants. Three inner-glass chips,
          // the selected one gold.
          if (isParticipant) ...[
            const SizedBox(height: 14),
            const _SectionLabel('RSVP'),
            const SizedBox(height: 6),
            Row(
              children: [
                _RsvpChip(
                  label: 'Going',
                  selected: myRsvp == MeetingRsvp.going,
                  onTap: () => onRsvp(MeetingRsvp.going),
                ),
                const SizedBox(width: 8),
                _RsvpChip(
                  label: 'Maybe',
                  selected: myRsvp == MeetingRsvp.maybe,
                  onTap: () => onRsvp(MeetingRsvp.maybe),
                ),
                const SizedBox(width: 8),
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
    );
  }
}

/// Small uppercase gold section label (matches the Sovereign mockup `.lab2`).
class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: const TextStyle(
        color: SovereignColors.gold,
        fontSize: 9,
        letterSpacing: 2.4,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

/// The gold "Join" call-to-action pill.
class _JoinPill extends StatelessWidget {
  const _JoinPill({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
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
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.videocam, size: 14, color: SovereignColors.navy),
              SizedBox(width: 6),
              Text(
                'Join',
                style: TextStyle(
                  color: SovereignColors.navy,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// One RSVP option as a lighter inner-glass chip. When [selected], the chip
/// fills with Sovereign gold and the label flips to navy.
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
    final labelStyle = TextStyle(
      color: selected
          ? SovereignColors.navy
          : SovereignColors.ivory.withValues(alpha: 0.85),
      fontSize: 12.5,
      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
    );

    final content = Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Text(label, style: labelStyle),
      ),
    );

    final Widget chip;
    if (selected) {
      // Selected chip: solid gold (not glass) so it reads as the active choice.
      chip = DecoratedBox(
        decoration: BoxDecoration(
          color: SovereignColors.gold,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: SovereignColors.gold.withValues(alpha: 0.22),
              blurRadius: 12,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: content,
      );
    } else {
      // Unselected chips: lighter nested glass layer.
      chip = GlassSurface.inner(
        borderRadius: 12,
        child: content,
      );
    }

    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: chip,
      ),
    );
  }
}

/// Error state: a glass message + a Retry button.
class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off,
                  color: SovereignColors.gold, size: 28),
              const SizedBox(height: 12),
              Text(
                message,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: SovereignColors.ivory.withValues(alpha: 0.85),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: onRetry,
                child: const Text(
                  'Retry',
                  style: TextStyle(
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

/// Full-screen empty state (no meetings at all).
class _EmptyView extends StatelessWidget {
  const _EmptyView();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.event_available,
                  color: SovereignColors.gold, size: 30),
              const SizedBox(height: 12),
              Text(
                'No meetings scheduled yet',
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium?.copyWith(fontSize: 16),
              ),
              const SizedBox(height: 6),
              Text(
                "When your TWG schedules a session, it'll appear here.",
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: SovereignColors.ivory.withValues(alpha: 0.65),
                  fontSize: 12.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Inline empty state shown under the toggle when one side has no meetings.
class _InlineEmpty extends StatelessWidget {
  const _InlineEmpty({required this.showPast});

  final bool showPast;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GlassCard(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            showPast ? 'No past meetings.' : 'No upcoming meetings.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: SovereignColors.ivory.withValues(alpha: 0.7),
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}
