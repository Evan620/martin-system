import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/documents/application/documents_controller.dart';
import 'package:member_app/features/documents/data/documents_models.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';

class _MockRepo extends Mock implements DocumentsRepository {}

Document _d(String id, String name, String mime, {bool conf = false}) => Document.fromJson({
  'id': id, 'file_name': name, 'file_type': mime, 'is_confidential': conf,
});

void main() {
  test('load filters out confidential + sets data/empty', () async {
    final repo = _MockRepo();
    when(() => repo.listDocuments()).thenAnswer((_) async => [
      _d('1', 'Open.pdf', 'application/pdf'),
      _d('2', 'Secret.pdf', 'application/pdf', conf: true),
    ]);
    final c = ProviderContainer(overrides: [documentsRepositoryProvider.overrideWithValue(repo)]);
    addTearDown(c.dispose);
    await c.read(documentsControllerProvider.notifier).load();
    final state = c.read(documentsControllerProvider) as DocumentsData;
    expect(state.all.length, 1); // confidential hidden
    expect(state.all.single.name, 'Open.pdf');
  });

  test('visibleDocs applies search + kind filter', () {
    final docs = [_d('1','Budget.xlsx','application/vnd.ms-excel'), _d('2','Policy.pdf','application/pdf')];
    expect(filterDocs(docs, query: 'pol', kind: null).single.name, 'Policy.pdf');
    expect(filterDocs(docs, query: '', kind: DocKind.sheet).single.name, 'Budget.xlsx');
    expect(filterDocs(docs, query: '', kind: null).length, 2);
  });
}
