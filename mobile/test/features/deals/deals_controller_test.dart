// test/features/deals/deals_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/deals/application/deals_controller.dart';
import 'package:member_app/features/deals/data/deals_models.dart';
import 'package:member_app/features/deals/data/deals_repository.dart';

class _MockRepo extends Mock implements DealsRepository {}

DealProject _p(String id, {bool following = false, int interest = 0}) => DealProject.fromJson({
      'id': id, 'name': 'P$id', 'status': 'PIPELINE',
      'is_following': following, 'interest_count': interest,
    });

DealInterestState _state(String id, {required bool following, required int interest}) =>
    DealInterestState.fromJson(
        {'project_id': id, 'is_following': following, 'interest_count': interest});

void main() {
  late _MockRepo repo;
  late ProviderContainer container;

  setUp(() {
    repo = _MockRepo();
    container = ProviderContainer(overrides: [
      dealsRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);
  });

  DealsController ctrl() => container.read(dealsControllerProvider.notifier);
  DealsState state() => container.read(dealsControllerProvider);

  test('starts Loading; load -> Data (empty list stays Data)', () async {
    expect(state(), isA<DealsLoading>());
    when(() => repo.listMyProjects()).thenAnswer((_) async => [_p('1')]);
    await ctrl().load();
    expect(state(), isA<DealsData>());
    expect((state() as DealsData).projects.single.name, 'P1');

    when(() => repo.listMyProjects()).thenAnswer((_) async => []);
    await ctrl().load();
    expect((state() as DealsData).projects, isEmpty);
  });

  test('load -> Error with the repo message', () async {
    when(() => repo.listMyProjects()).thenThrow(DealsException('down'));
    await ctrl().load();
    expect(state(), isA<DealsError>());
    expect((state() as DealsError).message, 'down');
  });

  test('toggleFollow follows optimistically then reconciles with server counts', () async {
    when(() => repo.listMyProjects()).thenAnswer((_) async => [_p('1', interest: 2)]);
    // Server says 5 followers — reconcile must win over the optimistic +1 (=3).
    when(() => repo.follow('1')).thenAnswer((_) async => _state('1', following: true, interest: 5));
    await ctrl().load();

    await ctrl().toggleFollow('1');
    final p = (state() as DealsData).projects.single;
    expect(p.isFollowing, isTrue);
    expect(p.interestCount, 5);
    verify(() => repo.follow('1')).called(1);
    verifyNever(() => repo.unfollow(any()));
  });

  test('toggleFollow on a followed project unfollows', () async {
    when(() => repo.listMyProjects()).thenAnswer((_) async => [_p('1', following: true, interest: 1)]);
    when(() => repo.unfollow('1')).thenAnswer((_) async => _state('1', following: false, interest: 0));
    await ctrl().load();

    await ctrl().toggleFollow('1');
    final p = (state() as DealsData).projects.single;
    expect(p.isFollowing, isFalse);
    expect(p.interestCount, 0);
    verify(() => repo.unfollow('1')).called(1);
    verifyNever(() => repo.follow(any()));
  });

  test('toggleFollow rolls back and rethrows on failure', () async {
    when(() => repo.listMyProjects()).thenAnswer((_) async => [_p('1', interest: 2)]);
    when(() => repo.follow('1')).thenThrow(DealsException('nope'));
    await ctrl().load();

    await expectLater(ctrl().toggleFollow('1'), throwsA(isA<DealsException>()));
    final p = (state() as DealsData).projects.single;
    expect(p.isFollowing, isFalse); // rolled back
    expect(p.interestCount, 2);
  });

  test('toggleFollow is a no-op outside Data or for unknown ids', () async {
    // Still Loading — nothing happens, repo untouched.
    await ctrl().toggleFollow('1');
    verifyNever(() => repo.follow(any()));
    verifyNever(() => repo.unfollow(any()));

    when(() => repo.listMyProjects()).thenAnswer((_) async => [_p('1')]);
    await ctrl().load();
    await ctrl().toggleFollow('ghost');
    verifyNever(() => repo.follow(any()));
    verifyNever(() => repo.unfollow(any()));
  });
}
