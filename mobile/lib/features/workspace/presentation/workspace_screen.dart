// lib/features/workspace/presentation/workspace_screen.dart
//
// The per-TWG Workspace hub · native dashboard (v2).
//
// Layout (top -> bottom), per the Native Dashboard v2 spec:
//   - back button + compact `AppHeader` (pillar label over TWG name) with the
//     TWG switcher chip trailing (members in 2+ TWGs only; replace-navigation
//     + `Key('workspace-switcher')` kept).
//   - a row of 3 `StatTile`s: Members / Open actions / Next mtg (HH:mm or '—').
//   - `SectionHeader` sections as `RowGroup`s: Next meeting, Documents (cap 5,
//     '+N more' kept), Your tasks (cap 5).
//   - the full-width yellow Ask-Martin pill — THE screen's one filled-yellow
//     action -> /martin?twg=<id>.
//
// Controller/best-effort logic unchanged: TWG detail is required; meetings +
// tasks are best-effort and empty sections show a gentle empty row.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

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
import '../../../core/ui/section_header.dart';
import '../../../core/ui/stat_tile.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../../documents/data/documents_models.dart';
import '../../profile/data/me_models.dart';
import '../application/workspace_controller.dart';

class WorkspaceScreen extends ConsumerStatefulWidget {
  const WorkspaceScreen({super.key, required this.twgId});
  final String twgId;

  @override
  ConsumerState<WorkspaceScreen> createState() => _WorkspaceScreenState();
}

class _WorkspaceScreenState extends ConsumerState<WorkspaceScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(workspaceControllerProvider(widget.twgId).notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(workspaceControllerProvider(widget.twgId));
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      body: Stack(
        children: [
          const _Backdrop(),
          SafeArea(
            bottom: false,
            child: RefreshIndicator(
              color: SovereignColors.gold,
              backgroundColor: SovereignColors.navyRaised,
              onRefresh: () => ref
                  .read(workspaceControllerProvider(widget.twgId).notifier)
                  .load(),
              child: AnimatedSwitcher(
                duration: Motion.base,
                child: switch (state) {
                  WorkspaceLoading() =>
                    const _LoadingView(key: ValueKey('loading')),
                  WorkspaceError(:final message) => _ErrorView(
                      key: const ValueKey('error'),
                      message: message,
                      onRetry: () => ref
                          .read(workspaceControllerProvider(widget.twgId)
                              .notifier)
                          .load()),
                  WorkspaceData() => _Body(
                      key: const ValueKey('data'),
                      twgId: widget.twgId,
                      data: state),
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Loaded state — header + 3 tiles + sections + the Ask-Martin pill.
// ---------------------------------------------------------------------------

class _Body extends ConsumerWidget {
  const _Body({super.key, required this.twgId, required this.data});
  final String twgId;
  final WorkspaceData data;

  static final _meetingFmt = DateFormat('EEE d MMM · HH:mm');
  static final _timeFmt = DateFormat('HH:mm');
  static final _dayFmt = DateFormat('EEE d MMM');
  static final _docFmt = DateFormat('d MMM yyyy');
  static const _cap = 5;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final myTwgs = auth is AuthAuthenticated ? auth.user.twgs : const <Twg>[];
    final detail = data.detail;
    final next = data.meetings.isNotEmpty ? data.meetings.first : null;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _BackButton(
                onTap: () =>
                    context.canPop() ? context.pop() : context.go('/home'),
              ),
              const SizedBox(width: Insets.md),
              Expanded(
                child: AppHeader(
                  title: detail.name,
                  context_: detail.pillarLabel,
                  trailing: myTwgs.length > 1
                      ? _SwitcherChip(current: twgId, twgs: myTwgs)
                      : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: Insets.lg),

          // 3 stat tiles — cascade in at indices 0–2.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: CascadeIn(
                  index: 0,
                  child: StatTile(
                    label: 'Members',
                    value: '${detail.members.length}',
                    sub: 'in this TWG',
                  ),
                ),
              ),
              const SizedBox(width: Insets.sm),
              Expanded(
                child: CascadeIn(
                  index: 1,
                  child: StatTile(
                    label: 'Open actions',
                    value: '${detail.openActions}',
                    sub: 'to close',
                  ),
                ),
              ),
              const SizedBox(width: Insets.sm),
              Expanded(
                child: CascadeIn(
                  index: 2,
                  child: StatTile(
                    label: 'Next mtg',
                    value: next != null
                        ? _timeFmt.format(next.scheduledAt)
                        : '—',
                    sub: next != null
                        ? _dayFmt.format(next.scheduledAt)
                        : 'not scheduled',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: Insets.section),

          // Next meeting.
          CascadeIn(
            index: 3,
            child: _Section(
              title: 'Next meeting',
              group: RowGroup(children: [
                if (next != null)
                  ListRow(
                    icon: Icons.event_rounded,
                    title: next.title,
                    meta: _meetingFmt.format(next.scheduledAt),
                  )
                else
                  const ListRow(
                    icon: Icons.event_busy_rounded,
                    title: 'No upcoming meetings',
                    meta: 'Nothing scheduled yet',
                  ),
              ]),
            ),
          ),
          const SizedBox(height: Insets.section),

          // Documents (cap 5, '+N more' kept).
          CascadeIn(
            index: 4,
            child: _Section(
              title: 'Documents',
              group: RowGroup(children: [
                if (detail.documents.isEmpty)
                  const ListRow(
                    icon: Icons.folder_open_rounded,
                    title: 'No documents yet',
                    meta: 'Uploads will appear here',
                  )
                else
                  for (final d in detail.documents.take(_cap))
                    _docRow(context, d),
              ]),
              overflow: detail.documents.length > _cap
                  ? detail.documents.length - _cap
                  : 0,
            ),
          ),
          const SizedBox(height: Insets.section),

          // Your tasks (cap 5, '+N more' kept).
          CascadeIn(
            index: 5,
            child: _Section(
              title: 'Your tasks',
              group: RowGroup(children: [
                if (data.tasks.isEmpty)
                  const ListRow(
                    icon: Icons.task_alt_rounded,
                    title: 'No tasks for you here',
                    meta: 'All clear',
                  )
                else
                  for (final t in data.tasks.take(_cap)) _taskRow(t),
              ]),
              overflow:
                  data.tasks.length > _cap ? data.tasks.length - _cap : 0,
            ),
          ),
          const SizedBox(height: Insets.section),

          // Ask Martin — THE screen's one filled-yellow action.
          CascadeIn(
            index: 6,
            child: _AskMartinButton(twgId: twgId, twgName: detail.name),
          ),
        ],
      ),
    );
  }

  /// One document row. Workspace is a pushed route under the Home branch, so a
  /// cross-branch push to the Documents shell's PDF viewer is unsafe. Open the
  /// document through Martin instead (existing behavior, unchanged).
  Widget _docRow(BuildContext context, Document d) {
    return ListRow(
      icon: Icons.insert_drive_file_outlined,
      title: d.name,
      meta: d.createdAt != null ? _docFmt.format(d.createdAt!) : null,
      onTap: () => context.push(
        '/martin?q=${Uri.encodeQueryComponent('Open the document ${d.name}')}',
      ),
    );
  }

  /// One task row: checkbox state leading, description, due/done meta.
  Widget _taskRow(ActionItem item) {
    return ListRow(
      icon: item.isDone
          ? Icons.check_box_rounded
          : Icons.check_box_outline_blank_rounded,
      title: item.description,
      meta: item.isDone
          ? 'Done'
          : (item.dueDate != null ? 'Due ${_dayFmt.format(item.dueDate!)}' : null),
    );
  }
}

/// A titled `RowGroup` section with an optional muted '+N more' line.
class _Section extends StatelessWidget {
  const _Section({required this.title, required this.group, this.overflow = 0});
  final String title;
  final Widget group;
  final int overflow;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(title: title),
        group,
        if (overflow > 0)
          Padding(
            padding: const EdgeInsets.only(top: Insets.sm, left: 2),
            child: Text(
              '+$overflow more',
              style: SovereignType.caption.copyWith(
                color: SovereignColors.ivory
                    .withValues(alpha: SovereignColors.alphaMid),
              ),
            ),
          ),
      ],
    );
  }
}

/// The full-width yellow Ask-Martin pill — the screen's ONE filled-yellow
/// action, scoped to this TWG (route unchanged: `/martin?twg=<id>`).
class _AskMartinButton extends StatelessWidget {
  const _AskMartinButton({required this.twgId, required this.twgName});
  final String twgId;
  final String twgName;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Ask Martin about $twgName',
      child: PressableScale(
        onTap: () => context.push('/martin?twg=$twgId'),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
              horizontal: Insets.lg, vertical: Insets.md + 2),
          decoration: BoxDecoration(
            color: SovereignColors.gold,
            borderRadius: BorderRadius.circular(13),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('✦',
                  style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 15,
                      color: SovereignColors.navy)),
              const SizedBox(width: Insets.sm),
              Flexible(
                child: Text(
                  'Ask Martin about $twgName',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 14.5,
                      fontWeight: FontWeight.w800,
                      color: SovereignColors.navy),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The TWG switcher, restyled as a gold-tinted chip (tiny accent — not a
/// filled-yellow action). Keeps `Key('workspace-switcher')` + the
/// replace-navigation so back never stacks workspaces.
class _SwitcherChip extends StatelessWidget {
  const _SwitcherChip({required this.current, required this.twgs});
  final String current;
  final List<Twg> twgs;

  @override
  Widget build(BuildContext context) {
    // Compact, fixed-width trigger — the header card already names the current
    // TWG, so the switcher only needs a short "Switch" affordance (showing the
    // long TWG name here overflowed the header on long names).
    return PopupMenuButton<String>(
      key: const Key('workspace-switcher'),
      color: SovereignColors.navyRaised,
      onSelected: (id) => context.replace('/home/workspace/$id'),
      itemBuilder: (_) => [
        // List only the member's OTHER TWGs — selecting the current one would
        // be a no-op self-replace.
        for (final t in twgs.where((t) => t.id != current))
          PopupMenuItem<String>(
            value: t.id,
            child: Text(t.name, style: SovereignType.body),
          ),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(
            horizontal: Insets.md, vertical: Insets.sm),
        decoration: BoxDecoration(
          color: SovereignColors.gold.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(9),
        ),
        child: const Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.swap_horiz_rounded, color: SovereignColors.gold, size: 16),
          SizedBox(width: 4),
          Text('Switch',
              style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                  color: SovereignColors.gold)),
        ]),
      ),
    );
  }
}

class _BackButton extends StatelessWidget {
  const _BackButton({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Back',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: const GlassSurface(
          borderRadius: 14,
          padding: EdgeInsets.all(10),
          child:
              Icon(Icons.arrow_back, size: 18, color: SovereignColors.ivory),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Loading — tile/row-shaped skeleton (3 tiles + section rows), no spinner.
// ---------------------------------------------------------------------------

class _LoadingView extends StatelessWidget {
  const _LoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
          ]),
          SizedBox(height: Insets.section),
          RowGroup(children: [SkeletonRow()]),
          SizedBox(height: Insets.section),
          RowGroup(children: [SkeletonRow(), SkeletonRow(), SkeletonRow()]),
          SizedBox(height: Insets.section),
          RowGroup(children: [SkeletonRow(), SkeletonRow()]),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Background + error state.
// ---------------------------------------------------------------------------

class _Backdrop extends StatelessWidget {
  const _Backdrop();
  @override
  Widget build(BuildContext context) {
    return const Positioned.fill(
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              SovereignColors.navyRaised,
              SovereignColors.navy,
              SovereignColors.navyDeep
            ],
            stops: [0, 0.5, 1],
          ),
        ),
      ),
    );
  }
}

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
          child: Column(mainAxisSize: MainAxisSize.min, children: [
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
                    color: SovereignColors.gold, fontWeight: FontWeight.w700),
              ),
            ),
          ]),
        ),
      ],
    );
  }
}
