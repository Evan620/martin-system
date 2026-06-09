// test/features/workspace/workspace_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/workspace/data/workspace_models.dart';

void main() {
  test('TwgDetail.fromJson parses name, pillar label, members, docs', () {
    final d = TwgDetail.fromJson({
      'id': 't1',
      'name': 'Energy',
      'pillar': 'energy_infrastructure',
      'status': 'active',
      'members': [
        {'id': 'u1', 'full_name': 'Amina Diallo', 'email': 'a@x.org', 'role': 'TWG_MEMBER'},
        {'id': 'u2', 'full_name': 'Kofi Mensah', 'email': 'k@x.org', 'role': 'TWG_FACILITATOR'},
      ],
      'documents': [
        {'id': 'd1', 'file_name': 'Grid brief.pdf', 'file_type': 'application/pdf', 'is_confidential': false},
      ],
      'stats': {'meetings_held': 5, 'open_actions': 2, 'pipeline_projects': 3, 'resources_count': 12},
    });
    expect(d.id, 't1');
    expect(d.name, 'Energy');
    expect(d.pillarLabel, 'Energy & Infrastructure');
    expect(d.members.length, 2);
    expect(d.members.first.name, 'Amina Diallo');
    expect(d.documents.single.name, 'Grid brief.pdf');
    expect(d.openActions, 2);
  });

  test('TwgDetail.fromJson tolerates missing members/documents/stats', () {
    final d = TwgDetail.fromJson({'id': 't2', 'name': 'Trade', 'pillar': 'protocol_logistics'});
    expect(d.members, isEmpty);
    expect(d.documents, isEmpty);
    expect(d.openActions, 0);
    expect(d.pillarLabel, 'Protocol & Logistics');
  });

  test('unknown pillar falls back to a humanized string', () {
    final d = TwgDetail.fromJson({'id': 't3', 'name': 'X', 'pillar': 'something_new'});
    expect(d.pillarLabel, 'Something New');
  });
}
