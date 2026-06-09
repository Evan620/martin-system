// test/features/workspace/workspace_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/workspace/data/workspace_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio;
  late WorkspaceRepository repo;
  setUp(() {
    dio = _MockDio();
    repo = WorkspaceRepository(dio: dio);
  });
  Response<T> resp<T>(T data) =>
      Response<T>(data: data, statusCode: 200, requestOptions: RequestOptions(path: '/'));

  test('twgDetail GETs /twgs/{id} and parses', () async {
    when(() => dio.get('/twgs/t1')).thenAnswer((_) async => resp<Map<String, dynamic>>({
          'id': 't1',
          'name': 'Energy',
          'pillar': 'energy_infrastructure',
          'members': [
            {'id': 'u1', 'full_name': 'Amina', 'email': 'a@x.org', 'role': 'TWG_MEMBER'}
          ],
          'documents': [],
          'stats': {'open_actions': 1},
        }));
    final d = await repo.twgDetail('t1');
    expect(d.name, 'Energy');
    expect(d.members.single.name, 'Amina');
    expect(d.openActions, 1);
  });

  test('twgDetail wraps DioException in WorkspaceException', () async {
    when(() => dio.get('/twgs/bad')).thenThrow(
      DioException(requestOptions: RequestOptions(path: '/twgs/bad')),
    );
    expect(() => repo.twgDetail('bad'), throwsA(isA<WorkspaceException>()));
  });
}
