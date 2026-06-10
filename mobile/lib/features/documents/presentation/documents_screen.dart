// lib/features/documents/presentation/documents_screen.dart
//
// Documents · native dashboard (v2) — everything shared with the member's TWG
// (their TWGs + global; transcripts/shared-workspace excluded server-side;
// confidential hidden client-side) as dense kit rows.
//
// Layout (top -> bottom), per the Native Dashboard v2 spec:
//   - compact `AppHeader`: TWG context label over "Documents" (no serif, no
//     eyebrow).
//   - the themed search field (filters locally by file name).
//   - 44px file-type filter chips: All + one per distinct DocKind present.
//   - one `RowGroup` of `ListRow`s: leading type-badge container, file name,
//     "TWG · date · uploader" meta, and a trailing ✦ Summarise icon-button —
//     THE screen's one filled-yellow action — pushing the existing
//     `/martin?q=Summarise…` route. Row tap keeps the existing open behavior
//     (PDF in-app, other types download + OS viewer).
//
// Loads via documentsControllerProvider.load() (post-frame), renders by sealed
// state (loading -> row-shaped skeletons / error / empty / data) inside an
// AnimatedSwitcher; pull-to-refresh re-runs load().
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../../core/glass/glass.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/motion/motion.dart';
import '../../../core/motion/pressable.dart';
import '../../../core/motion/skeleton.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/app_header.dart';
import '../../../core/ui/list_row.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/documents_controller.dart';
import '../data/documents_models.dart';
import '../data/documents_repository.dart';

/// The Documents screen: compact header, search field, filter chips and one
/// row group of documents, each with the trailing ✦ Summarise yellow action.
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

  /// ✦ Summarise — opens the Martin chat seeded with a summarise prompt for
  /// this document (the canonical `/martin?q=<seed>` route auto-sends the seed).
  void _summarise(Document d) {
    final seed = 'Summarise the document: ${d.name}';
    context.push('/martin?q=${Uri.encodeQueryComponent(seed)}');
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
        child: RefreshIndicator(
          color: SovereignColors.gold,
          backgroundColor: SovereignColors.navyRaised,
          onRefresh: () =>
              ref.read(documentsControllerProvider.notifier).load(),
          child: AnimatedSwitcher(
            duration: Motion.base,
            child: switch (state) {
              DocumentsLoading() =>
                const _LoadingView(key: ValueKey('loading')),
              DocumentsError(:final message) => _ErrorView(
                  key: const ValueKey('error'),
                  message: message,
                  onRetry: () =>
                      ref.read(documentsControllerProvider.notifier).load(),
                ),
              DocumentsEmpty() => const _EmptyView(key: ValueKey('empty')),
              DocumentsData(:final all) => _DataView(
                  key: const ValueKey('data'),
                  all: all,
                  query: _query,
                  kind: _kind,
                  twgLabel: _headerSubtitle(ref),
                  onQueryChanged: (v) => setState(() => _query = v),
                  onKindChanged: (k) => setState(() => _kind = k),
                  onOpen: _open,
                  onSummarise: _summarise,
                ),
            },
          ),
        ),
      ),
    );
  }
}

/// The member's TWG label, used as the header context line (one TWG → its
/// name, several → a compact multi-TWG label; falls back to a neutral label
/// when unknown).
String _headerSubtitle(WidgetRef ref) {
  final auth = ref.watch(authControllerProvider);
  if (auth is AuthAuthenticated) {
    final label = auth.user.twgs.headerLabel;
    if (label != null) return label;
  }
  return 'Shared with you';
}

/// Loaded list state: header, search field, filter chips, then the filtered
/// document rows in one RowGroup.
class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.all,
    required this.query,
    required this.kind,
    required this.twgLabel,
    required this.onQueryChanged,
    required this.onKindChanged,
    required this.onOpen,
    required this.onSummarise,
  });

  final List<Document> all;
  final String query;
  final DocKind? kind;
  final String twgLabel;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<DocKind?> onKindChanged;
  final ValueChanged<Document> onOpen;
  final ValueChanged<Document> onSummarise;

  @override
  Widget build(BuildContext context) {
    // Distinct kinds present in the data, in enum order, for the filter chips.
    final present =
        DocKind.values.where((k) => all.any((d) => d.kind == k)).toList();
    final shown = filterDocs(all, query: query, kind: kind);

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const CascadeIn(
            index: 0,
            child: AppHeader(title: 'Documents'),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 1,
            child: _TwgInfoCard(
              twgLabel: twgLabel,
              docCount: all.length,
              globalCount: all.where((d) => d.twgName == null).length,
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(index: 2, child: _SearchField(onChanged: onQueryChanged)),
          const SizedBox(height: Insets.md),
          CascadeIn(
            index: 3,
            child: _FilterChips(
              present: present,
              selected: kind,
              onChanged: onKindChanged,
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 4,
            child: RowGroup(children: [
              if (shown.isEmpty)
                const ListRow(
                  icon: Icons.search_off_rounded,
                  title: 'No documents match',
                  meta: 'Try a different search or filter.',
                )
              else
                for (final doc in shown)
                  ListRow(
                    leading: _KindBadge(kind: doc.kind),
                    title: doc.name,
                    meta: _docMeta(doc),
                    trailing: _SummariseButton(onTap: () => onSummarise(doc)),
                    onTap: () => onOpen(doc),
                  ),
            ]),
          ),
        ],
      ),
    );
  }
}

/// A header card housing the member's TWG context for the Documents screen:
/// a folder glyph, the TWG name (or multi-TWG label), and a document-count
/// summary. Built entirely from data already on hand (no fetch).
class _TwgInfoCard extends StatelessWidget {
  const _TwgInfoCard({
    required this.twgLabel,
    required this.docCount,
    required this.globalCount,
  });

  final String twgLabel;
  final int docCount;
  final int globalCount;

  String get _summary {
    final docs = '$docCount document${docCount == 1 ? '' : 's'}';
    // Show the global split only when there's a meaningful mix of TWG + global.
    if (globalCount > 0 && globalCount < docCount) {
      return '$docs · $globalCount global';
    }
    return '$docs shared with you';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(Insets.lg),
      decoration: BoxDecoration(
        color: SovereignColors.navyRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: SovereignColors.gold.withValues(alpha: 0.30)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: SovereignColors.gold.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.folder_shared_rounded,
                size: 22, color: SovereignColors.gold),
          ),
          const SizedBox(width: Insets.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  twgLabel,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: SovereignColors.ivory,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _summary,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 12.5,
                    color: SovereignColors.ivory
                        .withValues(alpha: SovereignColors.alphaMid),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The row meta line: "TWG · date · uploader" (Global when the document is not
/// scoped to a TWG; date/uploader only when present).
String _docMeta(Document d) {
  final fmt = DateFormat('d MMM');
  final parts = <String>[
    d.twgName ?? 'Global',
    if (d.createdAt != null) fmt.format(d.createdAt!),
    if ((d.uploadedByEmail ?? '').isNotEmpty) d.uploadedByEmail!,
  ];
  return parts.join(' · ');
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
      padding: const EdgeInsets.symmetric(
          horizontal: Insets.lg, vertical: Insets.xs),
      child: Row(
        children: [
          Icon(
            Icons.search,
            size: 20,
            color: SovereignColors.gold.withValues(alpha: 0.85),
          ),
          const SizedBox(width: Insets.md),
          Expanded(
            child: TextField(
              onChanged: onChanged,
              cursorColor: SovereignColors.gold,
              style: SovereignType.body,
              decoration: InputDecoration(
                isDense: true,
                border: InputBorder.none,
                hintText: 'Search documents…',
                hintStyle: SovereignType.body.copyWith(
                  color: SovereignColors.ivory
                      .withValues(alpha: SovereignColors.alphaMid),
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
/// distinct [DocKind] present in the data. 44px tall, segmented-style fills —
/// yellow stays reserved for the ✦ Summarise action.
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
            const SizedBox(width: Insets.sm),
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

/// One filter chip on the segmented-control language: selected = raised navy
/// with a gold ring, unselected = recessed ivory track. 44px tap target.
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
    return PressableScale(
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 44),
        padding: const EdgeInsets.symmetric(horizontal: Insets.lg),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected
              ? SovereignColors.navyRaised
              : SovereignColors.ivory.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected
                ? SovereignColors.gold.withValues(alpha: 0.45)
                : SovereignColors.ivory.withValues(alpha: 0.08),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: SovereignColors.ivory.withValues(
              alpha: selected
                  ? SovereignColors.alphaHigh
                  : SovereignColors.alphaMid,
            ),
          ),
        ),
      ),
    );
  }
}

/// The row's leading type badge — the kit's gold icon-container style holding
/// the short kind label (PDF / XLS / DOC / PPT / FILE).
class _KindBadge extends StatelessWidget {
  const _KindBadge({required this.kind});

  final DocKind kind;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 32,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: SovereignColors.gold.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(9),
      ),
      child: Text(
        kind.badge,
        style: const TextStyle(
          fontFamily: 'Inter',
          fontSize: 9.5,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
          color: SovereignColors.gold,
        ),
      ),
    );
  }
}

/// The trailing ✦ Summarise icon-button — THE screen's one filled-yellow
/// action, repeated per row (one pattern). 44px tap target around a 30px chip.
class _SummariseButton extends StatelessWidget {
  const _SummariseButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Summarise',
      child: PressableScale(
        onTap: onTap,
        child: SizedBox(
          width: 44,
          height: 44,
          child: Center(
            child: Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: SovereignColors.gold,
                borderRadius: BorderRadius.circular(9),
              ),
              child: const Icon(
                Icons.auto_awesome,
                size: 16,
                color: SovereignColors.navy,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Loading — header/search/row-shaped skeletons (no spinner), cross-fading to
/// content.
class _LoadingView extends StatelessWidget {
  const _LoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          SkeletonBlock(width: 90, height: 12),
          SizedBox(height: Insets.sm),
          SkeletonBlock(width: 170, height: 22),
          SizedBox(height: Insets.lg),
          SkeletonBlock(width: double.infinity, height: 44, radius: 16),
          SizedBox(height: Insets.md),
          SkeletonBlock(width: 200, height: 36, radius: 12),
          SizedBox(height: Insets.lg),
          RowGroup(children: [
            SkeletonRow(),
            SkeletonRow(),
            SkeletonRow(),
            SkeletonRow(),
          ]),
        ],
      ),
    );
  }
}

/// Error state: a glass message + a Retry button.
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
              const Icon(Icons.cloud_off, color: SovereignColors.gold, size: 28),
              const SizedBox(height: Insets.md),
              Text(
                message,
                textAlign: TextAlign.center,
                style: SovereignType.body.copyWith(
                  color: SovereignColors.ivory
                      .withValues(alpha: SovereignColors.alphaHigh),
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

/// Full-screen empty state (no documents shared at all).
class _EmptyView extends StatelessWidget {
  const _EmptyView({super.key});

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
              const Icon(Icons.folder_open,
                  color: SovereignColors.gold, size: 30),
              const SizedBox(height: Insets.md),
              const Text(
                'No documents shared yet',
                textAlign: TextAlign.center,
                style: SovereignType.section,
              ),
              const SizedBox(height: Insets.xs),
              Text(
                "When your TWG shares a file, it'll appear here.",
                textAlign: TextAlign.center,
                style: SovereignType.secondary.copyWith(
                  color: SovereignColors.ivory
                      .withValues(alpha: SovereignColors.alphaMid),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
