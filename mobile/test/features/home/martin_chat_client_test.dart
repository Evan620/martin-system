// test/features/home/martin_chat_client_test.dart
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/auth/application/auth_controller.dart';
import 'package:member_app/features/auth/data/auth_models.dart';
import 'package:member_app/features/home/application/chat_controller.dart';
import 'package:member_app/features/home/data/chat_models.dart';
import 'package:member_app/features/home/data/martin_chat_client.dart';

class _MockDio extends Mock implements Dio {}

/// Reads a captured-from-the-real-backend SSE fixture as raw bytes and chops
/// it into [chunkSize]-byte chunks, simulating TCP delivery that splits frames
/// (and even multi-byte UTF-8 chars) at arbitrary boundaries.
Stream<List<int>> _fixtureByteStream(String path, {int chunkSize = 7}) {
  final bytes = File(path).readAsBytesSync();
  final chunks = <List<int>>[];
  for (var i = 0; i < bytes.length; i += chunkSize) {
    chunks.add(bytes.sublist(
        i, i + chunkSize > bytes.length ? bytes.length : i + chunkSize));
  }
  return Stream<List<int>>.fromIterable(chunks);
}

/// Replays a pre-decoded event list so the real [ChatController] can be driven
/// by events that came out of the REAL captured bytes.
class _ReplayClient implements MartinChatClient {
  _ReplayClient(this.events);
  final List<ChatEvent> events;

  @override
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) =>
      Stream.fromIterable(events);
}

class _AuthedController extends AuthController {
  @override
  AuthState build() => AuthAuthenticated(AppUser(
        id: 'me',
        email: 'demo@ecowas.int',
        fullName: 'Amina Diallo',
        role: UserRole.twgMember,
        twgs: const [
          Twg(id: '4a03ff0a-c6a2-4602-9e86-cb4212c0a0e2', name: 'Energy TWG'),
        ],
      ));
}

ProviderContainer _replayContainer(List<ChatEvent> events) {
  final container = ProviderContainer(overrides: [
    martinChatClientProvider.overrideWithValue(_ReplayClient(events)),
    authControllerProvider.overrideWith(_AuthedController.new),
  ]);
  addTearDown(container.dispose);
  return container;
}

/// Encodes events as the `data: {...}\n\n` SSE frames the backend sends.
List<int> _frame(Map<String, dynamic> event) =>
    utf8.encode('data: ${jsonEncode(event)}\n\n');

void main() {
  setUpAll(() {
    registerFallbackValue(RequestOptions(path: '/'));
  });

  group('parseSseData', () {
    test('token → TokenEvent(content)', () {
      final e = parseSseData('{"type":"token","content":"Hel"}');
      expect(e, isA<TokenEvent>());
      expect((e as TokenEvent).text, 'Hel');
    });

    test('tool_call → ToolEvent with friendly label', () {
      final e = parseSseData('{"type":"tool_call","name":"get_schedule"}');
      expect(e, isA<ToolEvent>());
      expect((e as ToolEvent).label, '✦ get_schedule…');
    });

    test('tool_start → ToolEvent', () {
      final e = parseSseData('{"type":"tool_start","name":"search_documents"}');
      expect(e, isA<ToolEvent>());
      expect((e as ToolEvent).label, '✦ search_documents…');
    });

    test('final_response → FinalEvent(content, conversationId)', () {
      final e = parseSseData(
        '{"type":"final_response","content":"Hello there","conversation_id":"c1"}',
      );
      expect(e, isA<FinalEvent>());
      final f = e as FinalEvent;
      expect(f.text, 'Hello there');
      expect(f.conversationId, 'c1');
    });

    test('done → DoneEvent', () {
      expect(parseSseData('{"type":"done"}'), isA<DoneEvent>());
    });

    test('start → StartEvent carrying the conversation id', () {
      final e = parseSseData('{"type":"start","conversation_id":"c7"}');
      expect(e, isA<StartEvent>());
      expect((e as StartEvent).conversationId, 'c7');
      // A start frame without an id still parses (id stays null).
      final bare = parseSseData('{"type":"start"}');
      expect(bare, isA<StartEvent>());
      expect((bare as StartEvent).conversationId, isNull);
    });

    test("tool frames read the backend's 'tool' key as well as 'name'", () {
      final e = parseSseData('{"type":"tool_start","tool":"get_schedule"}');
      expect(e, isA<ToolEvent>());
      expect((e as ToolEvent).label, '✦ get_schedule…');
    });

    test("thinking with a status → ToolEvent chip label; without → null", () {
      final e = parseSseData(
          '{"type":"thinking","status":"Consulting the energy specialist"}');
      expect(e, isA<ToolEvent>());
      expect((e as ToolEvent).label, '✦ Consulting the energy specialist');
      expect(parseSseData('{"type":"thinking"}'), isNull);
      expect(parseSseData('{"type":"thinking","status":""}'), isNull);
    });

    test("response fallback frame → FinalEvent(message.content)", () {
      final e = parseSseData(
          '{"type":"response","message":{"content":"Full answer"}}');
      expect(e, isA<FinalEvent>());
      expect((e as FinalEvent).text, 'Full answer');
      // An empty/odd fallback frame stays ignored.
      expect(parseSseData('{"type":"response"}'), isNull);
      expect(parseSseData('{"type":"response","message":{}}'), isNull);
    });

    test("response frame carries the conversation_id into the FinalEvent", () {
      final e = parseSseData(
          '{"type":"response","message":{"content":"hi","conversation_id":"c3"}}');
      expect((e as FinalEvent).conversationId, 'c3');
      // Top-level conversation_id also works.
      final e2 = parseSseData(
          '{"type":"response","conversation_id":"c4","message":{"content":"hi"}}');
      expect((e2 as FinalEvent).conversationId, 'c4');
    });

    test("bare response frame with top-level content/response → FinalEvent",
        () {
      // Some backend dialects send the text at the top level instead of
      // nested under message — the parser must accept both.
      final e = parseSseData('{"type":"response","content":"Top answer"}');
      expect(e, isA<FinalEvent>());
      expect((e as FinalEvent).text, 'Top answer');

      final e2 = parseSseData('{"type":"response","response":"Alt answer"}');
      expect(e2, isA<FinalEvent>());
      expect((e2 as FinalEvent).text, 'Alt answer');
    });

    test("error frame → ErrorEvent (message preferred, error as fallback)",
        () {
      final e = parseSseData(
          '{"type":"error","error":"LLMError","message":"Model unavailable"}');
      expect(e, isA<ErrorEvent>());
      expect((e as ErrorEvent).message, 'Model unavailable');

      // Without a human message, fall back to the error field.
      final e2 = parseSseData('{"type":"error","error":"RBAC denied"}');
      expect((e2 as ErrorEvent).message, 'RBAC denied');

      // A bare error frame still surfaces a graceful generic message.
      final e3 = parseSseData('{"type":"error"}');
      expect(e3, isA<ErrorEvent>());
      expect((e3 as ErrorEvent).message, isNotEmpty);
    });

    test('parsing / interrupt / action_required are safely ignored', () {
      expect(
        parseSseData('{"type":"parsing","result":{"message_type":"natural"}}'),
        isNull,
      );
      expect(parseSseData('{"type":"interrupt","payload":{}}'), isNull);
      expect(
        parseSseData('{"type":"action_required","action_id":"a1"}'),
        isNull,
      );
      expect(parseSseData('{"type":"tool_complete","status":"ok"}'), isNull);
    });

    test('unknown / empty → null', () {
      expect(parseSseData('{"type":"who_knows"}'), isNull);
      expect(parseSseData('{"type":"token","content":""}'), isNull);
      expect(parseSseData(''), isNull);
      expect(parseSseData('   '), isNull);
    });

    test('malformed JSON → null (never throws)', () {
      expect(parseSseData('{not json'), isNull);
      expect(parseSseData('[1,2,3]'), isNull); // not a map
    });
  });

  group('decodeSseByteStream', () {
    test('emits token×N, final, done from well-formed frames', () async {
      final source = Stream<List<int>>.fromIterable([
        _frame({'type': 'start'}),
        _frame({'type': 'token', 'content': 'Hel'}),
        _frame({'type': 'token', 'content': 'lo'}),
        _frame({'type': 'final_response', 'content': 'Hello', 'conversation_id': 'c9'}),
        _frame({'type': 'done'}),
      ]);

      final events = await decodeSseByteStream(source).toList();

      expect(events.whereType<TokenEvent>().map((e) => e.text).toList(),
          ['Hel', 'lo']);
      final fin = events.whereType<FinalEvent>().single;
      expect(fin.text, 'Hello');
      expect(fin.conversationId, 'c9');
      expect(events.last, isA<DoneEvent>());
    });

    test('is robust to a frame split across two byte chunks', () async {
      final whole = _frame({'type': 'token', 'content': 'split-me'});
      final cut = whole.length ~/ 2;
      final source = Stream<List<int>>.fromIterable([
        whole.sublist(0, cut),
        whole.sublist(cut),
        _frame({'type': 'done'}),
      ]);

      final events = await decodeSseByteStream(source).toList();
      expect(events.whereType<TokenEvent>().single.text, 'split-me');
      expect(events.last, isA<DoneEvent>());
    });

    test('survives a multi-byte UTF-8 char split across two byte chunks',
        () async {
      // 'é' is 0xC3 0xA9 in UTF-8 — a 2-byte sequence. Cut a frame so the
      // split lands BETWEEN those two bytes. A per-chunk allowMalformed decode
      // would emit U+FFFD; a stateful chunked decoder reassembles 'é'.
      final whole = _frame({'type': 'token', 'content': 'Bagré'});
      // Byte index of 0xC3 (lead byte of 'é') in the encoded frame.
      final lead = whole.indexOf(0xC3);
      expect(lead, greaterThan(0));
      expect(whole[lead + 1], 0xA9); // confirm it really is the 'é' sequence
      final source = Stream<List<int>>.fromIterable([
        whole.sublist(0, lead + 1), // ends mid-char, on the 0xC3 lead byte
        whole.sublist(lead + 1), // starts with the 0xA9 trailing byte
        _frame({'type': 'done'}),
      ]);

      final events = await decodeSseByteStream(source).toList();
      expect(events.whereType<TokenEvent>().single.text, 'Bagré');
      expect(events.last, isA<DoneEvent>());
    });

    test('reassembles accented names split across many tiny chunks', () async {
      // One byte per chunk is the worst case for cross-chunk UTF-8 framing.
      final whole = <int>[
        ..._frame({'type': 'token', 'content': 'PAI-GDIZ à Bagré'}),
        ..._frame({'type': 'done'}),
      ];
      final source = Stream<List<int>>.fromIterable(
        whole.map((b) => <int>[b]),
      );
      final events = await decodeSseByteStream(source).toList();
      expect(events.whereType<TokenEvent>().single.text, 'PAI-GDIZ à Bagré');
      expect(events.last, isA<DoneEvent>());
    });

    test('handles two frames glued into one chunk', () async {
      final glued = <int>[
        ..._frame({'type': 'token', 'content': 'a'}),
        ..._frame({'type': 'token', 'content': 'b'}),
      ];
      final source = Stream<List<int>>.fromIterable([glued]);
      final events = await decodeSseByteStream(source).toList();
      expect(
        events.whereType<TokenEvent>().map((e) => e.text).toList(),
        ['a', 'b'],
      );
    });

    test('flushes a trailing line with no final newline', () async {
      final source = Stream<List<int>>.fromIterable([
        utf8.encode('data: {"type":"token","content":"tail"}'),
      ]);
      final events = await decodeSseByteStream(source).toList();
      expect(events.whereType<TokenEvent>().single.text, 'tail');
    });

    test('a stream error surfaces as a trailing ErrorEvent', () async {
      final source = Stream<List<int>>.multi((controller) {
        controller.add(_frame({'type': 'token', 'content': 'x'}));
        controller.addError(Exception('boom'));
      });
      final events = await decodeSseByteStream(source).toList();
      expect(events.whereType<TokenEvent>().single.text, 'x');
      expect(events.last, isA<ErrorEvent>());
    });
  });

  group('MartinChatClient.send', () {
    late _MockDio dio;
    late MartinChatClient client;

    setUp(() {
      dio = _MockDio();
      client = MartinChatClient(dio: dio);
    });

    Response<ResponseBody> streamResponse(Stream<Uint8List> stream) =>
        Response<ResponseBody>(
          data: ResponseBody(stream, 200),
          statusCode: 200,
          requestOptions: RequestOptions(path: '/agents/chat/stream'),
        );

    test('streams token×N, final, done from the SSE byte stream', () async {
      final byteStream = Stream<Uint8List>.fromIterable([
        Uint8List.fromList(_frame({'type': 'token', 'content': 'Hi '})),
        Uint8List.fromList(_frame({'type': 'token', 'content': 'there'})),
        Uint8List.fromList(_frame(
            {'type': 'final_response', 'content': 'Hi there', 'conversation_id': 'cv1'})),
        Uint8List.fromList(_frame({'type': 'done'})),
      ]);

      when(() => dio.post<ResponseBody>(
            '/agents/chat/stream',
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => streamResponse(byteStream));

      final events =
          await client.send(message: 'hello', twgId: 'twg-1').toList();

      expect(events.whereType<TokenEvent>().map((e) => e.text).toList(),
          ['Hi ', 'there']);
      expect(events.whereType<FinalEvent>().single.conversationId, 'cv1');
      expect(events.last, isA<DoneEvent>());

      final captured = verify(() => dio.post<ResponseBody>(
            '/agents/chat/stream',
            data: captureAny(named: 'data'),
            options: any(named: 'options'),
          )).captured.single as Map<String, dynamic>;
      expect(captured['message'], 'hello');
      expect(captured['twg_id'], 'twg-1');
      expect(captured.containsKey('conversation_id'), isFalse);
    });

    test('includes conversation_id when provided', () async {
      when(() => dio.post<ResponseBody>(
            '/agents/chat/stream',
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => streamResponse(
            Stream<Uint8List>.fromIterable(
                [Uint8List.fromList(_frame({'type': 'done'}))]),
          ));

      await client
          .send(message: 'm', twgId: 't', conversationId: 'cv-prev')
          .toList();

      final captured = verify(() => dio.post<ResponseBody>(
            '/agents/chat/stream',
            data: captureAny(named: 'data'),
            options: any(named: 'options'),
          )).captured.single as Map<String, dynamic>;
      expect(captured['conversation_id'], 'cv-prev');
    });

    test('emits ErrorEvent on DioException', () async {
      when(() => dio.post<ResponseBody>(
            '/agents/chat/stream',
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/agents/chat/stream'),
      ));

      final events =
          await client.send(message: 'hello', twgId: 'twg-1').toList();
      expect(events, hasLength(1));
      expect(events.single, isA<ErrorEvent>());
    });
  });

  // -------------------------------------------------------------------------
  // REAL-BACKEND fixtures (captured 2026-06-10 from the local backend at
  // http://localhost:8000, POST /api/v1/agents/chat/stream, authed as the
  // demo TWG member, twg_id=4a03ff0a-c6a2-4602-9e86-cb4212c0a0e2).
  //
  // The .txt files under fixtures/ are the byte-for-byte `data:` frames curl
  // captured off the wire — NOT hand-written JSON. They pin the two dialects
  // the real member path speaks today:
  //
  //  * real_stream_frames.txt — "Introduce yourself in one short sentence.":
  //    start → parsing → thinking×2 → token×22 → tool_complete →
  //    response(content:"") → done. The answer travels ONLY in the tokens;
  //    the terminal response frame is always empty on this path.
  //
  //  * real_stream_frames_silent.txt — "What is my next meeting?": the model
  //    makes a tool call, the backend swallows the reply (zero tokens), and
  //    the stream ends with the same empty response + done. The controller
  //    must surface a graceful error — never silence / a blank bubble.
  // -------------------------------------------------------------------------
  group('real backend SSE fixtures (e2e capture)', () {
    const tokensFixture = 'test/features/home/fixtures/real_stream_frames.txt';
    const silentFixture =
        'test/features/home/fixtures/real_stream_frames_silent.txt';

    // Exactly what the 22 real token frames concatenate to (note the real
    // U+2019 apostrophe and U+2014 em dash — they prove the UTF-8 path).
    const expectedReply = 'Hi, I’m Martin — your personal assistant '
        'for meetings, documents, action items, RSVPs, and reminders.';

    test('token-streaming capture decodes to start + tokens + done', () async {
      final events =
          await decodeSseByteStream(_fixtureByteStream(tokensFixture)).toList();

      // The start frame carries the real conversation id (multi-turn memory).
      final start = events.whereType<StartEvent>().single;
      expect(start.conversationId, '11825707-79c5-4572-8a44-2ab9d6df09a9');

      // The reply travels exclusively in the token frames.
      final tokens = events.whereType<TokenEvent>().map((e) => e.text).join();
      expect(tokens, expectedReply);

      // The backend's thinking frames surface as activity-chip ToolEvents.
      expect(
        events.whereType<ToolEvent>().map((e) => e.label).toList(),
        ['✦ Processing your request...', '✦ Starting Supervisor...'],
      );

      // The terminal response frame has content:"" on this path → no
      // FinalEvent may be emitted (it must never wipe the streamed tokens).
      expect(events.whereType<FinalEvent>(), isEmpty);
      expect(events.whereType<ErrorEvent>(), isEmpty);
      expect(events.last, isA<DoneEvent>());
    });

    test('controller shows the full reply from the REAL captured bytes',
        () async {
      final events =
          await decodeSseByteStream(_fixtureByteStream(tokensFixture)).toList();
      final container = _replayContainer(events);

      await container
          .read(chatControllerProvider(null).notifier)
          .send('Introduce yourself in one short sentence.');

      final state = container.read(chatControllerProvider(null));
      expect(state.streaming, isFalse);
      expect(state.error, isNull);
      expect(state.conversationId, '11825707-79c5-4572-8a44-2ab9d6df09a9');
      expect(state.messages, hasLength(2));
      expect(state.messages.last.role, ChatRole.martin);
      expect(state.messages.last.text, expectedReply);
      expect(state.messages.last.toolActivity, isNull);
      expect(state.messages.last.interrupted, isFalse);
    });

    test('silent capture (swallowed reply) → graceful error, never silence',
        () async {
      final events =
          await decodeSseByteStream(_fixtureByteStream(silentFixture)).toList();

      // The real silent stream: start + thinking×2 + done — zero tokens, no
      // FinalEvent (response content is ""), and crucially no ErrorEvent at
      // the transport level.
      expect(events.whereType<TokenEvent>(), isEmpty);
      expect(events.whereType<FinalEvent>(), isEmpty);
      expect(events.whereType<StartEvent>().single.conversationId,
          'c0e02f1e-bcd6-41b7-8b6d-5e2eb56c4f78');
      expect(events.last, isA<DoneEvent>());

      final container = _replayContainer(events);
      await container
          .read(chatControllerProvider(null).notifier)
          .send('What is my next meeting?');

      final state = container.read(chatControllerProvider(null));
      expect(state.streaming, isFalse);
      // Never silence: the user sees a graceful error, not a blank bubble.
      expect(state.error, isNotNull);
      expect(state.error, isNotEmpty);
      // No stranded empty Martin bubble — only the user's turn remains.
      expect(state.messages, hasLength(1));
      expect(state.messages.single.role, ChatRole.user);
    });
  });
}
