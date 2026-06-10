// lib/features/home/presentation/martin_chat_screen.dart
//
// Martin member chat (Task B4) — the full-screen, streaming, member-scoped chat
// that replaces the 4b placeholder. Reached only via the canonical top-level
// `/martin` route (the ✦ FAB, the Home ask bar / suggestion chips, and the
// Workspace Ask-Martin card all push it): `?q=` passes a `seed` that is
// auto-sent once on first build, and `?twg=` scopes the chat to a TWG
// (workspace entry).
//
// The screen watches `chatControllerProvider(widget.twgId)` — a family keyed
// by the TWG scope — so each scope (each TWG, plus the unscoped FAB chat) has
// its own transcript and conversationId. Opening "Ask Martin about TWG B"
// after chatting in TWG A (or via the FAB) starts from that scope's own
// thread, never the other one's.
//
// claude.ai-quality behaviors:
//   - Martin's replies render as Sovereign-styled markdown (see
//     martin_message_bubble.dart) with a pulsing gold caret while streaming.
//   - Smart autoscroll: the transcript follows the stream only while the
//     reader is pinned within ~80px of the bottom — never yanks them back
//     while they re-read history; a glass scroll-to-bottom pill floats above
//     the input bar when they've scrolled away.
//   - Errors land in the transcript as a glass bubble with a Retry chip that
//     re-sends the last user message.
//
// Everything leans on the Sovereign glass system (GlassSurface / GlassCard)
// and SovereignColors so it stays on-brand: navy + gold, never sky-blue.
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show ScrollDirection;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../application/chat_controller.dart';
import '../data/chat_models.dart';
import 'martin_message_bubble.dart';

/// The smart-autoscroll guard: the transcript only follows the stream while
/// the reader sits within [threshold] px of the bottom. Pure so it can be
/// unit-tested. An unscrollable transcript counts as pinned.
bool isPinnedToBottom({
  required double pixels,
  required double maxScrollExtent,
  double threshold = 80,
}) {
  if (maxScrollExtent <= 0) return true;
  return (maxScrollExtent - pixels) <= threshold;
}

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

  /// The chat provider for THIS scope (the `?twg=` param; null = unscoped
  /// FAB chat). Family-keyed so transcripts/threads never leak across scopes.
  NotifierProvider<ChatController, ChatState> get _chat =>
      chatControllerProvider(widget.twgId);

  /// True while the reader sits near the bottom — the only state in which the
  /// transcript auto-follows the stream.
  bool _pinnedToBottom = true;

  // What the autoscroll listener saw last — lets it detect growth even though
  // the in-flight draft message is mutated in place by the controller.
  int _seenCount = 0;
  int _seenLastLen = 0;

  double _lastBottomInset = 0;

  @override
  void initState() {
    super.initState();
    final seed = widget.seed?.trim() ?? '';
    if (seed.isNotEmpty) {
      // Auto-send the seed once after first frame (so the controller + provider
      // tree are ready and the post-send state lands on a built widget).
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ref.read(_chat.notifier).send(seed);
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
    ref.read(_chat.notifier).send(text);
  }

  void _retry() => ref.read(_chat.notifier).retry();

  /// Instant follow while tokens stream — jumpTo (not animateTo) so animation
  /// queues never fight each other across token publishes.
  void _jumpToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  /// A single smooth scroll for deliberate moments (own send / pill tap).
  void _animateToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  /// Reacts to transcript growth (new turns / streaming draft text):
  /// the member's own send always scrolls + re-pins; token growth only
  /// follows while pinned.
  void _onChatChanged(ChatState? prev, ChatState next) {
    final count = next.messages.length;
    final lastLen = count > 0 ? next.messages.last.text.length : 0;
    final newTurn = count > _seenCount;
    final grew = count != _seenCount || lastLen != _seenLastLen;
    _seenCount = count;
    _seenLastLen = lastLen;
    if (!grew) return;

    if (newTurn && next.streaming) {
      // The member just sent (user turn + draft appended): re-pin + animate.
      if (!_pinnedToBottom) setState(() => _pinnedToBottom = true);
      _animateToBottom();
    } else if (_pinnedToBottom) {
      _jumpToBottom();
    }
  }

  /// Tracks whether the reader is pinned near the bottom. Only user gestures
  /// can unpin (drag updates / an upward fling); reaching the bottom — by any
  /// means — re-pins.
  bool _handleScroll(ScrollNotification notification) {
    final m = notification.metrics;
    bool? next;
    if (isPinnedToBottom(pixels: m.pixels, maxScrollExtent: m.maxScrollExtent)) {
      next = true;
    } else if (notification is UserScrollNotification &&
        notification.direction == ScrollDirection.forward) {
      next = false;
    } else if (notification is ScrollUpdateNotification &&
        notification.dragDetails != null) {
      next = false;
    }
    if (next != null && next != _pinnedToBottom) {
      setState(() => _pinnedToBottom = next!);
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<ChatState>(_chat, _onChatChanged);
    final state = ref.watch(_chat);

    // Keyboard opening while pinned: keep the last turn visible.
    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;
    if (bottomInset != _lastBottomInset) {
      _lastBottomInset = bottomInset;
      if (_pinnedToBottom) _jumpToBottom();
    }

    final showEmptyState = state.messages.isEmpty && state.error == null;

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
                  child: Stack(
                    children: [
                      Positioned.fill(
                        child: showEmptyState
                            ? const _EmptyState()
                            : NotificationListener<ScrollNotification>(
                                onNotification: _handleScroll,
                                child: _Transcript(
                                  scroll: _scroll,
                                  messages: state.messages,
                                  streaming: state.streaming,
                                  error: state.error,
                                  onRetry: _retry,
                                ),
                              ),
                      ),
                      // Scroll-to-bottom pill, 12px above the input bar.
                      Positioned(
                        left: 0,
                        right: 0,
                        bottom: 12,
                        child: Center(
                          child: _ScrollToBottomPill(
                            visible: !_pinnedToBottom,
                            onTap: () {
                              setState(() => _pinnedToBottom = true);
                              _animateToBottom();
                            },
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                _InputBar(
                  controller: _input,
                  enabled: !state.streaming,
                  keyboardOpen: bottomInset > 0,
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
              fontFamily: 'Inter',
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
// Transcript — the scrolling list of turns (+ the inline error bubble).
// ---------------------------------------------------------------------------

class _Transcript extends StatelessWidget {
  const _Transcript({
    required this.scroll,
    required this.messages,
    required this.streaming,
    required this.error,
    required this.onRetry,
  });

  final ScrollController scroll;
  final List<ChatMessage> messages;
  final bool streaming;
  final String? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    // Bubble widths come from layout constraints, not MediaQuery.
    return LayoutBuilder(builder: (context, constraints) {
      final available = constraints.maxWidth - 36; // transcript H padding
      final itemCount = messages.length + (error != null ? 1 : 0);
      return ListView.builder(
        controller: scroll,
        padding: const EdgeInsets.fromLTRB(18, 6, 18, 12),
        itemCount: itemCount,
        itemBuilder: (context, i) {
          // The error bubble trails the transcript at the failure site.
          if (i == messages.length) {
            return _ErrorBubble(
              key: const ValueKey('chat-error'),
              message: error!,
              maxWidth: available * 0.86,
              onRetry: onRetry,
            );
          }
          final msg = messages[i];
          // The in-flight Martin draft is the last entry while streaming.
          final isStreamingDraft = streaming &&
              i == messages.length - 1 &&
              msg.role == ChatRole.martin;
          return RepaintBoundary(
            key: ValueKey('chat-msg-$i'),
            child: _MessageRow(
              message: msg,
              streaming: isStreamingDraft,
              // Assistant prose deserves more line length, like claude.ai.
              maxWidth: available * (msg.role == ChatRole.user ? 0.78 : 0.86),
            ),
          );
        },
      );
    });
  }
}

class _MessageRow extends StatelessWidget {
  const _MessageRow({
    required this.message,
    required this.streaming,
    required this.maxWidth,
  });

  final ChatMessage message;
  final bool streaming;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == ChatRole.user;

    final bubble = isUser
        ? _GoldBubble(text: message.text)
        : MartinMessageBubble(message: message, streaming: streaming);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: maxWidth),
              child: bubble,
            ),
          ),
        ],
      ),
    );
  }
}

/// The member's own turn — a solid gold bubble with navy text (plain text;
/// markdown is an assistant affordance).
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

// ---------------------------------------------------------------------------
// Error bubble — failure at the failure site, with a Retry chip beneath.
// ---------------------------------------------------------------------------

class _ErrorBubble extends StatelessWidget {
  const _ErrorBubble({
    super.key,
    required this.message,
    required this.maxWidth,
    required this.onRetry,
  });

  final String message;
  final double maxWidth;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: maxWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  GlassSurface(
                    borderRadius: 18,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 15, vertical: 12),
                    ringColor: SovereignColors.danger,
                    ringOpacity: 0.55,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline_rounded,
                            size: 16, color: SovereignColors.gold),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            message,
                            style: TextStyle(
                              color:
                                  SovereignColors.ivory.withValues(alpha: 0.9),
                              fontSize: 13.5,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  GestureDetector(
                    key: const Key('martin-chat-retry'),
                    behavior: HitTestBehavior.opaque,
                    onTap: onRetry,
                    child: GlassSurface.inner(
                      borderRadius: 12,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 7),
                      ringColor: SovereignColors.gold,
                      ringOpacity: 0.5,
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Retry',
                            style: TextStyle(
                              color: SovereignColors.gold,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          SizedBox(width: 6),
                          Icon(Icons.refresh_rounded,
                              size: 14, color: SovereignColors.gold),
                        ],
                      ),
                    ),
                  ),
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
// Scroll-to-bottom pill — floats above the input bar while unpinned.
// ---------------------------------------------------------------------------

class _ScrollToBottomPill extends StatelessWidget {
  const _ScrollToBottomPill({required this.visible, required this.onTap});

  final bool visible;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedOpacity(
      opacity: visible ? 1 : 0,
      duration: const Duration(milliseconds: 150),
      child: IgnorePointer(
        ignoring: !visible,
        child: GestureDetector(
          key: const Key('martin-scroll-to-bottom'),
          behavior: HitTestBehavior.opaque,
          onTap: onTap,
          child: GlassSurface.inner(
            borderRadius: 19,
            width: 38,
            height: 38,
            ringColor: SovereignColors.gold,
            ringOpacity: 0.5,
            child: const Icon(
              Icons.arrow_downward_rounded,
              size: 18,
              color: SovereignColors.gold,
            ),
          ),
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
    required this.keyboardOpen,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool keyboardOpen;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Padding(
      // Bottom padding collapses while the keyboard is up.
      padding: EdgeInsets.fromLTRB(18, 4, 18, keyboardOpen ? 6 : 14),
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
                keyboardType: TextInputType.multiline,
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
                  hintText: 'Ask Martin…',
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
