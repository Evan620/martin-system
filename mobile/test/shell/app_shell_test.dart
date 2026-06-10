// test/shell/app_shell_test.dart
//
// StatefulShellRoute.indexedStack builds ALL branch roots when the shell first
// builds, so Meetings / Documents / Home / Me each fire their load() on build.
// Every data provider must therefore be stubbed (and sharedPreferences
// overridden) or a branch will hang on a real network call / unimplemented
// provider.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/documents/application/documents_controller.dart';
import 'package:member_app/features/documents/data/documents_models.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/profile/data/me_repository.dart';
import 'package:member_app/features/profile/data/notification_prefs.dart';
import 'package:member_app/routing/app_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _MockMeetingsRepo extends Mock implements MeetingsRepository {}

class _MockDocumentsRepo extends Mock implements DocumentsRepository {}

class _MockHomeRepo extends Mock implements HomeRepository {}

class _MockMeRepo extends Mock implements MeRepository {}

class _AuthedController extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(
      AppUser(id: 'u1', email: 'a@x.org', fullName: 'Amina', role: UserRole.twgMember, twgs: []));
}

void main() {
  setUpAll(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<ProviderContainer> buildContainer() async {
    final prefs = await SharedPreferences.getInstance();

    final meetingsRepo = _MockMeetingsRepo();
    when(() => meetingsRepo.listMeetings()).thenAnswer((_) async => []);

    final docsRepo = _MockDocumentsRepo();
    when(() => docsRepo.listDocuments()).thenAnswer((_) async => [
          Document.fromJson({
            'id': '1',
            'file_name': 'A.pdf',
            'file_type': 'application/pdf',
            'is_confidential': false,
          }),
        ]);

    final homeRepo = _MockHomeRepo();
    when(() => homeRepo.getBriefing()).thenAnswer(
      (_) async => Briefing.fromJson({'greeting': 'Good morning', 'overdue_count': 0}),
    );

    final meRepo = _MockMeRepo();
    when(() => meRepo.listActionItems()).thenAnswer((_) async => []);
    when(() => meRepo.listReminders()).thenAnswer((_) async => []);

    return ProviderContainer(overrides: [
      authControllerProvider.overrideWith(_AuthedController.new),
      meetingsRepositoryProvider.overrideWithValue(meetingsRepo),
      documentsRepositoryProvider.overrideWithValue(docsRepo),
      homeRepositoryProvider.overrideWithValue(homeRepo),
      meRepositoryProvider.overrideWithValue(meRepo),
      sharedPreferencesProvider.overrideWithValue(prefs),
    ]);
  }

  testWidgets('shell shows 5 expanding-pill destinations + Martin FAB; tab switch works',
      (tester) async {
    final container = await buildContainer();
    addTearDown(container.dispose);
    final router = container.read(goRouterProvider);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pumpAndSettle();

    // All five expanding-pill destinations (keyed nav-0..nav-4).
    for (var i = 0; i < 5; i++) {
      expect(find.byKey(Key('nav-$i')), findsOneWidget);
    }
    // The active pill reveals its label (default branch = Home).
    expect(find.text('Home'), findsWidgets);
    // Floating Martin ✦ FAB.
    expect(find.byKey(const Key('martin-fab')), findsOneWidget);

    // Switching to the Documents branch via its pill.
    await tester.tap(find.byKey(const Key('nav-1')));
    await tester.pumpAndSettle();
    expect(find.text('Shared with you'), findsWidgets); // DocumentsScreen subtitle
  });

  testWidgets('tapping the Martin FAB opens the streaming Martin chat screen',
      (tester) async {
    final container = await buildContainer();
    addTearDown(container.dispose);
    final router = container.read(goRouterProvider);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('martin-fab')));
    await tester.pumpAndSettle();

    // The real chat screen renders: the ✦ Martin header + the input bar.
    expect(find.text('✦ Martin'), findsOneWidget);
    expect(find.byKey(const Key('martin-chat-input')), findsOneWidget);

    // Full-screen contract: /martin is a root-navigator push, so the shell's
    // nav pills and the FAB are covered (offstage) while the chat is open.
    for (var i = 0; i < 5; i++) {
      expect(find.byKey(Key('nav-$i')), findsNothing);
    }
    expect(find.byKey(const Key('martin-fab')), findsNothing);
  });
}
