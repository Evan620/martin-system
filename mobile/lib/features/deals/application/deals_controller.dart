// lib/features/deals/application/deals_controller.dart
//
// Deal Room state (mirrors meetings_controller.dart). An empty TWG portfolio
// is still DealsData([]) so the screen can render its own empty treatment.
// toggleFollow follows the meetings RSVP pattern: optimistic flip, persist,
// reconcile with the server's authoritative interest state, roll back +
// rethrow on failure so the screen can toast.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/deals_models.dart';
import '../data/deals_repository.dart';

sealed class DealsState {
  const DealsState();
}

class DealsLoading extends DealsState {
  const DealsLoading();
}

class DealsError extends DealsState {
  const DealsError(this.message);
  final String message;
}

class DealsData extends DealsState {
  const DealsData(this.projects);
  final List<DealProject> projects;
}

class DealsController extends Notifier<DealsState> {
  @override
  DealsState build() => const DealsLoading();

  DealsRepository get _repo => ref.read(dealsRepositoryProvider);

  Future<void> load() async {
    state = const DealsLoading();
    try {
      state = DealsData(await _repo.listMyProjects());
    } on DealsException catch (e) {
      state = DealsError(e.message);
    }
  }

  /// Optimistically toggle Follow on [projectId], then persist; reconcile
  /// with the server's returned count on success, roll back on failure.
  Future<void> toggleFollow(String projectId) async {
    final current = state;
    if (current is! DealsData) return;
    final previous = current.projects;

    DealProject? target;
    for (final p in previous) {
      if (p.id == projectId) {
        target = p;
        break;
      }
    }
    if (target == null) return;

    final following = !target.isFollowing;
    final optimisticCount = target.interestCount + (following ? 1 : -1);
    state = DealsData(_withInterest(
      previous,
      projectId,
      isFollowing: following,
      interestCount: optimisticCount < 0 ? 0 : optimisticCount,
    ));

    try {
      final confirmed =
          following ? await _repo.follow(projectId) : await _repo.unfollow(projectId);
      final cur = state;
      if (cur is DealsData) {
        state = DealsData(_withInterest(
          cur.projects,
          projectId,
          isFollowing: confirmed.isFollowing,
          interestCount: confirmed.interestCount,
        ));
      }
    } on DealsException {
      state = DealsData(previous); // rollback
      rethrow;
    }
  }

  List<DealProject> _withInterest(
    List<DealProject> list,
    String projectId, {
    required bool isFollowing,
    required int interestCount,
  }) {
    return [
      for (final p in list)
        if (p.id == projectId)
          p.copyWith(isFollowing: isFollowing, interestCount: interestCount)
        else
          p,
    ];
  }
}

final dealsControllerProvider =
    NotifierProvider<DealsController, DealsState>(DealsController.new);
