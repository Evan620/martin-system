// lib/features/profile/application/me_controller.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/application/auth_controller.dart';
import '../data/me_models.dart';
import '../data/me_repository.dart';

sealed class MeState { const MeState(); }
class MeLoading extends MeState { const MeLoading(); }
class MeError extends MeState { const MeError(this.message); final String message; }
class MeData extends MeState {
  const MeData({required this.items, required this.reminders});
  final List<ActionItem> items;
  final List<Reminder> reminders;
  MeData copyWith({List<ActionItem>? items, List<Reminder>? reminders}) =>
      MeData(items: items ?? this.items, reminders: reminders ?? this.reminders);
}

final meRepositoryProvider = Provider<MeRepository>((ref) => MeRepository(dio: ref.watch(dioProvider)));

class MeController extends Notifier<MeState> {
  @override
  MeState build() => const MeLoading();
  MeRepository get _repo => ref.read(meRepositoryProvider);

  Future<void> load() async {
    state = const MeLoading();
    try {
      final items = await _repo.listActionItems();
      // Reminders are best-effort: a failure (e.g. the /reminders route not yet
      // deployed to prod) must not blank the whole screen — show tasks with no
      // reminders rather than a full "could not load" error.
      List<Reminder> reminders = const [];
      try {
        reminders = await _repo.listReminders();
      } on MeException {
        reminders = const [];
      }
      state = MeData(items: items, reminders: reminders);
    } on MeException catch (e) {
      state = MeError(e.message);
    }
  }

  Future<void> markDone(String id) async {
    final s = state;
    if (s is! MeData) return;
    final prev = s.items;
    state = s.copyWith(items: [
      for (final a in prev)
        if (a.id == id) ActionItem(id: a.id, description: a.description, status: ActionStatus.completed, dueDate: a.dueDate) else a,
    ]);
    try {
      await _repo.markDone(id);
    } on MeException {
      state = (state as MeData).copyWith(items: prev);
      rethrow;
    }
  }

  Future<void> addReminder(String message, DateTime atUtc) async {
    final s = state; if (s is! MeData) return;
    final r = await _repo.addReminder(message, atUtc);
    state = s.copyWith(reminders: [...s.reminders, r]..sort((a, b) => a.remindAt.compareTo(b.remindAt)));
  }

  Future<void> deleteReminder(String id) async {
    final s = state; if (s is! MeData) return;
    await _repo.deleteReminder(id);
    state = s.copyWith(reminders: s.reminders.where((r) => r.id != id).toList());
  }
}

final meControllerProvider = NotifierProvider<MeController, MeState>(MeController.new);
