// lib/features/home/data/home_repository.dart
//
// Home repository — fetches the member-scoped briefing from the backend.
// `GET /martin/briefing` returns the greeting + upcoming meetings + overdue
// items; we map it into a `Briefing`. Network failures surface as a friendly
// `HomeException` (mirrors features/meetings/data/meetings_repository.dart).
import 'package:dio/dio.dart';
import 'briefing_models.dart';

class HomeException implements Exception {
  HomeException(this.message);
  final String message;
  @override
  String toString() => message;
}

class HomeRepository {
  HomeRepository({required this._dio});
  final Dio _dio;

  Future<Briefing> getBriefing() async {
    try {
      final res = await _dio.get('/martin/briefing');
      return Briefing.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw HomeException('Could not load your briefing.');
    }
  }
}
