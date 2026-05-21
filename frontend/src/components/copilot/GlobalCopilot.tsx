import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { RootState } from '../../store';
import { UserRole } from '../../types/auth';
import { useAgentStream, NavigateEvent } from '../../hooks/useAgentStream';
import CopilotHeader from './CopilotHeader';
import SuggestedActions from './SuggestedActions';
import CopilotInput from './CopilotInput';
import { getBriefing, BriefingData } from '../../services/martinService';

interface GlobalCopilotProps {
    onClose: () => void;
}

interface TWGOption {
    id: string;
    name: string;
}

interface UserMessage {
    id: string;
    content: string;
    sender: 'user';
    timestamp: string;
}

interface AgentMessage {
    id: string;
    content: string;
    sender: 'agent';
    timestamp: string;
}

type LocalMessage = UserMessage | AgentMessage;

// ---------------------------------------------------------------------------
// Context resolution helpers
// ---------------------------------------------------------------------------

function resolveInitialTwgId(
    routeTwgId: string | undefined,
    userTwgIds: string[],
    isAdmin: boolean,
): string | null {
    if (routeTwgId) return routeTwgId;
    if (!isAdmin && userTwgIds.length === 1) return userTwgIds[0];
    return null; // admin global or multi-TWG member (user must pick)
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GlobalCopilot({ onClose }: GlobalCopilotProps) {
    const navigate = useNavigate();
    const user = useSelector((state: RootState) => state.auth.user);
    const { twgId: routeTwgId } = useParams<{ twgId?: string }>();

    const isAdmin = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD;
    const userTwgIds = user?.twg_ids ?? [];
    const userTwgs: TWGOption[] = user?.twgs ?? [];

    const [activeTwgId, setActiveTwgId] = useState<string | null>(() =>
        resolveInitialTwgId(routeTwgId, userTwgIds, isAdmin)
    );

    // Sync when route changes (navigating to a workspace)
    useEffect(() => {
        if (routeTwgId) setActiveTwgId(routeTwgId);
    }, [routeTwgId]);

    const activeTwgName = userTwgs.find(t => t.id === activeTwgId)?.name ?? null;

    // Streaming
    const {
        messages: streamEvents,
        isStreaming,
        conversationId: streamConvId,
        sendMessage: sendStreamMessage,
        cancel,
    } = useAgentStream();

    // Local settled messages (user bubbles + agent done responses)
    const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);
    const [conversationId, setConversationId] = useState<string | undefined>();

    // Input
    const [input, setInput] = useState('');
    const [briefing, setBriefing] = useState<BriefingData | null>(null);
    const [isBriefingLoading, setIsBriefingLoading] = useState(true);

    // Scroll ref
    const scrollRef = useRef<HTMLDivElement>(null);

    // Sync conversationId from stream
    useEffect(() => {
        if (streamConvId) setConversationId(streamConvId);
    }, [streamConvId]);

    // Promote done event to local messages
    const prevStreamingRef = useRef(false);
    useEffect(() => {
        const wasStreaming = prevStreamingRef.current;
        prevStreamingRef.current = isStreaming;

        if (wasStreaming && !isStreaming) {
            const doneEvt = streamEvents.find(m => m.event.type === 'done');
            if (doneEvt && doneEvt.event.type === 'done') {
                const done = doneEvt.event;
                if (done.conversation_id) setConversationId(done.conversation_id);
                setLocalMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    content: done.response,
                    sender: 'agent',
                    timestamp: new Date().toISOString(),
                }]);
            }

            const errEvt = streamEvents.find(m => m.event.type === 'error');
            if (errEvt && errEvt.event.type === 'error' && !doneEvt) {
                const errMsg = (errEvt.event as { type: 'error'; message: string }).message;
                setLocalMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    content: `Error: ${errMsg}`,
                    sender: 'agent',
                    timestamp: new Date().toISOString(),
                }]);
            }
        }
    }, [isStreaming, streamEvents]);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [localMessages, isStreaming]);

    // Handle navigate events from Martin
    useEffect(() => {
        const navEvent = streamEvents.find(m => m.event.type === 'navigate');
        if (navEvent) {
            navigate((navEvent.event as NavigateEvent).path);
        }
    }, [streamEvents, navigate]);

    const buildBriefingMessage = (data: BriefingData): string => {
        const lines: string[] = [];
        const hasContent =
            data.upcoming_meetings.length > 0 ||
            data.threshold_alerts.length > 0 ||
            data.overdue_items.length > 0;

        if (!hasContent) {
            lines.push(`${data.greeting}. Things look good — nothing urgent today.`);
            lines.push('\nWhat would you like to do?');
        } else {
            lines.push(`${data.greeting}. A few things for your attention:\n`);
            data.threshold_alerts.forEach((a) => {
                const label = a.gap_type === 'gender' ? 'gender' : 'youth';
                const current = a.current_pct != null ? `${a.current_pct.toFixed(0)}%` : 'not set';
                lines.push(`⚠️ **${a.project_name}** — ${label} employment gap (${current} / ${a.required_pct}% required)`);
            });
            data.upcoming_meetings.forEach((m) => {
                const hrs = Math.floor(m.minutes_until / 60);
                const mins = m.minutes_until % 60;
                const timeStr = hrs > 0 ? `in ${hrs}h ${mins}m` : `in ${mins} minutes`;
                lines.push(`📅 **${m.title}** ${timeStr}${m.twg_name ? ` (${m.twg_name})` : ''}`);
            });
            data.overdue_items.forEach((o) => {
                lines.push(`📋 **${o.title}** — unread for ${o.days_overdue} day${o.days_overdue !== 1 ? 's' : ''}`);
            });
            lines.push('\nWhat would you like to tackle first?');
        }
        return lines.join('\n');
    };

    // Fetch briefing on mount and inject as first message
    useEffect(() => {
        let cancelled = false;
        setIsBriefingLoading(true);
        getBriefing()
            .then((data) => {
                if (cancelled) return;
                setBriefing(data);
                setLocalMessages([{
                    id: 'briefing',
                    content: buildBriefingMessage(data),
                    sender: 'agent',
                    timestamp: new Date().toISOString(),
                }]);
            })
            .catch(() => {
                if (cancelled) return;
            })
            .finally(() => {
                if (!cancelled) setIsBriefingLoading(false);
            });
        return () => { cancelled = true; };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleSend = () => {
        if (!input.trim() || isStreaming) return;
        const content = input.trim();
        setInput('');

        setLocalMessages(prev => [...prev, {
            id: Date.now().toString(),
            content,
            sender: 'user',
            timestamp: new Date().toISOString(),
        }]);

        sendStreamMessage({
            message: content,
            conversationId,
            twgId: activeTwgId ?? undefined,
        });
    };

    const handleFillInput = (text: string) => {
        setInput(text);
    };

    const handleClearHistory = () => {
        setLocalMessages([]);
        setConversationId(undefined);
        setBriefing(null);
        setIsBriefingLoading(true);
        getBriefing()
            .then((data) => {
                setBriefing(data);
                setLocalMessages([{
                    id: 'briefing-refresh',
                    content: buildBriefingMessage(data),
                    sender: 'agent',
                    timestamp: new Date().toISOString(),
                }]);
            })
            .catch(() => {})
            .finally(() => setIsBriefingLoading(false));
    };


    return (
        <div className="flex flex-col h-full bg-white dark:bg-dark-card">
            <CopilotHeader
                twgName={activeTwgName}
                twgId={activeTwgId}
                onTwgChange={setActiveTwgId}
                onClearHistory={handleClearHistory}
                onClose={onClose}
                userTwgs={isAdmin ? [] : userTwgs}
                isAdmin={isAdmin}
            />

            <SuggestedActions
                briefing={briefing}
                onFillInput={handleFillInput}
                onSubmit={(text) => {
                    setInput(text);
                    setTimeout(handleSend, 0);
                }}
            />

            {/* Message list */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
                {/* Settled messages */}
                {localMessages.map(msg => (
                    <div
                        key={msg.id}
                        className={`flex gap-2 w-full overflow-hidden ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                        {msg.sender !== 'user' && (
                            <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                                <span className="text-white text-[10px] font-bold leading-none">✦</span>
                            </div>
                        )}
                        <div className={`p-3 rounded-2xl max-w-[90%] text-xs leading-relaxed shadow-sm break-words min-w-0
                            ${msg.sender === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : 'bg-slate-50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 rounded-tl-none border border-slate-100 dark:border-slate-700'
                            }`}
                        >
                            {msg.sender === 'user' ? (
                                <span>{msg.content}</span>
                            ) : (
                                <div className="prose prose-xs dark:prose-invert max-w-none">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                            ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                                            ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                                            li: ({ children }) => <li className="pl-1">{children}</li>,
                                            strong: ({ children }) => <strong className="font-bold text-slate-900 dark:text-white">{children}</strong>,
                                            a: ({ href, children }) => <a href={href} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                                            code: ({ className, children }) => {
                                                const isBlock = className?.includes('language-');
                                                return isBlock ? (
                                                    <pre className="bg-slate-900 text-slate-50 rounded-lg p-3 my-2 overflow-x-auto text-xs">
                                                        <code className="font-mono">{children}</code>
                                                    </pre>
                                                ) : (
                                                    <code className="bg-slate-200 dark:bg-slate-700 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                                                );
                                            },
                                            pre: ({ children }) => <>{children}</>,
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Briefing loading indicator */}
                {isBriefingLoading && localMessages.length === 0 && (
                    <div className="flex gap-2 items-center">
                        <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                            <span className="text-white text-[10px] font-bold leading-none animate-pulse">✦</span>
                        </div>
                        <div className="flex gap-1 items-center px-1 py-2">
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                    </div>
                )}

                {/* Streaming: animated thinking indicator */}
                {isStreaming && (
                    <div className="flex gap-2 items-center">
                        <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                            <span className="text-white text-[10px] font-bold leading-none animate-pulse">✦</span>
                        </div>
                        <div className="flex gap-1 items-center px-1 py-2">
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                    </div>
                )}
            </div>

            <CopilotInput
                value={input}
                onChange={setInput}
                onSend={handleSend}
                onCancel={cancel}
                isStreaming={isStreaming}
                userTwgs={userTwgs}
                onMentionInsert={() => {}}
                userRole={user?.role}
            />
        </div>
    );
}
