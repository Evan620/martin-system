// lib/features/home/data/chat_models.dart
//
// Chat models for the member-scoped Martin chat (Part 4b).
//
// `ChatMessage` is what the UI renders (a user or Martin turn, with optional
// in-flight tool activity). `ChatEvent` is the wire-level vocabulary the SSE
// client emits as it parses `POST /agents/chat/stream` frames; the controller
// folds a stream of `ChatEvent`s into a growing Martin `ChatMessage`.
//
// `parseSseData` is a pure, top-level function so it can be unit-tested against
// raw event JSON without any Dio/stream plumbing. It maps one decoded SSE event
// map to a `ChatEvent` (or null for events we ignore, e.g. start/thinking).

import 'dart:convert';

/// Who authored a chat turn.
enum ChatRole { user, martin }

/// A single turn in the chat transcript.
///
/// While Martin is streaming, [text] grows token-by-token and [toolActivity]
/// holds a short "doing X…" label that the UI shows as a gold chip.
class ChatMessage {
  ChatMessage({
    required this.role,
    this.text = '',
    this.toolActivity,
    this.interrupted = false,
  });

  final ChatRole role;
  String text;
  String? toolActivity;

  /// True when a stream failed after partial text arrived — the UI renders a
  /// quiet "— interrupted" suffix under the partial answer.
  bool interrupted;

  ChatMessage copyWith({
    String? text,
    String? toolActivity,
    bool? interrupted,
  }) =>
      ChatMessage(
        role: role,
        text: text ?? this.text,
        toolActivity: toolActivity ?? this.toolActivity,
        interrupted: interrupted ?? this.interrupted,
      );
}

/// Wire-level events emitted by [parseSseData] / the SSE client.
sealed class ChatEvent {
  const ChatEvent();
}

/// The opening `start` frame. The member path's backend never emits
/// `final_response`, so this is the only frame that reliably carries the
/// `conversation_id` — parsing it is what keeps multi-turn memory alive.
class StartEvent extends ChatEvent {
  const StartEvent({this.conversationId});
  final String? conversationId;
}

/// A streamed content token (`token` events). [text] is the delta to append.
class TokenEvent extends ChatEvent {
  const TokenEvent(this.text);
  final String text;
}

/// A tool invocation (`tool_call` / `tool_start`). [label] is UI-friendly,
/// e.g. `✦ get_schedule…`.
class ToolEvent extends ChatEvent {
  const ToolEvent(this.label);
  final String label;
}

/// The completed assistant turn (`final_response`). [text] is the full answer;
/// [conversationId] (when present) lets the next turn continue the thread.
class FinalEvent extends ChatEvent {
  const FinalEvent(this.text, {this.conversationId});
  final String text;
  final String? conversationId;
}

/// Terminal "stream finished" marker (`done`).
class DoneEvent extends ChatEvent {
  const DoneEvent();
}

/// A transport/parse failure surfaced to the controller.
class ErrorEvent extends ChatEvent {
  const ErrorEvent(this.message);
  final String message;
}

/// Pretty label for a tool name shown while Martin works.
String toolLabel(String? name) {
  final n = (name ?? '').trim();
  return n.isEmpty ? '✦ Working…' : '✦ $n…';
}

/// Maps a single decoded SSE event map to a [ChatEvent].
///
/// Pure and side-effect free so it can be unit-tested directly. Accepts the raw
/// JSON string of one event's `data:` payload. Returns `null` for empty input,
/// undecodable JSON, or event types we intentionally ignore (`start`,
/// `thinking`, etc.) so the caller can simply skip nulls.
ChatEvent? parseSseData(String dataJson) {
  final trimmed = dataJson.trim();
  if (trimmed.isEmpty) return null;

  final Object? decoded;
  try {
    decoded = jsonDecode(trimmed);
  } on FormatException {
    return null;
  }
  if (decoded is! Map<String, dynamic>) return null;
  return parseSseEvent(decoded);
}

/// Maps an already-decoded SSE event map to a [ChatEvent] (or `null`).
ChatEvent? parseSseEvent(Map<String, dynamic> event) {
  final type = event['type']?.toString();
  switch (type) {
    case 'start':
      // Carries the conversation_id on the member path (which never emits
      // final_response) — required for multi-turn memory.
      return StartEvent(conversationId: event['conversation_id']?.toString());
    case 'token':
      final content = event['content']?.toString() ?? '';
      // Skip empty tokens so the UI never appends nothing.
      return content.isEmpty ? null : TokenEvent(content);
    case 'tool_call':
    case 'tool_start':
      // The backend payload keys are 'tool'/'status'; older frames used 'name'.
      return ToolEvent(
        toolLabel((event['tool'] ?? event['name'])?.toString()),
      );
    case 'thinking':
      // Surface the thinking status as the activity chip label so the chip
      // actually fires on the member path today.
      final status = event['status']?.toString().trim() ?? '';
      return status.isEmpty ? null : ToolEvent('✦ $status');
    case 'final_response':
      return FinalEvent(
        event['content']?.toString() ?? '',
        conversationId: event['conversation_id']?.toString(),
      );
    case 'response':
      // Terminal fallback frame ({'type':'response', message:{content}}) sent
      // when no final_response was emitted — without parsing it the Martin
      // bubble stays empty forever if token streaming ever fails upstream.
      final message = event['message'];
      final content =
          message is Map ? (message['content']?.toString() ?? '') : '';
      return content.isEmpty
          ? null
          : FinalEvent(
              content,
              conversationId: event['conversation_id']?.toString(),
            );
    case 'done':
      return const DoneEvent();
    default:
      // unknown → ignore.
      return null;
  }
}
