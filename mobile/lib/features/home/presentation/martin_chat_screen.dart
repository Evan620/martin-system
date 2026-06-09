// lib/features/home/presentation/martin_chat_screen.dart
//
// Martin member chat (Task B4) — the full-screen, streaming, member-scoped chat
// that replaces the 4b placeholder. Reached two ways:
//   - the floating ✦ Martin FAB (top-level `/martin` route), and
//   - the Home "Ask Martin…" bar / suggestion chips (nested `/home/chat?q=…`),
//     which pass a `seed` that is auto-sent once on first build.
//
// Layout (mirrors the placeholder's Sovereign backdrop + header so the two read
// as the same surface):
//   - an atmospheric navy field with a faint gold halo,
//   - a header row: a glass back button + a ✦ Martin serif title,
//   - a scrolling transcript (user = gold bubble; martin = glass bubble; while
//     streaming the in-flight Martin draft shows its toolActivity as a gold
//     `✦ …` chip plus an animated typing indicator),
//   - an input bar pinned to the bottom (disabled while streaming) that calls
//     chatController.send.
//
// Everything leans on the Sovereign glass system (GlassSurface / GlassCard) and
// SovereignColors so it stays on-brand: navy + gold, never sky-blue.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../application/chat_controller.dart';
import '../data/chat_models.dart';

/// Full-screen streaming chat with the member-scoped Martin agent.
///
/// When [seed] is non-null and non-empty, it is auto-sent once on first build
/// (so a Home suggestion chip / ask bar lands the member straight in a reply).
class MartinChatScreen extends ConsumerStatefulWidget {
  const MartinChatScreen({super.key, this.seed, this.twgId});

  /// Optional prompt to auto-send once when the screen first appears.
  final String? seed;

  /// Optional TWG to scope this chat to (workspace Ask-Martin). When null the
  /// controller falls back to the member's first TWG.
  final String? twgId;

  @override
  ConsumerState<MartinChatScreen> createState() => _MartinChatScreenState();
}

class _MartinChatScreenState extends ConsumerState<MartinChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    final seed = widget.seed?.trim() ?? '';
    if (seed.isNotEmpty) {
      // Auto-send the seed once after first frame (so the controller + provider
      // tree are ready and the post-send state lands on a built widget).
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ref
            .read(chatControllerProvider.notifier)
            .send(seed, overrideTwgId: widget.twgId);
      });
    }
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _send() {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    _input.clear();
    ref
        .read(chatControllerProvider.notifier)
        .send(text, overrideTwgId: widget.twgId);
  }

  // Keep the newest turn in view as the transcript grows / tokens stream in.
  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatControllerProvider);
    _scrollToEnd();

    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      // Let the input bar rise above the keyboard.
      resizeToAvoidBottomInset: true,
      body: Stack(
        children: [
          const _AmbientBackground(),
          SafeArea(
            child: Column(
              children: [
                const _ChatHeader(),
                Expanded(
                  child: state.messages.isEmpty
                      ? const _EmptyState()
                      : _Transcript(
                          scroll: _scroll,
                          messages: state.messages,
                          streaming: state.streaming,
                        ),
                ),
                if (state.error != null) _ErrorBanner(message: state.error!),
                _InputBar(
                  controller: _input,
                  enabled: !state.streaming,
                  onSend: _send,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Header — glass back button + ✦ Martin serif title (mirrors the placeholder).
// ---------------------------------------------------------------------------

class _ChatHeader extends StatelessWidget {
  const _ChatHeader();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 20, 8),
      child: Row(
        children: [
          GestureDetector(
            key: const Key('martin-chat-back'),
            behavior: HitTestBehavior.opaque,
            onTap: () {
              if (context.canPop()) {
                context.pop();
              } else {
                context.go('/home');
              }
            },
            child: const GlassSurface(
              borderRadius: 14,
              padding: EdgeInsets.all(10),
              child: Icon(
                Icons.arrow_back_rounded,
                size: 20,
                color: SovereignColors.ivory,
              ),
            ),
          ),
          const SizedBox(width: 14),
          const Text(
            '✦ Martin',
            style: TextStyle(
              color: SovereignColors.gold,
              fontFamily: 'Georgia',
              fontSize: 24,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty state — a quiet invitation before the first turn.
// ---------------------------------------------------------------------------

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.auto_awesome,
                  color: SovereignColors.gold, size: 28),
              const SizedBox(height: 14),
              Text(
                'Ask about your meetings, documents and tasks — '
                'Martin reads within your TWG.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.85),
                  fontSize: 15.5,
                  height: 1.42,
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
// Transcript — the scrolling list of turns.
// ---------------------------------------------------------------------------

class _Transcript extends StatelessWidget {
  const _Transcript({
    required this.scroll,
    required this.messages,
    required this.streaming,
  });

  final ScrollController scroll;
  final List<ChatMessage> messages;
  final bool streaming;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: scroll,
      padding: const EdgeInsets.fromLTRB(18, 6, 18, 12),
      itemCount: messages.length,
      itemBuilder: (context, i) {
        final msg = messages[i];
        // The in-flight Martin draft is the last entry while streaming.
        final isStreamingDraft =
            streaming && i == messages.length - 1 && msg.role == ChatRole.martin;
        return _MessageBubble(message: msg, streaming: isStreamingDraft);
      },
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message, required this.streaming});

  final ChatMessage message;
  final bool streaming;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == ChatRole.user;
    final hasText = message.text.trim().isNotEmpty;

    final bubble = isUser
        ? _GoldBubble(text: message.text)
        : _GlassBubble(
            message: message,
            streaming: streaming,
            hasText: hasText,
          );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.78,
              ),
              child: bubble,
            ),
          ),
        ],
      ),
    );
  }
}

/// The member's own turn — a solid gold bubble with navy text.
class _GoldBubble extends StatelessWidget {
  const _GoldBubble({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: SovereignColors.gold,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(18),
          topRight: Radius.circular(18),
          bottomLeft: Radius.circular(18),
          bottomRight: Radius.circular(6),
        ),
        boxShadow: [
          BoxShadow(
            color: SovereignColors.gold.withValues(alpha: 0.24),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
        child: Text(
          text,
          style: const TextStyle(
            color: SovereignColors.navy,
            fontSize: 15,
            height: 1.4,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

/// Martin's turn — a glass bubble. While streaming, shows the tool-activity
/// chip and a typing indicator until content arrives.
class _GlassBubble extends StatelessWidget {
  const _GlassBubble({
    required this.message,
    required this.streaming,
    required this.hasText,
  });

  final ChatMessage message;
  final bool streaming;
  final bool hasText;

  @override
  Widget build(BuildContext context) {
    final activity = message.toolActivity;
    return GlassSurface(
      borderRadius: 18,
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Gold `✦ …` tool-activity chip while Martin works.
          if (streaming && activity != null && activity.isNotEmpty) ...[
            _ToolChip(label: activity),
            if (hasText) const SizedBox(height: 8),
          ],
          if (hasText)
            Text(
              message.text,
              style: TextStyle(
                color: SovereignColors.ivory.withValues(alpha: 0.92),
                fontSize: 15,
                height: 1.42,
              ),
            )
          else if (streaming)
            // No content yet — show a typing indicator (unless a chip is up
            // already conveying activity).
            if (activity == null || activity.isEmpty) const _TypingIndicator(),
        ],
      ),
    );
  }
}

/// The gold `✦ get_schedule…` chip shown while Martin uses a tool.
class _ToolChip extends StatelessWidget {
  const _ToolChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      ringColor: SovereignColors.gold,
      ringOpacity: 0.5,
      tintColors: [
        SovereignColors.gold.withValues(alpha: 0.20),
        SovereignColors.gold.withValues(alpha: 0.10),
      ],
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

/// A small three-dot animated typing indicator (gold dots).
class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();

  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))
        ..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 10,
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              // Stagger each dot's pulse across the cycle.
              final phase = (_c.value + i * 0.22) % 1.0;
              final t = (0.5 - (phase - 0.5).abs()) * 2; // 0→1→0 triangle
              return Padding(
                padding: const EdgeInsets.only(right: 5),
                child: Opacity(
                  opacity: 0.35 + 0.55 * t,
                  child: Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: SovereignColors.gold,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error banner — a quiet glass strip above the input bar.
// ---------------------------------------------------------------------------

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 8),
      child: GlassSurface(
        borderRadius: 14,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        ringColor: SovereignColors.danger,
        ringOpacity: 0.55,
        child: Row(
          children: [
            const Icon(Icons.error_outline_rounded,
                size: 16, color: SovereignColors.gold),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.9),
                  fontSize: 13,
                  height: 1.35,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Input bar — glass field + inner gold send button. Disabled while streaming.
// ---------------------------------------------------------------------------

class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.enabled,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 4, 18, 14),
      child: GlassSurface(
        borderRadius: 18,
        padding: const EdgeInsets.fromLTRB(18, 8, 10, 8),
        ringOpacity: 0.42,
        goldGlow: true,
        child: Row(
          children: [
            Expanded(
              child: TextField(
                key: const Key('martin-chat-input'),
                controller: controller,
                enabled: enabled,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: enabled ? (_) => onSend() : null,
                cursorColor: SovereignColors.gold,
                style: const TextStyle(
                  color: SovereignColors.ivory,
                  fontSize: 14.5,
                ),
                decoration: InputDecoration(
                  isDense: true,
                  border: InputBorder.none,
                  hintText: enabled ? 'Ask Martin…' : 'Martin is thinking…',
                  hintStyle: TextStyle(
                    color: SovereignColors.ivory.withValues(alpha: 0.55),
                    fontSize: 14.5,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            GestureDetector(
              key: const Key('martin-chat-send'),
              behavior: HitTestBehavior.opaque,
              onTap: enabled ? onSend : null,
              child: GlassSurface.inner(
                borderRadius: 14,
                padding: const EdgeInsets.all(9),
                ringColor: SovereignColors.gold,
                ringOpacity: enabled ? 0.55 : 0.25,
                tintColors: [
                  SovereignColors.gold.withValues(alpha: enabled ? 0.22 : 0.10),
                  SovereignColors.gold.withValues(alpha: enabled ? 0.12 : 0.06),
                ],
                child: Icon(
                  Icons.arrow_upward_rounded,
                  size: 20,
                  color: SovereignColors.gold
                      .withValues(alpha: enabled ? 1.0 : 0.4),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Background — atmospheric navy field with a faint gold glow (mirrors Home).
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
