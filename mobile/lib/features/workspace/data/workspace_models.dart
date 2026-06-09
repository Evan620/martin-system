// lib/features/workspace/data/workspace_models.dart
//
// Shapes for the TWG Workspace, parsed from GET /twgs/{id} (TWGRead). The
// response already carries members, documents, and stats, so one call feeds the
// header + the documents section + the "open actions" count. Reuses the
// Documents feature's Document model for the docs array (same JSON keys).
import '../../documents/data/documents_models.dart';

/// One TWG member (from TWGRead.members -> UserSimple).
class TwgMember {
  const TwgMember({required this.id, required this.name, required this.role});
  final String id;
  final String name;
  final String role;

  factory TwgMember.fromJson(Map<String, dynamic> j) => TwgMember(
        id: j['id'].toString(),
        name: (j['full_name'] ?? '').toString(),
        role: (j['role'] ?? 'TWG_MEMBER').toString(),
      );
}

/// A TWG's detail bundle for the workspace header + docs section.
class TwgDetail {
  const TwgDetail({
    required this.id,
    required this.name,
    required this.pillarLabel,
    required this.members,
    required this.documents,
    required this.openActions,
  });

  final String id;
  final String name;
  final String pillarLabel;
  final List<TwgMember> members;
  final List<Document> documents;
  final int openActions;

  factory TwgDetail.fromJson(Map<String, dynamic> j) {
    final stats = (j['stats'] as Map?)?.cast<String, dynamic>();
    return TwgDetail(
      id: j['id'].toString(),
      name: (j['name'] ?? 'TWG').toString(),
      pillarLabel: _pillarLabel(j['pillar']?.toString()),
      members: ((j['members'] as List?) ?? const [])
          .map((e) => TwgMember.fromJson(e as Map<String, dynamic>))
          .toList(),
      documents: ((j['documents'] as List?) ?? const [])
          .map((e) => Document.fromJson(e as Map<String, dynamic>))
          .toList(),
      openActions: (stats?['open_actions'] as int?) ?? 0,
    );
  }
}

/// Maps the backend TWGPillar enum string to a member-facing label; falls back
/// to a humanized version of any unknown value.
String _pillarLabel(String? pillar) {
  switch (pillar) {
    case 'energy_infrastructure':
      return 'Energy & Infrastructure';
    case 'agriculture_food_systems':
      return 'Agriculture & Food Systems';
    case 'critical_minerals_industrialization':
      return 'Critical Minerals & Industrialization';
    case 'digital_economy_transformation':
      return 'Digital Economy & Transformation';
    case 'protocol_logistics':
      return 'Protocol & Logistics';
    case 'resource_mobilization':
      return 'Resource Mobilization';
    default:
      final raw = (pillar ?? '').replaceAll('_', ' ').trim();
      if (raw.isEmpty) return 'Working Group';
      return raw
          .split(' ')
          .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
          .join(' ');
  }
}
