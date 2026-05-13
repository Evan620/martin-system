import { useState, useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../../store';
import { ChatMessage, ChatMessageType, ActionType } from '../../types/agent';
import { UserRole } from '../../types/auth';
import { useAgentStream } from '../../hooks/useAgentStream';
import StreamingChatView from '../../components/agent/StreamingChatView';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function CopilotChat({ twgId: propTwgId, twgName, isExpanded, onToggleExpand }: { twgId?: string, twgName?: string, isExpanded?: boolean, onToggleExpand?: () => void }) {
    // Determine TWG Context: Use prop if available, otherwise fallback to user's primary TWG
    const user = useSelector((state: RootState) => state.auth.user);
    // State for Mentions
    const [twgs, setTwgs] = useState<any[]>([]);
    const [showMentions, setShowMentions] = useState(false);
    const [mentionQuery, setMentionQuery] = useState('');
    const [mentionIndex, setMentionIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

    // Chat State
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [conversationId, setConversationId] = useState<string | undefined>(undefined);
    const {
        messages: streamEvents,
        isStreaming,
        streamingText,
        conversationId: streamConvId,
        sendMessage: sendStreamMessage,
    } = useAgentStream();

    // No hardcoded welcome — agents greet naturally via their prompt's GREETING PROTOCOL

    // Auto-scroll to bottom (Scoped to container to prevent page jump)
    useEffect(() => {
        if (messagesContainerRef.current) {
            const { scrollHeight, clientHeight } = messagesContainerRef.current;
            messagesContainerRef.current.scrollTo({
                top: scrollHeight - clientHeight,
                behavior: 'smooth'
            });
        }
    }, [messages, isStreaming, streamingText]);

    // Sync conversation ID from stream
    useEffect(() => {
        if (streamConvId) setConversationId(streamConvId);
    }, [streamConvId]);

    // Promote done event to messages when stream finishes
    const prevIsStreamingRef = useRef(false);
    useEffect(() => {
        const wasStreaming = prevIsStreamingRef.current;
        prevIsStreamingRef.current = isStreaming;

        if (wasStreaming && !isStreaming) {
            const doneEvt = streamEvents.find(m => m.event.type === 'done');
            if (doneEvt && doneEvt.event.type === 'done') {
                const done = doneEvt.event;
                if (done.conversation_id) setConversationId(done.conversation_id);
                setMessages(prev => [...prev, {
                    message_id: Date.now().toString(),
                    conversation_id: done.conversation_id || conversationId || '',
                    message_type: ChatMessageType.AGENT_TEXT,
                    content: done.response,
                    sender: 'agent',
                    timestamp: new Date().toISOString(),
                } as ChatMessage]);
            }

            const errEvt = streamEvents.find(m => m.event.type === 'error');
            if (errEvt && errEvt.event.type === 'error' && !doneEvt) {
                setMessages(prev => [...prev, {
                    message_id: Date.now().toString(),
                    conversation_id: conversationId || '',
                    message_type: ChatMessageType.SYSTEM,
                    content: `Error: ${(errEvt.event as any).message}`,
                    sender: 'system',
                    timestamp: new Date().toISOString(),
                } as ChatMessage]);
            }
        }
    }, [isStreaming, streamEvents]);

    const handleSendMessage = () => {
        if (!input.trim() || isStreaming) return;

        const content = input.trim();
        setInput('');

        setMessages(prev => [...prev, {
            message_id: Date.now().toString(),
            conversation_id: conversationId || '',
            message_type: ChatMessageType.USER_TEXT,
            content,
            sender: 'user',
            timestamp: new Date().toISOString(),
        } as ChatMessage]);

        sendStreamMessage({
            message: content,
            conversationId,
            twgId: propTwgId || (user?.role !== UserRole.ADMIN ? user?.twg_ids?.[0] : undefined),
        });
    };

    // Fetch TWGs if authorized
    useEffect(() => {
        const canMention = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD;
        if (canMention && twgs.length === 0) {
            import('../../services/twgService').then(mod => {
                mod.default.listDropdown().then(data => setTwgs(data)).catch(console.error);
            });
        }
    }, [user?.role]);

    const filteredTwgs = twgs.filter(t =>
        t.name.toLowerCase().includes(mentionQuery.toLowerCase()) ||
        t.pillar?.toLowerCase().includes(mentionQuery.toLowerCase())
    );

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setInput(val);

        // Detect @mention
        // improved regex to check if the cursor is at a word starting with @
        const words = val.split(" ");
        const lastWord = words[words.length - 1];

        if ((lastWord.startsWith('@') || lastWord === '@') && (user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD)) {
            setShowMentions(true);
            setMentionQuery(lastWord.slice(1));
            setMentionIndex(0);
        } else {
            setShowMentions(false);
        }
    };

    const insertMention = (twg: any) => {
        const words = input.split(' ');
        words.pop(); // Remove the partial @mention
        const newValue = [...words, `@${twg.name} `].join(' ');
        setInput(newValue);
        setShowMentions(false);
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (showMentions && filteredTwgs.length > 0) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                setMentionIndex(prev => (prev > 0 ? prev - 1 : filteredTwgs.length - 1));
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                setMentionIndex(prev => (prev < filteredTwgs.length - 1 ? prev + 1 : 0));
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                e.preventDefault();
                insertMention(filteredTwgs[mentionIndex]);
            } else if (e.key === 'Escape') {
                setShowMentions(false);
            }
        } else if (e.key === 'Enter') {
            handleSendMessage();
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-dark-card relative">
            {/* Header */}
            <div className="p-4 border-b border-slate-100 dark:border-dark-border flex items-center justify-between transition-colors">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-900/20">
                        <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                    </div>
                    <div>
                        <h3 className="font-bold text-sm text-slate-900 dark:text-white">Martin Copilot</h3>
                        <p className="text-[10px] text-green-500 font-bold uppercase flex items-center gap-1 transition-colors">
                            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                            Online • {twgName ? `${twgName} Martin` : (user?.role === UserRole.ADMIN ? 'Secretariat Mode' : 'General Context')}
                        </p>
                    </div>
                </div>
                {onToggleExpand && (
                    <button
                        onClick={onToggleExpand}
                        className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-all"
                        title={isExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
                    >
                        <span className="material-symbols-outlined text-[20px]">
                            {isExpanded ? 'last_page' : 'first_page'}
                        </span>
                    </button>
                )}
            </div>

            {/* Chat Messages */}
            <div
                ref={messagesContainerRef}
                className="flex-1 overflow-y-auto p-4 space-y-4"
            >
                {messages.map((msg, idx) => (
                    <div key={msg.message_id || idx} className={`flex gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                        {msg.sender !== 'user' && (
                            <div className="w-6 h-6 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 transition-colors">
                                {msg.sender === 'system' ? (
                                    <span className="material-symbols-outlined text-[14px] text-red-500">warning</span>
                                ) : (
                                    <span className="material-symbols-outlined text-[14px] text-blue-600">smart_toy</span>
                                )}
                            </div>
                        )}


                        <div className={`
                            p-3 rounded-2xl max-w-[95%] text-xs leading-relaxed transition-colors shadow-sm
                            ${msg.sender === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : msg.sender === 'system'
                                    ? 'bg-red-50 text-red-600 border border-red-100'
                                    : 'bg-slate-50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 rounded-tl-none border border-slate-100 dark:border-slate-700'
                            }
                        `}>
                            <div className="prose prose-xs dark:prose-invert max-w-none">
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                        ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                                        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                                        li: ({ children }) => <li className="pl-1">{children}</li>,
                                        strong: ({ children }) => <strong className="font-bold text-slate-900 dark:text-white">{children}</strong>,
                                        em: ({ children }) => <em className="italic">{children}</em>,
                                        a: ({ href, children }) => <a href={href} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                                        code: ({ className, children }) => {
                                            const isBlock = className?.includes('language-');
                                            if (isBlock) {
                                                return (
                                                    <pre className="bg-slate-900 text-slate-50 rounded-lg p-3 my-2 overflow-x-auto text-xs">
                                                        <code className="font-mono">{children}</code>
                                                    </pre>
                                                );
                                            }
                                            return <code className="bg-slate-200 dark:bg-slate-700 px-1 py-0.5 rounded text-xs font-mono">{children}</code>;
                                        },
                                        pre: ({ children }) => <>{children}</>,
                                    }}
                                >
                                    {msg.content}
                                </ReactMarkdown>
                            </div>

                            {/* Render Tool Execution Metadata */}
                            {msg.metadata?.parsed?.type === 'command_result' && (
                                <div className="mt-2 pt-2 border-t border-black/10 dark:border-white/10 text-[10px] opacity-70 font-mono flex items-center gap-1">
                                    <span className="material-symbols-outlined text-[10px]">terminal</span>
                                    Executed: {msg.metadata.parsed.command}
                                </div>
                            )}

                            {/* Render Actions (Buttons) */}
                            {msg.actions && msg.actions.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {msg.actions.map(action => (
                                        <button
                                            key={action.action_id}
                                            className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-colors ${action.style === 'primary'
                                                ? 'bg-blue-600 text-white hover:bg-blue-700'
                                                : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-600'
                                                }`}
                                            onClick={() => {
                                                if (action.action_type === ActionType.BUTTON) {
                                                    setInput(action.value || action.label);
                                                    // Optional: auto-submit?
                                                }
                                            }}
                                        >
                                            {action.icon && <span className="material-symbols-outlined text-[12px] mr-1 align-bottom">{action.icon}</span>}
                                            {action.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {isStreaming && (
                    <div className="px-2">
                        <StreamingChatView
                            messages={streamEvents}
                            isStreaming={isStreaming}
                            streamingText={streamingText}
                        />
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 border-t border-slate-100 dark:border-dark-border bg-slate-50/50 dark:bg-slate-800/20 relative">
                {/* Mentions Popup */}
                {showMentions && filteredTwgs.length > 0 && (
                    <div className="absolute bottom-full left-4 mb-2 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
                        <div className="px-3 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700">
                            <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Mention TWG Agent</p>
                        </div>
                        <ul className="max-h-48 overflow-y-auto py-1">
                            {filteredTwgs.map((twg, idx) => (
                                <li
                                    key={twg.id}
                                    className={`px-3 py-2 text-xs cursor-pointer flex items-center gap-2 ${idx === mentionIndex
                                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                                        }`}
                                    onMouseDown={(e) => {
                                        e.preventDefault(); // Prevent blur
                                        insertMention(twg);
                                    }}
                                >
                                    <div className={`w-3 h-3 rounded-full flex-shrink-0 ${idx === mentionIndex ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                                        }`} />
                                    <div className="flex-1 truncate">
                                        <span className="font-medium">{twg.name}</span>
                                        {twg.pillar && <span className="ml-1 text-[10px] opacity-60">({twg.pillar})</span>}
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                <div className="relative">
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        placeholder={showMentions ? "Type to search TWGs..." : "Ask Copilot to analyze, draft, or schedule (@ to mention TWG)..."}
                        className="w-full bg-white dark:bg-slate-800 rounded-xl py-3 pl-4 pr-12 text-xs font-medium text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 transition-all shadow-sm outline-none"
                        disabled={isStreaming}
                        autoFocus
                        autoComplete="off"
                    />
                    <button
                        onClick={handleSendMessage}
                        disabled={!input.trim() || isStreaming}
                        className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors shadow-md shadow-blue-900/20"
                    >
                        <span className="material-symbols-outlined text-[16px] block">send</span>
                    </button>
                </div>
            </div>
        </div>
    );
}
