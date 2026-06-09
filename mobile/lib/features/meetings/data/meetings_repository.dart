// lib/features/meetings/data/meetings_repository.dart
import 'package:dio/dio.dart';
import 'meetings_models.dart';

class MeetingException implements Exception {
  MeetingException(this.message);
  final String message;
  @override
  String toString() => message;
}

class MeetingsRepository {
  MeetingsRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<List<Meeting>> listMeetings() async {
    try {
      final res = await _dio.get('/meetings/');
      final data = (res.data as List).cast<Map<String, dynamic>>();
      return data.map(Meeting.fromJson).toList();
    } on DioException {
      throw MeetingException('Could not load meetings. Check your connection and try again.');
    }
  }

  Future<Meeting> meetingDetail(String id) async {
    try {
      final res = await _dio.get('/meetings/$id');
      return Meeting.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw MeetingException('Could not open this meeting.');
    }
  }

  Future<void> setMyRsvp(String meetingId, MeetingRsvp rsvp) async {
    try {
      await _dio.put('/meetings/$meetingId/my-rsvp', data: {'rsvp_status': rsvp.toApi});
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        throw MeetingException("You're not on this meeting's invite list.");
      }
      throw MeetingException('Could not save your RSVP. Try again.');
    }
  }
}
