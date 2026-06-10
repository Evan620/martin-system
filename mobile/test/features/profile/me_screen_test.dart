// test/features/profile/me_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/core/ui/segmented.dart';
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

Future<Widget> _app(MeRepository repo) async {
  final prefs = await SharedPreferences.getInstance();
  return ProviderScope(
    overrides: [
      meRepositoryProvider.overrideWithValue(repo),
      authControllerProvider.overrideWith(_AuthedController.new),
      sharedPreferencesProvider.overrideWithValue(prefs),
    ],
    child: const MaterialApp(home: MeScreen()),
  );
}

_MockRepo _repo() {
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
  return repo;
}

void main() {
  setUpAll(() {
    SharedPreferences.setMockInitialValues({});
    registerFallbackValue(DateTime(2030));
  });

  testWidgets(
      'compact profile + stat tiles; Tasks segment marks done; Reminders segment lists reminders',
      (tester) async {
    final repo = _repo();
    await tester.pumpWidget(await _app(repo));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // Compact sans profile header: name + "role · TWG" meta.
    expect(find.text('Amina Diallo'), findsOneWidget);
    expect(find.text('Member · Energy TWG'), findsOneWidget);

    // Stat tiles: 1 open task, 1 reminder.
    expect(find.text('TASKS DUE'), findsOneWidget);
    expect(find.text('REMINDERS'), findsOneWidget);
    expect(find.text('1'), findsNWidgets(2));

    // Tasks is the default segment: the action item shows, reminders do not.
    expect(find.byType(SovereignSegmented), findsOneWidget);
    expect(find.text('Send budget input'), findsOneWidget);
    expect(find.text('Call the secretariat'), findsNothing);

    // Notifications + sign out stay.
    expect(find.text('Meeting updates'), findsOneWidget);
    expect(find.text('Sign out'), findsOneWidget);

    // Tapping an open task row marks it done via the existing wiring.
    await tester.tap(find.text('Send budget input'));
    await tester.pump(const Duration(milliseconds: 50));
    verify(() => repo.markDone('1')).called(1);

    // Switch to the Reminders segment: reminder rows + the yellow Add pill.
    await tester.tap(find.text('Reminders'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Call the secretariat'), findsOneWidget);
    expect(find.text('Add reminder'), findsOneWidget);
    expect(find.text('Send budget input'), findsNothing);
  });

  testWidgets('Add reminder opens the sheet and wires to addReminder',
      (tester) async {
    final repo = _repo();
    when(() => repo.addReminder(any(), any())).thenAnswer(
      (_) async => Reminder.fromJson({
        'id': 'r9',
        'message': 'Ping GIZ',
        'remind_at': '2031-06-12T09:00:00Z',
      }),
    );

    await tester.pumpWidget(await _app(repo));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 300)); // settle switcher

    await tester.tap(find.text('Reminders'));
    await tester.pumpAndSettle();

    // The yellow pill opens the Sovereign bottom sheet.
    await tester.tap(find.text('Add reminder'));
    await tester.pumpAndSettle();
    expect(find.text('New reminder'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'Ping GIZ');
    await tester.pump();

    // Pick date + time through the existing pickers.
    await tester.tap(find.text('Pick a date & time'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK')); // date picker
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK')); // time picker
    await tester.pumpAndSettle();

    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    verify(() => repo.addReminder('Ping GIZ', any())).called(1);
    // The controller appends the repo's reminder to the visible list.
    expect(find.text('Ping GIZ'), findsOneWidget);
  });
}
