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
  });

  final ChatRole role;
  String text;
  String? toolActivity;

  ChatMessage copyWith({String? text, String? toolActivity}) => ChatMessage(
        role: role,
        text: text ?? this.text,
        toolActivity: toolActivity ?? this.toolActivity,
      );
}

/// Wire-level events emitted by [parseSseData] / the SSE client.
sealed class ChatEvent {
  const ChatEvent();
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
    case 'token':
      final content = event['content']?.toString() ?? '';
      // Skip empty tokens so the UI never appends nothing.
      return content.isEmpty ? null : TokenEvent(content);
    case 'tool_call':
    case 'tool_start':
      return ToolEvent(toolLabel(event['name']?.toString()));
    case 'final_response':
      return FinalEvent(
        event['content']?.toString() ?? '',
        conversationId: event['conversation_id']?.toString(),
      );
    case 'done':
      return const DoneEvent();
    default:
      // start / thinking / unknown → ignore.
      return null;
  }
}
