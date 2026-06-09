// lib/features/home/presentation/home_screen.dart
//
// Home · Martin — the AI-first home of the Sovereign member app.
//
// Layout (top -> bottom), matching the approved Sovereign mockup:
//   - gold eyebrow "WAIIS"
//   - large serif greeting "Good morning, Amina"
//   - a glass Martin briefing card (chat-message style)
//   - a "YOUR ACTIONS" glass card with inner-glass action rows
//   - a row of suggestion chips (small glass pills)
//   - pinned near the bottom, a glass "Ask Martin…" input bar with a gold mic
//
// Everything sits on a navy background; cards use the Sovereign glass system,
// leaning on glass-inside-glass for layered depth (outer raised card holding
// lighter inner rows, and an inner gold mic inside the ask bar).
import 'package:flutter/material.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';

/// Representative seed content for the visual build. Live API data is a later
/// pass; these mirror the approved mockup so the screen reads true.
const String _memberFirstName = 'Amina';

const _actions = <_ActionItem>[
  _ActionItem(label: 'Send budget input', due: 'Due Tue', done: false),
  _ActionItem(label: 'Review policy draft', due: 'Today', done: false),
];

const _suggestions = <String>['RSVP yes', 'Brief me', 'Find a doc'];

/// The AI-first member home. Greets the member, surfaces what matters via a
/// Martin briefing, lists the week's actions, offers quick suggestions, and
/// pins an "Ask Martin" bar at the bottom.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          // Atmospheric navy field with a faint gold glow, so the glass blur
          // has something rich to frost over (never sky-blue).
          const _AmbientBackground(),

          SafeArea(
            bottom: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  _Eyebrow(),
                  SizedBox(height: 14),
                  _Greeting(),
                  SizedBox(height: 24),
                  _MartinBriefingCard(),
                  SizedBox(height: 20),
                  _ActionsCard(),
                  SizedBox(height: 20),
                  _SuggestionChips(),
                  SizedBox(height: 28),
                  _AskMartinBar(),
                ],
              ),
            ),
          ),
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
// Header
// ---------------------------------------------------------------------------

class _Eyebrow extends StatelessWidget {
  const _Eyebrow();

  @override
  Widget build(BuildContext context) {
    return Text(
      'WAIIS',
      style: TextStyle(
        color: SovereignColors.gold.withValues(alpha: 0.85),
        fontSize: 11,
        letterSpacing: 4,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

class _Greeting extends StatelessWidget {
  const _Greeting();

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context).textTheme.displaySmall;
    return Text(
      'Good morning,\n$_memberFirstName',
      style: (base ?? const TextStyle()).copyWith(
        color: SovereignColors.ivory,
        fontFamily: 'Georgia',
        fontSize: 38,
        height: 1.08,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.2,
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Martin briefing — a raised glass card styled as a chat message bubble.
// ---------------------------------------------------------------------------

class _MartinBriefingCard extends StatelessWidget {
  const _MartinBriefingCard();

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      // Chat-bubble silhouette: rounded everywhere but a snipped bottom-left
      // tail, echoing the mockup's message style.
      borderRadius: 20,
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 26,
                height: 26,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: SovereignColors.gold.withValues(alpha: 0.16),
                  border: Border.all(
                    color: SovereignColors.gold.withValues(alpha: 0.55),
                  ),
                ),
                alignment: Alignment.center,
                child: const Text(
                  'M',
                  style: TextStyle(
                    color: SovereignColors.gold,
                    fontFamily: 'Georgia',
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                'MARTIN',
                style: TextStyle(
                  color: SovereignColors.gold.withValues(alpha: 0.85),
                  fontSize: 10,
                  letterSpacing: 2.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          RichText(
            text: TextSpan(
              style: const TextStyle(
                color: SovereignColors.ivory,
                fontSize: 15.5,
                height: 1.42,
              ),
              children: const [
                TextSpan(text: 'One session today — '),
                TextSpan(
                  text: 'TWG Energy Sync, 14:00',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                TextSpan(text: ' — and '),
                TextSpan(
                  text: '2 tasks',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                TextSpan(text: ' need you this week.'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Your actions — outer raised glass card holding lighter inner-glass rows.
// (Glass-inside-glass.)
// ---------------------------------------------------------------------------

class _ActionItem {
  const _ActionItem({
    required this.label,
    required this.due,
    required this.done,
  });

  final String label;
  final String due;
  final bool done;
}

class _ActionsCard extends StatelessWidget {
  const _ActionsCard();

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionLabel('Your actions'),
          const SizedBox(height: 12),
          for (var i = 0; i < _actions.length; i++) ...[
            if (i > 0) const SizedBox(height: 10),
            _ActionRow(item: _actions[i]),
          ],
        ],
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({required this.item});

  final _ActionItem item;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      child: Row(
        children: [
          Icon(
            item.done
                ? Icons.check_box_rounded
                : Icons.check_box_outline_blank_rounded,
            size: 18,
            color: item.done
                ? SovereignColors.gold
                : SovereignColors.ivory.withValues(alpha: 0.55),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              item.label,
              style: TextStyle(
                color: SovereignColors.ivory,
                fontSize: 13.5,
                decoration:
                    item.done ? TextDecoration.lineThrough : TextDecoration.none,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            item.due,
            style: const TextStyle(
              color: SovereignColors.gold,
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Suggestion chips — small base-glass pills.
// ---------------------------------------------------------------------------

class _SuggestionChips extends StatelessWidget {
  const _SuggestionChips();

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final label in _suggestions) _SuggestionChip(label: label),
      ],
    );
  }
}

class _SuggestionChip extends StatelessWidget {
  const _SuggestionChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
      ringOpacity: 0.45,
      child: Text(
        label,
        style: const TextStyle(
          color: SovereignColors.gold,
          fontSize: 12,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Ask Martin bar — base glass bar with an inner gold mic (glass-inside-glass).
// ---------------------------------------------------------------------------

class _AskMartinBar extends StatelessWidget {
  const _AskMartinBar();

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: 18,
      padding: const EdgeInsets.fromLTRB(18, 12, 12, 12),
      ringOpacity: 0.42,
      goldGlow: true,
      child: Row(
        children: [
          Expanded(
            child: Text(
              'Ask Martin…',
              style: TextStyle(
                color: SovereignColors.ivory.withValues(alpha: 0.75),
                fontSize: 14.5,
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Inner glass mic button, tinted gold.
          GlassSurface.inner(
            borderRadius: 14,
            padding: const EdgeInsets.all(9),
            ringColor: SovereignColors.gold,
            ringOpacity: 0.55,
            tintColors: [
              SovereignColors.gold.withValues(alpha: 0.22),
              SovereignColors.gold.withValues(alpha: 0.12),
            ],
            child: const Icon(
              Icons.mic_rounded,
              size: 20,
              color: SovereignColors.gold,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared bits
// ---------------------------------------------------------------------------

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: TextStyle(
        color: SovereignColors.gold.withValues(alpha: 0.85),
        fontSize: 10,
        letterSpacing: 2.4,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}
