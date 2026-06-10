// test/features/documents/documents_screen_test.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/motion/skeleton.dart';
import 'package:member_app/core/ui/list_row.dart';
import 'package:member_app/features/documents/application/documents_controller.dart';
import 'package:member_app/features/documents/data/documents_models.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';
import 'package:member_app/features/documents/presentation/documents_screen.dart';

class _MockRepo extends Mock implements DocumentsRepository {}

void main() {
  testWidgets('compact header + document rows; search filters', (tester) async {
    final repo = _MockRepo();
    when(() => repo.listDocuments()).thenAnswer((_) async => [
      Document.fromJson({'id':'1','file_name':'Energy Policy.pdf','file_type':'application/pdf','is_confidential':false}),
      Document.fromJson({'id':'2','file_name':'Q2 Budget.xlsx','file_type':'application/vnd.ms-excel','is_confidential':false}),
    ]);
    await tester.pumpWidget(ProviderScope(
      overrides: [documentsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: DocumentsScreen()),
    ));
    await tester.pump(); // post-frame load()
    // Let the skeleton->content AnimatedSwitcher finish dropping the old view.
    await tester.pump(const Duration(milliseconds: 300));

    // Compact AppHeader: bold sans title + TWG context label; the old serif
    // eyebrow pattern is gone.
    expect(find.text('Documents'), findsOneWidget);
    expect(find.text('Shared with you'), findsOneWidget);
    expect(find.text('SHARED WITH YOU'), findsNothing);

    // The documents render as ListRows inside one RowGroup.
    expect(find.byType(RowGroup), findsOneWidget);
    expect(find.descendant(of: find.byType(ListRow), matching: find.text('Energy Policy.pdf')), findsOneWidget);
    expect(find.text('Q2 Budget.xlsx'), findsOneWidget);

    // Each row carries the trailing yellow ✦ Summarise icon-button.
    expect(find.byIcon(Icons.auto_awesome), findsNWidgets(2));

    await tester.enterText(find.byType(TextField), 'budget');
    await tester.pump();
    expect(find.text('Energy Policy.pdf'), findsNothing);
    expect(find.text('Q2 Budget.xlsx'), findsOneWidget);
  });

  testWidgets('trailing ✦ pushes /martin?q=Summarise the document: <name>',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.listDocuments()).thenAnswer((_) async => [
          Document.fromJson({
            'id': '1',
            'file_name': 'Energy Policy.pdf',
            'file_type': 'application/pdf',
            'is_confidential': false,
          }),
        ]);

    final router = GoRouter(
      initialLocation: '/documents',
      routes: [
        GoRoute(path: '/documents', builder: (_, _) => const DocumentsScreen()),
        // Probe stand-in for the canonical /martin chat route.
        GoRoute(
          path: '/martin',
          builder: (_, st) =>
              _ProbeChatScreen(seed: st.uri.queryParameters['q']),
        ),
      ],
    );

    await tester.pumpWidget(ProviderScope(
      overrides: [documentsRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    // The Summarise action is icon-only now (yellow micro-action per row).
    expect(find.text('Summarise'), findsNothing);
    await tester.tap(find.byIcon(Icons.auto_awesome));
    await tester.pumpAndSettle();

    // The probe echoes the decoded ?q= seed.
    expect(
      find.text('seed=Summarise the document: Energy Policy.pdf'),
      findsOneWidget,
    );
  });

  testWidgets('loading shows row-shaped skeletons, not a spinner',
      (tester) async {
    final repo = _MockRepo();
    final pending = Completer<List<Document>>();
    when(() => repo.listDocuments()).thenAnswer((_) => pending.future);

    await tester.pumpWidget(ProviderScope(
      overrides: [documentsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: DocumentsScreen()),
    ));
    await tester.pump(); // post-frame load() -> still loading

    expect(find.byType(SkeletonRow), findsNWidgets(4));
    expect(find.byType(CircularProgressIndicator), findsNothing);

    pending.complete(const []); // let the future settle (-> empty state)
    await tester.pumpAndSettle();
    expect(find.text('No documents shared yet'), findsOneWidget);
  });
}

/// A tiny stand-in for the Martin chat route that echoes the decoded seed.
class _ProbeChatScreen extends StatelessWidget {
  const _ProbeChatScreen({required this.seed});
  final String? seed;
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('seed=$seed')));
}
