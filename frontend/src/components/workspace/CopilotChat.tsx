import { useState, useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../../store';
import { ChatMessage, ChatMessageType, EnhancedChatRequest, ActionType } from '../../types/agent';
import { UserRole } from '../../types/auth';
import { useStreamingChat, StreamEvent } from '../../hooks/useStreamingChat';
import ReactMarkdown from 'react-markdown';

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

    const { streamingState, sendStreamingMessage, cancelStream } = useStreamingChat();
    const { isStreaming, currentStatus, currentTool } = streamingState;

    // Initial Welcome Message
    useEffect(() => {
        if (messages.length === 0) {
            setMessages([
                {
                    message_id: 'welcome',
                    conversation_id: 'init',
                    message_type: ChatMessageType.AGENT_TEXT,
                    content: twgName
                        ? `Greetings. I am ${twgName} Martin. How may I assist you with your technical deliverables today?`
                        : "Greetings. I am Secretariat Martin. I can assist with cross-pillar coordination, document synthesis, and conflict resolution.",
                    sender: 'agent',
                    timestamp: new Date().toISOString()
                }
            ]);
        }
    }, [messages.length, twgName]); // Update welcome if twgName loads late? careful with loops

    // ... (omitted for brevity, assume standard existing code is preserved if unchanged, but ReplaceFileContent requires context match)
    // Actually, ReplaceFileContent replaces a block. I need to replace from signature down to header.
    // I will target the Signature line and the Header lines.
    // But they are far apart (Line 8 vs Line 167).
    // I should use `multi_replace_file_content` or just replace the header if I can't change signature easily without context.
    // Wait, signature is line 8.
    // Header is line 167.
    // I will use `replace_file_content` for the signature and `replace_file_content` for the header? No, parallel calls not allowed on same file usually, or discouraged.
    // I will use `multi_replace_file_content`.

    // Wait, Replace 1: Signature
    // Replace 2: Welcome Message (Lines 28-41)
    // Replace 3: Header Display (Lines 167)

    // This is perfect for `multi_replace_file_content`.

    // Lint fix: "Property 'twgName' does not exist..." (ID: 29ee6...)
    // This tool call will fix it.


    // Auto-scroll to bottom (Scoped to container to prevent page jump)
    useEffect(() => {
        if (messagesContainerRef.current) {
            const { scrollHeight, clientHeight } = messagesContainerRef.current;
            messagesContainerRef.current.scrollTo({
                top: scrollHeight - clientHeight,
                behavior: 'smooth'
            });
        }
    }, [messages, streamingState]);

    const handleSendMessage = async () => {
        if (!input.trim() || isStreaming) return;

        const content = input.trim();
        setInput('');

        const userMsg: ChatMessage = {
            message_id: Date.now().toString(),
            conversation_id: conversationId || '',
            message_type: ChatMessageType.USER_TEXT,
            content: content,
            sender: 'user',
            timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, userMsg]);

        const request: EnhancedChatRequest = {
            message: content,
            conversation_id: conversationId,
            twg_id: propTwgId || (user?.role !== UserRole.ADMIN ? user?.twg_ids?.[0] : undefined) // Pass TWG Context
        };

        // DEBUG: Log the request details
        console.log('[COPILOT] Sending request:', {
            twg_id: request.twg_id,
            propTwgId,
            userRole: user?.role,
            userTwgIds: user?.twg_ids
        });

        await sendStreamingMessage(
            request,
            (event: StreamEvent) => {
                if (event.type === 'start' && event.conversation_id) {
                    setConversationId(event.conversation_id);
                }
            },
            (finalMsg: any) => {
                setMessages(prev => [...prev, finalMsg]);
            },
            (err: string) => {
                setMessages(prev => [...prev, {
                    message_id: Date.now().toString(),
                    conversation_id: conversationId || '',
                    message_type: ChatMessageType.SYSTEM,
                    content: `Error: ${err}`,
                    sender: 'system',
                    timestamp: new Date().toISOString()
                }]);
            }
        );
    };

    // Fetch TWGs if authorized
    useEffect(() => {
        const canMention = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD;
        if (canMention && twgs.length === 0) {
            import('../../services/twgService').then(mod => {
                mod.default.listTWGs().then(data => setTwgs(data)).catch(console.error);
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
                                    components={{
                                        p: ({ node, ...props }: any) => <p className="mb-2 last:mb-0" {...props} />,
                                        ul: ({ node, ...props }: any) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
                                        ol: ({ node, ...props }: any) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
                                        li: ({ node, ...props }: any) => <li className="pl-1" {...props} />,
                                        strong: ({ node, ...props }: any) => <strong className="font-bold text-slate-900 dark:text-white" {...props} />,
                                        a: ({ node, ...props }: any) => <a className="text-blue-500 hover:underline" {...props} />
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
                    <div className="flex gap-3">
                        <div className="w-6 h-6 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 transition-colors">
                            <span className="material-symbols-outlined text-[14px] text-blue-600 animate-spin">sync</span>
                        </div>
                        <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-2xl rounded-tl-none transition-colors border border-slate-100 dark:border-slate-700">
                            <div className="flex flex-col gap-1">
                                <p className="text-xs text-slate-500 dark:text-slate-400 font-bold animate-pulse">
                                    {currentStatus || 'Thinking...'}
                                </p>
                                {currentTool && (
                                    <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
                                        <span className="material-symbols-outlined text-[10px]">build</span>
                                        Using: {currentTool}
                                    </div>
                                )}
                            </div>
                        </div>
                        <button
                            onClick={cancelStream}
                            className="w-6 h-6 rounded-full bg-slate-100 hover:bg-red-100 text-slate-400 hover:text-red-500 flex items-center justify-center transition-colors"
                            title="Stop generating"
                        >
                            <span className="material-symbols-outlined text-[14px]">stop</span>
                        </button>
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
