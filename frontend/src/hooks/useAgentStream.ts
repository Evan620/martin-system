import { useState, useCallback, useRef } from 'react';
import { API_URL } from '../services/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type StreamEventType =
    | 'routing'
    | 'agent'
    | 'tool_call'
    | 'tool_result'
    | 'token'
    | 'done'
    | 'error';

export interface RoutingEvent {
    type: 'routing';
    content: string;
}

export interface AgentEvent {
    type: 'agent';
    content: string;   // agent key e.g. "energy"
    label: string;     // human label e.g. "Energy Martin"
}

export interface ToolCallEvent {
    type: 'tool_call';
    name: string;
    args: Record<string, unknown>;
}

export interface ToolResultEvent {
    type: 'tool_result';
    name: string;
    content: string;
}

export interface TokenEvent {
    type: 'token';
    content: string;
}

export interface DoneEvent {
    type: 'done';
    response: string;
    agent_id: string;
    conversation_id: string;
    citations: unknown[];
}

export interface ErrorEvent {
    type: 'error';
    message: string;
}

export type StreamEvent =
    | RoutingEvent
    | AgentEvent
    | ToolCallEvent
    | ToolResultEvent
    | TokenEvent
    | DoneEvent
    | ErrorEvent;

// ---------------------------------------------------------------------------
// Hook state
// ---------------------------------------------------------------------------

export interface StreamMessage {
    id: string;
    event: StreamEvent;
    /** Accumulated text (only present while type === 'token' stream is ongoing) */
    partialText?: string;
}

export interface UseAgentStreamResult {
    /** Ordered list of events/messages for rendering */
    messages: StreamMessage[];
    /** Whether a request is in progress */
    isStreaming: boolean;
    /** Last error message, if any */
    error: string | null;
    /** Accumulated token text (the in-progress response bubble) */
    streamingText: string;
    /** The conversation_id returned by done event */
    conversationId: string | undefined;
    /** Send a message */
    sendMessage: (params: SendParams) => Promise<void>;
    /** Cancel an in-progress stream */
    cancel: () => void;
}

export interface SendParams {
    message: string;
    conversationId?: string;
    twgId?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseSSEChunk(chunk: string): StreamEvent[] {
    const events: StreamEvent[] = [];
    // Lines may be buffered imperfectly; split on double-newline SSE boundaries
    const blocks = chunk.split(/\n\n+/);
    for (const block of blocks) {
        const dataLine = block.split('\n').find(l => l.startsWith('data: '));
        if (!dataLine) continue;
        try {
            const json = JSON.parse(dataLine.slice(6));
            events.push(json as StreamEvent);
        } catch {
            // Malformed chunk — ignore
        }
    }
    return events;
}

function makeId(): string {
    return Math.random().toString(36).slice(2);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAgentStream(): UseAgentStreamResult {
    const [messages, setMessages] = useState<StreamMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [streamingText, setStreamingText] = useState('');
    const [conversationId, setConversationId] = useState<string | undefined>();

    const abortRef = useRef<AbortController | null>(null);

    const cancel = useCallback(() => {
        abortRef.current?.abort();
        setIsStreaming(false);
    }, []);

    const sendMessage = useCallback(async ({ message, conversationId: convId, twgId }: SendParams) => {
        abortRef.current?.abort();
        const controller = new AbortController();
        abortRef.current = controller;

        setMessages([]);
        setStreamingText('');
        setError(null);
        setIsStreaming(true);

        const token = localStorage.getItem('token');
        const params = new URLSearchParams({ message });
        if (convId) params.set('conversation_id', convId);
        if (twgId) params.set('twg_id', twgId);

        try {
            const response = await fetch(`${API_URL}/agents/chat/stream?${params.toString()}`, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: 'text/event-stream',
                },
                signal: controller.signal,
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(`HTTP ${response.status}: ${text}`);
            }

            if (!response.body) throw new Error('ReadableStream not supported');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE blocks (terminated by \n\n)
                let boundary = buffer.indexOf('\n\n');
                while (boundary !== -1) {
                    const block = buffer.slice(0, boundary + 2);
                    buffer = buffer.slice(boundary + 2);
                    boundary = buffer.indexOf('\n\n');

                    const events = parseSSEChunk(block);
                    for (const event of events) {
                        handleEvent(event);
                    }
                }
            }
        } catch (err: unknown) {
            if ((err as Error).name === 'AbortError') return;
            const msg = (err as Error).message || 'Unknown error';
            setError(msg);
            setMessages(prev => [
                ...prev,
                { id: makeId(), event: { type: 'error', message: msg } as ErrorEvent },
            ]);
        } finally {
            setIsStreaming(false);
        }

        function handleEvent(event: StreamEvent) {
            if (event.type === 'token') {
                setStreamingText(prev => prev + event.content);
                return;
            }

            if (event.type === 'done') {
                setConversationId(event.conversation_id);
                setStreamingText('');
            }

            if (event.type === 'error') {
                setError(event.message);
            }

            setMessages(prev => [...prev, { id: makeId(), event }]);
        }
    }, []);

    return { messages, isStreaming, error, streamingText, conversationId, sendMessage, cancel };
}
