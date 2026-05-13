/**
 * StreamingChatView — minimal inline progress indicator.
 *
 * One status line at a time while the agent works, then the
 * response streams in as plain text. No dark boxes, no colours.
 */

import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
    StreamMessage,
    AgentEvent,
    ToolCallEvent,
    ToolResultEvent,
    DoneEvent,
    ErrorEvent,
} from '../../hooks/useAgentStream';

interface StreamingChatViewProps {
    messages: StreamMessage[];
    isStreaming: boolean;
    streamingText: string;
    activeAgentLabel?: string;
}

export default function StreamingChatView({
    messages,
    isStreaming,
    streamingText,
}: StreamingChatViewProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages.length, streamingText]);

    if (messages.length === 0 && !isStreaming) return null;

    // Derive the single most-recent status line to show while no text yet
    let statusLine = 'Thinking…';
    for (const m of messages) {
        const e = m.event;
        if (e.type === 'routing') statusLine = e.content;
        else if (e.type === 'agent') statusLine = `${(e as AgentEvent).label}…`;
        else if (e.type === 'tool_call') statusLine = `${(e as ToolCallEvent).name}…`;
        else if (e.type === 'tool_result') statusLine = `✓ ${(e as ToolResultEvent).name}`;
        else if (e.type === 'error') statusLine = `Error: ${(e as ErrorEvent).message}`;
    }

    // Once we have streaming text, show the response directly
    const showResponse = !!streamingText;

    // After done, let parent hide this component entirely
    const isDone = messages.some(m => m.event.type === 'done') && !isStreaming;
    if (isDone) return null;

    return (
        <div className="py-1">
            <style>{`
                @keyframes cursorBlink {
                    0%, 100% { opacity: 1; }
                    50%       { opacity: 0; }
                }
            `}</style>

            {!showResponse && (
                <div className="flex items-center gap-2 text-sm text-slate-400 select-none py-1">
                    <span className="relative flex h-1.5 w-1.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-400 opacity-60" />
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-slate-400" />
                    </span>
                    <span>{statusLine}</span>
                </div>
            )}

            {showResponse && (
                <div className="text-sm text-[#0d121b] dark:text-white leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {streamingText}
                    </ReactMarkdown>
                    {isStreaming && (
                        <span
                            className="inline-block w-0.5 h-4 bg-slate-400 ml-0.5 align-text-bottom"
                            style={{ animation: 'cursorBlink 1s step-end infinite' }}
                        />
                    )}
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}
