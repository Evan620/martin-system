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
import api from '../../services/api';

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

    type ConfirmCard = {
        status: 'confirmation_required';
        type?: string;
        action_id: string;
        action_type: string;
        summary: string;
        payload: Record<string, any>;
        irreversible?: boolean;
        confirm_endpoint: string;
    };

    function tryParseConfirm(content: string): ConfirmCard | null {
        const trimmed = content.trim();
        if (!trimmed.startsWith('{')) return null;
        try {
            const j = JSON.parse(trimmed);
            if (j && j.status === 'confirmation_required' && j.action_id && j.confirm_endpoint) return j as ConfirmCard;
        } catch { /* not JSON */ }
        return null;
    }

    async function executeConfirm(card: ConfirmCard, confirmed: boolean): Promise<string> {
        // The backend emits confirm_endpoint as "/api/v1/agents/execute" (an
        // origin-relative path), but the Vite proxy strips the "/api" prefix,
        // so calling it directly yields 404. Resolve via the api service base
        // URL so the request lands on the FastAPI router cleanly.
        const base = (api.defaults.baseURL || '').replace(/\/$/, '');
        const path = card.confirm_endpoint.replace(/^\/api\/v1/, '').replace(/^\//, '');
        const url = `${base}/${path}`;
        const token = localStorage.getItem('token');
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ action_id: card.action_id, confirmed, edits: {} }),
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) return `Action failed: ${data.detail || resp.statusText}`;
        if (data.cancelled) return 'Cancelled.';
        if (data.success === true || data.status === 'ok') return 'Done.';
        return JSON.stringify(data);
    }

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
        <div style={{
            display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0,
            width: '100%', overflow: 'hidden',
            background: 'var(--surface)',
            fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
        }}>
            <CopilotHeader
                twgName={activeTwgName}
                twgId={activeTwgId}
                onTwgChange={setActiveTwgId}
                onClearHistory={handleClearHistory}
                onClose={onClose}
                userTwgs={isAdmin ? [] : userTwgs}
                isAdmin={isAdmin}
            />
            {localMessages.length === 0 && (
                <SuggestedActions
                    briefing={briefing}
                    onFillInput={handleFillInput}
                    onSubmit={(text) => { setInput(text); setTimeout(handleSend, 0); }}
                />
            )}
            <div ref={scrollRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '12px 14px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {localMessages.map(msg => {
                    const monogram = (
                        <div style={{
                            width: 22, height: 22, border: '1px solid var(--border)', background: 'var(--ink-50)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontFamily: "'Source Serif 4', serif", fontSize: 11, color: 'var(--accent)', flexShrink: 0,
                        }}>M</div>
                    );
                    const confirmCard = msg.sender !== 'user' ? tryParseConfirm(msg.content) : null;
                    if (confirmCard) {
                        return (
                            <div
                                key={msg.id}
                                style={{
                                    display: 'flex', gap: 8, width: '100%', overflow: 'hidden', flexDirection: 'row',
                                }}
                            >
                                {monogram}
                                <div style={{
                                    padding: 12, border: '1px solid var(--border)', background: 'var(--ink-50)',
                                    fontFamily: "'Geist', 'Inter', system-ui, sans-serif", maxWidth: '90%', minWidth: 0,
                                }}>
                                    <div style={{
                                        fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
                                        fontWeight: 600, color: confirmCard.irreversible ? 'var(--terra)' : 'var(--accent)', marginBottom: 8,
                                    }}>
                                        {confirmCard.irreversible ? 'Irreversible action' : 'Confirm action'}
                                    </div>
                                    <div style={{ fontSize: 13, color: 'var(--ink-900)', marginBottom: 12 }}>{confirmCard.summary}</div>
                                    <div style={{ display: 'flex', gap: 8 }}>
                                        <button
                                            onClick={async () => {
                                                const result = await executeConfirm(confirmCard, true);
                                                setLocalMessages(prev => [
                                                    ...prev,
                                                    { id: `r_${confirmCard.action_id}`, sender: 'agent', content: result, timestamp: new Date().toISOString() },
                                                ]);
                                            }}
                                            style={{
                                                background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)',
                                                padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                                            }}
                                        >Confirm</button>
                                        <button
                                            onClick={async () => {
                                                // Tell the backend to drop the pending action too.
                                                await executeConfirm(confirmCard, false).catch(() => {});
                                                setLocalMessages(prev => [
                                                    ...prev,
                                                    { id: `c_${confirmCard.action_id}`, sender: 'agent', content: 'Cancelled.', timestamp: new Date().toISOString() },
                                                ]);
                                            }}
                                            style={{
                                                background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)',
                                                padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                                            }}
                                        >Cancel</button>
                                    </div>
                                </div>
                            </div>
                        );
                    }
                    return (
                        <div
                            key={msg.id}
                            style={{
                                display: 'flex', gap: 8, width: '100%', overflow: 'hidden',
                                flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row',
                            }}
                        >
                            {msg.sender !== 'user' && monogram}
                            <div style={{
                                padding: '10px 12px', maxWidth: '90%', minWidth: 0,
                                fontSize: 12, lineHeight: 1.6, wordBreak: 'break-word',
                                background: msg.sender === 'user' ? 'var(--accent)' : 'var(--ink-50)',
                                color: msg.sender === 'user' ? 'var(--accent-ink)' : 'var(--ink-800)',
                                border: msg.sender === 'user' ? '1px solid var(--accent)' : '1px solid var(--border)',
                            }}>
                                {msg.sender === 'user' ? (
                                    <span>{msg.content}</span>
                                ) : (
                                    <div className="prose prose-xs dark:prose-invert max-w-none">
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                p: ({ children }) => <p style={{ margin: '0 0 8px' }}>{children}</p>,
                                                ul: ({ children }) => <ul style={{ listStyle: 'disc', paddingLeft: 18, margin: '0 0 8px', display: 'flex', flexDirection: 'column', gap: 3 }}>{children}</ul>,
                                                ol: ({ children }) => <ol style={{ listStyle: 'decimal', paddingLeft: 18, margin: '0 0 8px', display: 'flex', flexDirection: 'column', gap: 3 }}>{children}</ol>,
                                                li: ({ children }) => <li style={{ paddingLeft: 2 }}>{children}</li>,
                                                strong: ({ children }) => <strong style={{ fontWeight: 600, color: 'var(--ink-900)' }}>{children}</strong>,
                                                a: ({ href, children }) => <a href={href} style={{ color: 'var(--accent)', textDecoration: 'underline' }} target="_blank" rel="noopener noreferrer">{children}</a>,
                                                code: ({ className, children }) => {
                                                    const isBlock = className?.includes('language-');
                                                    return isBlock ? (
                                                        <pre style={{ background: 'var(--ink-900)', color: 'var(--ink-50)', padding: 12, margin: '8px 0', overflowX: 'auto', fontSize: 11 }}>
                                                            <code style={{ fontFamily: "'Geist Mono', monospace" }}>{children}</code>
                                                        </pre>
                                                    ) : (
                                                        <code style={{ background: 'var(--ink-100)', padding: '1px 4px', fontSize: 11, fontFamily: "'Geist Mono', monospace" }}>{children}</code>
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
                    );
                })}
                {((isBriefingLoading && localMessages.length === 0) || isStreaming) && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                            width: 22, height: 22, border: '1px solid var(--border)', background: 'var(--ink-50)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontFamily: "'Source Serif 4', serif", fontSize: 11, color: 'var(--accent)', flexShrink: 0,
                        }}>M</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 4px' }}>
                            <span style={{ width: 4, height: 4, borderRadius: 4, background: 'var(--accent)', display: 'inline-block', animationDelay: '0ms' }} className="animate-bounce" />
                            <span style={{ width: 4, height: 4, borderRadius: 4, background: 'var(--accent)', display: 'inline-block', animationDelay: '150ms' }} className="animate-bounce" />
                            <span style={{ width: 4, height: 4, borderRadius: 4, background: 'var(--accent)', display: 'inline-block', animationDelay: '300ms' }} className="animate-bounce" />
                        </div>
                    </div>
                )}
              </div>
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
