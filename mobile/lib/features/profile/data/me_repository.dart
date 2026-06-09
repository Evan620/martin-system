// lib/features/profile/data/me_repository.dart
import 'package:dio/dio.dart';
import 'me_models.dart';

class MeException implements Exception {
  MeException(this.message);
  final String message;
  @override
  String toString() => message;
}

class MeRepository {
  MeRepository({required this._dio});
  final Dio _dio;

  Future<List<ActionItem>> listActionItems({String? twgId}) async {
    try {
      final res = await _dio.get('/action-items/', queryParameters: {
        'mine_only': true,
        'twg_id': ?twgId,
      });
      return (res.data as List).cast<Map<String, dynamic>>().map(ActionItem.fromJson).toList();
    } on DioException {
      throw MeException('Could not load your tasks.');
    }
  }

  Future<void> markDone(String id) async {
    try {
      await _dio.patch('/action-items/$id', data: {'status': 'COMPLETED'});
    } on DioException {
      throw MeException('Could not update the task.');
    }
  }

  Future<List<Reminder>> listReminders() async {
    try {
      final res = await _dio.get('/reminders/');
      return (res.data as List).cast<Map<String, dynamic>>().map(Reminder.fromJson).toList();
    } on DioException {
      throw MeException('Could not load your reminders.');
    }
  }

  Future<Reminder> addReminder(String message, DateTime remindAtUtc) async {
    try {
      final res = await _dio.post('/reminders/', data: {
        'message': message,
        'remind_at': remindAtUtc.toUtc().toIso8601String(),
      });
      return Reminder.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw MeException('Could not save the reminder.');
    }
  }

  Future<void> deleteReminder(String id) async {
    try {
      await _dio.delete('/reminders/$id');
    } on DioException {
      throw MeException('Could not delete the reminder.');
    }
  }
}
