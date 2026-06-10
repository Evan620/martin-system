// lib/features/workspace/presentation/workspace_screen.dart
//
// The per-TWG Workspace hub: an ambient navy/gold backdrop, a header (back +
// TWG name + pillar chip + member count + a switcher when the member is in 2+
// TWGs), then glass-inside-glass sections — next meeting, documents, your
// tasks — and an Ask-Martin card scoped to this TWG. Best-effort: empty
// sections show a gentle empty state.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../../documents/data/documents_models.dart';
import '../../meetings/data/meetings_models.dart';
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
            child: switch (state) {
              WorkspaceLoading() => const Center(
                  child: CircularProgressIndicator(color: SovereignColors.gold)),
              WorkspaceError(:final message) => _ErrorView(
                  message: message,
                  onRetry: () => ref
                      .read(workspaceControllerProvider(widget.twgId).notifier)
                      .load()),
              WorkspaceData() => _Body(twgId: widget.twgId, data: state),
            },
          ),
        ],
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.twgId, required this.data});
  final String twgId;
  final WorkspaceData data;

  static final _fmt = DateFormat('EEE d MMM · HH:mm');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final myTwgs = auth is AuthAuthenticated ? auth.user.twgs : const <Twg>[];
    final detail = data.detail;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row: back + (switcher when 2+ TWGs).
          Row(
            children: [
              _GlassIconButton(
                icon: Icons.arrow_back_rounded,
                onTap: () => context.canPop() ? context.pop() : context.go('/home'),
              ),
              const Spacer(),
              if (myTwgs.length > 1)
                _Switcher(current: twgId, twgs: myTwgs),
            ],
          ),
          const SizedBox(height: 12),
          Text(detail.pillarLabel.toUpperCase(),
              style: TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 10,
                  letterSpacing: 3,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(detail.name,
              style: const TextStyle(
                  color: SovereignColors.ivory,
                  fontFamily: 'Georgia',
                  fontSize: 30,
                  fontWeight: FontWeight.w500)),
          const SizedBox(height: 6),
          Text(
            '${detail.members.length} member${detail.members.length == 1 ? '' : 's'}'
            '${detail.openActions > 0 ? ' · ${detail.openActions} open action${detail.openActions == 1 ? '' : 's'}' : ''}',
            style: TextStyle(
                color: SovereignColors.ivory.withValues(alpha: 0.6), fontSize: 13),
          ),
          const SizedBox(height: 18),

          // Next meeting.
          _Section(
            label: 'NEXT MEETING',
            child: data.meetings.isEmpty
                ? const _Empty('No upcoming meetings.')
                : _NextMeeting(meeting: data.meetings.first, fmt: _fmt),
          ),
          const SizedBox(height: 14),

          // Documents.
          _Section(
            label: 'DOCUMENTS',
            child: detail.documents.isEmpty
                ? const _Empty('No documents yet.')
                : _CappedList(
                    total: detail.documents.length,
                    builder: (i) => _DocRow(document: detail.documents[i]),
                  ),
          ),
          const SizedBox(height: 14),

          // Your tasks.
          _Section(
            label: 'YOUR TASKS',
            child: data.tasks.isEmpty
                ? const _Empty('No tasks for you here.')
                : _CappedList(
                    total: data.tasks.length,
                    builder: (i) => _TaskRow(item: data.tasks[i]),
                  ),
          ),
          const SizedBox(height: 14),

          // Ask Martin (scoped to this TWG).
          GlassCard(
            onTap: () => context.push('/martin?twg=$twgId'),
            child: Row(children: [
              const Text('✦',
                  style: TextStyle(color: SovereignColors.gold, fontSize: 18)),
              const SizedBox(width: 10),
              Expanded(
                child: Text('Ask Martin about ${detail.name}',
                    style: TextStyle(
                        color: SovereignColors.ivory.withValues(alpha: 0.9),
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600)),
              ),
              Icon(Icons.chevron_right, color: SovereignColors.gold.withValues(alpha: 0.8)),
            ]),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.label, required this.child});
  final String label;
  final Widget child;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(label,
              style: const TextStyle(
                  color: SovereignColors.gold,
                  fontSize: 9,
                  letterSpacing: 2.4,
                  fontWeight: FontWeight.w600)),
        ),
        GlassCard(child: child),
      ],
    );
  }
}

class _NextMeeting extends StatelessWidget {
  const _NextMeeting({required this.meeting, required this.fmt});
  final Meeting meeting;
  final DateFormat fmt;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(meeting.title,
            style: const TextStyle(
                color: SovereignColors.ivory, fontSize: 15, fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Row(children: [
          const Icon(Icons.schedule, size: 14, color: SovereignColors.gold),
          const SizedBox(width: 6),
          Text(fmt.format(meeting.scheduledAt),
              style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.82), fontSize: 13)),
        ]),
      ],
    );
  }
}

class _TaskRow extends StatelessWidget {
  const _TaskRow({required this.item});
  final ActionItem item;
  @override
  Widget build(BuildContext context) {
    final done = item.isDone;
    return GlassSurface.inner(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
      child: Row(children: [
        Icon(done ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded,
            size: 18, color: SovereignColors.gold),
        const SizedBox(width: 10),
        Expanded(
          child: Text(item.description,
              style: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: done ? 0.5 : 0.9),
                  fontSize: 13.5,
                  decoration: done ? TextDecoration.lineThrough : null)),
        ),
      ]),
    );
  }
}

/// Renders up to [cap] rows (10px gaps) with a muted "+N more" line when the
/// list is longer — keeps documents and tasks symmetric and bounded.
class _CappedList extends StatelessWidget {
  const _CappedList({required this.total, required this.builder});
  final int total;
  final Widget Function(int index) builder;
  static const cap = 5;
  @override
  Widget build(BuildContext context) {
    final shown = total < cap ? total : cap;
    return Column(
      children: [
        for (var i = 0; i < shown; i++) ...[
          if (i > 0) const SizedBox(height: 10),
          builder(i),
        ],
        if (total > cap)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text('+${total - cap} more',
                  style: TextStyle(
                      color: SovereignColors.ivory.withValues(alpha: 0.5), fontSize: 12)),
            ),
          ),
      ],
    );
  }
}

/// One document row. Tappable: full preview/open lives in the Documents tab, so
/// we point the member there (mirrors the meeting-detail doc rows) rather than
/// hijacking the bottom-nav branch from inside the workspace.
class _DocRow extends StatelessWidget {
  const _DocRow({required this.document});
  final Document document;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      // Workspace is a pushed route under the Home branch, so a cross-branch
      // push to the Documents shell's PDF viewer is unsafe. Open the document
      // through Martin instead.
      onTap: () => context.push(
        '/martin?q=${Uri.encodeQueryComponent('Open the document ${document.name}')}',
      ),
      child: GlassSurface.inner(
        borderRadius: 12,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        child: Row(children: [
          const Icon(Icons.insert_drive_file_outlined, size: 16, color: SovereignColors.gold),
          const SizedBox(width: 10),
          Expanded(
            child: Text(document.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    color: SovereignColors.ivory.withValues(alpha: 0.9), fontSize: 13.5)),
          ),
          Icon(Icons.chevron_right, size: 16, color: SovereignColors.gold.withValues(alpha: 0.8)),
        ]),
      ),
    );
  }
}

class _Switcher extends StatelessWidget {
  const _Switcher({required this.current, required this.twgs});
  final String current;
  final List<Twg> twgs;
  @override
  Widget build(BuildContext context) {
    final currentName =
        twgs.firstWhere((t) => t.id == current, orElse: () => twgs.first).name;
    return PopupMenuButton<String>(
      key: const Key('workspace-switcher'),
      color: SovereignColors.navyRaised,
      onSelected: (id) => context.replace('/home/workspace/$id'),
      itemBuilder: (_) => [
        // List only the member's OTHER TWGs — selecting the current one would be
        // a no-op self-replace.
        for (final t in twgs.where((t) => t.id != current))
          PopupMenuItem<String>(
            value: t.id,
            child: Text(t.name, style: const TextStyle(color: SovereignColors.ivory)),
          ),
      ],
      child: GlassSurface(
        borderRadius: 12,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ringColor: SovereignColors.gold,
        ringOpacity: 0.5,
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(currentName,
              style: const TextStyle(
                  color: SovereignColors.gold, fontSize: 13, fontWeight: FontWeight.w700)),
          const Icon(Icons.arrow_drop_down, color: SovereignColors.gold, size: 18),
        ]),
      ),
    );
  }
}

class _GlassIconButton extends StatelessWidget {
  const _GlassIconButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: GlassSurface(
        borderRadius: 14,
        padding: const EdgeInsets.all(10),
        child: Icon(icon, size: 18, color: SovereignColors.ivory),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Text(text,
        style: TextStyle(color: SovereignColors.ivory.withValues(alpha: 0.5), fontSize: 13));
  }
}

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
            colors: [SovereignColors.navyRaised, SovereignColors.navy, SovereignColors.navyDeep],
            stops: [0, 0.5, 1],
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: GlassCard(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.cloud_off, color: SovereignColors.gold, size: 28),
            const SizedBox(height: 12),
            Text(message,
                textAlign: TextAlign.center,
                style: TextStyle(color: SovereignColors.ivory.withValues(alpha: 0.85))),
            const SizedBox(height: 12),
            TextButton(
              onPressed: onRetry,
              child: const Text('Retry',
                  style: TextStyle(color: SovereignColors.gold, fontWeight: FontWeight.w700)),
            ),
          ]),
        ),
      ),
    );
  }
}
