// lib/features/home/presentation/martin_message_bubble.dart
//
// Martin's side of the chat transcript — a claude.ai-quality assistant bubble
// mapped to the Sovereign system (navy 0xFF0A1F44 / gold 0xFFC9A227 / ivory
// 0xFFF6F1E7, GlassSurface/GlassCard).
//
// What lives here:
//   - [MartinMessageBubble]  the glass bubble: tool-activity chip, typing dots
//     pre-first-token, markdown body, a pulsing caret while text streams, an
//     "— interrupted" suffix for partial answers, and long-press-to-copy.
//   - [MartinMarkdown]       GptMarkdown styled to Sovereign: ivory body, gold
//     headings/links/list markers, monospace inline code on navyRaised, code
//     blocks on inner glass with a copy affordance.
//   - [StreamingCaret]       the 7x15 gold block pulsing 0.25→0.9 @650ms.
//   - [ToolChip] / [TypingIndicator]  the gold `✦ …` chip and 3-dot indicator.
//
// gpt_markdown is used because it degrades gracefully on the partially-formed
// markdown that token streaming produces (unclosed ** / half-open ``` fences)
// instead of flickering or throwing.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gpt_markdown/gpt_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../data/chat_models.dart';

/// Monospace stack for inline code + code blocks ('Menlo' on iOS, falls
/// through to the platform monospace elsewhere).
const List<String> _monoFallback = ['Menlo', 'Consolas', 'monospace'];

// ---------------------------------------------------------------------------
// Martin bubble
// ---------------------------------------------------------------------------

/// Martin's turn — a glass bubble rendering [ChatMessage.text] as Sovereign
/// markdown. While [streaming]:
///   * no text yet → tool chip (if any) or the 3-dot typing indicator,
///   * text growing → markdown + a pulsing gold caret at the block's end.
/// Long-press copies the full markdown source and floats a "Copied" toast.
class MartinMessageBubble extends StatelessWidget {
  const MartinMessageBubble({
    super.key,
    required this.message,
    required this.streaming,
  });

  final ChatMessage message;
  final bool streaming;

  void _copy(BuildContext context) {
    HapticFeedback.selectionClick();
    Clipboard.setData(ClipboardData(text: message.text));
    showMartinToast(context, 'Copied');
  }

  @override
  Widget build(BuildContext context) {
    final hasText = message.text.trim().isNotEmpty;
    final activity = message.toolActivity;
    final showChip = streaming && activity != null && activity.isNotEmpty;

    return GestureDetector(
      onLongPress: hasText ? () => _copy(context) : null,
      child: GlassSurface(
        borderRadius: 18,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Gold `✦ …` activity chip while Martin works.
            if (showChip) ...[
              ToolChip(label: activity),
              if (hasText) const SizedBox(height: 8),
            ],
            if (hasText)
              streaming
                  // Streaming: caret rides bottom-aligned right after the
                  // markdown block (claude.ai reads the same either way).
                  ? Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Flexible(child: MartinMarkdown(data: message.text)),
                        const SizedBox(width: 2),
                        const Padding(
                          padding: EdgeInsets.only(bottom: 3),
                          child: StreamingCaret(
                            key: Key('martin-streaming-caret'),
                          ),
                        ),
                      ],
                    )
                  : MartinMarkdown(data: message.text)
            else if (streaming && !showChip)
              // Pre-first-token (and no chip up conveying activity).
              const TypingIndicator(),
            if (message.interrupted) ...[
              const SizedBox(height: 6),
              Text(
                '— interrupted',
                style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.5),
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Sovereign markdown
// ---------------------------------------------------------------------------

/// GptMarkdown with the Sovereign style map: ivory body, gold serif H1, gold
/// underlined links (→ url_launcher), gold list markers, monospace inline code
/// on navyRaised, and code blocks on inner glass with a copy affordance.
class MartinMarkdown extends StatelessWidget {
  const MartinMarkdown({super.key, required this.data});

  final String data;

  static const _body = TextStyle(
    color: Color(0xEBF6F1E7), // ivory @0.92
    fontSize: 15,
    height: 1.45,
  );

  static const _h3 = TextStyle(
    color: SovereignColors.ivory,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.2,
    height: 1.4,
  );

  static final _theme = GptMarkdownThemeData(
    brightness: Brightness.dark,
    highlightColor: SovereignColors.navyRaised.withValues(alpha: 0.7),
    h1: const TextStyle(
      fontFamily: 'Georgia',
      color: SovereignColors.gold,
      fontSize: 19,
      fontWeight: FontWeight.w600,
      height: 1.4,
    ),
    h2: const TextStyle(
      color: SovereignColors.ivory,
      fontSize: 17,
      fontWeight: FontWeight.w700,
      height: 1.4,
    ),
    // H4–H6 clamp to the H3 treatment.
    h3: _h3,
    h4: _h3,
    h5: _h3,
    h6: _h3,
    hrLineThickness: 1,
    hrLineColor: SovereignColors.ivory.withValues(alpha: 0.12),
    hrLinePadding: const EdgeInsets.symmetric(vertical: 12),
    linkColor: SovereignColors.gold,
    linkHoverColor: SovereignColors.gold,
    autoAddDividerLineAfterH1: false,
  );

  static void _openLink(String url, String title) {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return GptMarkdownTheme(
      gptThemeData: _theme,
      child: GptMarkdown(
        data,
        style: _body,
        onLinkTap: _openLink,
        // Inline `code` — monospace on a navyRaised pill.
        highlightBuilder: (context, text, style) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
          decoration: BoxDecoration(
            color: SovereignColors.navyRaised.withValues(alpha: 0.7),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            text,
            style: TextStyle(
              fontFamily: _monoFallback.first,
              fontFamilyFallback: _monoFallback,
              fontSize: 13.5,
              height: 1.35,
              color: SovereignColors.ivory.withValues(alpha: 0.95),
            ),
          ),
        ),
        // ``` fences — inner glass block with header strip + copy.
        codeBuilder: (context, name, code, closed) =>
            SovereignCodeBlock(language: name, code: code),
        // Gold bullet for unordered items.
        unOrderedListBuilder: (context, child, config) => Padding(
          padding: const EdgeInsets.only(left: 6, top: 2, bottom: 2),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.only(top: 8, right: 10),
                child: Container(
                  width: 5,
                  height: 5,
                  decoration: const BoxDecoration(
                    color: SovereignColors.gold,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
              Flexible(child: child),
            ],
          ),
        ),
        // Gold numerals for ordered items.
        orderedListBuilder: (context, no, child, config) => Padding(
          padding: const EdgeInsets.only(left: 6, top: 2, bottom: 2),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Text(
                  '$no.',
                  style: const TextStyle(
                    color: SovereignColors.gold,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    height: 1.5,
                  ),
                ),
              ),
              Flexible(child: child),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Code block — inner glass, header strip (language + copy), monospace body.
// ---------------------------------------------------------------------------

/// A fenced code block on [GlassSurface.inner]: a header strip with the
/// language label (gold, uppercase; `✦ code` when empty) and a copy affordance
/// that flips to a check for 1.5s, then a horizontally scrollable monospace
/// body (long lines never wrap — claude.ai behavior).
class SovereignCodeBlock extends StatefulWidget {
  const SovereignCodeBlock({
    super.key,
    required this.language,
    required this.code,
  });

  final String language;
  final String code;

  @override
  State<SovereignCodeBlock> createState() => _SovereignCodeBlockState();
}

class _SovereignCodeBlockState extends State<SovereignCodeBlock> {
  bool _copied = false;
  Timer? _revert;

  @override
  void dispose() {
    _revert?.cancel();
    super.dispose();
  }

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.code));
    setState(() => _copied = true);
    _revert?.cancel();
    _revert = Timer(const Duration(milliseconds: 1500), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final label = widget.language.trim();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: GlassSurface.inner(
        borderRadius: 12,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 4, 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      label.isEmpty ? '✦ code' : label.toUpperCase(),
                      style: const TextStyle(
                        color: SovereignColors.gold,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ),
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: _copy,
                    child: SizedBox(
                      width: 28,
                      height: 28,
                      child: Icon(
                        _copied ? Icons.check_rounded : Icons.copy_rounded,
                        size: 14,
                        color: SovereignColors.gold
                            .withValues(alpha: _copied ? 1.0 : 0.8),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Container(
              height: 1,
              color: SovereignColors.ivory.withValues(alpha: 0.08),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SelectableText(
                  widget.code,
                  style: TextStyle(
                    fontFamily: _monoFallback.first,
                    fontFamilyFallback: _monoFallback,
                    fontSize: 13,
                    height: 1.5,
                    color: SovereignColors.ivory.withValues(alpha: 0.9),
                  ),
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
// Streaming caret — a pulsing gold block signalling "still writing".
// ---------------------------------------------------------------------------

/// A 7x15 rounded-2 gold block whose opacity pulses 0.25→0.9 every 650ms
/// (repeat-reverse). Shown at the end of the growing draft while streaming.
class StreamingCaret extends StatefulWidget {
  const StreamingCaret({super.key});

  @override
  State<StreamingCaret> createState() => _StreamingCaretState();
}

class _StreamingCaretState extends State<StreamingCaret>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 650),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.25, end: 0.9)
          .animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut)),
      child: Container(
        width: 7,
        height: 15,
        decoration: BoxDecoration(
          color: SovereignColors.gold,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Tool chip + typing indicator (moved from the screen, unchanged treatment).
// ---------------------------------------------------------------------------

/// The gold `✦ get_schedule…` chip shown while Martin uses a tool / thinks.
class ToolChip extends StatelessWidget {
  const ToolChip({super.key, required this.label});

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
class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1100))
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
// Toast — a 1.2s glass "Copied" confirmation floating above the input bar.
// ---------------------------------------------------------------------------

/// Floats [message] on inner glass (gold ring, ivory 12px) above the input bar
/// for 1.2 seconds. No-ops when no [Overlay] is available.
void showMartinToast(BuildContext context, String message) {
  final overlay = Overlay.maybeOf(context, rootOverlay: true);
  if (overlay == null) return;
  final entry = OverlayEntry(
    builder: (context) => Positioned(
      left: 0,
      right: 0,
      bottom: 110,
      child: IgnorePointer(
        child: Center(
          child: GlassSurface.inner(
            borderRadius: 12,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            ringColor: SovereignColors.gold,
            ringOpacity: 0.5,
            child: Text(
              message,
              style: const TextStyle(
                color: SovereignColors.ivory,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    ),
  );
  overlay.insert(entry);
  Timer(const Duration(milliseconds: 1200), entry.remove);
}
