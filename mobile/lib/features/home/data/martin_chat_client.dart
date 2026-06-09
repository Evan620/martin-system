// lib/features/home/data/martin_chat_client.dart
//
// Streaming chat client for the member-scoped Martin agent (Part 4b).
//
// POSTs to `/agents/chat/stream` with `ResponseType.stream` and parses the
// server-sent-events byte stream into a `Stream<ChatEvent>`. The SSE framing
// (`data: {...}\n\n`) is decoded incrementally with a line buffer that is
// robust to chunk boundaries splitting a line mid-frame.
//
// The byte→event transform lives in the top-level `decodeSseByteStream` so it
// can be unit-tested by feeding a fake `Stream<List<int>>` without any Dio.

import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import 'chat_models.dart';

class MartinChatClient {
  // ignore: prefer_initializing_formals — keep `dio` as the public named param.
  MartinChatClient({required Dio dio}) : _dio = dio;
  final Dio _dio;

  /// Streams Martin's reply for [message]. [twgId] scopes the member agent to
  /// the caller's TWG; [conversationId] continues an existing thread.
  ///
  /// Emits [TokenEvent]/[ToolEvent]/[FinalEvent]/[DoneEvent] as they arrive and
  /// a single [ErrorEvent] on any transport/parse failure.
  Stream<ChatEvent> send({
    required String message,
    required String twgId,
    String? conversationId,
  }) async* {
    final Stream<List<int>> bytes;
    try {
      final res = await _dio.post<ResponseBody>(
        '/agents/chat/stream',
        data: {
          'message': message,
          'twg_id': twgId,
          'conversation_id': ?conversationId,
        },
        options: Options(responseType: ResponseType.stream),
      );
      final body = res.data;
      if (body == null) {
        yield const ErrorEvent('No response from Martin.');
        return;
      }
      bytes = body.stream;
    } on DioException {
      yield const ErrorEvent('Could not reach Martin. Please try again.');
      return;
    } catch (_) {
      yield const ErrorEvent('Something went wrong talking to Martin.');
      return;
    }

    yield* decodeSseByteStream(bytes);
  }
}

/// Decodes a raw SSE byte stream into a `Stream<ChatEvent>`.
///
/// Buffers across chunks, splits on `\n`, strips the leading `data:` prefix,
/// and routes each payload through [parseSseData]. Partial trailing lines are
/// held back until the next chunk completes them; a final flush handles a last
/// line that arrives without a trailing newline. Any error in the byte stream
/// is surfaced as a single trailing [ErrorEvent].
Stream<ChatEvent> decodeSseByteStream(Stream<List<int>> bytes) async* {
  var buffer = '';

  Iterable<ChatEvent> emitLine(String rawLine) sync* {
    var line = rawLine;
    // SSE keep-alive comments begin with ':'.
    if (line.startsWith(':')) return;
    if (line.startsWith('data:')) {
      line = line.substring('data:'.length);
    }
    final payload = line.trim();
    if (payload.isEmpty) return;
    final event = parseSseData(payload);
    if (event != null) yield event;
  }

  try {
    await for (final chunk in bytes) {
      buffer += utf8.decode(chunk, allowMalformed: true);
      var newline = buffer.indexOf('\n');
      while (newline != -1) {
        final line = buffer.substring(0, newline);
        buffer = buffer.substring(newline + 1);
        yield* Stream<ChatEvent>.fromIterable(emitLine(line));
        newline = buffer.indexOf('\n');
      }
    }
    // Flush any trailing line that lacked a final newline.
    if (buffer.trim().isNotEmpty) {
      yield* Stream<ChatEvent>.fromIterable(emitLine(buffer));
    }
  } catch (_) {
    yield const ErrorEvent('Lost connection to Martin.');
  }
}
