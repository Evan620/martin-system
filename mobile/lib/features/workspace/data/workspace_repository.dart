// lib/features/workspace/data/workspace_repository.dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart'; // dioProvider
import 'workspace_models.dart';

class WorkspaceException implements Exception {
  WorkspaceException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Reads a single TWG's detail (name, pillar, members, documents, stats).
/// Scoped meetings + tasks are fetched by the controller via the existing
/// MeetingsRepository / MeRepository with a twgId.
class WorkspaceRepository {
  // ignore: prefer_initializing_formals — keep `dio` as the public named param.
  WorkspaceRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<TwgDetail> twgDetail(String twgId) async {
    try {
      final res = await _dio.get('/twgs/$twgId');
      return TwgDetail.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw WorkspaceException('Could not open this workspace.');
    }
  }
}

final workspaceRepositoryProvider = Provider<WorkspaceRepository>(
  (ref) => WorkspaceRepository(dio: ref.watch(dioProvider)),
);
