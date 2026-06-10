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

/// Replays one script per call (last script repeats), recording each message —
/// lets a test fail the first send and succeed the retry.
class _SequenceClient implements MartinChatClient {
  _SequenceClient(this.scripts);
  final List<List<ChatEvent>> scripts;
  final messages = <String>[];

  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) {
    final i = messages.length.clamp(0, scripts.length - 1);
    messages.add(message);
    return Stream.fromIterable(scripts[i]);
  }
}

ProviderContainer _container(
  MartinChatClient client, {
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

  test('StartEvent sets the conversationId so multi-turn memory survives',
      () async {
    final client = _FakeClient(const [
      StartEvent(conversationId: 'conv-start'),
      TokenEvent('hi'),
      DoneEvent(),
    ]);
    final container = _container(client);
    final notifier = container.read(chatControllerProvider.notifier);

    await notifier.send('one');
    expect(container.read(chatControllerProvider).conversationId, 'conv-start');

    await notifier.send('two');
    expect(client.lastConversationId, 'conv-start');
  });

  test('error removes the empty Martin draft from the transcript', () async {
    final client = _FakeClient(const [ErrorEvent('boom')]);
    final container = _container(client);

    await container.read(chatControllerProvider.notifier).send('Hi');
    final state = container.read(chatControllerProvider);
    // Only the user's turn remains — no stranded empty bubble.
    expect(state.messages, hasLength(1));
    expect(state.messages.single.role, ChatRole.user);
    expect(state.error, 'boom');
  });

  test('a partial draft survives an error and is marked interrupted',
      () async {
    final client = _FakeClient(const [
      TokenEvent('partial answer'),
      ErrorEvent('lost connection'),
    ]);
    final container = _container(client);

    await container.read(chatControllerProvider.notifier).send('Hi');
    final state = container.read(chatControllerProvider);
    expect(state.messages, hasLength(2));
    expect(state.messages.last.role, ChatRole.martin);
    expect(state.messages.last.text, 'partial answer');
    expect(state.messages.last.interrupted, isTrue);
    expect(state.error, 'lost connection');
  });

  test('retry() re-sends the last user message without duplicating the turn',
      () async {
    final client = _SequenceClient([
      const [ErrorEvent('boom')],
      const [TokenEvent('Recovered'), DoneEvent()],
    ]);
    final container = _container(client);
    final notifier = container.read(chatControllerProvider.notifier);

    await notifier.send('Brief me');
    expect(container.read(chatControllerProvider).error, 'boom');

    await notifier.retry();
    final state = container.read(chatControllerProvider);
    expect(state.error, isNull);
    expect(client.messages, ['Brief me', 'Brief me']);
    // The user's turn renders once, followed by the recovered reply.
    expect(state.messages, hasLength(2));
    expect(state.messages.first.role, ChatRole.user);
    expect(state.messages.first.text, 'Brief me');
    expect(state.messages.last.role, ChatRole.martin);
    expect(state.messages.last.text, 'Recovered');
  });

  test('retry() without a prior send is a no-op', () async {
    final client = _FakeClient(const [TokenEvent('x'), DoneEvent()]);
    final container = _container(client);

    await container.read(chatControllerProvider.notifier).retry();
    expect(container.read(chatControllerProvider).messages, isEmpty);
    expect(client.lastMessage, isNull);
  });

  test('send(overrideTwgId:) uses the override instead of the first TWG',
      () async {
    final fakeClient = _FakeClient(const [
      FinalEvent('ok', conversationId: 'conv-2'),
      DoneEvent(),
    ]);
    // Authed user is in TWG 'first-twg'; the override must win.
    final container = _container(fakeClient,
        twgs: const [Twg(id: 'first-twg', name: 'First TWG')]);
    final controller = container.read(chatControllerProvider.notifier);

    await controller.send('hi', overrideTwgId: 'other-twg');
    expect(fakeClient.lastTwgId, 'other-twg');
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
