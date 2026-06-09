import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'documents_models.dart';

class DocumentException implements Exception {
  DocumentException(this.message);
  final String message;
  @override
  String toString() => message;
}

class DocumentsRepository {
  DocumentsRepository({required this._dio});
  final Dio _dio;

  Future<List<Document>> listDocuments() async {
    try {
      final res = await _dio.get('/documents/');
      final data = (res.data as List).cast<Map<String, dynamic>>();
      return data.map(Document.fromJson).toList();
    } on DioException {
      throw DocumentException('Could not load documents. Check your connection and try again.');
    }
  }

  /// Downloads the file bytes (JWT bearer applied by the shared Dio interceptor).
  Future<Uint8List> downloadBytes(String id) async {
    try {
      final res = await _dio.get<List<int>>(
        '/documents/$id/download',
        options: Options(responseType: ResponseType.bytes),
      );
      return Uint8List.fromList(res.data ?? const []);
    } on DioException {
      throw DocumentException('Could not open this document.');
    }
  }
}
