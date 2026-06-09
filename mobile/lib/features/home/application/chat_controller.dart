// lib/features/home/application/chat_controller.dart
//
// Chat controller for the member-scoped Martin chat (Task B3).
//
// Folds the `Stream<ChatEvent>` from [MartinChatClient] into a growing chat
// transcript: each `send` appends the user's turn plus an empty Martin draft,
// then streams tokens into that draft, reflects tool activity, finalizes on
// `final_response`/`done`, and surfaces transport errors gracefully.
//
// The member agent must be scoped to the caller's TWG, so `twgId` is derived
// from the authed user's first TWG (mirroring how other controllers read the
// auth state). If the user has no TWG we fail gracefully without calling the
// client.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart';
import '../data/chat_models.dart';
import '../data/martin_chat_client.dart';

/// Streaming chat client, built from the shared [dioProvider].
final martinChatClientProvider = Provider<MartinChatClient>(
  (ref) => MartinChatClient(dio: ref.watch(dioProvider)),
);

/// Immutable snapshot of the chat transcript.
class ChatState {
  const ChatState({
    this.messages = const [],
    this.streaming = false,
    this.conversationId,
    this.error,
  });

  /// The transcript, oldest first. The last entry is the in-flight Martin draft
  /// while [streaming] is true.
  final List<ChatMessage> messages;

  /// True while a reply is being streamed (used to disable the input bar).
  final bool streaming;

  /// Carried across turns so the backend can continue the same thread.
  final String? conversationId;

  /// A user-facing error for the most recent send (null when healthy).
  final String? error;

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? streaming,
    String? conversationId,
    Object? error = _noError,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        streaming: streaming ?? this.streaming,
        conversationId: conversationId ?? this.conversationId,
        error: identical(error, _noError) ? this.error : error as String?,
      );

  // Sentinel so copyWith can distinguish "leave error" from "clear error".
  static const Object _noError = Object();
}

class ChatController extends Notifier<ChatState> {
  @override
  ChatState build() => const ChatState();

  MartinChatClient get _client => ref.read(martinChatClientProvider);

  /// The caller's TWG id (first TWG of the authed user), or null if none.
  String? get _twgId {
    final auth = ref.read(authControllerProvider);
    if (auth is AuthAuthenticated && auth.user.twgs.isNotEmpty) {
      return auth.user.twgs.first.id;
    }
    return null;
  }

  /// Sends [text] to Martin and streams the reply into a new Martin message.
  Future<void> send(String text, {String? overrideTwgId}) async {
    final message = text.trim();
    if (message.isEmpty || state.streaming) return;

    final twgId = overrideTwgId ?? _twgId;
    if (twgId == null) {
      state = state.copyWith(
        error: "You're not assigned to a TWG yet, so Martin can't help here.",
      );
      return;
    }

    // Append the user's turn + an empty Martin draft; begin streaming.
    final draft = ChatMessage(role: ChatRole.martin);
    state = state.copyWith(
      messages: [
        ...state.messages,
        ChatMessage(role: ChatRole.user, text: message),
        draft,
      ],
      streaming: true,
      error: null,
    );

    // Mutate the draft in place, then re-publish a fresh list so listeners see
    // the change (ChatMessage is mutable; the list identity is what triggers).
    void publish() => state = state.copyWith(messages: List.of(state.messages));

    try {
      await for (final event in _client.send(
        message: message,
        twgId: twgId,
        conversationId: state.conversationId,
      )) {
        switch (event) {
          case TokenEvent(:final text):
            draft.text += text;
            // First content token supersedes any "doing X…" chip.
            draft.toolActivity = null;
            publish();
          case ToolEvent(:final label):
            draft.toolActivity = label;
            publish();
          case FinalEvent(:final text, :final conversationId):
            if (text.isNotEmpty) draft.text = text;
            draft.toolActivity = null;
            state = state.copyWith(
              messages: List.of(state.messages),
              conversationId: conversationId ?? state.conversationId,
            );
          case DoneEvent():
            // Terminal marker; finalization happens after the loop.
            break;
          case ErrorEvent(:final message):
            draft.toolActivity = null;
            state = state.copyWith(
              messages: List.of(state.messages),
              streaming: false,
              error: message,
            );
            return;
        }
      }
    } catch (_) {
      draft.toolActivity = null;
      state = state.copyWith(
        messages: List.of(state.messages),
        streaming: false,
        error: 'Something went wrong talking to Martin.',
      );
      return;
    }

    // Normal completion.
    draft.toolActivity = null;
    state = state.copyWith(
      messages: List.of(state.messages),
      streaming: false,
    );
  }
}

final chatControllerProvider =
    NotifierProvider<ChatController, ChatState>(ChatController.new);
