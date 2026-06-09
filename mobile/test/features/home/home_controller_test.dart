// test/features/home/home_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';

class _MockRepo extends Mock implements HomeRepository {}

Briefing _briefing() => Briefing.fromJson({
      'greeting': 'Good morning',
      'upcoming_meetings': [
        {'title': 'Energy Sync', 'twg_name': 'Energy', 'minutes_until': 30},
      ],
      'overdue_items': const [],
    });

void main() {
  test('initial state is loading', () {
    final repo = _MockRepo();
    final container = ProviderContainer(overrides: [
      homeRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);
    expect(container.read(homeControllerProvider), isA<HomeLoading>());
  });

  test('load -> data on success', () async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());
    final container = ProviderContainer(overrides: [
      homeRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);

    await container.read(homeControllerProvider.notifier).load();
    final state = container.read(homeControllerProvider);
    expect(state, isA<HomeData>());
    expect((state as HomeData).briefing.nextMeeting?.title, 'Energy Sync');
  });

  test('load -> error on HomeException', () async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenThrow(HomeException('nope'));
    final container = ProviderContainer(overrides: [
      homeRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);

    await container.read(homeControllerProvider.notifier).load();
    final state = container.read(homeControllerProvider);
    expect(state, isA<HomeError>());
    expect((state as HomeError).message, 'nope');
  });
}
