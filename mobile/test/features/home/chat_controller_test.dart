// test/features/home/chat_controller_test.dart
//
// Tests for the member-scoped Martin chat controller (Task B3). A fake
// MartinChatClient returns a controlled Stream<ChatEvent>; we assert the
// controller folds those events into a growing Martin ChatMessage and toggles
// the streaming flag correctly, derives the twgId from the authed user, and
// surfaces errors gracefully when there is no TWG / the stream errors.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/application/chat_controller.dart';
import 'package:member_app/features/home/data/chat_models.dart';
import 'package:member_app/features/home/data/martin_chat_client.dart';

/// A fake client that replays a scripted list of events and records the args.
class _FakeClient implements MartinChatClient {
  _FakeClient(this.events);
  final List<ChatEvent> events;
  String? lastTwgId;
  String? lastMessage;
  String? lastConversationId;

  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) {
    lastMessage = message;
    lastTwgId = twgId;
    lastConversationId = conversationId;
    return Stream.fromIterable(events);
  }
}

class _AuthedController extends AuthController {
  _AuthedController(this._twgs);
  final List<Twg> _twgs;
  @override
  AuthState build() => AuthAuthenticated(AppUser(
        id: 'me',
        email: 'amina@x.org',
        fullName: 'Amina Diallo',
        role: UserRole.twgMember,
        twgs: _twgs,
      ));
}

ProviderContainer _container(
  _FakeClient client, {
  List<Twg> twgs = const [Twg(id: 't1', name: 'Energy TWG')],
}) {
  final container = ProviderContainer(overrides: [
    martinChatClientProvider.overrideWithValue(client),
    authControllerProvider.overrideWith(() => _AuthedController(twgs)),
  ]);
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('initial state is empty and not streaming', () {
    final container = _container(_FakeClient(const []));
    final state = container.read(chatControllerProvider);
    expect(state.messages, isEmpty);
    expect(state.streaming, isFalse);
    expect(state.conversationId, isNull);
    expect(state.error, isNull);
  });

  test('send assembles Martin message from tokens + final, toggles streaming',
      () async {
    final client = _FakeClient(const [
      TokenEvent('Hel'),
      TokenEvent('lo '),
      TokenEvent('there'),
      FinalEvent('Hello there', conversationId: 'conv-1'),
      DoneEvent(),
    ]);
    final container = _container(client);

    await container.read(chatControllerProvider.notifier).send('Hi Martin');

    final state = container.read(chatControllerProvider);
    expect(state.streaming, isFalse);
    expect(state.error, isNull);
    expect(state.conversationId, 'conv-1');
    expect(state.messages, hasLength(2));
    expect(state.messages.first.role, ChatRole.user);
    expect(state.messages.first.text, 'Hi Martin');
    expect(state.messages.last.role, ChatRole.martin);
    expect(state.messages.last.text, 'Hello there');

    // twgId derived from the authed user's first TWG.
    expect(client.lastTwgId, 't1');
    expect(client.lastMessage, 'Hi Martin');
  });

  test('streaming flag is true while events are in flight', () async {
    final controller = StreamController<ChatEvent>();
    final client = _StreamingClient(controller.stream);
    final container = ProviderContainer(overrides: [
      martinChatClientProvider.overrideWithValue(client),
      authControllerProvider.overrideWith(() => _AuthedController(
            const [Twg(id: 't1', name: 'Energy TWG')],
          )),
    ]);
    addTearDown(container.dispose);

    final future = container.read(chatControllerProvider.notifier).send('Hi');

    // Push a token, then let the microtasks settle.
    controller.add(const TokenEvent('Hi'));
    await Future<void>.delayed(Duration.zero);
    expect(container.read(chatControllerProvider).streaming, isTrue);
    expect(container.read(chatControllerProvider).messages.last.text, 'Hi');

    await controller.close();
    await future;
    expect(container.read(chatControllerProvider).streaming, isFalse);
  });

  test('tool event sets toolActivity on the draft', () async {
    final client = _FakeClient(const [
      ToolEvent('✦ get_schedule…'),
      TokenEvent('Your next meeting is…'),
      DoneEvent(),
    ]);
    final container = _container(client);

    await container.read(chatControllerProvider.notifier).send('What is next?');
    final martin = container.read(chatControllerProvider).messages.last;
    // Tool activity is cleared once content streams / stream finishes.
    expect(martin.text, 'Your next meeting is…');
    expect(container.read(chatControllerProvider).streaming, isFalse);
  });

  test('ErrorEvent sets a graceful error and stops streaming', () async {
    final client = _FakeClient(const [
      ErrorEvent('Could not reach Martin. Please try again.'),
    ]);
    final container = _container(client);

    await container.read(chatControllerProvider.notifier).send('Hi');
    final state = container.read(chatControllerProvider);
    expect(state.streaming, isFalse);
    expect(state.error, 'Could not reach Martin. Please try again.');
  });

  test('no TWG → graceful error, client never called', () async {
    final client = _FakeClient(const [TokenEvent('nope')]);
    final container = _container(client, twgs: const []);

    await container.read(chatControllerProvider.notifier).send('Hi');
    final state = container.read(chatControllerProvider);
    expect(state.streaming, isFalse);
    expect(state.error, isNotNull);
    expect(client.lastTwgId, isNull); // never reached the client
  });

  test('conversationId is reused on the next turn', () async {
    final client = _FakeClient(const [
      FinalEvent('first', conversationId: 'conv-9'),
      DoneEvent(),
    ]);
    final container = _container(client);
    final notifier = container.read(chatControllerProvider.notifier);

    await notifier.send('one');
    expect(container.read(chatControllerProvider).conversationId, 'conv-9');

    await notifier.send('two');
    expect(client.lastConversationId, 'conv-9');
  });
}

/// Client backed by a live StreamController so a test can observe mid-stream
/// state.
class _StreamingClient implements MartinChatClient {
  _StreamingClient(this._stream);
  final Stream<ChatEvent> _stream;
  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) =>
      _stream;
}
