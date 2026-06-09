// test/features/profile/me_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/profile/data/me_models.dart';
import 'package:member_app/features/profile/data/me_repository.dart';
import 'package:member_app/features/profile/data/notification_prefs.dart';
import 'package:member_app/features/profile/presentation/me_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _MockRepo extends Mock implements MeRepository {}

class _AuthedController extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(AppUser(
        id: 'me',
        email: 'amina@x.org',
        fullName: 'Amina Diallo',
        role: UserRole.twgMember,
        twgs: [Twg(id: 't1', name: 'Energy TWG')],
      ));
}

void main() {
  setUpAll(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('shows my action item + reminder; tapping checkbox calls markDone',
      (tester) async {
    final prefs = await SharedPreferences.getInstance();
    final repo = _MockRepo();
    when(() => repo.listActionItems()).thenAnswer((_) async => [
          ActionItem.fromJson(
              {'id': '1', 'description': 'Send budget input', 'status': 'PENDING'}),
        ]);
    when(() => repo.listReminders()).thenAnswer((_) async => [
          Reminder.fromJson({
            'id': 'r1',
            'message': 'Call the secretariat',
            'remind_at': '2031-06-10T14:00:00Z',
          }),
        ]);
    when(() => repo.markDone('1')).thenAnswer((_) async {});

    await tester.pumpWidget(ProviderScope(
      overrides: [
        meRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
      child: const MaterialApp(home: MeScreen()),
    ));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Amina Diallo'), findsOneWidget);
    expect(find.text('Send budget input'), findsOneWidget);
    expect(find.text('Call the secretariat'), findsOneWidget);

    await tester.tap(find.text('Send budget input'));
    await tester.pump(const Duration(milliseconds: 50));
    verify(() => repo.markDone('1')).called(1);
  });
}
