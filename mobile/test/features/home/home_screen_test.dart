// test/features/home/home_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/application/home_controller.dart';
import 'package:member_app/features/home/data/briefing_models.dart';
import 'package:member_app/features/home/data/home_repository.dart';
import 'package:member_app/features/home/presentation/home_screen.dart';

class _MockRepo extends Mock implements HomeRepository {}

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

Briefing _briefing() => Briefing.fromJson({
      'greeting': 'Good morning',
      'upcoming_meetings': [
        {
          'title': 'TWG Energy Sync',
          'twg_name': 'Energy',
          'starts_at': '2031-06-10T14:00:00Z',
          'minutes_until': 120,
        },
      ],
      'overdue_items': [
        {'title': 'Send notes', 'days_overdue': 2},
      ],
    });

void main() {
  testWidgets('renders greeting (with first name) + next meeting title',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));

    // Gold WAIIS eyebrow.
    expect(find.text('WAIIS'), findsOneWidget);
    // Greeting uses briefing.greeting + the member's first name.
    expect(find.textContaining('Good morning'), findsOneWidget);
    expect(find.textContaining('Amina'), findsOneWidget);
    // Martin briefing card shows the next meeting title (in a RichText span).
    expect(
      find.textContaining('TWG Energy Sync', findRichText: true),
      findsOneWidget,
    );
    // "N action items due" derived from overdueCount.
    expect(find.textContaining('1 action item'), findsOneWidget);
  });

  testWidgets('Ask Martin bar shows a coming-soon SnackBar (no /home/chat yet)',
      (tester) async {
    final repo = _MockRepo();
    when(() => repo.getBriefing()).thenAnswer((_) async => _briefing());

    await tester.pumpWidget(ProviderScope(
      overrides: [
        homeRepositoryProvider.overrideWithValue(repo),
        authControllerProvider.overrideWith(_AuthedController.new),
      ],
      child: const MaterialApp(home: HomeScreen()),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await tester.tap(find.text('Ask Martin…'));
    await tester.pump();
    expect(find.text('Martin chat is coming.'), findsOneWidget);
  });
}
