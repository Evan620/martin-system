// test/features/profile/me_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/profile/data/me_models.dart';
import 'package:member_app/features/profile/data/me_repository.dart';

class _MockRepo extends Mock implements MeRepository {}
ActionItem _ai(String id, String st) => ActionItem.fromJson({'id':id,'description':'t$id','status':st});

void main() {
  test('load -> data; markDone optimistic + rollback on error', () async {
    final repo = _MockRepo();
    when(() => repo.listActionItems()).thenAnswer((_) async => [_ai('1','PENDING')]);
    when(() => repo.listReminders()).thenAnswer((_) async => []);
    final c = ProviderContainer(overrides: [meRepositoryProvider.overrideWithValue(repo)]);
    addTearDown(c.dispose);
    await c.read(meControllerProvider.notifier).load();
    expect(c.read(meControllerProvider), isA<MeData>());

    when(() => repo.markDone('1')).thenThrow(MeException('nope'));
    await expectLater(c.read(meControllerProvider.notifier).markDone('1'), throwsA(isA<MeException>()));
    final st = c.read(meControllerProvider) as MeData;
    expect(st.items.single.isDone, isFalse); // rolled back
  });
}
