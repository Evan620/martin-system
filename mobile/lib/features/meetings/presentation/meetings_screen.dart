// lib/features/meetings/presentation/meetings_screen.dart
//
// Meetings — Sovereign glass list of the member's upcoming sessions.
//
// Visual build only: representative seed content (Amina Diallo / Energy TWG),
// live API data is a later pass. Uses the Sovereign glass design system
// (lib/core/glass/glass.dart) with glass-inside-glass: each outer GlassCard
// holds lighter GlassSurface.inner panels (agenda + RSVP chips).
import 'package:flutter/material.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';

/// RSVP states for a meeting.
enum _Rsvp { going, maybe, no }

/// Representative seed meeting (visual build only).
class _Meeting {
  const _Meeting({
    required this.title,
    required this.when,
    required this.location,
    required this.rsvp,
    this.agenda,
  });

  final String title;
  final String when;
  final String location;
  final _Rsvp rsvp;

  /// Optional agenda lines, rendered inside an inner-glass panel.
  final List<String>? agenda;
}

const _seedMeetings = <_Meeting>[
  _Meeting(
    title: 'TWG Energy Sync',
    when: 'Mon 8 Jun · 14:00–15:00',
    location: 'Virtual',
    rsvp: _Rsvp.going,
    agenda: <String>[
      '1 · Review Q2 targets',
      '2 · Grid interconnection',
      '3 · Next steps',
    ],
  ),
  _Meeting(
    title: 'Steering Committee',
    when: 'Wed 10 Jun · 10:00–11:30',
    location: 'Hybrid · Room A',
    rsvp: _Rsvp.maybe,
  ),
  _Meeting(
    title: 'Doc review',
    when: 'Fri 12 Jun · 09:00–09:45',
    location: 'Virtual',
    rsvp: _Rsvp.no,
  ),
];

/// Meetings screen: serif title + a scrollable list of glass meeting cards.
class MeetingsScreen extends StatelessWidget {
  const MeetingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'ENERGY TWG',
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
                'Your upcoming sessions, Amina',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: SovereignColors.ivory.withValues(alpha: 0.65),
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 20),
              for (final meeting in _seedMeetings) ...[
                _MeetingCard(meeting: meeting),
                const SizedBox(height: 14),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// A single meeting rendered as a raised GlassCard. Glass-inside-glass:
/// the agenda and the RSVP chip row are lighter GlassSurface.inner layers.
class _MeetingCard extends StatelessWidget {
  const _MeetingCard({required this.meeting});

  final _Meeting meeting;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GlassCard(
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
              const SizedBox(width: 12),
              const _JoinPill(),
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
                  '${meeting.when} · ${meeting.location}',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: SovereignColors.ivory.withValues(alpha: 0.72),
                    fontSize: 12.5,
                  ),
                ),
              ),
            ],
          ),

          // Optional agenda — nested inner glass.
          if (meeting.agenda != null) ...[
            const SizedBox(height: 14),
            _SectionLabel('Agenda'),
            const SizedBox(height: 6),
            GlassSurface.inner(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < meeting.agenda!.length; i++) ...[
                    if (i > 0) const SizedBox(height: 6),
                    Text(
                      meeting.agenda![i],
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: SovereignColors.ivory.withValues(alpha: 0.88),
                        fontSize: 12.5,
                        height: 1.2,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],

          // RSVP row — three inner-glass chips, selected one gold.
          const SizedBox(height: 14),
          _SectionLabel('RSVP'),
          const SizedBox(height: 6),
          Row(
            children: [
              _RsvpChip(
                label: 'Going',
                selected: meeting.rsvp == _Rsvp.going,
              ),
              const SizedBox(width: 8),
              _RsvpChip(
                label: 'Maybe',
                selected: meeting.rsvp == _Rsvp.maybe,
              ),
              const SizedBox(width: 8),
              _RsvpChip(
                label: 'No',
                selected: meeting.rsvp == _Rsvp.no,
              ),
            ],
          ),
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
  const _JoinPill();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
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
    );
  }
}

/// One RSVP option as a lighter inner-glass chip. When [selected], the chip
/// fills with Sovereign gold and the label flips to navy.
class _RsvpChip extends StatelessWidget {
  const _RsvpChip({required this.label, required this.selected});

  final String label;
  final bool selected;

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

    if (selected) {
      // Selected chip: solid gold (not glass) so it reads as the active choice.
      return Expanded(
        child: DecoratedBox(
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
        ),
      );
    }

    // Unselected chips: lighter nested glass layer.
    return Expanded(
      child: GlassSurface.inner(
        borderRadius: 12,
        child: content,
      ),
    );
  }
}
