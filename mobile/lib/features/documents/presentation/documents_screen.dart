// lib/features/documents/presentation/documents_screen.dart
//
// Documents — the third member screen. Everything shared with the member's TWG,
// surfaced as Sovereign glass cards. Martin can summarise any of them on request.
//
// Visual build only: representative seed content (member "Amina Diallo",
// "Energy TWG"). Live API data is a later pass.
import 'package:flutter/material.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';

/// Lightweight view-model for a seeded document row.
class _DocItem {
  const _DocItem({
    required this.icon,
    required this.name,
    required this.meta,
  });

  final IconData icon;
  final String name;

  /// Type/date line, e.g. "PDF · 6 Jun".
  final String meta;
}

/// The Documents screen: serif title, a glass search field, a list of glass
/// document cards (each with an inner-glass type/icon chip), and a gold hint
/// that nudges the member to ask Martin for a summary.
class DocumentsScreen extends StatelessWidget {
  const DocumentsScreen({super.key});

  static const List<_DocItem> _docs = [
    _DocItem(
      icon: Icons.picture_as_pdf_outlined,
      name: 'Energy Policy Draft v3',
      meta: 'PDF · 6 Jun',
    ),
    _DocItem(
      icon: Icons.table_chart_outlined,
      name: 'Q2 Budget',
      meta: 'XLSX · 5 Jun',
    ),
    _DocItem(
      icon: Icons.description_outlined,
      name: 'Minutes',
      meta: 'DOCX · 4 Jun',
    ),
    _DocItem(
      icon: Icons.slideshow_outlined,
      name: 'Grid Interconnection Brief',
      meta: 'PPTX · 2 Jun',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: SovereignColors.navy,
      body: SafeArea(
        bottom: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Eyebrow + serif title + subtitle.
              Text(
                'DOCUMENTS',
                style: TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 11,
                  letterSpacing: 2.4,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Documents',
                style: textTheme.displaySmall?.copyWith(
                  fontSize: 32,
                  height: 1.05,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Shared with you',
                style: textTheme.bodyMedium?.copyWith(
                  color: SovereignColors.ivory.withValues(alpha: 0.62),
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 20),

              // Glass search field (read-only visual stand-in for now).
              const _SearchField(),
              const SizedBox(height: 16),

              // Document cards.
              for (final doc in _docs) ...[
                _DocumentCard(doc: doc),
                const SizedBox(height: 12),
              ],

              const SizedBox(height: 8),

              // Gold hint line.
              const _MartinHint(),
            ],
          ),
        ),
      ),
    );
  }
}

/// A base glass surface styled as a search field.
class _SearchField extends StatelessWidget {
  const _SearchField();

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Icon(
            Icons.search,
            size: 20,
            color: SovereignColors.gold.withValues(alpha: 0.85),
          ),
          const SizedBox(width: 12),
          Text(
            'Search documents…',
            style: TextStyle(
              color: SovereignColors.ivory.withValues(alpha: 0.55),
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}

/// One document row rendered as a raised glass card. The leading type/icon
/// badge is an inner glass chip (glass-inside-glass) so it reads as a lighter
/// layer nested in the card.
class _DocumentCard extends StatelessWidget {
  const _DocumentCard({required this.doc});

  final _DocItem doc;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(14),
      onTap: () {},
      child: Row(
        children: [
          // Inner-glass type/icon chip.
          GlassSurface.inner(
            borderRadius: 14,
            width: 46,
            height: 46,
            alignment: Alignment.center,
            child: Icon(
              doc.icon,
              size: 22,
              color: SovereignColors.gold,
            ),
          ),
          const SizedBox(width: 14),
          // Name + type/date line.
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  doc.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: SovereignColors.ivory,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  doc.meta,
                  style: TextStyle(
                    color: SovereignColors.ivory.withValues(alpha: 0.58),
                    fontSize: 12.5,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Icon(
            Icons.chevron_right,
            size: 22,
            color: SovereignColors.gold.withValues(alpha: 0.7),
          ),
        ],
      ),
    );
  }
}

/// Gold-tinted hint nudging the member to ask Martin for a summary.
class _MartinHint extends StatelessWidget {
  const _MartinHint();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: SovereignColors.gold.withValues(alpha: 0.10),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(12),
          topRight: Radius.circular(12),
          bottomRight: Radius.circular(12),
          bottomLeft: Radius.circular(2),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.auto_awesome,
            size: 18,
            color: SovereignColors.gold,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Ask Martin to summarise any of these.',
              style: TextStyle(
                color: SovereignColors.ivory.withValues(alpha: 0.9),
                fontSize: 13.5,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
