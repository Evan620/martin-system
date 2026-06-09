// lib/features/profile/presentation/me_screen.dart
//
// "Me" (profile) screen — Sovereign glass design, wired to live data.
//
// Matches the approved mockup (app-shape.html · screen ④ Me):
//   - a glass profile header card with a gold circular avatar (initials),
//     the member's name and "<first TWG> · <role>";
//   - a "MY ACTION ITEMS" glass card with inner-glass checkbox rows — tapping
//     an open item calls meController.markDone(id) (SnackBar on failure);
//   - a "REMINDERS" glass card listing the member's reminders (message + local
//     date/time) with a delete affordance, plus an "+ Add a reminder" action
//     that opens a glass sheet (TextField + date/time picker → addReminder);
//   - a "NOTIFICATIONS" settings glass card with toggle rows backed by the
//     device-local notificationPrefsProvider;
//   - a subtle "Sign out" text button at the bottom (authController.signOut).
//
// Uses glass-inside-glass throughout: each outer GlassCard holds lighter
// GlassSurface.inner rows/chips so the stack reads as layered depth.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';
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
    final result = await showModalBottomSheet<_NewReminder>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _AddReminderSheet(),
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
      backgroundColor: SovereignColors.navy,
      body: DecoratedBox(
        // A soft navy gradient so the glass surfaces have something to blur over.
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              SovereignColors.navyRaised,
              SovereignColors.navy,
              SovereignColors.navyDeep,
            ],
            stops: [0.0, 0.45, 1.0],
          ),
        ),
        child: SafeArea(
          bottom: false,
          child: switch (state) {
            MeLoading() => const Center(
                child: CircularProgressIndicator(color: SovereignColors.gold),
              ),
            MeError(:final message) => _ErrorView(
                message: message,
                onRetry: () =>
                    ref.read(meControllerProvider.notifier).load(),
              ),
            MeData(:final items, :final reminders) => SingleChildScrollView(
                // ~104px bottom padding so the floating glass nav never covers content.
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _ProfileHeaderCard(user: _user()),
                    const SizedBox(height: 18),
                    _ActionItemsCard(items: items, onToggle: _markDone),
                    const SizedBox(height: 18),
                    _RemindersCard(
                      reminders: reminders,
                      onDelete: _deleteReminder,
                      onAdd: _openAddReminder,
                    ),
                    const SizedBox(height: 18),
                    _NotificationsCard(
                      prefs: _prefs,
                      onMeetingUpdates: _setMeetingUpdates,
                      onNewDocuments: _setNewDocuments,
                      onAnnouncements: _setAnnouncements,
                    ),
                    const SizedBox(height: 26),
                    _SignOutButton(
                      onTap: () =>
                          ref.read(authControllerProvider.notifier).signOut(),
                    ),
                    const SizedBox(height: 8),
                  ],
                ),
              ),
          },
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
// Profile header — glass card with a gold avatar + name + role.
// ---------------------------------------------------------------------------
class _ProfileHeaderCard extends StatelessWidget {
  const _ProfileHeaderCard({required this.user});

  final AppUser? user;

  @override
  Widget build(BuildContext context) {
    final name = user?.fullName ?? 'Member';
    final twg = (user?.twgs.isNotEmpty ?? false) ? user!.twgs.first.name : null;
    final role = _roleLabel(user?.role ?? UserRole.twgMember);
    final subtitle = twg != null ? '$twg · $role' : role;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          _GoldAvatar(initials: _initialsOf(name)),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  name,
                  style: const TextStyle(
                    fontFamily: 'Georgia',
                    color: SovereignColors.ivory,
                    fontSize: 22,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: SovereignColors.ivory,
                    fontSize: 13,
                    height: 1.2,
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

class _GoldAvatar extends StatelessWidget {
  const _GoldAvatar({required this.initials});

  final String initials;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFE6C766), SovereignColors.gold],
        ),
        boxShadow: [
          BoxShadow(
            color: SovereignColors.gold.withValues(alpha: 0.40),
            blurRadius: 16,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Center(
        child: Text(
          initials,
          style: const TextStyle(
            color: SovereignColors.navy,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// MY ACTION ITEMS — outer glass card, inner-glass checkbox rows.
// ---------------------------------------------------------------------------
class _ActionItemsCard extends StatelessWidget {
  const _ActionItemsCard({required this.items, required this.onToggle});

  final List<ActionItem> items;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionLabel('MY ACTION ITEMS'),
          const SizedBox(height: 12),
          if (items.isEmpty)
            const _EmptyHint('No action items assigned to you.')
          else
            for (var i = 0; i < items.length; i++) ...[
              if (i > 0) const SizedBox(height: 10),
              _ActionItemRow(
                item: items[i],
                onTap: items[i].isDone ? null : () => onToggle(items[i].id),
              ),
            ],
        ],
      ),
    );
  }
}

class _ActionItemRow extends StatelessWidget {
  const _ActionItemRow({required this.item, required this.onTap});

  final ActionItem item;
  final VoidCallback? onTap;

  static final _fmt = DateFormat('EEE d MMM');

  @override
  Widget build(BuildContext context) {
    final done = item.isDone;
    final trailing = done
        ? 'done'
        : (item.dueDate != null ? 'Due ${_fmt.format(item.dueDate!)}' : '');

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: GlassSurface.inner(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            Icon(
              done
                  ? Icons.check_box_rounded
                  : Icons.check_box_outline_blank_rounded,
              size: 20,
              color: done
                  ? SovereignColors.gold
                  : SovereignColors.ivory.withValues(alpha: 0.65),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                item.description,
                style: TextStyle(
                  color: done
                      ? SovereignColors.ivory.withValues(alpha: 0.55)
                      : SovereignColors.ivory,
                  fontSize: 14,
                  decoration: done ? TextDecoration.lineThrough : null,
                  decorationColor:
                      SovereignColors.ivory.withValues(alpha: 0.55),
                ),
              ),
            ),
            if (trailing.isNotEmpty) ...[
              const SizedBox(width: 10),
              Text(
                trailing,
                style: TextStyle(
                  color: done
                      ? SovereignColors.ivory.withValues(alpha: 0.5)
                      : SovereignColors.gold,
                  fontSize: 11.5,
                  fontWeight: done ? FontWeight.w400 : FontWeight.w600,
                  letterSpacing: 0.3,
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
// REMINDERS — outer glass card listing the member's reminders + an add action.
// ---------------------------------------------------------------------------
class _RemindersCard extends StatelessWidget {
  const _RemindersCard({
    required this.reminders,
    required this.onDelete,
    required this.onAdd,
  });

  final List<Reminder> reminders;
  final ValueChanged<String> onDelete;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionLabel('REMINDERS'),
          const SizedBox(height: 12),
          if (reminders.isEmpty)
            const _EmptyHint('No reminders yet.')
          else
            for (var i = 0; i < reminders.length; i++) ...[
              if (i > 0) const SizedBox(height: 10),
              _ReminderRow(
                reminder: reminders[i],
                onDelete: () => onDelete(reminders[i].id),
              ),
            ],
          const SizedBox(height: 12),
          _AddReminderButton(onTap: onAdd),
        ],
      ),
    );
  }
}

class _ReminderRow extends StatelessWidget {
  const _ReminderRow({required this.reminder, required this.onDelete});

  final Reminder reminder;
  final VoidCallback onDelete;

  static final _fmt = DateFormat('EEE d MMM · HH:mm');

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Icon(
            Icons.notifications_active_rounded,
            size: 19,
            color: SovereignColors.gold.withValues(alpha: 0.85),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  reminder.message,
                  style: const TextStyle(
                    color: SovereignColors.ivory,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _fmt.format(reminder.remindAt),
                  style: const TextStyle(
                    color: SovereignColors.gold,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.3,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: onDelete,
            visualDensity: VisualDensity.compact,
            iconSize: 18,
            tooltip: 'Delete reminder',
            icon: Icon(
              Icons.close_rounded,
              color: SovereignColors.ivory.withValues(alpha: 0.55),
            ),
          ),
        ],
      ),
    );
  }
}

/// A dashed-feel inner-glass "+ Add a reminder" row.
class _AddReminderButton extends StatelessWidget {
  const _AddReminderButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: GlassSurface.inner(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.add_rounded, size: 18, color: SovereignColors.gold),
            SizedBox(width: 8),
            Text(
              'Add a reminder',
              style: TextStyle(
                color: SovereignColors.gold,
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.3,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// The result returned by [_AddReminderSheet] when the member saves.
class _NewReminder {
  const _NewReminder(this.message, this.at);
  final String message;
  final DateTime at;
}

/// A glass bottom sheet: a message TextField + a date/time picker, returning a
/// [_NewReminder] when the member taps Save.
class _AddReminderSheet extends StatefulWidget {
  const _AddReminderSheet();

  @override
  State<_AddReminderSheet> createState() => _AddReminderSheetState();
}

class _AddReminderSheetState extends State<_AddReminderSheet> {
  final _controller = TextEditingController();
  DateTime? _picked;

  static final _fmt = DateFormat('EEE d MMM · HH:mm');

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
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 12,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: GlassCard(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _SectionLabel('NEW REMINDER'),
            const SizedBox(height: 14),
            TextField(
              controller: _controller,
              autofocus: true,
              onChanged: (_) => setState(() {}),
              style: const TextStyle(
                color: SovereignColors.ivory,
                fontSize: 15,
              ),
              cursorColor: SovereignColors.gold,
              decoration: InputDecoration(
                hintText: 'What should we remind you about?',
                hintStyle: TextStyle(
                  color: SovereignColors.ivory.withValues(alpha: 0.45),
                  fontSize: 14,
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
            const SizedBox(height: 16),
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: _pickDateTime,
              child: GlassSurface.inner(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Row(
                  children: [
                    const Icon(Icons.schedule_rounded,
                        size: 18, color: SovereignColors.gold),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _picked == null
                            ? 'Pick a date & time'
                            : _fmt.format(_picked!),
                        style: TextStyle(
                          color: _picked == null
                              ? SovereignColors.ivory.withValues(alpha: 0.7)
                              : SovereignColors.ivory,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 18),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: TextButton.styleFrom(
                    foregroundColor:
                        SovereignColors.ivory.withValues(alpha: 0.7),
                  ),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
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
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// NOTIFICATIONS — settings glass card backed by device-local prefs.
// ---------------------------------------------------------------------------
class _NotificationsCard extends StatelessWidget {
  const _NotificationsCard({
    required this.prefs,
    required this.onMeetingUpdates,
    required this.onNewDocuments,
    required this.onAnnouncements,
  });

  final NotificationPrefsData prefs;
  final ValueChanged<bool> onMeetingUpdates;
  final ValueChanged<bool> onNewDocuments;
  final ValueChanged<bool> onAnnouncements;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionLabel('NOTIFICATIONS'),
          const SizedBox(height: 12),
          _ToggleRow(
            icon: Icons.event_available_rounded,
            label: 'Meeting updates',
            value: prefs.meetingUpdates,
            onChanged: onMeetingUpdates,
          ),
          const SizedBox(height: 10),
          _ToggleRow(
            icon: Icons.description_rounded,
            label: 'New shared documents',
            value: prefs.newDocuments,
            onChanged: onNewDocuments,
          ),
          const SizedBox(height: 10),
          _ToggleRow(
            icon: Icons.campaign_rounded,
            label: 'Summit announcements',
            value: prefs.announcements,
            onChanged: onAnnouncements,
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared bits.
// ---------------------------------------------------------------------------

/// Uppercase, gold, letter-spaced section label (matches the mockup `.lab2`).
class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: SovereignColors.gold,
        fontSize: 11,
        fontWeight: FontWeight.w600,
        letterSpacing: 1.8,
      ),
    );
  }
}

/// A muted inner hint shown when a section has no content.
class _EmptyHint extends StatelessWidget {
  const _EmptyHint(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Text(
        text,
        style: TextStyle(
          color: SovereignColors.ivory.withValues(alpha: 0.6),
          fontSize: 13,
        ),
      ),
    );
  }
}

/// An inner-glass row with a leading icon, label and a working toggle.
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
    return GlassSurface.inner(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Icon(
            icon,
            size: 19,
            color: SovereignColors.gold.withValues(alpha: 0.85),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: SovereignColors.ivory,
                fontSize: 14,
              ),
            ),
          ),
          const SizedBox(width: 10),
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => onChanged(!value),
            child: _GlassToggle(value: value),
          ),
        ],
      ),
    );
  }
}

/// A small Sovereign-styled on/off pill.
class _GlassToggle extends StatelessWidget {
  const _GlassToggle({required this.value});

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
      child: Align(
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
          foregroundColor: SovereignColors.ivory.withValues(alpha: 0.6),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        ),
        child: const Text(
          'Sign out',
          style: TextStyle(
            fontSize: 13.5,
            letterSpacing: 0.4,
          ),
        ),
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
              const Icon(Icons.cloud_off,
                  color: SovereignColors.gold, size: 28),
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
