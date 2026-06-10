// test/features/home/martin_chat_client_test.dart
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/home/data/chat_models.dart';
import 'package:member_app/features/home/data/martin_chat_client.dart';

class _MockDio extends Mock implements Dio {}

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
}
