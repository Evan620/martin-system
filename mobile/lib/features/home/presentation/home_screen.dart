// lib/features/home/presentation/home_screen.dart
//
// Home · Martin — the AI-first home of the Sovereign member app, wired to the
// live member-scoped briefing (`GET /martin/briefing`).
//
// Layout (top -> bottom), matching the approved Sovereign mockup:
//   - gold eyebrow "WAIIS"
//   - large serif greeting "<briefing.greeting>, <member first name>"
//   - a glass Martin briefing card (chat-message style): the next meeting title
//     + a relative time + a gold "Join" pill when present, plus an
//     "N action items due" line derived from overdueCount
//   - a row of suggestion chips (small glass pills)
//   - a glass "Ask Martin…" input bar with a gold mic
//
// Loads via homeControllerProvider.load() (post-frame) and renders by sealed
// state (loading / error / data). Everything sits on a navy background; cards
// use the Sovereign glass system, leaning on glass-inside-glass for layered
// depth (outer raised card holding lighter inner rows, and an inner gold mic
// inside the ask bar).
//
// The Ask-Martin bar + suggestion chips push the canonical full-screen
// `/martin?q=<seed>` route (covering the nav), which opens the streaming
// Martin chat and auto-sends the seed.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../application/home_controller.dart';
import '../data/briefing_models.dart';
import 'your_twgs_section.dart';

/// Quick prompts offered under the briefing. Each seeds a Martin chat (4b).
const _suggestions = <String>['Brief me', 'RSVP', 'Find a doc', "What's due?"];

/// The AI-first member home. Greets the member, surfaces what matters via a
/// live Martin briefing, offers quick suggestions, and pins an "Ask Martin"
/// bar near the bottom.
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

  /// Opens the streaming Martin chat, seeding it with [seed] (URL-encoded) when
  /// a suggestion chip / the ask bar carries a prompt. The top-level `/martin`
  /// route presents the chat full-screen, covering the nav.
  void _askMartin(String seed) {
    final trimmed = seed.trim();
    final suffix =
        trimmed.isEmpty ? '' : '?q=${Uri.encodeQueryComponent(trimmed)}';
    context.push('/martin$suffix');
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(homeControllerProvider);

    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          // Atmospheric navy field with a faint gold glow, so the glass blur
          // has something rich to frost over (never sky-blue).
          const _AmbientBackground(),
          SafeArea(
            bottom: false,
            child: switch (state) {
              HomeLoading() => const Center(
                  child: CircularProgressIndicator(color: SovereignColors.gold),
                ),
              HomeError(:final message) => _ErrorView(
                  message: message,
                  onRetry: () =>
                      ref.read(homeControllerProvider.notifier).load(),
                ),
              HomeData(:final briefing) => _DataView(
                  briefing: briefing,
                  firstName: _firstName(ref),
                  onAsk: _askMartin,
                ),
            },
          ),
        ],
      ),
    );
  }
}

/// The member's first name from the authed user (falls back to a warm neutral
/// when unknown), used in the serif greeting.
String _firstName(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  if (auth is AuthAuthenticated) {
    final full = auth.user.fullName.trim();
    if (full.isNotEmpty) return full.split(RegExp(r'\s+')).first;
  }
  return 'there';
}

// ---------------------------------------------------------------------------
// Loaded state — the live briefing.
// ---------------------------------------------------------------------------

class _DataView extends StatelessWidget {
  const _DataView({
    required this.briefing,
    required this.firstName,
    required this.onAsk,
  });

  final Briefing briefing;
  final String firstName;
  final ValueChanged<String> onAsk;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _Eyebrow(),
          const SizedBox(height: 14),
          _Greeting(greeting: briefing.greeting, firstName: firstName),
          const SizedBox(height: 24),
          _MartinBriefingCard(briefing: briefing),
          const SizedBox(height: 22),
          const YourTwgsSection(),
          const SizedBox(height: 22),
          _SuggestionChips(onTap: onAsk),
          const SizedBox(height: 28),
          _AskMartinBar(onTap: () => onAsk('')),
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
  const _Greeting({required this.greeting, required this.firstName});

  final String greeting;
  final String firstName;

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context).textTheme.displaySmall;
    return Text(
      '$greeting,\n$firstName',
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
// Martin briefing — a raised glass card styled as a chat message bubble,
// rendered from the live briefing (next meeting + relative time + Join, and an
// "N action items due" line).
// ---------------------------------------------------------------------------

class _MartinBriefingCard extends StatelessWidget {
  const _MartinBriefingCard({required this.briefing});

  final Briefing briefing;

  @override
  Widget build(BuildContext context) {
    final next = briefing.nextMeeting;
    final overdue = briefing.overdueCount;

    return GlassCard(
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

          // Next meeting — title + relative time + a gold Join pill if present.
          if (next != null) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: RichText(
                    text: TextSpan(
                      style: const TextStyle(
                        color: SovereignColors.ivory,
                        fontSize: 15.5,
                        height: 1.42,
                      ),
                      children: [
                        const TextSpan(text: 'Next up — '),
                        TextSpan(
                          text: next.title,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        TextSpan(text: ' ${_relativeTime(next)}.'),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
          ] else ...[
            Text(
              'Nothing on your calendar right now.',
              style: TextStyle(
                color: SovereignColors.ivory.withValues(alpha: 0.85),
                fontSize: 15.5,
                height: 1.42,
              ),
            ),
            const SizedBox(height: 12),
          ],

          // Action items due — derived from the briefing's overdue count.
          Row(
            children: [
              Icon(
                overdue > 0
                    ? Icons.flag_rounded
                    : Icons.check_circle_outline_rounded,
                size: 16,
                color: SovereignColors.gold,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  overdue > 0
                      ? '$overdue action ${overdue == 1 ? 'item' : 'items'} due'
                      : "You're all caught up on action items.",
                  style: TextStyle(
                    color: SovereignColors.ivory.withValues(alpha: 0.82),
                    fontSize: 13.5,
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ),

          // Join pill — only when the briefing carries a video link for the
          // next meeting (null until prod deploy → pill hidden). Launches the
          // link via url_launcher.
          if (next?.videoLink != null) ...[
            const SizedBox(height: 14),
            Align(
              alignment: Alignment.centerLeft,
              child: _JoinPill(videoLink: next!.videoLink!),
            ),
          ],
        ],
      ),
    );
  }
}

/// A friendly relative time for the next meeting, derived from `minutesUntil`
/// (falls back to a generic phrase when unknown).
String _relativeTime(BriefingMeeting m) {
  final mins = m.minutesUntil;
  if (mins == null) return 'soon';
  if (mins <= 0) return 'now';
  if (mins < 60) return 'in $mins min';
  final hours = mins ~/ 60;
  if (hours < 24) {
    final rem = mins % 60;
    return rem == 0 ? 'in ${hours}h' : 'in ${hours}h ${rem}m';
  }
  final days = hours ~/ 24;
  return days == 1 ? 'tomorrow' : 'in $days days';
}

/// The gold "Join" call-to-action pill for the next meeting. Launches the
/// meeting's [videoLink] externally when tapped.
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
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: _launch,
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

// ---------------------------------------------------------------------------
// Suggestion chips — small base-glass pills that seed a Martin chat.
// ---------------------------------------------------------------------------

class _SuggestionChips extends StatelessWidget {
  const _SuggestionChips({required this.onTap});

  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final label in _suggestions)
          _SuggestionChip(label: label, onTap: () => onTap(label)),
      ],
    );
  }
}

class _SuggestionChip extends StatelessWidget {
  const _SuggestionChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: GlassSurface(
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
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Ask Martin bar — base glass bar with an inner gold mic (glass-inside-glass).
// ---------------------------------------------------------------------------

class _AskMartinBar extends StatelessWidget {
  const _AskMartinBar({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: GlassSurface(
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
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error state — a glass message + a Retry button.
// ---------------------------------------------------------------------------

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
