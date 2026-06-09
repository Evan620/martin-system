// test/features/home/martin_chat_screen_test.dart
//
// Widget test for the streaming Martin chat screen (Task B4). A fake
// MartinChatClient streams "Hello" as a token + a final/done; we pump the
// screen with a `seed` (so it auto-sends on first build) and assert a Martin
// glass bubble shows "Hello", and that the input bar disables while streaming.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/application/chat_controller.dart';
import 'package:member_app/features/home/data/chat_models.dart';
import 'package:member_app/features/home/data/martin_chat_client.dart';
import 'package:member_app/features/home/presentation/martin_chat_screen.dart';

/// Replays a scripted list of events for whatever message is sent.
class _FakeClient implements MartinChatClient {
  _FakeClient(this.events);
  final List<ChatEvent> events;

  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) =>
      Stream.fromIterable(events);
}

/// Backed by a live StreamController so a test can observe the mid-stream
/// (disabled input) state.
class _LiveClient implements MartinChatClient {
  _LiveClient(this.stream);
  final Stream<ChatEvent> stream;
  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) =>
      stream;
}

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

/// Pumps the chat screen inside a router (so the glass back button's
/// context.pop / context.go has a navigator) with the given overrides.
Future<void> _pump(
  WidgetTester tester, {
  required MartinChatClient client,
  String? seed,
}) async {
  final router = GoRouter(
    initialLocation: '/chat',
    routes: [
      GoRoute(
        path: '/chat',
        builder: (_, _) => MartinChatScreen(seed: seed),
      ),
    ],
  );

  await tester.pumpWidget(ProviderScope(
    overrides: [
      martinChatClientProvider.overrideWithValue(client),
      authControllerProvider.overrideWith(_AuthedController.new),
    ],
    child: MaterialApp.router(routerConfig: router),
  ));
}

void main() {
  testWidgets('seed auto-sends and a Martin bubble shows "Hello"',
      (tester) async {
    final client = _FakeClient(const [
      TokenEvent('Hello'),
      FinalEvent('Hello', conversationId: 'c1'),
      DoneEvent(),
    ]);

    await _pump(tester, client: client, seed: 'Hi Martin');
    await tester.pumpAndSettle();

    // The seeded user turn and the streamed Martin reply both render.
    expect(find.text('Hi Martin'), findsOneWidget);
    expect(find.text('Hello'), findsOneWidget);
    // Header is present.
    expect(find.text('✦ Martin'), findsOneWidget);
  });

  testWidgets('input bar is disabled while streaming, re-enabled when done',
      (tester) async {
    final controller = StreamController<ChatEvent>();
    final client = _LiveClient(controller.stream);

    await _pump(tester, client: client, seed: 'What is next?');
    // Let the post-frame auto-send fire and begin streaming.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 10));

    final field = tester.widget<TextField>(
      find.byKey(const Key('martin-chat-input')),
    );
    expect(field.enabled, isFalse);

    controller.add(const TokenEvent('Soon.'));
    controller.add(const DoneEvent());
    await controller.close();
    await tester.pumpAndSettle();

    final fieldAfter = tester.widget<TextField>(
      find.byKey(const Key('martin-chat-input')),
    );
    expect(fieldAfter.enabled, isTrue);
    expect(find.text('Soon.'), findsOneWidget);
  });

  testWidgets('no seed → empty state invitation, no auto-send', (tester) async {
    final client = _FakeClient(const [TokenEvent('should not appear')]);

    await _pump(tester, client: client);
    await tester.pumpAndSettle();

    expect(find.textContaining('Ask about your meetings'), findsOneWidget);
    expect(find.text('should not appear'), findsNothing);
  });
}
