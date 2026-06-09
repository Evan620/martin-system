// test/features/meetings/meetings_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio;
  late MeetingsRepository repo;

  setUp(() {
    dio = _MockDio();
    repo = MeetingsRepository(dio: dio);
  });

  Response<T> resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('listMeetings parses a list', () async {
    when(() => dio.get('/meetings/')).thenAnswer((_) async => resp<List<dynamic>>([
          {'id': 'm1', 'title': 'Sync', 'scheduled_at': '2026-06-10T14:00:00Z', 'status': 'SCHEDULED',
           'meeting_type': 'virtual', 'participants': []},
        ]));
    final list = await repo.listMeetings();
    expect(list, isA<List<Meeting>>());
    expect(list.single.title, 'Sync');
  });

  test('setMyRsvp PUTs the api value', () async {
    when(() => dio.put('/meetings/m1/my-rsvp', data: any(named: 'data')))
        .thenAnswer((_) async => resp<Map<String, dynamic>>({'id': 'p1', 'rsvp_status': 'TENTATIVE'}));
    await repo.setMyRsvp('m1', MeetingRsvp.maybe);
    verify(() => dio.put('/meetings/m1/my-rsvp', data: {'rsvp_status': 'TENTATIVE'})).called(1);
  });

  test('throws MeetingException on Dio error', () async {
    when(() => dio.get('/meetings/')).thenThrow(
      DioException(requestOptions: RequestOptions(path: '/meetings/'), response:
        Response(statusCode: 500, requestOptions: RequestOptions(path: '/meetings/'))),
    );
    expect(() => repo.listMeetings(), throwsA(isA<MeetingException>()));
  });

  test('meetingAgenda returns content, null on 404', () async {
    when(() => dio.get('/meetings/m1/agenda'))
        .thenAnswer((_) async => resp<Map<String, dynamic>>({'content': '1. Open\n2. Close'}));
    expect(await repo.meetingAgenda('m1'), '1. Open\n2. Close');

    when(() => dio.get('/meetings/m2/agenda')).thenThrow(DioException(
      requestOptions: RequestOptions(path: '/meetings/m2/agenda'),
      response: Response(statusCode: 404, requestOptions: RequestOptions(path: '/meetings/m2/agenda')),
    ));
    expect(await repo.meetingAgenda('m2'), isNull);
  });
}
