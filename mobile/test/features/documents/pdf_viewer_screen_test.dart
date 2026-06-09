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
