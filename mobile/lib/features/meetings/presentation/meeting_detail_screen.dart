// lib/features/meetings/presentation/meeting_detail_screen.dart
//
// Meeting detail — Sovereign glass full view of a single meeting, fetched by id.
//
// A ConsumerStatefulWidget that loads GET /meetings/{id} via the repository in
// initState (held as a Future and rendered with a FutureBuilder), showing
// loading / error+retry / data states. The data body shows the serif title,
// full date/time + duration, location, a gold Join pill (url_launcher) when a
// video_link is present, an attendees list with each participant's RSVP, and —
// for participants only — the member's own RSVP control. RSVP goes through
// meetingsController.setRsvp so the list screen stays in sync; on success we
// re-fetch the detail so this screen reflects the new state.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../application/meetings_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';

/// Full detail view for one meeting, loaded by [meetingId].
class MeetingDetailScreen extends ConsumerStatefulWidget {
  const MeetingDetailScreen({super.key, required this.meetingId});

  final String meetingId;

  @override
  ConsumerState<MeetingDetailScreen> createState() =>
      _MeetingDetailScreenState();
}

class _MeetingDetailScreenState extends ConsumerState<MeetingDetailScreen> {
  late Future<Meeting> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Meeting> _load() =>
      ref.read(meetingsRepositoryProvider).meetingDetail(widget.meetingId);

  void _reload() {
    setState(() => _future = _load());
  }

  Future<void> _join(Meeting m) async {
    final link = m.videoLink;
    if (link == null || link.isEmpty) return;
    await launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication);
  }

  Future<void> _setRsvp(Meeting m, MeetingRsvp rsvp, String userId) async {
    try {
      await ref
          .read(meetingsControllerProvider.notifier)
          .setRsvp(m.id, rsvp, userId);
      // Keep this screen in sync with the persisted state.
      _reload();
    } on MeetingException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final userId = ref.watch(currentUserIdProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: FutureBuilder<Meeting>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(
                child: CircularProgressIndicator(color: SovereignColors.gold),
              );
            }
            if (snapshot.hasError) {
              final err = snapshot.error;
              final message = err is MeetingException
                  ? err.message
                  : 'Could not open this meeting.';
              return _DetailError(message: message, onRetry: _reload);
            }
            final meeting = snapshot.data!;
            return _DetailBody(
              meeting: meeting,
              userId: userId,
              onJoin: () => _join(meeting),
              onRsvp: (rsvp) => _setRsvp(meeting, rsvp, userId),
            );
          },
        ),
      ),
    );
  }
}

/// The loaded detail content (title, time, location, Join, attendees, RSVP).
class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.meeting,
    required this.userId,
    required this.onJoin,
    required this.onRsvp,
  });

  final Meeting meeting;
  final String userId;
  final VoidCallback onJoin;
  final ValueChanged<MeetingRsvp> onRsvp;

  static final _fmt = DateFormat('EEEE, d MMMM · HH:mm');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isParticipant = meeting.isParticipant(userId);
    final myRsvp = meeting.myRsvp(userId);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Back affordance.
          Align(
            alignment: Alignment.centerLeft,
            child: _BackButton(onTap: () => _back(context)),
          ),
          const SizedBox(height: 12),
          if ((meeting.twgName ?? '').isNotEmpty) ...[
            Text(
              meeting.twgName!.toUpperCase(),
              style: theme.textTheme.bodySmall?.copyWith(
                color: SovereignColors.gold,
                letterSpacing: 3,
                fontSize: 10,
              ),
            ),
            const SizedBox(height: 6),
          ],
          Text(
            meeting.title,
            style: theme.textTheme.displaySmall?.copyWith(fontSize: 30),
          ),
          const SizedBox(height: 16),

          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _IconRow(
                  icon: Icons.schedule,
                  text:
                      '${_fmt.format(meeting.scheduledAt)} · ${meeting.durationMinutes} min',
                ),
                if ((meeting.location ?? '').isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _IconRow(icon: Icons.place_outlined, text: meeting.location!),
                ],
                if (meeting.hasVideo) ...[
                  const SizedBox(height: 16),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: _JoinPill(onTap: onJoin),
                  ),
                ],
              ],
            ),
          ),

          // Attendees.
          if (meeting.participants.isNotEmpty) ...[
            const SizedBox(height: 16),
            const _SectionLabel('Attendees'),
            const SizedBox(height: 8),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < meeting.participants.length; i++) ...[
                    if (i > 0) const SizedBox(height: 10),
                    _AttendeeRow(participant: meeting.participants[i]),
                  ],
                ],
              ),
            ),
          ],

          // The member's own RSVP control (participants only).
          if (isParticipant) ...[
            const SizedBox(height: 16),
            const _SectionLabel('Your RSVP'),
            const SizedBox(height: 8),
            GlassCard(
              child: Row(
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
            ),
          ],
        ],
      ),
    );
  }

  void _back(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/');
    }
  }
}

/// A small glass circular back button.
class _BackButton extends StatelessWidget {
  const _BackButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: const GlassSurface(
        borderRadius: 14,
        padding: EdgeInsets.all(10),
        child: Icon(Icons.arrow_back, size: 18, color: SovereignColors.ivory),
      ),
    );
  }
}

/// A gold-icon + text row used for time / location.
class _IconRow extends StatelessWidget {
  const _IconRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 15, color: SovereignColors.gold),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: SovereignColors.ivory.withValues(alpha: 0.82),
              fontSize: 13,
            ),
          ),
        ),
      ],
    );
  }
}

/// One attendee: name + their RSVP as a small chip.
class _AttendeeRow extends StatelessWidget {
  const _AttendeeRow({required this.participant});

  final MeetingParticipant participant;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final name = (participant.name ?? '').isNotEmpty
        ? participant.name!
        : 'Participant';
    return Row(
      children: [
        Expanded(
          child: Text(
            name,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: SovereignColors.ivory.withValues(alpha: 0.88),
              fontSize: 13.5,
            ),
          ),
        ),
        const SizedBox(width: 12),
        _RsvpBadge(rsvp: participant.rsvp),
      ],
    );
  }
}

/// A small read-only RSVP status badge.
class _RsvpBadge extends StatelessWidget {
  const _RsvpBadge({required this.rsvp});

  final MeetingRsvp rsvp;

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (rsvp) {
      MeetingRsvp.going => ('Going', SovereignColors.gold),
      MeetingRsvp.maybe => ('Maybe', SovereignColors.ivory),
      MeetingRsvp.no => ('No', SovereignColors.ivory),
      MeetingRsvp.pending => ('No reply', SovereignColors.ivory),
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: color.withValues(alpha: 0.5), width: 1),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        child: Text(
          label,
          style: TextStyle(
            color: color.withValues(alpha: 0.9),
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}

/// Small uppercase gold section label.
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
          padding: EdgeInsets.symmetric(horizontal: 18, vertical: 9),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.videocam, size: 15, color: SovereignColors.navy),
              SizedBox(width: 6),
              Text(
                'Join meeting',
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

/// One RSVP option chip (mirrors the list screen's chip styling).
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
      chip = GlassSurface.inner(borderRadius: 12, child: content);
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

/// Error state with a Retry action.
class _DetailError extends StatelessWidget {
  const _DetailError({required this.message, required this.onRetry});

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
