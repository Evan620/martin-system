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
