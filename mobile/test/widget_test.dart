// Smoke test for the member app entry point.
//
// The scaffolded counter test was replaced when Task 13 wired the real app
// entry (ProviderScope + MemberApp). It boots through the router into the
// StatefulShellRoute navigation shell while the session bootstrap runs.
//
// StatefulShellRoute.indexedStack builds every branch root on shell build, so
// each branch fires its load() at once — stub all data providers (and override
// sharedPreferences) so nothing hangs on a real network call.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:member_app/app.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/documents/application/documents_controller.dart';
import 'package:member_app/features/documents/data/documents_repository.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/profile/data/me_repository.dart';
import 'package:member_app/features/profile/data/notification_prefs.dart';
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

  testWidgets('app boots and wires the router into the navigation shell',
      (WidgetTester tester) async {
    final prefs = await SharedPreferences.getInstance();

    final meetingsRepo = _MockMeetingsRepo();
    when(() => meetingsRepo.listMeetings()).thenAnswer((_) async => []);
    final docsRepo = _MockDocumentsRepo();
    when(() => docsRepo.listDocuments()).thenAnswer((_) async => []);
    final homeRepo = _MockHomeRepo();
    when(() => homeRepo.getBriefing()).thenAnswer(
      (_) async => Briefing.fromJson({'greeting': 'Good morning'}),
    );
    final meRepo = _MockMeRepo();
    when(() => meRepo.listActionItems()).thenAnswer((_) async => []);
    when(() => meRepo.listReminders()).thenAnswer((_) async => []);

    await tester.pumpWidget(ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(_AuthedController.new),
        meetingsRepositoryProvider.overrideWithValue(meetingsRepo),
        documentsRepositoryProvider.overrideWithValue(docsRepo),
        homeRepositoryProvider.overrideWithValue(homeRepo),
        meRepositoryProvider.overrideWithValue(meRepo),
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
      child: const MemberApp(),
    ));
    await tester.pump();

    // The raised Home centre is the fixed anchor of the nav shell.
    expect(find.byKey(const Key('home-center')), findsOneWidget);
  });
}
