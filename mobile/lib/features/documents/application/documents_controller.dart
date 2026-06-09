import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/application/auth_controller.dart';
import '../data/documents_models.dart';
import '../data/documents_repository.dart';

sealed class DocumentsState { const DocumentsState(); }
class DocumentsLoading extends DocumentsState { const DocumentsLoading(); }
class DocumentsEmpty extends DocumentsState { const DocumentsEmpty(); }
class DocumentsError extends DocumentsState { const DocumentsError(this.message); final String message; }
class DocumentsData extends DocumentsState { const DocumentsData(this.all); final List<Document> all; }

final documentsRepositoryProvider = Provider<DocumentsRepository>(
  (ref) => DocumentsRepository(dio: ref.watch(dioProvider)),
);

/// Pure helper: narrow by search text (name) + selected kind.
List<Document> filterDocs(List<Document> docs, {required String query, required DocKind? kind}) {
  final q = query.trim().toLowerCase();
  return docs.where((d) {
    final okQ = q.isEmpty || d.name.toLowerCase().contains(q);
    final okK = kind == null || d.kind == kind;
    return okQ && okK;
  }).toList();
}

class DocumentsController extends Notifier<DocumentsState> {
  @override
  DocumentsState build() => const DocumentsLoading();
  DocumentsRepository get _repo => ref.read(documentsRepositoryProvider);

  Future<void> load() async {
    state = const DocumentsLoading();
    try {
      final list = (await _repo.listDocuments()).where((d) => !d.isConfidential).toList();
      state = list.isEmpty ? const DocumentsEmpty() : DocumentsData(list);
    } on DocumentException catch (e) {
      state = DocumentsError(e.message);
    }
  }
}

final documentsControllerProvider =
    NotifierProvider<DocumentsController, DocumentsState>(DocumentsController.new);
