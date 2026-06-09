enum DocKind { pdf, sheet, doc, slides, other }

extension DocKindX on DocKind {
  /// Short uppercase badge label.
  String get badge => switch (this) {
        DocKind.pdf => 'PDF',
        DocKind.sheet => 'XLS',
        DocKind.doc => 'DOC',
        DocKind.slides => 'PPT',
        DocKind.other => 'FILE',
      };

  /// Filter-chip label.
  String get filterLabel => switch (this) {
        DocKind.pdf => 'PDF',
        DocKind.sheet => 'Sheets',
        DocKind.doc => 'Docs',
        DocKind.slides => 'Slides',
        DocKind.other => 'Other',
      };

  static DocKind fromMime(String? mime) {
    final m = (mime ?? '').toLowerCase();
    if (m.contains('pdf')) return DocKind.pdf;
    if (m.contains('sheet') || m.contains('excel') || m.contains('csv')) return DocKind.sheet;
    if (m.contains('word') || m.contains('document') || m.contains('msword')) return DocKind.doc;
    if (m.contains('presentation') || m.contains('powerpoint')) return DocKind.slides;
    return DocKind.other;
  }
}

class Document {
  const Document({
    required this.id,
    required this.name,
    required this.mime,
    required this.kind,
    required this.twgName,
    required this.uploadedByEmail,
    required this.isConfidential,
    required this.createdAt,
  });

  final String id;
  final String name;
  final String? mime;
  final DocKind kind;
  final String? twgName;
  final String? uploadedByEmail;
  final bool isConfidential;
  final DateTime? createdAt;

  bool get isPdf => kind == DocKind.pdf;

  factory Document.fromJson(Map<String, dynamic> j) {
    final mime = j['file_type']?.toString();
    return Document(
      id: j['id'].toString(),
      name: (j['file_name'] ?? 'Document').toString(),
      mime: mime,
      kind: DocKindX.fromMime(mime),
      twgName: (j['twg'] as Map?)?['name']?.toString(),
      uploadedByEmail: (j['uploaded_by'] as Map?)?['email']?.toString(),
      isConfidential: j['is_confidential'] == true,
      createdAt: j['created_at'] != null ? DateTime.tryParse(j['created_at'].toString())?.toLocal() : null,
    );
  }
}
