// lib/features/home/application/home_controller.dart
//
// Home controller — loads the member's Martin briefing and exposes it as a
// sealed `HomeState` (loading | data | error). Mirrors the meetings controller
// (Notifier + repository provider over dioProvider).
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/application/auth_controller.dart';
import '../data/briefing_models.dart';
import '../data/home_repository.dart';

sealed class HomeState {
  const HomeState();
}

class HomeLoading extends HomeState {
  const HomeLoading();
}

class HomeError extends HomeState {
  const HomeError(this.message);
  final String message;
}

class HomeData extends HomeState {
  const HomeData(this.briefing);
  final Briefing briefing;
}

final homeRepositoryProvider = Provider<HomeRepository>(
  (ref) => HomeRepository(dio: ref.watch(dioProvider)),
);

class HomeController extends Notifier<HomeState> {
  @override
  HomeState build() => const HomeLoading();

  HomeRepository get _repo => ref.read(homeRepositoryProvider);

  Future<void> load() async {
    state = const HomeLoading();
    try {
      state = HomeData(await _repo.getBriefing());
    } on HomeException catch (e) {
      state = HomeError(e.message);
    }
  }
}

final homeControllerProvider =
    NotifierProvider<HomeController, HomeState>(HomeController.new);
