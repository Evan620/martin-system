// test/features/deals/deals_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/deals/data/deals_models.dart';
import 'package:member_app/features/deals/data/deals_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio;
  late DealsRepository repo;

  setUp(() {
    dio = _MockDio();
    repo = DealsRepository(dio: dio);
  });

  Response<T> resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  DioException err(String path, int code) => DioException(
        requestOptions: RequestOptions(path: path),
        response: Response(statusCode: code, requestOptions: RequestOptions(path: path)),
      );

  test('listMyProjects GETs /pipeline/member and parses the list', () async {
    when(() => dio.get('/pipeline/member')).thenAnswer((_) async => resp<List<dynamic>>([
          {
            'id': 'p1', 'name': 'Bagre Solar PV', 'sector': 'energy_infrastructure',
            'status': 'DEAL_ROOM_FEATURED', 'investment_size': '25000000.00', 'currency': 'USD',
            'readiness_score': 4.2, 'afcen_score': 55.0, 'strategic_alignment_score': null,
            'location': 'Ghana', 'description': 'Solar.', 'is_following': false, 'interest_count': 0,
          },
        ]));
    final list = await repo.listMyProjects();
    expect(list, isA<List<DealProject>>());
    expect(list.single.name, 'Bagre Solar PV');
    expect(list.single.stage, DealStage.dealRoom);
    verify(() => dio.get('/pipeline/member')).called(1);
  });

  test('follow POSTs /pipeline/{id}/interest and returns the reconcile state', () async {
    when(() => dio.post('/pipeline/p1/interest')).thenAnswer(
        (_) async => resp<Map<String, dynamic>>({'project_id': 'p1', 'is_following': true, 'interest_count': 1}));
    final s = await repo.follow('p1');
    expect(s.isFollowing, isTrue);
    expect(s.interestCount, 1);
    verify(() => dio.post('/pipeline/p1/interest')).called(1);
  });

  test('unfollow DELETEs /pipeline/{id}/interest and returns the reconcile state', () async {
    when(() => dio.delete('/pipeline/p1/interest')).thenAnswer(
        (_) async => resp<Map<String, dynamic>>({'project_id': 'p1', 'is_following': false, 'interest_count': 0}));
    final s = await repo.unfollow('p1');
    expect(s.isFollowing, isFalse);
    expect(s.interestCount, 0);
    verify(() => dio.delete('/pipeline/p1/interest')).called(1);
  });

  test('listMyProjects wraps Dio errors in DealsException', () async {
    when(() => dio.get('/pipeline/member')).thenThrow(err('/pipeline/member', 500));
    expect(() => repo.listMyProjects(), throwsA(isA<DealsException>()));
  });

  test('follow/unfollow wrap Dio errors (incl. anti-enumeration 404) in DealsException', () async {
    when(() => dio.post('/pipeline/ghost/interest')).thenThrow(err('/pipeline/ghost/interest', 404));
    expect(() => repo.follow('ghost'), throwsA(isA<DealsException>()));

    when(() => dio.delete('/pipeline/ghost/interest')).thenThrow(err('/pipeline/ghost/interest', 404));
    expect(() => repo.unfollow('ghost'), throwsA(isA<DealsException>()));
  });
}
