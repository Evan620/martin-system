# Documents (Member App) End-to-End — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox steps. *(Executed via a dynamic Workflow.)*

**Goal:** Wire the member Documents screen to live data — list (member-scoped), client-side search + file-type filter, in-app PDF viewer, open-other-types externally; ✦ Summarise stubbed until Martin (#4).

**Architecture:** Mirror the meetings feature (`data`/`application`/`presentation`). The repo fetches the member's docs (`GET /documents/`) and downloads bytes (`GET /documents/{id}/download`, bearer applied via `dioProvider`). PDFs render in-app via `pdfx` from the downloaded bytes; other types are written to a temp file and opened with the OS (`open_filex`). The PDF viewer is a nested route in the Documents branch of the existing `StatefulShellRoute` (nav persists).

**Tech Stack:** Flutter, flutter_riverpod, dio, pdfx, open_filex, path_provider, go_router, mocktail.

**Spec:** `docs/superpowers/specs/2026-06-09-documents-end-to-end-design.md`

**Environment:** `mobile/`, `export PATH="$PATH:/opt/homebrew/bin"`, `flutter test/analyze`, package `member_app`. Commit per task; never push. Sequential.

**Verified backend (no change):**
- `GET /api/v1/documents/` → `List[DocumentRead]` member-scoped (their TWGs + global; transcripts/shared_workspace excluded). Fields: `id, twg_id, file_name, file_type` (MIME), `stage, is_confidential, file_path, uploaded_by{id,email,role}, twg{id,name}, created_at`. (No `document_type` in the response → filter by file type.)
- `GET /api/v1/documents/{id}/download` → streams bytes (`Content-Type: file_type`), JWT required, TWG-access checked.

**Conventions to mirror:** `dioProvider`/`authControllerProvider` in `features/auth/application/auth_controller.dart`; manual `fromJson`; sealed states; the seed `documents_screen.dart` already has a search field, filter chips, doc cards + "Ask Martin to summarise" hint (reuse its widgets).

---

## Task 1: Dependencies

**Files:** Modify `mobile/pubspec.yaml`
- [ ] **Step 1** add under `dependencies:`:
```yaml
  pdfx: ^2.9.2
  open_filex: ^4.7.0
  path_provider: ^2.1.5
```
- [ ] **Step 2** `cd mobile && flutter pub get` → `Got dependencies!`. (If `pdfx` requires a higher Android `minSdkVersion`, set `minSdk = 21` in `android/app/build.gradle.kts` / `build.gradle` — it usually is already.)
- [ ] **Step 3** commit: `git add mobile/pubspec.yaml mobile/pubspec.lock && git commit -m "chore(mobile): add pdfx + open_filex + path_provider for documents"`

---

## Task 2: Documents model

**Files:** Create `mobile/lib/features/documents/data/documents_models.dart`; Test `mobile/test/features/documents/documents_models_test.dart`

- [ ] **Step 1: Failing test**
```dart
// test/features/documents/documents_models_test.dart
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
```
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement**
```dart
// lib/features/documents/data/documents_models.dart
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
```
- [ ] **Step 4: Run — PASS.**
- [ ] **Step 5: Commit** `git add mobile/lib/features/documents/data/documents_models.dart mobile/test/features/documents && git commit -m "feat(mobile): documents model"`

---

## Task 3: Documents repository

**Files:** Create `mobile/lib/features/documents/data/documents_repository.dart`; Test `mobile/test/features/documents/documents_repository_test.dart`

- [ ] **Step 1: Failing test**
```dart
// test/features/documents/documents_repository_test.dart
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/documents/data/documents_models.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio; late DocumentsRepository repo;
  setUp(() { dio = _MockDio(); repo = DocumentsRepository(dio: dio); });
  Response<T> resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('listDocuments parses a list', () async {
    when(() => dio.get('/documents/')).thenAnswer((_) async => resp<List<dynamic>>([
      {'id': 'd1', 'file_name': 'A.pdf', 'file_type': 'application/pdf', 'is_confidential': false},
    ]));
    final list = await repo.listDocuments();
    expect(list.single.name, 'A.pdf');
  });

  test('downloadBytes requests bytes and returns them', () async {
    when(() => dio.get<List<int>>('/documents/d1/download', options: any(named: 'options')))
        .thenAnswer((_) async => resp<List<int>>([1, 2, 3]));
    final bytes = await repo.downloadBytes('d1');
    expect(bytes, isA<Uint8List>());
    expect(bytes.length, 3);
  });

  test('listDocuments throws DocumentException on error', () async {
    when(() => dio.get('/documents/')).thenThrow(DioException(
      requestOptions: RequestOptions(path: '/documents/'),
      response: Response(statusCode: 500, requestOptions: RequestOptions(path: '/documents/'))));
    expect(() => repo.listDocuments(), throwsA(isA<DocumentException>()));
  });
}
```
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement**
```dart
// lib/features/documents/data/documents_repository.dart
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'documents_models.dart';

class DocumentException implements Exception {
  DocumentException(this.message);
  final String message;
  @override
  String toString() => message;
}

class DocumentsRepository {
  DocumentsRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<List<Document>> listDocuments() async {
    try {
      final res = await _dio.get('/documents/');
      final data = (res.data as List).cast<Map<String, dynamic>>();
      return data.map(Document.fromJson).toList();
    } on DioException {
      throw DocumentException('Could not load documents. Check your connection and try again.');
    }
  }

  /// Downloads the file bytes (JWT bearer applied by the shared Dio interceptor).
  Future<Uint8List> downloadBytes(String id) async {
    try {
      final res = await _dio.get<List<int>>(
        '/documents/$id/download',
        options: Options(responseType: ResponseType.bytes),
      );
      return Uint8List.fromList(res.data ?? const []);
    } on DioException {
      throw DocumentException('Could not open this document.');
    }
  }
}
```
- [ ] **Step 4: Run — PASS.**
- [ ] **Step 5: Commit** `git add mobile/lib/features/documents/data/documents_repository.dart mobile/test/features/documents && git commit -m "feat(mobile): documents repository (list + download bytes)"`

---

## Task 4: Documents controller (state + search/filter)

**Files:** Create `mobile/lib/features/documents/application/documents_controller.dart`; Test `mobile/test/features/documents/documents_controller_test.dart`

- [ ] **Step 1: Failing test**
```dart
// test/features/documents/documents_controller_test.dart
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
```
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement**
```dart
// lib/features/documents/application/documents_controller.dart
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
```
- [ ] **Step 4: Run — PASS.**
- [ ] **Step 5: Commit** `git add mobile/lib/features/documents/application mobile/test/features/documents && git commit -m "feat(mobile): documents controller + filter helper"`

---

## Task 5: Wire the Documents screen

**Files:** Modify `mobile/lib/features/documents/presentation/documents_screen.dart`; Test `mobile/test/features/documents/documents_screen_test.dart`

Rewrite the seed screen to a `ConsumerStatefulWidget`:
- `initState` → `documentsController.load()` (post-frame).
- Watch `documentsControllerProvider`; render loading/error(+Retry)/empty/data.
- Local state: `String _query = ''`, `DocKind? _kind`.
- Header (serif "Documents" + member's TWG eyebrow from `authControllerProvider` + "Shared with you").
- A glass **search field** (`TextField`, `onChanged: (v)=>setState(()=>_query=v)`) — reuse the seed's search styling.
- **Filter chips**: `All` + one chip per distinct `DocKind` present in the data (`.filterLabel`); tapping sets `_kind` (null for All). Reuse the seed chip styling.
- Cards from `filterDocs(data.all, query:_query, kind:_kind)`: reuse the seed doc-card look — leading `GlassSurface.inner` badge showing `d.kind.badge`, name, a meta line (`${d.mime?...} · ${date} · ${uploadedByEmail}`), a **✦ Summarise** button (calls `_summariseStub(context)` → SnackBar "Martin summaries are coming with the assistant." — wired in #4), and a chevron. Tapping the card → `_open(d)`.
- `_open(Document d)`:
  - PDF → `context.push('/documents/${d.id}/pdf?name=${Uri.encodeComponent(d.name)}')` (route added in Task 6).
  - else → `try { final bytes = await ref.read(documentsRepositoryProvider).downloadBytes(d.id); final dir = await getTemporaryDirectory(); final f = File('${dir.path}/${d.name}'); await f.writeAsBytes(bytes); await OpenFilex.open(f.path); } on DocumentException catch(e){ SnackBar(e.message); }` (imports: `dart:io`, `package:path_provider/path_provider.dart`, `package:open_filex/open_filex.dart`).
- Bottom padding 104 so the floating nav clears content.

- [ ] **Step 1: Widget test**
```dart
// test/features/documents/documents_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/documents/application/documents_controller.dart';
import 'package:member_app/features/documents/data/documents_models.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';
import 'package:member_app/features/documents/presentation/documents_screen.dart';

class _MockRepo extends Mock implements DocumentsRepository {}

void main() {
  testWidgets('shows a document name + filters on search', (tester) async {
    final repo = _MockRepo();
    when(() => repo.listDocuments()).thenAnswer((_) async => [
      Document.fromJson({'id':'1','file_name':'Energy Policy.pdf','file_type':'application/pdf','is_confidential':false}),
      Document.fromJson({'id':'2','file_name':'Q2 Budget.xlsx','file_type':'application/vnd.ms-excel','is_confidential':false}),
    ]);
    await tester.pumpWidget(ProviderScope(
      overrides: [documentsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: DocumentsScreen()),
    ));
    await tester.pump(); await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Energy Policy.pdf'), findsOneWidget);
    expect(find.text('Q2 Budget.xlsx'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'budget');
    await tester.pump();
    expect(find.text('Energy Policy.pdf'), findsNothing);
    expect(find.text('Q2 Budget.xlsx'), findsOneWidget);
  });
}
```
- [ ] **Step 2: Run — FAIL** (seed screen has no live data/TextField).
- [ ] **Step 3: Implement** the rewrite described above (reuse seed widgets).
- [ ] **Step 4: Run — PASS**; `flutter analyze lib/features/documents` clean.
- [ ] **Step 5: Commit** `git add mobile/lib/features/documents/presentation/documents_screen.dart mobile/test/features/documents && git commit -m "feat(mobile): wire documents list to live data + open"`

---

## Task 6: In-app PDF viewer + route

**Files:** Create `mobile/lib/features/documents/presentation/pdf_viewer_screen.dart`; Modify `mobile/lib/routing/app_router.dart` (nest under Documents branch); Test `mobile/test/features/documents/pdf_viewer_screen_test.dart`

- [ ] **Step 1: Add the nested route** in the Documents `StatefulShellBranch` (in `app_router.dart`):
```dart
GoRoute(
  path: '/documents',
  builder: (_, __) => const DocumentsScreen(),
  routes: [
    GoRoute(
      path: ':id/pdf',
      pageBuilder: (context, st) => sovereignPage(
        child: PdfViewerScreen(
          documentId: st.pathParameters['id']!,
          title: st.uri.queryParameters['name'] ?? 'Document',
        ),
      ),
    ),
  ],
),
```
(import `pdf_viewer_screen.dart`.)

- [ ] **Step 2: Implement the viewer** — fetch bytes via the repo, render with `pdfx`:
```dart
// lib/features/documents/presentation/pdf_viewer_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pdfx/pdfx.dart';
import '../../../core/theme/sovereign_colors.dart';
import '../application/documents_controller.dart';
import '../data/documents_repository.dart';

class PdfViewerScreen extends ConsumerStatefulWidget {
  const PdfViewerScreen({super.key, required this.documentId, required this.title});
  final String documentId;
  final String title;
  @override
  ConsumerState<PdfViewerScreen> createState() => _PdfViewerScreenState();
}

class _PdfViewerScreenState extends ConsumerState<PdfViewerScreen> {
  PdfControllerPinch? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _open();
  }

  Future<void> _open() async {
    try {
      final bytes = await ref.read(documentsRepositoryProvider).downloadBytes(widget.documentId);
      setState(() => _controller = PdfControllerPinch(document: PdfDocument.openData(bytes)));
    } on DocumentException catch (e) {
      setState(() => _error = e.message);
    }
  }

  @override
  void dispose() { _controller?.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      appBar: AppBar(
        backgroundColor: SovereignColors.navy,
        foregroundColor: SovereignColors.ivory,
        title: Text(widget.title, style: const TextStyle(fontSize: 15)),
      ),
      body: _error != null
          ? Center(child: Padding(padding: const EdgeInsets.all(24),
              child: Text(_error!, textAlign: TextAlign.center,
                style: TextStyle(color: SovereignColors.ivory.withValues(alpha: 0.85)))))
          : _controller == null
              ? const Center(child: CircularProgressIndicator(color: SovereignColors.gold))
              : PdfViewPinch(controller: _controller!),
    );
  }
}
```
- [ ] **Step 3: Test** (the bytes are not valid PDF in the mock, so assert the loading→error path, which keeps it deterministic without a real PDF):
```dart
// test/features/documents/pdf_viewer_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/documents/application/documents_controller.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';
import 'package:member_app/features/documents/presentation/pdf_viewer_screen.dart';

class _MockRepo extends Mock implements DocumentsRepository {}

void main() {
  testWidgets('shows error when the document fails to load', (tester) async {
    final repo = _MockRepo();
    when(() => repo.downloadBytes('d1')).thenThrow(DocumentException('Could not open this document.'));
    await tester.pumpWidget(ProviderScope(
      overrides: [documentsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: PdfViewerScreen(documentId: 'd1', title: 'Doc')),
    ));
    await tester.pump(); await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Could not open this document.'), findsOneWidget);
  });
}
```
- [ ] **Step 4: Run** — `flutter test test/features/documents/` all PASS; `flutter analyze lib` clean; also rerun `flutter test test/routing test/shell` (route change) — green.
- [ ] **Step 5: Commit** `git add mobile/lib/features/documents/presentation/pdf_viewer_screen.dart mobile/lib/routing/app_router.dart mobile/test/features/documents && git commit -m "feat(mobile): in-app PDF viewer + nested documents route"`

---

## Final verification
- [ ] `cd mobile && export PATH="$PATH:/opt/homebrew/bin" && flutter analyze && flutter test` → analyze clean (pre-existing info-lints OK), all tests pass.
- [ ] On device: Documents tab → live docs; search + file-type chips filter; tap a PDF → in-app viewer (nav persists); tap a non-PDF → opens in the OS viewer; ✦ Summarise shows the "coming with Martin" hint.

## Notes
- Filter chips are by **file type** (PDF/Sheets/Docs/Slides/Other) since `DocumentRead` has no `document_type`. (A trivial backend follow-up could add `document_type` for richer categories.)
- ✦ Summarise is a stub until #4 (Martin); it shows a hint, no backend call.
- Confidential docs hidden client-side (defensive); a server-side filter is a later backend fix.
