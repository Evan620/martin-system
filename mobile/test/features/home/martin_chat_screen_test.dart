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
import 'package:gpt_markdown/gpt_markdown.dart';
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

/// Records the twgId each send carried, so a test can assert the screen's
/// `twgId` (the `?twg=` query param on /martin) reaches the client.
class _CapturingClient implements MartinChatClient {
  final twgIds = <String>[];
  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) {
    twgIds.add(twgId);
    return Stream.fromIterable(const [
      TokenEvent('Hello'),
      FinalEvent('Hello', conversationId: 'c1'),
      DoneEvent(),
    ]);
  }
}

/// Fails the first send with an ErrorEvent, then succeeds — exercises the
/// inline error bubble + Retry affordance.
class _FlakyClient implements MartinChatClient {
  final messages = <String>[];

  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) {
    messages.add(message);
    if (messages.length == 1) {
      return Stream.fromIterable(const [
        ErrorEvent('Could not reach Martin. Please try again.'),
      ]);
    }
    return Stream.fromIterable(const [
      TokenEvent('Recovered'),
      DoneEvent(),
    ]);
  }
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
/// context.pop / context.go has a navigator) with the given overrides. The
/// probe route mirrors the app's canonical full-screen `/martin` route.
Future<void> _pump(
  WidgetTester tester, {
  required MartinChatClient client,
  String? seed,
  String? twgId,
}) async {
  final router = GoRouter(
    initialLocation: '/martin',
    routes: [
      GoRoute(
        path: '/martin',
        builder: (_, _) => MartinChatScreen(seed: seed, twgId: twgId),
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

  testWidgets('twgId (the ?twg= scope) is passed through to client.send',
      (tester) async {
    final client = _CapturingClient();

    await _pump(tester, client: client, seed: 'Brief me', twgId: 't9');
    await tester.pumpAndSettle();

    // The workspace scope wins over the authed user's first TWG ('t1').
    expect(client.twgIds, ['t9']);
  });

  testWidgets("martin replies render as styled markdown, not literal sigils",
      (tester) async {
    final client = _FakeClient(const [
      TokenEvent('**bold** and\n- item'),
      DoneEvent(),
    ]);

    await _pump(tester, client: client, seed: 'Format please');
    await tester.pumpAndSettle();

    // Martin's bubble renders through the markdown widget…
    expect(find.byType(GptMarkdown), findsOneWidget);
    // …so the bold sigils never appear literally…
    expect(find.textContaining('**', findRichText: true), findsNothing);
    // …while the content itself does.
    expect(find.textContaining('bold', findRichText: true), findsWidgets);
    expect(find.textContaining('item', findRichText: true), findsWidgets);
    // The member's own turn stays plain text (gold bubble).
    expect(find.text('Format please'), findsOneWidget);
  });

  testWidgets('pulsing caret shows while text streams, gone when done',
      (tester) async {
    final controller = StreamController<ChatEvent>();
    final client = _LiveClient(controller.stream);

    await _pump(tester, client: client, seed: 'Hi');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 10));

    // Pre-first-token: typing dots, no caret yet.
    expect(find.byKey(const Key('martin-streaming-caret')), findsNothing);

    controller.add(const TokenEvent('Hel'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 10));
    expect(find.byKey(const Key('martin-streaming-caret')), findsOneWidget);

    controller.add(const DoneEvent());
    await controller.close();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('martin-streaming-caret')), findsNothing);
  });

  testWidgets('error shows an inline retry bubble; tap re-sends the message',
      (tester) async {
    final client = _FlakyClient();

    await _pump(tester, client: client, seed: 'Brief me');
    await tester.pumpAndSettle();

    // The failure lands in the transcript with a Retry affordance.
    expect(find.textContaining('Could not reach Martin'), findsOneWidget);
    final retry = find.byKey(const Key('martin-chat-retry'));
    expect(retry, findsOneWidget);

    await tester.tap(retry);
    await tester.pumpAndSettle();

    // The same message was re-sent and the reply streamed in.
    expect(client.messages, ['Brief me', 'Brief me']);
    expect(find.textContaining('Recovered', findRichText: true),
        findsOneWidget);
    expect(find.byKey(const Key('martin-chat-retry')), findsNothing);
    // The user's turn is not duplicated by the retry.
    expect(find.text('Brief me'), findsOneWidget);
  });

  group('isPinnedToBottom (smart-autoscroll guard)', () {
    test('pinned at the exact bottom', () {
      expect(isPinnedToBottom(pixels: 1000, maxScrollExtent: 1000), isTrue);
    });

    test('pinned within the 80px grace band', () {
      expect(isPinnedToBottom(pixels: 921, maxScrollExtent: 1000), isTrue);
      expect(isPinnedToBottom(pixels: 920, maxScrollExtent: 1000), isTrue);
    });

    test('NOT pinned once the reader scrolls past the band', () {
      expect(isPinnedToBottom(pixels: 919, maxScrollExtent: 1000), isFalse);
      expect(isPinnedToBottom(pixels: 0, maxScrollExtent: 1000), isFalse);
    });

    test('an unscrollable transcript is always pinned', () {
      expect(isPinnedToBottom(pixels: 0, maxScrollExtent: 0), isTrue);
    });

    test('threshold is tunable', () {
      expect(
        isPinnedToBottom(pixels: 880, maxScrollExtent: 1000, threshold: 120),
        isTrue,
      );
    });
  });

  testWidgets('no seed → empty state invitation, no auto-send', (tester) async {
    final client = _FakeClient(const [TokenEvent('should not appear')]);

    await _pump(tester, client: client);
    await tester.pumpAndSettle();

    expect(find.textContaining('Ask about your meetings'), findsOneWidget);
    expect(find.text('should not appear'), findsNothing);
  });
}
