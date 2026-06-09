// lib/core/glass/glass.dart
//
// Sovereign glass design system — Apple "Liquid Glass" reading, but navy + gold,
// never sky-blue.
//
// The visual recipe (ported from the floating nav reference in app_shell.dart):
//   ClipRRect
//     -> BackdropFilter(ImageFilter.blur)          // frost the content behind
//        -> Container(
//             gradient: translucent navy             // the tint
//             border:   thin gold ring               // the Sovereign edge
//             boxShadow: layered soft shadows        // real, stacked depth
//           )
//
// Glass-inside-glass:
//   An outer [GlassSurface] (depth `base`/`raised`) can contain inner
//   [GlassSurface.inner] layers. Inner layers are intentionally LIGHTER — less
//   blur, lower tint, no heavy drop shadow, and a hairline ivory highlight on
//   top — so a nested stack reads as layered depth rather than turning muddy.
//
// Public API:
//   - GlassDepth            enum {base, raised, inner}
//   - GlassSurface          the core glassmorphic container (+ .inner ctor)
//   - GlassCard             a GlassSurface tuned as a content card
//
// See README-style usage notes at the bottom of this file.
import 'dart:ui' show ImageFilter;
import 'package:flutter/material.dart';
import '../theme/sovereign_colors.dart';

/// How a glass layer sits in the depth stack.
///
/// * [base]   — a normal surface floating over content (e.g. the nav pill).
/// * [raised] — a more prominent / hero surface; slightly stronger tint + glow.
/// * [inner]  — a nested layer placed *inside* another glass surface. Lighter
///   blur and tint, no heavy shadow, hairline highlight — for Liquid Glass
///   nesting that reads as layered depth, not mud.
enum GlassDepth { base, raised, inner }

/// Tuning constants per depth. Centralised so the look stays DRY + Sovereign.
class _GlassSpec {
  const _GlassSpec({
    required this.blurSigma,
    required this.tintOpacity,
    required this.ringOpacity,
    required this.shadows,
    required this.topHighlight,
  });

  final double blurSigma;
  final double tintOpacity;
  final double ringOpacity;
  final List<BoxShadow> shadows;

  /// A hairline ivory highlight along the top edge (gives inner layers a
  /// "lit rim" so they lift off the surface below). Null = no highlight.
  final BorderSide? topHighlight;

  static const _baseShadows = <BoxShadow>[
    BoxShadow(color: Color(0x57000000), blurRadius: 18, offset: Offset(0, 10)),
    BoxShadow(color: Color(0x38000000), blurRadius: 46, offset: Offset(0, 28)),
  ];

  static const _raisedShadows = <BoxShadow>[
    BoxShadow(color: Color(0x66000000), blurRadius: 26, offset: Offset(0, 14)),
    BoxShadow(color: Color(0x40000000), blurRadius: 60, offset: Offset(0, 34)),
  ];

  // Inner layers cast almost nothing — just a whisper to detach from the layer
  // beneath without muddying the stack.
  static const _innerShadows = <BoxShadow>[
    BoxShadow(color: Color(0x1F000000), blurRadius: 10, offset: Offset(0, 4)),
  ];

  static const base = _GlassSpec(
    blurSigma: 22,
    tintOpacity: 0.82,
    ringOpacity: 0.30,
    shadows: _baseShadows,
    topHighlight: null,
  );

  static const raised = _GlassSpec(
    blurSigma: 26,
    tintOpacity: 0.88,
    ringOpacity: 0.38,
    shadows: _raisedShadows,
    topHighlight: null,
  );

  static const inner = _GlassSpec(
    blurSigma: 8,
    tintOpacity: 0.34,
    ringOpacity: 0.18,
    shadows: _innerShadows,
    topHighlight: BorderSide(color: Color(0x26F6F1E7), width: 1),
  );

  static _GlassSpec of(GlassDepth depth) => switch (depth) {
        GlassDepth.base => base,
        GlassDepth.raised => raised,
        GlassDepth.inner => inner,
      };
}

/// The core Sovereign glassmorphic container.
///
/// `ClipRRect` + `BackdropFilter(ImageFilter.blur)` + a translucent navy
/// gradient + a thin gold ring + a layered soft-shadow stack.
///
/// Defaults match the floating nav. Override any knob as needed; or pass a
/// [depth] to pick a tuned preset ([GlassDepth.base] / [raised] / [inner]).
///
/// For nested Liquid-Glass layers, prefer the [GlassSurface.inner] constructor.
class GlassSurface extends StatelessWidget {
  const GlassSurface({
    super.key,
    this.child,
    this.depth = GlassDepth.base,
    this.borderRadius = 24,
    this.padding,
    this.width,
    this.height,
    this.alignment,
    this.blurSigma,
    this.tintOpacity,
    this.ringColor,
    this.ringOpacity,
    this.goldGlow = false,
    this.shadows,
    this.tintColors,
  });

  /// Convenience constructor for a nested layer placed *inside* another glass
  /// surface. Lighter blur/tint, hairline highlight, near-zero shadow.
  ///
  /// Equivalent to `GlassSurface(depth: GlassDepth.inner, ...)`, with a tighter
  /// default corner radius suited to inset chips/rows.
  const GlassSurface.inner({
    super.key,
    this.child,
    this.borderRadius = 16,
    this.padding,
    this.width,
    this.height,
    this.alignment,
    this.blurSigma,
    this.tintOpacity,
    this.ringColor,
    this.ringOpacity,
    this.goldGlow = false,
    this.shadows,
    this.tintColors,
  }) : depth = GlassDepth.inner;

  /// Content rendered on top of the glass.
  final Widget? child;

  /// Depth preset that drives blur, tint, ring and shadow defaults.
  final GlassDepth depth;

  /// Corner radius for the clip, gradient and ring.
  final double borderRadius;

  /// Inner padding around [child].
  final EdgeInsetsGeometry? padding;

  final double? width;
  final double? height;
  final AlignmentGeometry? alignment;

  /// Gaussian blur sigma for the backdrop. Defaults to the [depth] preset.
  final double? blurSigma;

  /// Opacity (0–1) of the navy tint gradient. Defaults to the [depth] preset.
  final double? tintOpacity;

  /// Ring (border) colour. Defaults to Sovereign gold.
  final Color? ringColor;

  /// Ring opacity (0–1). Defaults to the [depth] preset.
  final double? ringOpacity;

  /// Add a faint gold halo so the surface reads as Sovereign, not generic.
  final bool goldGlow;

  /// Override the entire drop-shadow stack. Defaults to the [depth] preset.
  /// Pass an empty list for a flat, shadowless surface.
  final List<BoxShadow>? shadows;

  /// Override the two-stop tint gradient colours (already alpha-applied).
  /// When null, a navy gradient is derived from [tintOpacity].
  final List<Color>? tintColors;

  @override
  Widget build(BuildContext context) {
    final spec = _GlassSpec.of(depth);
    final radius = BorderRadius.circular(borderRadius);
    final sigma = blurSigma ?? spec.blurSigma;
    final tint = tintOpacity ?? spec.tintOpacity;
    final ring = (ringColor ?? SovereignColors.gold)
        .withValues(alpha: ringOpacity ?? spec.ringOpacity);

    final gradientColors = tintColors ??
        [
          SovereignColors.navy.withValues(alpha: tint),
          SovereignColors.navyDeep.withValues(alpha: tint * 0.78),
        ];

    final boxShadows = <BoxShadow>[
      ...(shadows ?? spec.shadows),
      if (goldGlow)
        BoxShadow(
          color: SovereignColors.gold.withValues(alpha: 0.06),
          blurRadius: 28,
        ),
    ];

    return DecoratedBox(
      // Shadows must live OUTSIDE the ClipRRect, or the clip eats them.
      decoration: BoxDecoration(
        borderRadius: radius,
        boxShadow: boxShadows.isEmpty ? null : boxShadows,
      ),
      child: ClipRRect(
        borderRadius: radius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: sigma, sigmaY: sigma),
          child: Container(
            width: width,
            height: height,
            alignment: alignment,
            padding: padding,
            decoration: BoxDecoration(
              borderRadius: radius,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: gradientColors,
              ),
              border: Border.fromBorderSide(
                BorderSide(color: ring, width: 1),
              ),
            ),
            // Hairline ivory highlight on top for inner/nested layers.
            foregroundDecoration: spec.topHighlight == null
                ? null
                : BoxDecoration(
                    borderRadius: radius,
                    border: Border(top: spec.topHighlight!),
                  ),
            child: child,
          ),
        ),
      ),
    );
  }
}

/// A [GlassSurface] tuned as a content card: rounded ~20, comfortable padding,
/// `raised` depth by default so cards sit clearly above the background.
///
/// Place [GlassSurface.inner] widgets inside a [GlassCard] for layered depth.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    this.child,
    this.depth = GlassDepth.raised,
    this.borderRadius = 20,
    this.padding = const EdgeInsets.all(20),
    this.width,
    this.height,
    this.goldGlow = true,
    this.onTap,
  });

  final Widget? child;
  final GlassDepth depth;
  final double borderRadius;
  final EdgeInsetsGeometry padding;
  final double? width;
  final double? height;
  final bool goldGlow;

  /// Optional tap handler. When set, the card becomes tappable with an ink-free
  /// (glass-friendly) hit region.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final surface = GlassSurface(
      depth: depth,
      borderRadius: borderRadius,
      padding: padding,
      width: width,
      height: height,
      goldGlow: goldGlow,
      child: child,
    );
    if (onTap == null) return surface;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: surface,
    );
  }
}

// ---------------------------------------------------------------------------
// USAGE
//
// Base surface (a floating panel over page content):
//
//   GlassSurface(
//     borderRadius: 34,
//     padding: const EdgeInsets.symmetric(horizontal: 12),
//     goldGlow: true,
//     child: Row(children: [...]),
//   )
//
// A content card (raised, glowing, padded):
//
//   GlassCard(
//     child: Column(children: [Text('Next meeting'), ...]),
//   )
//
// Glass-inside-glass (Liquid Glass nesting):
//   Wrap inner panels with GlassSurface.inner — they auto-lighten (less blur,
//   lower tint, hairline highlight, near-zero shadow) so the stack reads as
//   layered depth instead of muddy frost.
//
//   GlassCard(                            // outer = raised
//     child: Column(
//       children: [
//         const Text('Agenda'),
//         const SizedBox(height: 12),
//         GlassSurface.inner(              // nested lighter layer
//           padding: const EdgeInsets.all(12),
//           child: const Text('1. Opening remarks'),
//         ),
//       ],
//     ),
//   )
//
// You can nest deeper (inner-inside-inner) — each inner layer is already light,
// so additional nesting stays legible. Override any knob (blurSigma,
// tintOpacity, ringColor/ringOpacity, shadows, borderRadius) when a one-off
// needs it; reach for the depth presets first to stay DRY + Sovereign.
// ---------------------------------------------------------------------------
