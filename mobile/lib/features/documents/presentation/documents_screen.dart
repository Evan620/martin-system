// lib/features/documents/presentation/documents_screen.dart
//
// Documents — the third member screen, wired to live data. Everything shared
// with the member's TWG (their TWGs + global; transcripts/shared-workspace
// excluded server-side; confidential hidden client-side) surfaced as Sovereign
// glass cards.
//
// Loads via documentsControllerProvider.load() (post-frame), renders by sealed
// state (loading / error / empty / data), a glass search field that filters
// locally, file-type filter chips built from the DocKinds present, and doc
// cards that reuse the seed's glass look. Tapping a PDF pushes the in-app
// viewer (/documents/:id/pdf); other types download to a temp file and open
// with the OS. ✦ Summarise is a stub until Martin (#4).
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../application/documents_controller.dart';
import '../data/documents_models.dart';
import '../data/documents_repository.dart';

/// The Documents screen: serif title, a glass search field, file-type filter
/// chips, a list of glass document cards (each with an inner-glass type badge
/// and a ✦ Summarise action), rendered from live data by sealed state.
class DocumentsScreen extends ConsumerStatefulWidget {
  const DocumentsScreen({super.key});

  @override
  ConsumerState<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends ConsumerState<DocumentsScreen> {
  /// Local search text (filters by file name).
  String _query = '';

  /// Selected file-type filter (null = All).
  DocKind? _kind;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(documentsControllerProvider.notifier).load();
    });
  }

  /// ✦ Summarise — stubbed until Martin (#4); shows a hint, no backend call.
  void _summariseStub() {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(
        content: Text('Martin summaries are coming with the assistant.'),
      ));
  }

  /// Open a document: PDFs render in-app; other types download to a temp file
  /// and open with the OS viewer.
  Future<void> _open(Document d) async {
    if (d.isPdf) {
      context.push(
        '/documents/${d.id}/pdf?name=${Uri.encodeComponent(d.name)}',
      );
      return;
    }
    try {
      final bytes = await ref.read(documentsRepositoryProvider).downloadBytes(d.id);
      final dir = await getTemporaryDirectory();
      final f = File('${dir.path}/${d.name}');
      await f.writeAsBytes(bytes);
      await OpenFilex.open(f.path);
    } on DocumentException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(documentsControllerProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: switch (state) {
          DocumentsLoading() => const Center(
              child: CircularProgressIndicator(color: SovereignColors.gold),
            ),
          DocumentsError(:final message) => _ErrorView(
              message: message,
              onRetry: () =>
                  ref.read(documentsControllerProvider.notifier).load(),
            ),
          DocumentsEmpty() => const _EmptyView(),
          DocumentsData(:final all) => _DataView(
              all: all,
              query: _query,
              kind: _kind,
              twgName: _headerSubtitle(ref),
              onQueryChanged: (v) => setState(() => _query = v),
              onKindChanged: (k) => setState(() => _kind = k),
              onOpen: _open,
              onSummarise: _summariseStub,
            ),
        },
      ),
    );
  }
}

/// The member's first TWG name, used as the header eyebrow (falls back to a
/// neutral label when unknown).
String _headerSubtitle(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  if (auth is AuthAuthenticated && auth.user.twgs.isNotEmpty) {
    return auth.user.twgs.first.name;
  }
  return 'Shared with you';
}

/// Loaded list state: header, glass search field, file-type filter chips, then
/// the filtered document cards.
class _DataView extends StatelessWidget {
  const _DataView({
    required this.all,
    required this.query,
    required this.kind,
    required this.twgName,
    required this.onQueryChanged,
    required this.onKindChanged,
    required this.onOpen,
    required this.onSummarise,
  });

  final List<Document> all;
  final String query;
  final DocKind? kind;
  final String twgName;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<DocKind?> onKindChanged;
  final ValueChanged<Document> onOpen;
  final VoidCallback onSummarise;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    // Distinct kinds present in the data, in enum order, for the filter chips.
    final present = DocKind.values.where((k) => all.any((d) => d.kind == k)).toList();
    final shown = filterDocs(all, query: query, kind: kind);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Eyebrow (member's TWG) + serif title + subtitle.
          Text(
            twgName.toUpperCase(),
            style: const TextStyle(
              color: SovereignColors.gold,
              fontSize: 11,
              letterSpacing: 2.4,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Documents',
            style: textTheme.displaySmall?.copyWith(fontSize: 32, height: 1.05),
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

          // Glass search field.
          _SearchField(onChanged: onQueryChanged),
          const SizedBox(height: 14),

          // File-type filter chips: All + one per distinct kind present.
          _FilterChips(
            present: present,
            selected: kind,
            onChanged: onKindChanged,
          ),
          const SizedBox(height: 16),

          // Document cards (filtered) — or an inline empty when filters match
          // nothing.
          if (shown.isEmpty)
            const _InlineEmpty()
          else
            for (final doc in shown) ...[
              _DocumentCard(
                doc: doc,
                onTap: () => onOpen(doc),
                onSummarise: onSummarise,
              ),
              const SizedBox(height: 12),
            ],

          const SizedBox(height: 8),

          // Gold hint line.
          const _MartinHint(),
        ],
      ),
    );
  }
}

/// A glass surface styled as a search field. Wraps a borderless [TextField] so
/// typing filters the list locally.
class _SearchField extends StatelessWidget {
  const _SearchField({required this.onChanged});

  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      borderRadius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Icon(
            Icons.search,
            size: 20,
            color: SovereignColors.gold.withValues(alpha: 0.85),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: TextField(
              onChanged: onChanged,
              cursorColor: SovereignColors.gold,
              style: const TextStyle(
                color: SovereignColors.ivory,
                fontSize: 14,
              ),
              decoration: InputDecoration(
                isDense: true,
                border: InputBorder.none,
                hintText: 'Search documents…',
                hintStyle: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.55),
                  fontSize: 14,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Horizontal row of file-type filter chips: an "All" chip plus one chip per
/// distinct [DocKind] present in the data. The selected chip fills with gold.
class _FilterChips extends StatelessWidget {
  const _FilterChips({
    required this.present,
    required this.selected,
    required this.onChanged,
  });

  final List<DocKind> present;
  final DocKind? selected;
  final ValueChanged<DocKind?> onChanged;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _Chip(
            label: 'All',
            selected: selected == null,
            onTap: () => onChanged(null),
          ),
          for (final k in present) ...[
            const SizedBox(width: 8),
            _Chip(
              label: k.filterLabel,
              selected: selected == k,
              onTap: () => onChanged(k),
            ),
          ],
        ],
      ),
    );
  }
}

/// One filter chip. Selected = solid gold pill; unselected = lighter inner
/// glass.
class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final labelStyle = TextStyle(
      color: selected
          ? SovereignColors.navy
          : SovereignColors.ivory.withValues(alpha: 0.85),
      fontSize: 12.5,
      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
    );

    final content = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
      child: Text(label, style: labelStyle),
    );

    final Widget chip = selected
        ? DecoratedBox(
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
          )
        : GlassSurface.inner(borderRadius: 12, child: content);

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: chip,
    );
  }
}

/// One document rendered as a raised glass card. The leading type badge is an
/// inner glass chip (glass-inside-glass). Holds a meta line and a ✦ Summarise
/// action; tapping the card body opens the document.
class _DocumentCard extends StatelessWidget {
  const _DocumentCard({
    required this.doc,
    required this.onTap,
    required this.onSummarise,
  });

  final Document doc;
  final VoidCallback onTap;
  final VoidCallback onSummarise;

  static final _fmt = DateFormat('d MMM');

  @override
  Widget build(BuildContext context) {
    // Meta line: short MIME suffix · date · uploader email (whichever present).
    final created = doc.createdAt;
    final meta = [
      if (doc.mime != null) doc.kind.badge,
      if (created != null) _fmt.format(created),
      if ((doc.uploadedByEmail ?? '').isNotEmpty) doc.uploadedByEmail!,
    ].join(' · ');

    return GlassCard(
      padding: const EdgeInsets.all(14),
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // Inner-glass type badge.
              GlassSurface.inner(
                borderRadius: 14,
                width: 46,
                height: 46,
                alignment: Alignment.center,
                child: Text(
                  doc.kind.badge,
                  style: const TextStyle(
                    color: SovereignColors.gold,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              // Name + meta line.
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
                      meta,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
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
          const SizedBox(height: 10),
          // ✦ Summarise action (stub until Martin).
          Align(
            alignment: Alignment.centerLeft,
            child: _SummariseButton(onTap: onSummarise),
          ),
        ],
      ),
    );
  }
}

/// The ✦ Summarise pill (stub until Martin #4).
class _SummariseButton extends StatelessWidget {
  const _SummariseButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: SovereignColors.gold.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: SovereignColors.gold.withValues(alpha: 0.30),
          ),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.auto_awesome, size: 14, color: SovereignColors.gold),
            SizedBox(width: 6),
            Text(
              'Summarise',
              style: TextStyle(
                color: SovereignColors.gold,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
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
          const Icon(Icons.auto_awesome, size: 18, color: SovereignColors.gold),
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

/// Error state: a glass message + a Retry button.
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
              const Icon(Icons.cloud_off, color: SovereignColors.gold, size: 28),
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

/// Full-screen empty state (no documents shared at all).
class _EmptyView extends StatelessWidget {
  const _EmptyView();

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
              const Icon(Icons.folder_open, color: SovereignColors.gold, size: 30),
              const SizedBox(height: 12),
              Text(
                'No documents shared yet',
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium?.copyWith(fontSize: 16),
              ),
              const SizedBox(height: 6),
              Text(
                "When your TWG shares a file, it'll appear here.",
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: SovereignColors.ivory.withValues(alpha: 0.65),
                  fontSize: 12.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Inline empty state shown under the search/filters when nothing matches.
class _InlineEmpty extends StatelessWidget {
  const _InlineEmpty();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GlassCard(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            'No documents match your search.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: SovereignColors.ivory.withValues(alpha: 0.7),
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}
