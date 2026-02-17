import { useState, useCallback, useRef } from 'react';
import { EnhancedChatRequest } from '../types/agent';
import { ThinkingStep } from '../components/agent/ThinkingTimeline';

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
    payload?: any; // Added for interrupt payloads
    step_id?: string;
    icon?: string;
    image?: string;
}

export interface StreamingState {
    isStreaming: boolean;
    currentStatus: string | null;
    currentTool: string | null;
    error: string | null;
    steps: ThinkingStep[];
    startTime: number;
}

export function useStreamingChat() {
    const [streamingState, setStreamingState] = useState<StreamingState>({
        isStreaming: false,
        currentStatus: null,
        currentTool: null,
        error: null,
        steps: [],
        startTime: 0
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
                steps: [],
                startTime: Date.now()
            });

            try {
                // Use agentService for consistent handling
                abortControllerRef.current = new AbortController();

                const { agentService } = await import('../services/agentService');

                await agentService.chatStream(request, {
                    onStep: (step) => {
                        setStreamingState(prev => {
                            const newSteps = [...prev.steps];
                            // Mark previous step as complete if new one starts
                            if (newSteps.length > 0) {
                                const lastStep = newSteps[newSteps.length - 1];
                                if (lastStep.status === 'active') {
                                    lastStep.status = 'complete';
                                    lastStep.durationMs = Date.now() - lastStep.timestamp;
                                }
                            }
                            // Add new step
                            newSteps.push({
                                ...step,
                                timestamp: Date.now()
                            });
                            return { ...prev, steps: newSteps, currentStatus: step.label };
                        });
                        // Forward to generic event handler if needed
                        onEvent({ type: 'step', ...step });
                    },
                    onThinking: (status) => {
                        onEvent({ type: 'thinking', status });
                    },
                    onResponse: (msg) => {
                        // Mark all steps complete
                        setStreamingState(prev => ({
                            ...prev,
                            steps: prev.steps.map(s => s.status === 'active' ? { ...s, status: 'complete', durationMs: Date.now() - s.timestamp } : s)
                        }));
                        onComplete(msg);
                    },
                    onInterrupt: (payload) => {
                        // Mark steps complete
                        setStreamingState(prev => ({
                            ...prev,
                            steps: prev.steps.map(s => s.status === 'active' ? { ...s, status: 'complete', durationMs: Date.now() - s.timestamp } : s)
                        }));
                        onEvent({ type: 'interrupt', payload });
                    },
                    onError: (err) => {
                        setStreamingState(prev => {
                            const newSteps = [...prev.steps];
                            if (newSteps.length > 0) {
                                newSteps[newSteps.length - 1].status = 'error';
                            }
                            return { ...prev, error: typeof err === 'string' ? err : 'Unknown error', isStreaming: false, steps: newSteps };
                        });
                        onError(typeof err === 'string' ? err : 'Unknown error');
                    },
                    onDone: () => {
                        setStreamingState(prev => ({ ...prev, isStreaming: false }));
                    }
                });
            } catch (error: any) {
                if (error.name === 'AbortError') {
                    console.log('Stream aborted');
                } else {
                    console.error('Streaming error:', error);
                    setStreamingState((prev) => ({
                        ...prev,
                        isStreaming: false,
                        error: error.message || 'Unknown error',
                    }));
                    onError(error.message || 'Unknown error');
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
            steps: [],
            startTime: 0
        });
    }, []);

    return {
        streamingState,
        sendStreamingMessage,
        cancelStream,
    };
}
