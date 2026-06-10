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

/// Runs raw SSE frame payloads through the real parser so the dialect tests
/// exercise the full parse→fold pipeline, not hand-built events.
List<ChatEvent> _parseFrames(List<String> frames) =>
    frames.map(parseSseData).whereType<ChatEvent>().toList();

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
    final state = container.read(chatControllerProvider(null));
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

    await container.read(chatControllerProvider(null).notifier).send('Hi Martin');

    final state = container.read(chatControllerProvider(null));
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

    final future = container.read(chatControllerProvider(null).notifier).send('Hi');

    // Push a token, then let the microtasks settle.
    controller.add(const TokenEvent('Hi'));
    await Future<void>.delayed(Duration.zero);
    expect(container.read(chatControllerProvider(null)).streaming, isTrue);
    expect(container.read(chatControllerProvider(null)).messages.last.text, 'Hi');

    await controller.close();
    await future;
    expect(container.read(chatControllerProvider(null)).streaming, isFalse);
  });

  test('tool event sets toolActivity on the draft', () async {
    final client = _FakeClient(const [
      ToolEvent('✦ get_schedule…'),
      TokenEvent('Your next meeting is…'),
      DoneEvent(),
    ]);
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('What is next?');
    final martin = container.read(chatControllerProvider(null)).messages.last;
    // Tool activity is cleared once content streams / stream finishes.
    expect(martin.text, 'Your next meeting is…');
    expect(container.read(chatControllerProvider(null)).streaming, isFalse);
  });

  test('ErrorEvent sets a graceful error and stops streaming', () async {
    final client = _FakeClient(const [
      ErrorEvent('Could not reach Martin. Please try again.'),
    ]);
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Hi');
    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    expect(state.error, 'Could not reach Martin. Please try again.');
  });

  test('no TWG → graceful error, client never called', () async {
    final client = _FakeClient(const [TokenEvent('nope')]);
    final container = _container(client, twgs: const []);

    await container.read(chatControllerProvider(null).notifier).send('Hi');
    final state = container.read(chatControllerProvider(null));
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
    final notifier = container.read(chatControllerProvider(null).notifier);

    await notifier.send('one');
    expect(container.read(chatControllerProvider(null)).conversationId, 'conv-9');

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
    final notifier = container.read(chatControllerProvider(null).notifier);

    await notifier.send('one');
    expect(container.read(chatControllerProvider(null)).conversationId, 'conv-start');

    await notifier.send('two');
    expect(client.lastConversationId, 'conv-start');
  });

  test('error removes the empty Martin draft from the transcript', () async {
    final client = _FakeClient(const [ErrorEvent('boom')]);
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Hi');
    final state = container.read(chatControllerProvider(null));
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

    await container.read(chatControllerProvider(null).notifier).send('Hi');
    final state = container.read(chatControllerProvider(null));
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
    final notifier = container.read(chatControllerProvider(null).notifier);

    await notifier.send('Brief me');
    expect(container.read(chatControllerProvider(null)).error, 'boom');

    await notifier.retry();
    final state = container.read(chatControllerProvider(null));
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

    await container.read(chatControllerProvider(null).notifier).retry();
    expect(container.read(chatControllerProvider(null)).messages, isEmpty);
    expect(client.lastMessage, isNull);
  });

  // ---------------------------------------------------------------------
  // Backend-dialect end-to-end scenarios: raw SSE frame payloads are pushed
  // through the real parser (parseSseData) and the resulting events through
  // the controller, proving the user gets the reply text whichever dialect
  // the server speaks.
  // ---------------------------------------------------------------------

  test(
      'prod dialect (command path): answer arrives only in the terminal '
      "'response' frame and becomes the Martin reply", () async {
    // Old prod for `/search …`: no token events at all — the only carrier of
    // the answer text is the terminal {'type':'response'} fallback frame.
    final client = _FakeClient(_parseFrames([
      '{"type":"start","conversation_id":"conv-prod"}',
      '{"type":"parsing","result":{"message_type":"command"}}',
      '{"type":"command_detected","command":"/search"}',
      '{"type":"tool_start","tool":"search_documents","status":"running"}',
      '{"type":"tool_complete","status":"ok","step_id":"s1"}',
      '{"type":"response","message":{"content":"Here are the search results.","conversation_id":"conv-prod"}}',
      '{"type":"done"}',
    ]));
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('/search PCB');

    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    expect(state.error, isNull);
    expect(state.conversationId, 'conv-prod');
    expect(state.messages, hasLength(2));
    expect(state.messages.last.role, ChatRole.martin);
    expect(state.messages.last.text, 'Here are the search results.');
    expect(state.messages.last.interrupted, isFalse);
  });

  test(
      'branch dialect (member natural path): tokens carry the answer; the '
      "empty terminal 'response' frame never wipes it", () async {
    // Branch member path: thinking ×2, token*, tool_complete, then the
    // terminal response frame whose content is ALWAYS '' on the natural path,
    // and a bare done. The streamed tokens must survive as the reply.
    final client = _FakeClient(_parseFrames([
      '{"type":"start","conversation_id":"conv-branch"}',
      '{"type":"parsing","result":{"message_type":"natural"}}',
      '{"type":"thinking","status":"Reading your TWG context","step_id":"t1"}',
      '{"type":"thinking","status":"Drafting a reply","step_id":"t2"}',
      '{"type":"token","content":"The Bagré "}',
      '{"type":"token","content":"deal is on track."}',
      '{"type":"tool_complete","status":"ok","step_id":"t2"}',
      '{"type":"response","message":{"content":""}}',
      '{"type":"done"}',
    ]));
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Brief me');

    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    expect(state.error, isNull);
    expect(state.conversationId, 'conv-branch');
    expect(state.messages.last.role, ChatRole.martin);
    expect(state.messages.last.text, 'The Bagré deal is on track.');
    expect(state.messages.last.toolActivity, isNull);
    expect(state.messages.last.interrupted, isFalse);
  });

  test(
      'silent stream (zero tokens, empty response, bare done) → graceful '
      'error instead of a blank bubble', () async {
    // Prod swallowing the answer ("Access denied: TWG not found." etc.):
    // tool_complete + response('') + done with no token and no error frame.
    final client = _FakeClient(_parseFrames([
      '{"type":"start","conversation_id":"conv-silent"}',
      '{"type":"parsing","result":{"message_type":"natural"}}',
      '{"type":"tool_complete","status":"ok","step_id":"s1"}',
      '{"type":"response","message":{"content":""}}',
      '{"type":"done"}',
    ]));
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Hello?');

    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    // No stranded empty Martin bubble — just the user's turn…
    expect(state.messages, hasLength(1));
    expect(state.messages.single.role, ChatRole.user);
    // …and a graceful, user-facing error (rendered as the error bubble).
    expect(state.error, isNotNull);
    expect(state.error, isNotEmpty);
  });

  test('silent EOF with no done frame also surfaces the graceful error',
      () async {
    final client = _FakeClient(_parseFrames([
      '{"type":"start","conversation_id":"c"}',
    ]));
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Hi');

    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    expect(state.messages, hasLength(1));
    expect(state.error, isNotNull);
  });

  test('streamed text with no Final is finalized on EOF, never discarded',
      () async {
    // Stream dies after tokens without final/response/done — the partial
    // text must still be committed as the reply.
    final client = _FakeClient(_parseFrames([
      '{"type":"token","content":"Partial but "}',
      '{"type":"token","content":"useful answer"}',
    ]));
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Hi');

    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    expect(state.error, isNull);
    expect(state.messages.last.text, 'Partial but useful answer');
  });

  test('backend error frame → ErrorEvent surfaces its message to the user',
      () async {
    final client = _FakeClient(_parseFrames([
      '{"type":"start","conversation_id":"c"}',
      '{"type":"error","error":"HTTPException","message":"Access denied: TWG not found."}',
    ]));
    final container = _container(client);

    await container.read(chatControllerProvider(null).notifier).send('Hi');

    final state = container.read(chatControllerProvider(null));
    expect(state.streaming, isFalse);
    expect(state.error, 'Access denied: TWG not found.');
    // The empty draft was removed — only the user's turn remains.
    expect(state.messages, hasLength(1));
    expect(state.messages.single.role, ChatRole.user);
  });

  test('a TWG-scoped controller uses its scope instead of the first TWG',
      () async {
    final fakeClient = _FakeClient(const [
      FinalEvent('ok', conversationId: 'conv-2'),
      DoneEvent(),
    ]);
    // Authed user is in TWG 'first-twg'; the family scope must win.
    final container = _container(fakeClient,
        twgs: const [Twg(id: 'first-twg', name: 'First TWG')]);
    final controller = container.read(chatControllerProvider('other-twg').notifier);

    await controller.send('hi');
    expect(fakeClient.lastTwgId, 'other-twg');
  });

  test(
      'REGRESSION: scopes are isolated — a TWG-scoped chat never continues '
      'the unscoped thread (no conversation_id leak, no shared transcript)',
      () async {
    // (1) Member chats via the FAB (unscoped): the backend starts thread C1.
    // (2) Member opens "Ask Martin about <other TWG>" (/martin?twg=twg-b).
    // The second send must POST {twg_id: twg-b} WITHOUT conversation_id C1,
    // and the scoped transcript must not show the unscoped chat's turns.
    final client = _FakeClient(const [
      StartEvent(conversationId: 'C1'),
      TokenEvent('first reply'),
      DoneEvent(),
    ]);
    final container = _container(client);

    // FAB chat (unscoped → falls back to the member's first TWG, t1).
    await container.read(chatControllerProvider(null).notifier).send('fab chat');
    expect(client.lastTwgId, 't1');
    expect(client.lastConversationId, isNull);
    expect(container.read(chatControllerProvider(null)).conversationId, 'C1');

    // Workspace chat scoped to a DIFFERENT TWG.
    await container
        .read(chatControllerProvider('twg-b').notifier)
        .send('about twg b');

    // The scoped send targets twg-b and carries NO conversation_id from the
    // unscoped thread — it starts its own thread.
    expect(client.lastTwgId, 'twg-b');
    expect(client.lastConversationId, isNull);

    // The scoped transcript holds only its own turns; the FAB chat's turns
    // never bleed in (and vice versa).
    final scoped = container.read(chatControllerProvider('twg-b'));
    expect(scoped.messages.map((m) => m.text), isNot(contains('fab chat')));
    expect(scoped.messages.first.text, 'about twg b');
    final unscoped = container.read(chatControllerProvider(null));
    expect(
        unscoped.messages.map((m) => m.text), isNot(contains('about twg b')));
    expect(unscoped.messages.first.text, 'fab chat');
    // Each scope tracks its own thread id.
    expect(scoped.conversationId, 'C1'); // its OWN start frame (fake replays)
    expect(unscoped.conversationId, 'C1');
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
