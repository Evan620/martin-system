import { useState, useCallback, useRef } from 'react';
import { EnhancedChatRequest } from '../types/agent';

export interface StreamEvent {
    type: string;
    conversation_id?: string;
    command?: string;
    params?: Record<string, any>;
    tool?: string;
    status?: string;
    agents?: string[];
    message?: any;
    error?: string;
    result?: any;
}

export interface StreamingState {
    isStreaming: boolean;
    currentStatus: string | null;
    currentTool: string | null;
    error: string | null;
}

export function useStreamingChat() {
    const [streamingState, setStreamingState] = useState<StreamingState>({
        isStreaming: false,
        currentStatus: null,
        currentTool: null,
        error: null,
    });

    const eventSourceRef = useRef<EventSource | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const sendStreamingMessage = useCallback(
        async (
            request: EnhancedChatRequest,
            onEvent: (event: StreamEvent) => void,
            onComplete: (finalMessage: any) => void,
            onError: (error: string) => void
        ) => {
            // Clean up any existing connection
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }

            setStreamingState({
                isStreaming: true,
                currentStatus: 'Connecting...',
                currentTool: null,
                error: null,
            });

            try {
                // Use fetch with streaming for SSE
                abortControllerRef.current = new AbortController();

                const token = localStorage.getItem('access_token');
                const response = await fetch('/api/v1/agents/chat/stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': token ? `Bearer ${token}` : '',
                    },
                    body: JSON.stringify(request),
                    signal: abortControllerRef.current.signal,
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();

                if (!reader) {
                    throw new Error('No response body');
                }

                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();

                    if (done) {
                        break;
                    }

                    // Decode the chunk and add to buffer
                    buffer += decoder.decode(value, { stream: true });

                    // Process complete SSE messages
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // Keep incomplete line in buffer

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.substring(6);
                            try {
                                const event: StreamEvent = JSON.parse(data);

                                // Update streaming state based on event type
                                switch (event.type) {
                                    case 'start':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentStatus: 'Connected',
                                        }));
                                        break;

                                    case 'parsing':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentStatus: 'Parsing message...',
                                        }));
                                        break;

                                    case 'command_detected':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentStatus: `Executing command: ${event.command}`,
                                        }));
                                        break;

                                    case 'tool_start':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentTool: event.tool || null,
                                            currentStatus: event.status || 'Running tool...',
                                        }));
                                        break;

                                    case 'agent_routing':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentStatus: event.status || 'Routing to agent...',
                                        }));
                                        break;

                                    case 'thinking':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentStatus: event.status || 'Thinking...',
                                        }));
                                        break;

                                    case 'tool_complete':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            currentTool: null,
                                        }));
                                        break;

                                    case 'response':
                                        onComplete(event.message);
                                        break;

                                    case 'error':
                                        setStreamingState((prev) => ({
                                            ...prev,
                                            error: event.error || 'Unknown error',
                                        }));
                                        onError(event.error || 'Unknown error');
                                        break;

                                    case 'done':
                                        setStreamingState({
                                            isStreaming: false,
                                            currentStatus: null,
                                            currentTool: null,
                                            error: null,
                                        });
                                        break;
                                }

                                // Call the event callback
                                onEvent(event);
                            } catch (parseError) {
                                console.error('Error parsing SSE data:', parseError);
                            }
                        }
                    }
                }
            } catch (error: any) {
                if (error.name === 'AbortError') {
                    console.log('Stream aborted');
                } else {
                    console.error('Streaming error:', error);
                    setStreamingState((prev) => ({
                        ...prev,
                        isStreaming: false,
                        error: error.message,
                    }));
                    onError(error.message);
                }
            }
        },
        []
    );

    const cancelStream = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        setStreamingState({
            isStreaming: false,
            currentStatus: null,
            currentTool: null,
            error: null,
        });
    }, []);

    return {
        streamingState,
        sendStreamingMessage,
        cancelStream,
    };
}
