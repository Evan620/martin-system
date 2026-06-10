// lib/features/profile/presentation/me_screen.dart
//
// "Me" (profile) · native dashboard (v2) — wired to live data.
//
// Layout (top -> bottom), per the Native Dashboard v2 spec:
//   - compact profile header: 40px initials avatar, name (17 w800 Inter — no
//     serif), "role · TWG" meta line.
//   - two `StatTile`s: Tasks due / Reminders (tap selects the segment below).
//   - `SovereignSegmented` Tasks | Reminders switching one `RowGroup`:
//     Tasks = leading-checkbox rows (tap an open item -> existing
//     meController.markDone, SnackBar on failure); Reminders = clock-icon rows
//     with a delete affordance (existing deleteReminder wiring).
//   - **Add reminder** — THE screen's one filled-yellow action — a yellow pill
//     by the Reminders section header opening a `showSovereignSheet` with the
//     existing inputs (message + date/time picker -> addReminder).
//   - Notifications `RowGroup` with toggle rows backed by the device-local
//     notificationPrefsProvider; a subtle Sign out at the bottom.
//
// Loads via meControllerProvider.load() (post-frame), renders by sealed state
// (loading -> tile/row-shaped skeletons / error / data) inside an
// AnimatedSwitcher; pull-to-refresh re-runs load().
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/glass/glass.dart';
import '../../../core/motion/cascade_in.dart';
import '../../../core/motion/motion.dart';
import '../../../core/motion/pressable.dart';
import '../../../core/motion/skeleton.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../../../core/theme/sovereign_spacing.dart';
import '../../../core/theme/sovereign_type.dart';
import '../../../core/ui/list_row.dart';
import '../../../core/ui/section_header.dart';
import '../../../core/ui/segmented.dart';
import '../../../core/ui/sheet.dart';
import '../../../core/ui/stat_tile.dart';
import '../../auth/application/auth_controller.dart';
import '../../auth/data/auth_models.dart';
import '../application/me_controller.dart';
import '../data/me_models.dart';
import '../data/me_repository.dart';
import '../data/notification_prefs.dart';

class MeScreen extends ConsumerStatefulWidget {
  const MeScreen({super.key});

  @override
  ConsumerState<MeScreen> createState() => _MeScreenState();
}

class _MeScreenState extends ConsumerState<MeScreen> {
  /// Local snapshot of device notification preferences, refreshed on toggle.
  late NotificationPrefsData _prefs;

  /// 0 = Tasks, 1 = Reminders — the segmented control's selection.
  int _segment = 0;

  @override
  void initState() {
    super.initState();
    _prefs = ref.read(notificationPrefsProvider).read();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(meControllerProvider.notifier).load();
    });
  }

  Future<void> _markDone(String id) async {
    try {
      await ref.read(meControllerProvider.notifier).markDone(id);
    } on MeException catch (e) {
      _snack(e.message);
    }
  }

  Future<void> _deleteReminder(String id) async {
    try {
      await ref.read(meControllerProvider.notifier).deleteReminder(id);
    } on MeException catch (e) {
      _snack(e.message);
    }
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openAddReminder() async {
    final result = await showSovereignSheet<_NewReminder>(
      context,
      child: const _AddReminderSheetBody(),
    );
    if (result == null) return;
    try {
      await ref
          .read(meControllerProvider.notifier)
          .addReminder(result.message, result.at);
    } on MeException catch (e) {
      _snack(e.message);
    }
  }

  void _setMeetingUpdates(bool v) {
    ref.read(notificationPrefsProvider).setMeetingUpdates(v);
    setState(() => _prefs = _prefs.copyWith(meetingUpdates: v));
  }

  void _setNewDocuments(bool v) {
    ref.read(notificationPrefsProvider).setNewDocuments(v);
    setState(() => _prefs = _prefs.copyWith(newDocuments: v));
  }

  void _setAnnouncements(bool v) {
    ref.read(notificationPrefsProvider).setAnnouncements(v);
    setState(() => _prefs = _prefs.copyWith(announcements: v));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(meControllerProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          color: SovereignColors.gold,
          backgroundColor: SovereignColors.navyRaised,
          onRefresh: () => ref.read(meControllerProvider.notifier).load(),
          child: AnimatedSwitcher(
            duration: Motion.base,
            child: switch (state) {
              MeLoading() => const _LoadingView(key: ValueKey('loading')),
              MeError(:final message) => _ErrorView(
                  key: const ValueKey('error'),
                  message: message,
                  onRetry: () =>
                      ref.read(meControllerProvider.notifier).load(),
                ),
              MeData(:final items, :final reminders) => _DataView(
                  key: const ValueKey('data'),
                  user: _user(),
                  items: items,
                  reminders: reminders,
                  segment: _segment,
                  onSegment: (i) => setState(() => _segment = i),
                  onToggleTask: _markDone,
                  onDeleteReminder: _deleteReminder,
                  onAddReminder: _openAddReminder,
                  prefs: _prefs,
                  onMeetingUpdates: _setMeetingUpdates,
                  onNewDocuments: _setNewDocuments,
                  onAnnouncements: _setAnnouncements,
                  onSignOut: () =>
                      ref.read(authControllerProvider.notifier).signOut(),
                ),
            },
          ),
        ),
      ),
    );
  }

  AppUser? _user() {
    final auth = ref.watch(authControllerProvider);
    return auth is AuthAuthenticated ? auth.user : null;
  }
}

/// Initials from a full name: first letters of the first and last words, or a
/// single letter when there's only one word. Falls back to a dash.
String _initialsOf(String fullName) {
  final parts =
      fullName.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
  if (parts.isEmpty) return '–';
  if (parts.length == 1) return parts.first.characters.first.toUpperCase();
  return (parts.first.characters.first + parts.last.characters.first)
      .toUpperCase();
}

/// Human-readable role label for the profile subtitle.
String _roleLabel(UserRole role) => switch (role) {
      UserRole.admin => 'Admin',
      UserRole.twgFacilitator => 'Facilitator',
      UserRole.twgMember => 'Member',
      UserRole.secretariatLead => 'Secretariat Lead',
      UserRole.unknown => 'Member',
    };

// ---------------------------------------------------------------------------
// Loaded state — profile header, stat tiles, segmented Tasks/Reminders,
// notifications, sign out.
// ---------------------------------------------------------------------------
class _DataView extends StatelessWidget {
  const _DataView({
    super.key,
    required this.user,
    required this.items,
    required this.reminders,
    required this.segment,
    required this.onSegment,
    required this.onToggleTask,
    required this.onDeleteReminder,
    required this.onAddReminder,
    required this.prefs,
    required this.onMeetingUpdates,
    required this.onNewDocuments,
    required this.onAnnouncements,
    required this.onSignOut,
  });

  final AppUser? user;
  final List<ActionItem> items;
  final List<Reminder> reminders;
  final int segment;
  final ValueChanged<int> onSegment;
  final ValueChanged<String> onToggleTask;
  final ValueChanged<String> onDeleteReminder;
  final VoidCallback onAddReminder;
  final NotificationPrefsData prefs;
  final ValueChanged<bool> onMeetingUpdates;
  final ValueChanged<bool> onNewDocuments;
  final ValueChanged<bool> onAnnouncements;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final open = items.where((i) => !i.isDone).length;
    final overdue =
        items.where((i) => i.status == ActionStatus.overdue).length;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding:
          const EdgeInsets.fromLTRB(Insets.gutter, Insets.lg, Insets.gutter, 0)
              .add(navClearance(context)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CascadeIn(index: 0, child: _ProfileHeader(user: user)),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 1,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: StatTile(
                    label: 'Tasks due',
                    value: '$open',
                    sub: overdue > 0
                        ? '$overdue overdue'
                        : 'action items',
                    onTap: () => onSegment(0),
                  ),
                ),
                const SizedBox(width: Insets.sm),
                Expanded(
                  child: StatTile(
                    label: 'Reminders',
                    value: '${reminders.length}',
                    sub: 'scheduled',
                    onTap: () => onSegment(1),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 2,
            child: SovereignSegmented(
              options: const ['Tasks', 'Reminders'],
              selected: segment,
              onChanged: onSegment,
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(
            index: 3,
            child: segment == 0 ? _tasksSection() : _remindersSection(),
          ),
          const SizedBox(height: Insets.section),
          CascadeIn(
            index: 4,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SectionHeader(title: 'Notifications'),
                RowGroup(children: [
                  _ToggleRow(
                    icon: Icons.event_available_rounded,
                    label: 'Meeting updates',
                    value: prefs.meetingUpdates,
                    onChanged: onMeetingUpdates,
                  ),
                  _ToggleRow(
                    icon: Icons.description_rounded,
                    label: 'New shared documents',
                    value: prefs.newDocuments,
                    onChanged: onNewDocuments,
                  ),
                  _ToggleRow(
                    icon: Icons.campaign_rounded,
                    label: 'Summit announcements',
                    value: prefs.announcements,
                    onChanged: onAnnouncements,
                  ),
                ]),
              ],
            ),
          ),
          const SizedBox(height: Insets.lg),
          CascadeIn(index: 5, child: _SignOutButton(onTap: onSignOut)),
          const SizedBox(height: Insets.sm),
        ],
      ),
    );
  }

  /// Tasks segment: leading-checkbox rows wired to the existing markDone.
  Widget _tasksSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionHeader(title: 'Tasks'),
        RowGroup(children: [
          if (items.isEmpty)
            const ListRow(
              icon: Icons.check_circle_outline_rounded,
              title: 'No action items',
              meta: 'Tasks assigned to you appear here.',
            )
          else
            for (final item in items) _TaskRow(item: item, onToggle: onToggleTask),
        ]),
      ],
    );
  }

  /// Reminders segment: clock rows with delete, headed by THE yellow
  /// Add-reminder pill.
  Widget _remindersSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Expanded(child: SectionHeader(title: 'Reminders')),
            _AddReminderPill(onTap: onAddReminder),
          ],
        ),
        const SizedBox(height: Insets.sm),
        RowGroup(children: [
          if (reminders.isEmpty)
            const ListRow(
              icon: Icons.notifications_none_rounded,
              title: 'No reminders yet',
              meta: 'Tap Add reminder to create one.',
            )
          else
            for (final r in reminders)
              ListRow(
                icon: Icons.schedule_rounded,
                title: r.message,
                meta: _reminderFmt.format(r.remindAt),
                trailing: IconButton(
                  onPressed: () => onDeleteReminder(r.id),
                  tooltip: 'Delete reminder',
                  iconSize: 18,
                  icon: Icon(
                    Icons.close_rounded,
                    color: SovereignColors.ivory
                        .withValues(alpha: SovereignColors.alphaMid),
                  ),
                ),
              ),
        ]),
      ],
    );
  }
}

final _reminderFmt = DateFormat('EEE d MMM · HH:mm');
final _dueFmt = DateFormat('EEE d MMM');

/// One task row: leading checkbox icon, description, due/done meta. Tapping an
/// open row marks it done (existing wiring); done rows are inert.
class _TaskRow extends StatelessWidget {
  const _TaskRow({required this.item, required this.onToggle});

  final ActionItem item;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    final done = item.isDone;
    return ListRow(
      icon: done
          ? Icons.check_box_rounded
          : Icons.check_box_outline_blank_rounded,
      title: item.description,
      meta: done
          ? 'Done'
          : (item.dueDate != null
              ? 'Due ${_dueFmt.format(item.dueDate!)}'
              : 'No due date'),
      trailing: const SizedBox.shrink(),
      onTap: done ? null : () => onToggle(item.id),
    );
  }
}

// ---------------------------------------------------------------------------
// Profile header — compact, sans-serif: 40px initials avatar, name, role·TWG.
// ---------------------------------------------------------------------------
class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.user});

  final AppUser? user;

  @override
  Widget build(BuildContext context) {
    final name = user?.fullName ?? 'Member';
    final twg = user?.twgs.headerLabel;
    final role = _roleLabel(user?.role ?? UserRole.twgMember);
    final subtitle = twg != null ? '$role · $twg' : role;

    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [SovereignColors.gold, SovereignColors.sunDeep],
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            _initialsOf(name),
            style: const TextStyle(
              fontFamily: 'Inter',
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: SovereignColors.navy,
            ),
          ),
        ),
        const SizedBox(width: Insets.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                  color: SovereignColors.ivory,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
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
    );
  }
}

// ---------------------------------------------------------------------------
// Add reminder — THE screen's one filled-yellow action.
// ---------------------------------------------------------------------------
class _AddReminderPill extends StatelessWidget {
  const _AddReminderPill({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Add reminder',
      child: PressableScale(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
              horizontal: Insets.md, vertical: Insets.xs + 2),
          decoration: BoxDecoration(
            color: SovereignColors.gold,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.add_rounded, size: 14, color: SovereignColors.navy),
              SizedBox(width: Insets.xs),
              Text(
                'Add reminder',
                style: TextStyle(
                  fontFamily: 'Inter',
                  color: SovereignColors.navy,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The result returned by [_AddReminderSheetBody] when the member saves.
class _NewReminder {
  const _NewReminder(this.message, this.at);
  final String message;
  final DateTime at;
}

/// The add-reminder sheet body (lives inside `showSovereignSheet`): a message
/// TextField + a date/time picker row, returning a [_NewReminder] on Save.
class _AddReminderSheetBody extends StatefulWidget {
  const _AddReminderSheetBody();

  @override
  State<_AddReminderSheetBody> createState() => _AddReminderSheetBodyState();
}

class _AddReminderSheetBodyState extends State<_AddReminderSheetBody> {
  final _controller = TextEditingController();
  DateTime? _picked;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _pickDateTime() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _picked ?? now,
      firstDate: now.subtract(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 365 * 2)),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_picked ?? now),
    );
    if (time == null || !mounted) return;
    setState(() {
      _picked =
          DateTime(date.year, date.month, date.day, time.hour, time.minute);
    });
  }

  void _save() {
    final msg = _controller.text.trim();
    if (msg.isEmpty || _picked == null) return;
    Navigator.of(context).pop(_NewReminder(msg, _picked!));
  }

  @override
  Widget build(BuildContext context) {
    final canSave = _controller.text.trim().isNotEmpty && _picked != null;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionHeader(title: 'New reminder'),
        TextField(
          controller: _controller,
          autofocus: true,
          onChanged: (_) => setState(() {}),
          style: SovereignType.body,
          cursorColor: SovereignColors.gold,
          decoration: InputDecoration(
            hintText: 'What should we remind you about?',
            hintStyle: SovereignType.body.copyWith(
              color: SovereignColors.ivory
                  .withValues(alpha: SovereignColors.alphaMid),
            ),
            enabledBorder: UnderlineInputBorder(
              borderSide: BorderSide(
                color: SovereignColors.ivory.withValues(alpha: 0.25),
              ),
            ),
            focusedBorder: const UnderlineInputBorder(
              borderSide: BorderSide(color: SovereignColors.gold),
            ),
          ),
        ),
        const SizedBox(height: Insets.lg),
        RowGroup(children: [
          ListRow(
            icon: Icons.schedule_rounded,
            title: _picked == null
                ? 'Pick a date & time'
                : _reminderFmt.format(_picked!),
            onTap: _pickDateTime,
          ),
        ]),
        const SizedBox(height: Insets.lg),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              style: TextButton.styleFrom(
                foregroundColor: SovereignColors.ivory
                    .withValues(alpha: SovereignColors.alphaMid),
              ),
              child: const Text('Cancel'),
            ),
            const SizedBox(width: Insets.sm),
            FilledButton(
              onPressed: canSave ? _save : null,
              style: FilledButton.styleFrom(
                backgroundColor: SovereignColors.gold,
                foregroundColor: SovereignColors.navy,
                disabledBackgroundColor:
                    SovereignColors.gold.withValues(alpha: 0.3),
              ),
              child: const Text(
                'Save',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Notifications — kit rows with a working toggle (whole row is the target).
// ---------------------------------------------------------------------------
class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return ListRow(
      icon: icon,
      title: label,
      trailing: _TogglePill(value: value),
      onTap: () => onChanged(!value),
    );
  }
}

/// A small Sovereign-styled on/off pill (gold = on; a tiny selected-state
/// fill, allowed beside the screen's one yellow action).
class _TogglePill extends StatelessWidget {
  const _TogglePill({required this.value});

  final bool value;

  @override
  Widget build(BuildContext context) {
    final track = value
        ? SovereignColors.gold.withValues(alpha: 0.85)
        : SovereignColors.ivory.withValues(alpha: 0.18);
    final knobColor = value ? SovereignColors.navy : SovereignColors.ivory;

    return Container(
      width: 42,
      height: 24,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: track,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: value
              ? SovereignColors.gold
              : SovereignColors.ivory.withValues(alpha: 0.25),
          width: 1,
        ),
      ),
      child: AnimatedAlign(
        duration: Motion.fast,
        curve: Motion.curve,
        alignment: value ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: knobColor,
          ),
        ),
      ),
    );
  }
}

/// A subtle text-only "Sign out" action at the bottom of the screen.
class _SignOutButton extends StatelessWidget {
  const _SignOutButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: TextButton(
        onPressed: onTap,
        style: TextButton.styleFrom(
          foregroundColor:
              SovereignColors.ivory.withValues(alpha: SovereignColors.alphaMid),
          padding: const EdgeInsets.symmetric(
              horizontal: Insets.lg, vertical: Insets.sm),
        ),
        child: Text(
          'Sign out',
          style: SovereignType.secondary.copyWith(letterSpacing: 0.4),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Loading — profile/tile/row-shaped skeletons (no spinner).
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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(children: [
            SkeletonBlock(width: 40, height: 40, radius: 20),
            SizedBox(width: Insets.md),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SkeletonBlock(width: 150, height: 14),
              SizedBox(height: Insets.xs),
              SkeletonBlock(width: 100, height: 10),
            ]),
          ]),
          SizedBox(height: Insets.lg),
          Row(children: [
            Expanded(child: SkeletonTile()),
            SizedBox(width: Insets.sm),
            Expanded(child: SkeletonTile()),
          ]),
          SizedBox(height: Insets.lg),
          SkeletonBlock(width: double.infinity, height: 44, radius: 12),
          SizedBox(height: Insets.lg),
          RowGroup(children: [
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
              const Icon(Icons.cloud_off,
                  color: SovereignColors.gold, size: 28),
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
