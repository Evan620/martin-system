import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/documents/data/documents_models.dart';

void main() {
  test('Document.fromJson parses fields + kind from mime', () {
    final d = Document.fromJson({
      'id': 'd1', 'file_name': 'Energy Policy.pdf', 'file_type': 'application/pdf',
      'is_confidential': false, 'created_at': '2026-06-06T09:00:00Z',
      'twg': {'id': 't1', 'name': 'Energy TWG'}, 'uploaded_by': {'email': 'jo@x.org'},
    });
    expect(d.name, 'Energy Policy.pdf');
    expect(d.kind, DocKind.pdf);
    expect(d.isPdf, isTrue);
    expect(d.twgName, 'Energy TWG');
    expect(d.uploadedByEmail, 'jo@x.org');
    expect(DocKindX.fromMime('application/vnd.ms-excel'), DocKind.sheet);
    expect(DocKindX.fromMime('application/vnd.openxmlformats-officedocument.wordprocessingml.document'), DocKind.doc);
    expect(DocKindX.fromMime('application/vnd.ms-powerpoint'), DocKind.slides);
    expect(DocKindX.fromMime('image/png'), DocKind.other);
  });
}
