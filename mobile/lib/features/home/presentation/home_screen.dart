// lib/features/home/presentation/home_screen.dart
//
// Home · Martin — the editorial, AI-first home of the Sovereign member app,
// wired to the live member-scoped briefing (`GET /martin/briefing`).
//
// Layout (top -> bottom), per the Sovereign redesign (editorial hero):
//   - gold eyebrow "WAIIS · <weekday, d MMM>"
//   - large serif greeting "<briefing.greeting>,\n<member first name>" (display)
//   - a prominent hero "NEXT" meeting card: eyebrow (NEXT · TWG/meeting), a big
//     serif relative time, a secondary location/virtual·attending line, and the
//     screen's ONE solid-gold action — a gold "Join" pill (only when a video
//     link is present). When there is no next meeting, a calm body card with no
//     gold instead.
//   - a "THEN" section: an action-items summary row (overdueCount) + the
//     Your-TWGs section, each a quiet glass row (navy-raised, no gold fill).
//   - a gold-OUTLINE "Ask Martin…" bar (the hero owns the gold; this is outline).
//
// Loads via homeControllerProvider.load() (post-frame), renders by sealed state
// (loading → content-shaped skeleton / error / data). Sections cascade in;
// pull-to-refresh re-runs load(); tappable rows give press feedback.
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
import '../application/home_controller.dart';
import '../data/briefing_models.dart';
import 'your_twgs_section.dart';

/// The AI-first member home. Greets the member, surfaces what matters via a
/// live Martin briefing, and pins a gold-outline "Ask Martin" bar near the
/// bottom.
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
  /// the ask bar carries a prompt. The top-level `/martin` route presents the
  /// chat full-screen, covering the nav.
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
            child: RefreshIndicator(
              color: SovereignColors.gold,
              backgroundColor: SovereignColors.navyRaised,
              onRefresh: () => ref.read(homeControllerProvider.notifier).load(),
              child: AnimatedSwitcher(
                duration: Motion.base,
                child: switch (state) {
                  HomeLoading() => const _LoadingView(key: ValueKey('loading')),
                  HomeError(:final message) => _ErrorView(
                      key: const ValueKey('error'),
                      message: message,
                      onRetry: () =>
                          ref.read(homeControllerProvider.notifier).load(),
                    ),
                  HomeData(:final briefing) => _DataView(
                      key: const ValueKey('data'),
                      briefing: briefing,
                      firstName: _firstName(ref),
                      onAsk: _askMartin,
                    ),
                },
              ),
            ),
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
// Loaded state — the live briefing, editorial layout.
// ---------------------------------------------------------------------------

class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
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
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
          .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CascadeIn(index: 0, child: const _Eyebrow()),
          const SizedBox(height: Insets.md),
          CascadeIn(
            index: 1,
            child: _Greeting(greeting: briefing.greeting, firstName: firstName),
          ),
          const SizedBox(height: Insets.section),
          CascadeIn(index: 2, child: _HeroMeetingCard(briefing: briefing)),
          const SizedBox(height: Insets.section),
          CascadeIn(
            index: 3,
            child: _ThenSection(overdueCount: briefing.overdueCount),
          ),
          const SizedBox(height: Insets.section),
          CascadeIn(index: 4, child: _AskMartinBar(onTap: () => onAsk(''))),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Loading — content-shaped skeleton (hero + two rows), no spinner.
// ---------------------------------------------------------------------------

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
          SkeletonBlock(width: 160, height: 12),
          SizedBox(height: Insets.lg),
          SkeletonBlock(width: 220, height: 34),
          SizedBox(height: Insets.section),
          // A hero-shaped skeleton card + two quiet rows.
          SkeletonList(count: 1),
          SizedBox(height: Insets.section),
          SkeletonList(count: 2),
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
// Header — gold eyebrow with today's date + serif greeting.
// ---------------------------------------------------------------------------

class _Eyebrow extends StatelessWidget {
  const _Eyebrow();

  @override
  Widget build(BuildContext context) {
    final today = DateFormat('EEEE, d MMM').format(DateTime.now());
    return Text(
      'WAIIS · ${today.toUpperCase()}',
      style: SovereignType.eyebrow,
    );
  }
}

class _Greeting extends StatelessWidget {
  const _Greeting({required this.greeting, required this.firstName});

  final String greeting;
  final String firstName;

  @override
  Widget build(BuildContext context) {
    return Text('$greeting,\n$firstName', style: SovereignType.display);
  }
}

// ---------------------------------------------------------------------------
// Hero next-meeting card — the editorial centrepiece. When a next meeting
// exists: a raised glass card with an eyebrow (NEXT · TWG/meeting), a big serif
// relative time, a secondary location/virtual·attending line, and the screen's
// ONE solid-gold action (the Join pill, only when a video link is present).
// When there is no next meeting: a calm body card, no gold.
// ---------------------------------------------------------------------------

class _HeroMeetingCard extends StatelessWidget {
  const _HeroMeetingCard({required this.briefing});

  final Briefing briefing;

  @override
  Widget build(BuildContext context) {
    final next = briefing.nextMeeting;

    if (next == null) {
      return GlassCard(
        goldGlow: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('NEXT', style: SovereignType.eyebrow),
            const SizedBox(height: Insets.md),
            Text(
              'Nothing on your calendar right now.',
              style: SovereignType.body.copyWith(
                color: SovereignColors.ivory.withValues(
                  alpha: SovereignColors.alphaMid,
                ),
              ),
            ),
          ],
        ),
      );
    }

    final eyebrowLabel = (next.twgName ?? next.title).toUpperCase();

    return GlassCard(
      borderRadius: 22,
      padding: const EdgeInsets.all(Insets.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('NEXT · $eyebrowLabel', style: SovereignType.eyebrow),
          const SizedBox(height: Insets.md),

          // Big serif relative time — the hero's focal point.
          Text(_relativeTime(next), style: SovereignType.title),
          const SizedBox(height: Insets.xs),

          // Meeting title (section weight) so the time stays the focal point.
          Text(next.title, style: SovereignType.section),
          const SizedBox(height: Insets.sm),

          // Secondary detail line — clock time / virtual, when available.
          Text(
            _detailLine(next),
            style: SovereignType.secondary.copyWith(
              color: SovereignColors.ivory.withValues(
                alpha: SovereignColors.alphaMid,
              ),
            ),
          ),

          // The ONE solid-gold action: Join — only when the briefing carries a
          // video link for the next meeting (null until prod deploy → hidden).
          if (next.videoLink != null) ...[
            const SizedBox(height: Insets.lg),
            Align(
              alignment: Alignment.centerLeft,
              child: _JoinPill(videoLink: next.videoLink!),
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
  if (mins == null) return 'Soon';
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

/// The secondary detail line under the hero time: the clock time when known,
/// plus a "Virtual" hint when the meeting carries a video link.
String _detailLine(BriefingMeeting m) {
  final parts = <String>[];
  final at = m.startsAt;
  if (at != null) parts.add(DateFormat('EEE, d MMM · HH:mm').format(at));
  if (m.videoLink != null) parts.add('Virtual');
  if (parts.isEmpty) return 'You’re attending';
  return parts.join(' · ');
}

/// The gold "Join" call-to-action pill for the next meeting — the screen's ONE
/// solid-gold action. Launches the meeting's [videoLink] externally when tapped.
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
    return Semantics(
      button: true,
      label: 'Join meeting',
      child: PressableScale(
        onTap: _launch,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: SovereignColors.gold,
            borderRadius: BorderRadius.circular(22),
            boxShadow: [
              BoxShadow(
                color: SovereignColors.gold.withValues(alpha: 0.28),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: 18, vertical: 11),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.videocam_rounded, size: 16, color: SovereignColors.navy),
                SizedBox(width: 7),
                Text(
                  'Join',
                  style: TextStyle(
                    fontFamily: 'Inter',
                    color: SovereignColors.navy,
                    fontSize: 14,
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

// ---------------------------------------------------------------------------
// "THEN" section — an action-items summary row (overdueCount) + the Your-TWGs
// section. Each is a quiet glass row (navy-raised, no gold fill) with press
// feedback that pushes its destination.
// ---------------------------------------------------------------------------

class _ThenSection extends StatelessWidget {
  const _ThenSection({required this.overdueCount});

  final int overdueCount;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: Insets.xs, bottom: Insets.md),
          child: Text('THEN', style: SovereignType.eyebrow),
        ),
        _ActionItemsRow(overdueCount: overdueCount),
        const SizedBox(height: Insets.md),
        const YourTwgsSection(),
      ],
    );
  }
}

/// A quiet glass row summarising action items, derived from the briefing's
/// overdue count. Pushes the Me tab (where action items live).
class _ActionItemsRow extends StatelessWidget {
  const _ActionItemsRow({required this.overdueCount});

  final int overdueCount;

  @override
  Widget build(BuildContext context) {
    final overdue = overdueCount > 0;
    final label = overdue
        ? '$overdueCount action ${overdueCount == 1 ? 'item' : 'items'} due'
        : "You're all caught up on action items.";

    return PressableScale(
      onTap: () => context.go('/me'),
      child: GlassCard(
        goldGlow: false,
        borderRadius: 16,
        padding: const EdgeInsets.symmetric(
            horizontal: Insets.lg, vertical: Insets.lg),
        child: Row(
          children: [
            Icon(
              overdue
                  ? Icons.flag_rounded
                  : Icons.check_circle_outline_rounded,
              size: 18,
              color: overdue ? SovereignColors.gold : SovereignColors.success,
            ),
            const SizedBox(width: Insets.md),
            Expanded(child: Text(label, style: SovereignType.body)),
            Icon(
              Icons.chevron_right,
              size: 18,
              color: SovereignColors.ivory.withValues(
                alpha: SovereignColors.alphaLow,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Ask Martin bar — gold OUTLINE (not filled; the hero owns the gold). Pushes
// the full-screen /martin chat.
// ---------------------------------------------------------------------------

class _AskMartinBar extends StatelessWidget {
  const _AskMartinBar({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Ask Martin',
      child: PressableScale(
        onTap: onTap,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: SovereignColors.navyRaised.withValues(alpha: 0.45),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: SovereignColors.gold.withValues(alpha: 0.65),
              width: 1.4,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 14, 14, 14),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Ask Martin…',
                    style: SovereignType.body.copyWith(
                      color: SovereignColors.ivory.withValues(
                        alpha: SovereignColors.alphaMid,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: Insets.md),
                Icon(
                  Icons.mic_rounded,
                  size: 22,
                  color: SovereignColors.gold,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error state — a glass message + a Retry button.
// ---------------------------------------------------------------------------

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
              const Icon(Icons.cloud_off,
                  color: SovereignColors.gold, size: 28),
              const SizedBox(height: Insets.md),
              Text(
                message,
                textAlign: TextAlign.center,
                style: SovereignType.body.copyWith(
                  color: SovereignColors.ivory.withValues(
                    alpha: SovereignColors.alphaHigh,
                  ),
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
