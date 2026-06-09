// lib/features/workspace/application/workspace_controller.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../meetings/application/meetings_controller.dart'; // meetingsRepositoryProvider
import '../../meetings/data/meetings_models.dart';
import '../../meetings/data/meetings_repository.dart';
import '../../profile/application/me_controller.dart'; // meRepositoryProvider
import '../../profile/data/me_models.dart';
import '../../profile/data/me_repository.dart';
import '../data/workspace_models.dart';
import '../data/workspace_repository.dart';

sealed class WorkspaceState {
  const WorkspaceState();
}

class WorkspaceLoading extends WorkspaceState {
  const WorkspaceLoading();
}

class WorkspaceError extends WorkspaceState {
  const WorkspaceError(this.message);
  final String message;
}

class WorkspaceData extends WorkspaceState {
  const WorkspaceData({
    required this.detail,
    required this.meetings,
    required this.tasks,
  });
  final TwgDetail detail;
  final List<Meeting> meetings; // upcoming, soonest-first
  final List<ActionItem> tasks; // the member's tasks in this TWG
}

class WorkspaceController extends Notifier<WorkspaceState> {
  WorkspaceController(this._twgId);
  final String _twgId;

  @override
  WorkspaceState build() {
    return const WorkspaceLoading();
  }

  Future<void> load() async {
    state = const WorkspaceLoading();
    final WorkspaceRepository ws = ref.read(workspaceRepositoryProvider);
    final MeetingsRepository meetingsRepo = ref.read(meetingsRepositoryProvider);
    final MeRepository meRepo = ref.read(meRepositoryProvider);

    // TWG detail is required — its failure is the only fatal one.
    final TwgDetail detail;
    try {
      detail = await ws.twgDetail(_twgId);
    } on WorkspaceException catch (e) {
      state = WorkspaceError(e.message);
      return;
    }

    // Meetings + tasks are best-effort: a failure shows an empty section.
    List<Meeting> meetings = const [];
    try {
      final all = await meetingsRepo.listMeetings(twgId: _twgId);
      final upcoming = all.where((m) => !m.isPast).toList()
        ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
      meetings = upcoming;
    } on MeetingException {
      meetings = const [];
    }

    List<ActionItem> tasks = const [];
    try {
      tasks = await meRepo.listActionItems(twgId: _twgId);
    } on MeException {
      tasks = const [];
    }

    state = WorkspaceData(detail: detail, meetings: meetings, tasks: tasks);
  }
}

final workspaceControllerProvider =
    NotifierProvider.family<WorkspaceController, WorkspaceState, String>(
  WorkspaceController.new,
);
