// test/features/meetings/meeting_detail_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/presentation/meeting_detail_screen.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

class _MeController extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(
      AppUser(id: 'me', email: 'me@x.org', fullName: 'Me', role: UserRole.twgMember, twgs: []));
}

void main() {
  testWidgets('renders meeting detail title', (tester) async {
    final repo = _MockRepo();
    when(() => repo.meetingDetail('m1')).thenAnswer((_) async => Meeting.fromJson({
          'id': 'm1', 'title': 'Steering Committee',
          'scheduled_at': '2031-06-10T10:00:00Z', 'status': 'SCHEDULED', 'meeting_type': 'virtual',
          'participants': const [],
        }));
    when(() => repo.meetingAgenda(any())).thenAnswer((_) async => null);
    when(() => repo.meetingMinutes(any())).thenAnswer((_) async => null);
    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MeetingDetailScreen(meetingId: 'm1')),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Steering Committee'), findsOneWidget);
  });

  testWidgets('detail shows title, the Agenda tab, and pinned RSVP', (tester) async {
    final repo = _MockRepo();
    when(() => repo.meetingDetail('m1')).thenAnswer((_) async => Meeting.fromJson({
      'id': 'm1', 'title': 'Steering Committee', 'scheduled_at': '2031-06-10T10:00:00Z',
      'status': 'SCHEDULED', 'meeting_type': 'virtual',
      'participants': [{'id': 'p', 'user_id': 'me', 'rsvp_status': 'PENDING'}],
    }));
    when(() => repo.meetingAgenda('m1')).thenAnswer((_) async => '1. Open\n2. Close');
    when(() => repo.meetingMinutes('m1')).thenAnswer((_) async => null);
    await tester.pumpWidget(ProviderScope(
      overrides: [
        meetingsRepositoryProvider.overrideWithValue(repo),
        // The viewer is the participant 'me', so the RSVP control renders.
        authControllerProvider.overrideWith(_MeController.new),
      ],
      child: const MaterialApp(home: MeetingDetailScreen(meetingId: 'm1')),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Steering Committee'), findsOneWidget);
    // Tabbed layout: Overview/Agenda/People/Docs tab labels are present.
    expect(find.text('Agenda'), findsOneWidget);
    expect(find.text('Overview'), findsOneWidget);
    expect(find.text('Going'), findsOneWidget); // pinned RSVP (participant)
  });
}
