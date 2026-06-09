// lib/features/meetings/presentation/meeting_detail_screen.dart
//
// Meeting detail — Sovereign Layout B: dense-data full view of a single meeting.
//
// A ConsumerStatefulWidget that loads the meeting (GET /meetings/{id}) plus its
// agenda (GET /meetings/{id}/agenda) and minutes (GET /meetings/{id}/minutes) in
// initState, held as a single Future<_DetailData> and rendered with a
// FutureBuilder (loading / error+retry / data). Agenda + minutes tolerate null
// (404 = "none").
//
// The data body is an ambient navy+gold backdrop behind a CustomScrollView:
//   * a collapsing SliverAppBar header — TWG eyebrow + serif title + status badge
//   * expandable sections (Agenda / Attendees / Documents / Minutes) with counts
//   * a pinned bottom action bar (Join + RSVP) that sits above the floating nav.
//
// Documents rows are display-only this pass (tapping shows a SnackBar);
// full open/preview ships with the Documents sub-project. RSVP goes through
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

/// The meeting plus its (optional) agenda + minutes, loaded together.
class _DetailData {
  const _DetailData({required this.meeting, this.agenda, this.minutes});
  final Meeting meeting;
  final String? agenda;
  final String? minutes;
}

/// Full detail view for one meeting, loaded by [meetingId].
class MeetingDetailScreen extends ConsumerStatefulWidget {
  const MeetingDetailScreen({super.key, required this.meetingId});

  final String meetingId;

  @override
  ConsumerState<MeetingDetailScreen> createState() =>
      _MeetingDetailScreenState();
}

class _MeetingDetailScreenState extends ConsumerState<MeetingDetailScreen> {
  late Future<_DetailData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_DetailData> _load() async {
    final repo = ref.read(meetingsRepositoryProvider);
    final meeting = await repo.meetingDetail(widget.meetingId);
    final agenda = await repo.meetingAgenda(widget.meetingId);
    final minutes = await repo.meetingMinutes(widget.meetingId);
    return _DetailData(meeting: meeting, agenda: agenda, minutes: minutes);
  }

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
      body: FutureBuilder<_DetailData>(
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
            return SafeArea(
              child: _DetailError(message: message, onRetry: _reload),
            );
          }
          final data = snapshot.data!;
          return _DetailBody(
            data: data,
            userId: userId,
            onJoin: () => _join(data.meeting),
            onRsvp: (rsvp) => _setRsvp(data.meeting, rsvp, userId),
          );
        },
      ),
    );
  }
}

/// The loaded detail content — ambient backdrop, collapsing header, expandable
/// sections, and a pinned Join + RSVP bar.
class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.data,
    required this.userId,
    required this.onJoin,
    required this.onRsvp,
  });

  final _DetailData data;
  final String userId;
  final VoidCallback onJoin;
  final ValueChanged<MeetingRsvp> onRsvp;

  static final _fmt = DateFormat('EEEE, d MMMM · HH:mm');

  Meeting get _meeting => data.meeting;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final meeting = _meeting;
    final isParticipant = meeting.isParticipant(userId);
    final myRsvp = meeting.myRsvp(userId);

    final agendaLines = (data.agenda ?? '')
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    final hasAgenda = agendaLines.isNotEmpty;
    final hasMinutes = (data.minutes ?? '').trim().isNotEmpty;

    final showActions = meeting.hasVideo || isParticipant;

    return _AmbientBackdrop(
      child: Stack(
        children: [
          Positioned.fill(
            child: CustomScrollView(
              slivers: [
                SliverAppBar(
                  pinned: true,
                  expandedHeight: 150,
                  backgroundColor: Colors.transparent,
                  surfaceTintColor: Colors.transparent,
                  elevation: 0,
                  leadingWidth: 64,
                  leading: Padding(
                    padding: const EdgeInsets.only(left: 16, top: 8, bottom: 8),
                    child: _BackButton(onTap: () => _back(context)),
                  ),
                  flexibleSpace: FlexibleSpaceBar(
                    titlePadding:
                        const EdgeInsets.only(left: 20, right: 20, bottom: 14),
                    title: Text(
                      meeting.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontFamily: 'serif',
                        color: SovereignColors.ivory,
                        fontSize: 19,
                      ),
                    ),
                    background: SafeArea(
                      bottom: false,
                      child: Padding(
                        padding:
                            const EdgeInsets.fromLTRB(20, 12, 20, 44),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.end,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if ((meeting.twgName ?? '').isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Text(
                                  meeting.twgName!.toUpperCase(),
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: SovereignColors.gold,
                                    letterSpacing: 3,
                                    fontSize: 10,
                                  ),
                                ),
                              ),
                            _StatusBadge(status: meeting.status),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
                    child: GlassCard(
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
                            _IconRow(
                                icon: Icons.place_outlined,
                                text: meeting.location!),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
                if (hasAgenda)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                      child: _ExpandableSection(
                        label: 'Agenda',
                        count: agendaLines.length,
                        initiallyOpen: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (final line in agendaLines)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Text(
                                  line,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    color: SovereignColors.ivory
                                        .withValues(alpha: 0.85),
                                    fontSize: 13.5,
                                    height: 1.4,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                if (meeting.participants.isNotEmpty)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                      child: _ExpandableSection(
                        label: 'Attendees',
                        count: meeting.participants.length,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0;
                                i < meeting.participants.length;
                                i++) ...[
                              if (i > 0) const SizedBox(height: 10),
                              _AttendeeRow(
                                  participant: meeting.participants[i]),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
                if (meeting.documents.isNotEmpty)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                      child: _ExpandableSection(
                        label: 'Documents',
                        count: meeting.documents.length,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0;
                                i < meeting.documents.length;
                                i++) ...[
                              if (i > 0) const SizedBox(height: 10),
                              _DocumentRow(document: meeting.documents[i]),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
                if (hasMinutes)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                      child: _ExpandableSection(
                        label: 'Minutes',
                        count: null,
                        child: Text(
                          data.minutes!.trim(),
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color:
                                SovereignColors.ivory.withValues(alpha: 0.85),
                            fontSize: 13.5,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ),
                  ),
                // Clear the pinned action bar (~84) + the floating nav (~92).
                const SliverToBoxAdapter(child: SizedBox(height: 200)),
              ],
            ),
          ),
          if (showActions)
            Positioned(
              left: 0,
              right: 0,
              bottom: 92, // sit above the floating nav
              child: _ActionBar(
                meeting: meeting,
                isParticipant: isParticipant,
                myRsvp: myRsvp,
                onJoin: onJoin,
                onRsvp: onRsvp,
              ),
            ),
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

/// Ambient Sovereign backdrop — navy gradient with a top-right gold radial glow.
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

/// The pinned bottom action bar: a Join pill (when video) + the three RSVP
/// chips (participants only), in a glass surface above the floating nav.
class _ActionBar extends StatelessWidget {
  const _ActionBar({
    required this.meeting,
    required this.isParticipant,
    required this.myRsvp,
    required this.onJoin,
    required this.onRsvp,
  });

  final Meeting meeting;
  final bool isParticipant;
  final MeetingRsvp myRsvp;
  final VoidCallback onJoin;
  final ValueChanged<MeetingRsvp> onRsvp;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 18),
      child: GlassSurface(
        borderRadius: 24,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        goldGlow: true,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (meeting.hasVideo)
              Align(
                alignment: Alignment.centerLeft,
                child: _JoinPill(onTap: onJoin),
              ),
            if (meeting.hasVideo && isParticipant)
              const SizedBox(height: 10),
            if (isParticipant)
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
        ),
      ),
    );
  }
}

/// A collapsible glass section card with a tappable header + count badge.
class _ExpandableSection extends StatefulWidget {
  const _ExpandableSection({
    required this.label,
    required this.count,
    required this.child,
    this.initiallyOpen = false,
  });

  final String label;
  final int? count;
  final Widget child;
  final bool initiallyOpen;

  @override
  State<_ExpandableSection> createState() => _ExpandableSectionState();
}

class _ExpandableSectionState extends State<_ExpandableSection> {
  late bool _open = widget.initiallyOpen;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => setState(() => _open = !_open),
            child: Row(
              children: [
                _SectionLabel(widget.count == null
                    ? widget.label
                    : '${widget.label} · ${widget.count}'),
                const Spacer(),
                AnimatedRotation(
                  turns: _open ? 0.25 : 0,
                  duration: const Duration(milliseconds: 200),
                  child: const Icon(Icons.chevron_right,
                      color: SovereignColors.gold, size: 18),
                ),
              ],
            ),
          ),
          AnimatedSize(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
            alignment: Alignment.topCenter,
            child: _open
                ? Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: widget.child)
                : const SizedBox(width: double.infinity),
          ),
        ],
      ),
    );
  }
}

/// A gold-outline status pill mapping the backend status to a member label.
class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final label = switch (status.toUpperCase()) {
      'SCHEDULED' => 'Scheduled',
      'IN_PROGRESS' => 'In progress',
      'COMPLETED' => 'Completed',
      'CANCELLED' => 'Cancelled',
      _ => status,
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(
            color: SovereignColors.gold.withValues(alpha: 0.55), width: 1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        child: Text(
          label.toUpperCase(),
          style: const TextStyle(
            color: SovereignColors.gold,
            fontSize: 10,
            letterSpacing: 1.6,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
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

/// One attached document: a type badge + file name (display-only this pass).
class _DocumentRow extends StatelessWidget {
  const _DocumentRow({required this.document});

  final MeetingDocument document;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
              const SnackBar(content: Text('Opens in Documents')));
      },
      child: Row(
        children: [
          Icon(Icons.insert_drive_file_outlined,
              size: 16, color: SovereignColors.gold),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              document.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: SovereignColors.ivory.withValues(alpha: 0.88),
                fontSize: 13.5,
              ),
            ),
          ),
          const SizedBox(width: 8),
          const Icon(Icons.chevron_right,
              size: 16, color: SovereignColors.gold),
        ],
      ),
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
