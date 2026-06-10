// lib/features/deals/data/deals_repository.dart
//
// Deal Room HTTP layer (mirrors meetings_repository.dart). All paths ride the
// member-JWT Dio from dioProvider; TWG scoping is server-enforced, so there is
// no twg_id parameter anywhere. Follow/unfollow are idempotent on the server
// and return the authoritative DealInterestState for reconciling optimistic UI.
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart';
import 'deals_models.dart';

class DealsException implements Exception {
  DealsException(this.message);
  final String message;
  @override
  String toString() => message;
}

class DealsRepository {
  DealsRepository({required this._dio});
  final Dio _dio;

  /// Own-TWG projects at every lifecycle stage, sorted by name server-side.
  Future<List<DealProject>> listMyProjects() async {
    try {
      final res = await _dio.get('/pipeline/member');
      final data = (res.data as List).cast<Map<String, dynamic>>();
      return data.map(DealProject.fromJson).toList();
    } on DioException {
      throw DealsException('Could not load the Deal Room. Check your connection and try again.');
    }
  }

  Future<DealInterestState> follow(String projectId) => _setInterest(projectId, follow: true);

  Future<DealInterestState> unfollow(String projectId) => _setInterest(projectId, follow: false);

  Future<DealInterestState> _setInterest(String projectId, {required bool follow}) async {
    try {
      final res = follow
          ? await _dio.post('/pipeline/$projectId/interest')
          : await _dio.delete('/pipeline/$projectId/interest');
      return DealInterestState.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      // 404 covers both nonexistent and cross-TWG projects (anti-enumeration).
      if (e.response?.statusCode == 404) {
        throw DealsException('This project is no longer available.');
      }
      throw DealsException('Could not update your follow. Try again.');
    }
  }
}

final dealsRepositoryProvider = Provider<DealsRepository>(
  (ref) => DealsRepository(dio: ref.watch(dioProvider)),
);
