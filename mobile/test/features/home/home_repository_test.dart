// test/features/home/home_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio;
  late HomeRepository repo;

  setUp(() {
    dio = _MockDio();
    repo = HomeRepository(dio: dio);
  });

  Response<T> resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('getBriefing parses the /martin/briefing payload', () async {
    when(() => dio.get('/martin/briefing')).thenAnswer(
      (_) async => resp<Map<String, dynamic>>({
        'greeting': 'Good morning',
        'upcoming_meetings': [
          {
            'title': 'Energy Sync',
            'twg_name': 'Energy',
            'starts_at': '2031-06-10T14:00:00Z',
            'minutes_until': 120,
          },
        ],
        'overdue_items': [
          {'title': 'Send notes', 'days_overdue': 2},
        ],
      }),
    );

    final b = await repo.getBriefing();
    expect(b, isA<Briefing>());
    expect(b.greeting, 'Good morning');
    expect(b.nextMeeting?.title, 'Energy Sync');
    expect(b.overdueCount, 1);
  });

  test('throws HomeException on Dio error', () async {
    when(() => dio.get('/martin/briefing')).thenThrow(
      DioException(
        requestOptions: RequestOptions(path: '/martin/briefing'),
        response: Response(
          statusCode: 500,
          requestOptions: RequestOptions(path: '/martin/briefing'),
        ),
      ),
    );
    expect(() => repo.getBriefing(), throwsA(isA<HomeException>()));
  });
}
