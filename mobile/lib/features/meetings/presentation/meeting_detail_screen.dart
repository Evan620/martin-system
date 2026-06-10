// lib/features/meetings/presentation/meeting_detail_screen.dart
//
// Meeting detail — Sovereign Layout A: tabbed full view of a single meeting.
//
// A ConsumerStatefulWidget that loads the meeting (GET /meetings/{id}) plus its
// agenda (GET /meetings/{id}/agenda) and minutes (GET /meetings/{id}/minutes) in
// initState, held as a single Future<_DetailData> and rendered with a
// FutureBuilder (loading → content-shaped skeleton / error+retry / data).
// Agenda + minutes tolerate null (404 = "none").
//
// The data body is an ambient navy+gold backdrop behind a static compact
// header (back + status chip, then a bold sans title + TWG meta line) and a
// segmented tab bar:
//   * Overview — minutes/summary (when present)
//   * Agenda   — numbered items
//   * People   — attendees + their RSVPs
//   * Docs     — attached files (display-only; full open ships with Documents)
// Join + RSVP stay in a pinned bottom action bar above the floating nav.
//
// The title is the destination of the Hero keyed by meeting id (kept so a
// list-side Hero can morph in if one exists). The active tab's content
// cascades in; loading shows a skeleton header + card (no spinner). The pinned
// Join pill is the screen's ONE filled-yellow action; RSVP chips are
// gold-outline-when-selected.
//
// RSVP goes through meetingsController.setRsvp so the list screen stays in sync;
// on success we re-fetch the detail so this screen reflects the new state.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/glass/glass.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/motion/pressable.dart';
import '../../../core/motion/skeleton.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/header_card.dart';
import '../../../core/ui/section_header.dart';
import '../application/meetings_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';
import 'meetings_screen.dart' show meetingHeroTag;

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
    // Block body (not an arrow) so the setState callback returns void rather
    // than the Future from _load() — Flutter asserts on a Future-returning
    // setState callback.
    setState(() {
      _future = _load();
    });
  }

  Future<void> _join(Meeting m) async {
    final link = m.videoLink;
    if (link == null || link.isEmpty) return;
    await launchUrl(Uri.parse(link), mode: LaunchMode.externalApplication);
  }

  Future<void> _setRsvp(Meeting m, MeetingRsvp rsvp, String userId) async {
    try {
      // When the meetings list has loaded, route through the controller so the
      // list screen stays in sync. On a deep-linked detail (the list never
      // loaded → state isn't MeetingsData), the controller's setRsvp no-ops, so
      // persist directly via the repository instead — the RSVP still saves.
      final listState = ref.read(meetingsControllerProvider);
      if (listState is MeetingsData) {
        await ref
            .read(meetingsControllerProvider.notifier)
            .setRsvp(m.id, rsvp, userId);
      } else {
        await ref.read(meetingsRepositoryProvider).setMyRsvp(m.id, rsvp);
      }
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
            return const _AmbientBackdrop(
              child: SafeArea(bottom: false, child: _DetailSkeleton()),
            );
          }
          if (snapshot.hasError) {
            final err = snapshot.error;
            final message = err is MeetingException
                ? err.message
                : 'Could not open this meeting.';
            return _AmbientBackdrop(
              child: SafeArea(
                child: _DetailError(message: message, onRetry: _reload),
              ),
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

/// The loaded detail content — ambient backdrop, a static header, a tab bar
/// (Overview / Agenda / People / Docs), and a pinned Join + RSVP bar.
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
            child: SafeArea(
              bottom: false,
              child: DefaultTabController(
                length: 4,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Compact header: back + status chip, then a bold sans
                    // title with the TWG meta line under it (no serif, no
                    // eyebrow).
                    // Back button (chrome) above the header card.
                    Padding(
                      padding: const EdgeInsets.fromLTRB(Insets.lg, Insets.sm, Insets.lg, 0),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: _BackButton(onTap: () => _back(context)),
                      ),
                    ),
                    // Header card: title + TWG meta, with the status badge.
                    Padding(
                      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.md, Insets.gutter, 0),
                      child: HeaderCard(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Hero destination — keyed by the meeting id.
                                  Hero(
                                    tag: meetingHeroTag(meeting.id),
                                    flightShuttleBuilder: _heroShuttle,
                                    child: Material(
                                      type: MaterialType.transparency,
                                      child: Text(
                                        meeting.title,
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
                                    ),
                                  ),
                                  if ((meeting.twgName ?? '').isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 2),
                                      child: Text(
                                        meeting.twgName!,
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
                            _StatusBadge(status: meeting.status),
                          ],
                        ),
                      ),
                    ),
                    // Persistent info header — stays visible across all tabs so
                    // the member always sees the essentials up top.
                    Padding(
                      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.md, Insets.gutter, 0),
                      child: _InfoHeader(meeting: meeting, fmt: _fmt),
                    ),
                    // Segmented tab bar.
                    Padding(
                      padding: const EdgeInsets.fromLTRB(Insets.md, Insets.md, Insets.md, 0),
                      child: TabBar(
                        isScrollable: false,
                        indicatorColor: SovereignColors.gold,
                        indicatorWeight: 2.5,
                        indicatorSize: TabBarIndicatorSize.label,
                        labelColor: SovereignColors.gold,
                        unselectedLabelColor:
                            SovereignColors.ivory.withValues(alpha: 0.5),
                        labelStyle: SovereignType.caption
                            .copyWith(fontWeight: FontWeight.w700),
                        unselectedLabelStyle: SovereignType.caption
                            .copyWith(fontWeight: FontWeight.w500),
                        dividerColor: Colors.transparent,
                        tabs: const [
                          Tab(text: 'Overview'),
                          Tab(text: 'Agenda'),
                          Tab(text: 'People'),
                          Tab(text: 'Docs'),
                        ],
                      ),
                    ),
                    Expanded(
                      child: TabBarView(
                        children: [
                          // ---- Overview ----
                          // Facts moved to the persistent header; Overview now
                          // leads with the minutes/summary in its own inner panel.
                          _TabScroll(children: [
                            CascadeIn(
                              index: 0,
                              child: _OuterSection(
                                label: 'Minutes',
                                children: [
                                  _InnerPanel(
                                    child: Text(
                                      hasMinutes
                                          ? data.minutes!.trim()
                                          : 'No minutes yet.',
                                      style: SovereignType.body.copyWith(
                                        color: SovereignColors.ivory.withValues(
                                          alpha: hasMinutes
                                              ? SovereignColors.alphaHigh
                                              : SovereignColors.alphaLow,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ]),
                          // ---- Agenda ----
                          _TabScroll(children: [
                            if (hasAgenda)
                              CascadeIn(
                                index: 0,
                                child: _OuterSection(
                                  label: 'Agenda',
                                  children: [
                                    for (var i = 0; i < agendaLines.length; i++)
                                      _InnerPanel(
                                        child: _AgendaRow(
                                          number: i + 1,
                                          text: agendaLines[i],
                                        ),
                                      ),
                                  ],
                                ),
                              )
                            else
                              const _EmptyTab('No agenda yet.'),
                          ]),
                          // ---- People ----
                          _TabScroll(children: [
                            if (meeting.participants.isNotEmpty)
                              CascadeIn(
                                index: 0,
                                child: _OuterSection(
                                  label: 'Attendees',
                                  children: [
                                    for (final p in meeting.participants)
                                      _InnerPanel(
                                        child: _AttendeeRow(participant: p),
                                      ),
                                  ],
                                ),
                              )
                            else
                              const _EmptyTab('No attendees listed.'),
                          ]),
                          // ---- Docs ----
                          _TabScroll(children: [
                            if (meeting.documents.isNotEmpty)
                              CascadeIn(
                                index: 0,
                                child: _OuterSection(
                                  label: 'Documents',
                                  children: [
                                    for (final d in meeting.documents)
                                      _InnerPanel(
                                        child: _DocumentRow(document: d),
                                      ),
                                  ],
                                ),
                              )
                            else
                              const _EmptyTab('No documents attached.'),
                          ]),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
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
      context.go('/meetings');
    }
  }

  /// Keeps the title legible (single style) mid-flight.
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

/// A padded, scrollable tab body that clears the pinned action bar + floating nav.
class _TabScroll extends StatelessWidget {
  const _TabScroll({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
          .add(navClearance(context, extra: 96)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: children,
      ),
    );
  }
}

/// A gentle empty state for a tab with no content.
class _EmptyTab extends StatelessWidget {
  const _EmptyTab(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 48),
      child: Center(
        child: Text(
          text,
          style: SovereignType.secondary.copyWith(
            color:
                SovereignColors.ivory.withValues(alpha: SovereignColors.alphaLow),
          ),
        ),
      ),
    );
  }
}

/// Loading — a content-shaped skeleton: a header block + the info-card shape,
/// cross-fading to the real content once loaded (no spinner).
class _DetailSkeleton extends StatelessWidget {
  const _DetailSkeleton();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.xl, Insets.gutter, 0),
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
        // Minimal one-row bar: Join (left) + a compact RSVP chip (right) that
        // opens a small popup, dismissing on choice or outside-tap.
        child: Row(
          children: [
            if (meeting.hasVideo) _JoinPill(onTap: onJoin),
            const Spacer(),
            if (isParticipant)
              _RsvpControl(current: myRsvp, onRsvp: onRsvp),
          ],
        ),
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
            fontFamily: 'Inter',
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

/// The persistent info header — an outer [GlassCard] wrapping a [Wrap] of
/// glass-inside-glass fact chips (date·time, duration, location/Virtual,
/// attendee count). Stays visible across all tabs, kept compact (1–2 rows).
class _InfoHeader extends StatelessWidget {
  const _InfoHeader({required this.meeting, required this.fmt});

  final Meeting meeting;
  final DateFormat fmt;

  @override
  Widget build(BuildContext context) {
    final location = (meeting.location ?? '').trim();
    final locationLabel = location.isNotEmpty
        ? location
        : (meeting.hasVideo ? 'Virtual' : null);
    final attendees = meeting.participants.length;

    return GlassCard(
      padding: const EdgeInsets.all(Insets.md),
      child: Wrap(
        spacing: Insets.sm,
        runSpacing: Insets.sm,
        children: [
          _FactChip(
            icon: Icons.event,
            text: fmt.format(meeting.scheduledAt),
          ),
          _FactChip(
            icon: Icons.schedule,
            text: '${meeting.durationMinutes} min',
          ),
          if (locationLabel != null)
            _FactChip(
              icon: locationLabel == 'Virtual'
                  ? Icons.videocam_outlined
                  : Icons.place_outlined,
              text: locationLabel,
            ),
          if (attendees > 0)
            _FactChip(
              icon: Icons.group_outlined,
              text: '$attendees attending',
            ),
        ],
      ),
    );
  }
}

/// A compact glass-inside-glass fact chip: small gold icon + short text, in a
/// recessed [GlassSurface.inner] panel. Used inside [_InfoHeader].
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

/// An outer tab section frame — an optional [SectionHeader] above a raised
/// card (navyRaised + hairline border) that holds one [_InnerPanel] per
/// logical item, stacked with ~8px gaps. The card-inside-card shell for tab
/// content: this lighter raised frame pops from the navy backdrop while its
/// inner panels recess into it.
class _OuterSection extends StatelessWidget {
  const _OuterSection({this.label, required this.children});

  final String? label;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) SectionHeader(title: label!),
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

/// A single recessed inner panel — one logical item inside an [_OuterSection].
/// Deeper navy + its own hairline border so it clearly reads as a card nested
/// inside the lighter outer frame.
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
        border: Border.all(color: SovereignColors.ivory.withValues(alpha: 0.06)),
      ),
      child: child,
    );
  }
}

/// One numbered agenda line: a small gold number badge + the line text.
class _AgendaRow extends StatelessWidget {
  const _AgendaRow({required this.number, required this.text});

  final int number;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 22,
          height: 22,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
                color: SovereignColors.gold.withValues(alpha: 0.55), width: 1),
          ),
          child: Text(
            '$number',
            style: const TextStyle(
              fontFamily: 'Inter',
              color: SovereignColors.gold,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: Insets.md),
        Expanded(
          child: Text(
            text,
            style: SovereignType.body.copyWith(
              color: SovereignColors.ivory
                  .withValues(alpha: SovereignColors.alphaHigh),
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
    return Semantics(
      button: true,
      label: document.name,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        // This detail screen is a top-level pushed route (not the Documents shell
        // branch), so a cross-branch push to /documents/:id/pdf is unsafe. Open
        // the document through Martin instead — works from any screen.
        onTap: () => context.push(
          '/martin?q=${Uri.encodeQueryComponent('Open the document ${document.name}')}',
        ),
        child: Row(
          children: [
            const Icon(Icons.insert_drive_file_outlined,
                size: 16, color: SovereignColors.gold),
            const SizedBox(width: Insets.md),
            Expanded(
              child: Text(
                document.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: SovereignType.body.copyWith(
                  color: SovereignColors.ivory
                      .withValues(alpha: SovereignColors.alphaHigh),
                ),
              ),
            ),
            const SizedBox(width: Insets.sm),
            const Icon(Icons.chevron_right,
                size: 16, color: SovereignColors.gold),
          ],
        ),
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
    final name = (participant.name ?? '').isNotEmpty
        ? participant.name!
        : 'Participant';
    return Row(
      children: [
        Expanded(
          child: Text(
            name,
            style: SovereignType.body.copyWith(
              color: SovereignColors.ivory
                  .withValues(alpha: SovereignColors.alphaHigh),
            ),
          ),
        ),
        const SizedBox(width: Insets.md),
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
            fontFamily: 'Inter',
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

/// The gold "Join" call-to-action pill — the screen's ONE solid-gold action.
class _JoinPill extends StatelessWidget {
  const _JoinPill({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Join meeting',
      child: GestureDetector(
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
            padding: EdgeInsets.symmetric(horizontal: 18, vertical: 11),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.videocam, size: 15, color: SovereignColors.navy),
                SizedBox(width: 6),
                Text(
                  'Join meeting',
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

/// One RSVP option chip (mirrors the list screen's chip styling): a ≥44px
/// gold-OUTLINE pill when selected so the pinned Join stays the only solid gold.
/// Minimal RSVP control: a compact chip showing the current reply. Tapping it
/// opens a small popup (Material [showMenu]) with the three options — the popup
/// dismisses automatically when an option is chosen OR the user taps outside.
/// The chosen reply persists via [onRsvp]; the chip then reflects it.
class _RsvpControl extends StatelessWidget {
  const _RsvpControl({required this.current, required this.onRsvp});

  final MeetingRsvp current;
  final ValueChanged<MeetingRsvp> onRsvp;

  static (String, IconData) _display(MeetingRsvp r) => switch (r) {
        MeetingRsvp.going => ('Going', Icons.check_circle_rounded),
        MeetingRsvp.maybe => ('Maybe', Icons.help_rounded),
        MeetingRsvp.no => ('Not going', Icons.cancel_rounded),
        MeetingRsvp.pending => ('RSVP', Icons.event_available_rounded),
      };

  Future<void> _open(BuildContext context) async {
    final box = context.findRenderObject() as RenderBox;
    final overlay =
        Overlay.of(context).context.findRenderObject() as RenderBox;
    final position = RelativeRect.fromRect(
      Rect.fromPoints(
        box.localToGlobal(Offset.zero, ancestor: overlay),
        box.localToGlobal(box.size.bottomRight(Offset.zero), ancestor: overlay),
      ),
      Offset.zero & overlay.size,
    );

    PopupMenuItem<MeetingRsvp> item(MeetingRsvp r) {
      final (label, icon) = _display(r);
      final sel = r == current;
      return PopupMenuItem<MeetingRsvp>(
        value: r,
        height: 46,
        child: Row(
          children: [
            Icon(icon,
                size: 18,
                color: sel
                    ? SovereignColors.gold
                    : SovereignColors.ivory
                        .withValues(alpha: SovereignColors.alphaMid)),
            const SizedBox(width: Insets.md),
            Text(
              label,
              style: SovereignType.body.copyWith(
                color: sel ? SovereignColors.gold : SovereignColors.ivory,
                fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            if (sel) ...[
              const Spacer(),
              const Icon(Icons.check_rounded,
                  size: 16, color: SovereignColors.gold),
            ],
          ],
        ),
      );
    }

    final choice = await showMenu<MeetingRsvp>(
      context: context,
      position: position,
      color: SovereignColors.navyRaised,
      elevation: 8,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side:
            BorderSide(color: SovereignColors.ivory.withValues(alpha: 0.08)),
      ),
      items: [
        item(MeetingRsvp.going),
        item(MeetingRsvp.maybe),
        item(MeetingRsvp.no),
      ],
    );
    if (choice != null) onRsvp(choice);
  }

  @override
  Widget build(BuildContext context) {
    final (label, icon) = _display(current);
    final set = current != MeetingRsvp.pending;
    return Semantics(
      button: true,
      label: 'RSVP, currently $label',
      child: PressableScale(
        onTap: () => _open(context),
        child: Container(
          height: 40,
          padding: const EdgeInsets.symmetric(horizontal: Insets.md),
          decoration: BoxDecoration(
            color: set
                ? SovereignColors.gold.withValues(alpha: 0.12)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: SovereignColors.gold.withValues(alpha: set ? 0.85 : 0.45),
              width: set ? 1.4 : 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 16, color: SovereignColors.gold),
              const SizedBox(width: Insets.sm),
              Text(
                label,
                style: SovereignType.caption.copyWith(
                  color: SovereignColors.gold,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 2),
              const Icon(Icons.keyboard_arrow_down_rounded,
                  size: 16, color: SovereignColors.gold),
            ],
          ),
        ),
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
