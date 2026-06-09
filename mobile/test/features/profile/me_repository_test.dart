// test/features/profile/me_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/profile/data/me_repository.dart';

class _MockDio extends Mock implements Dio {}
void main() {
  late _MockDio dio; late MeRepository repo;
  setUp(() { dio = _MockDio(); repo = MeRepository(dio: dio); });
  Response<T> resp<T>(T data, {int code = 200}) => Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('listActionItems hits mine_only', () async {
    when(() => dio.get('/action-items/', queryParameters: any(named: 'queryParameters')))
      .thenAnswer((_) async => resp<List<dynamic>>([{'id':'a1','description':'x','status':'PENDING'}]));
    final items = await repo.listActionItems();
    expect(items.single.description, 'x');
    verify(() => dio.get('/action-items/', queryParameters: {'mine_only': true})).called(1);
  });
  test('markDone PATCHes COMPLETED', () async {
    when(() => dio.patch('/action-items/a1', data: any(named: 'data')))
      .thenAnswer((_) async => resp<Map<String,dynamic>>({'id':'a1','description':'x','status':'COMPLETED'}));
    await repo.markDone('a1');
    verify(() => dio.patch('/action-items/a1', data: {'status': 'COMPLETED'})).called(1);
  });
  test('addReminder POSTs message + remind_at (utc)', () async {
    when(() => dio.post('/reminders/', data: any(named: 'data')))
      .thenAnswer((_) async => resp<Map<String,dynamic>>({'id':'r1','message':'Prep','remind_at':'2026-06-10T09:00:00Z','user_id':'u1'}));
    final r = await repo.addReminder('Prep', DateTime.utc(2026,6,10,9));
    expect(r.message, 'Prep');
  });
}
