import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/documents/data/documents_models.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio; late DocumentsRepository repo;
  setUp(() { dio = _MockDio(); repo = DocumentsRepository(dio: dio); });
  Response<T> resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('listDocuments parses a list', () async {
    when(() => dio.get('/documents/')).thenAnswer((_) async => resp<List<dynamic>>([
      {'id': 'd1', 'file_name': 'A.pdf', 'file_type': 'application/pdf', 'is_confidential': false},
    ]));
    final list = await repo.listDocuments();
    expect(list.single.name, 'A.pdf');
  });

  test('downloadBytes requests bytes and returns them', () async {
    when(() => dio.get<List<int>>('/documents/d1/download', options: any(named: 'options')))
        .thenAnswer((_) async => resp<List<int>>([1, 2, 3]));
    final bytes = await repo.downloadBytes('d1');
    expect(bytes, isA<Uint8List>());
    expect(bytes.length, 3);
  });

  test('listDocuments throws DocumentException on error', () async {
    when(() => dio.get('/documents/')).thenThrow(DioException(
      requestOptions: RequestOptions(path: '/documents/'),
      response: Response(statusCode: 500, requestOptions: RequestOptions(path: '/documents/'))));
    expect(() => repo.listDocuments(), throwsA(isA<DocumentException>()));
  });
}
