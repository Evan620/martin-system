import { useState } from 'react';
import { Citation } from '../../services/agentService';
import { EmailApprovalRequest } from './EmailApprovalModal';

interface Message {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    citations?: Citation[];
    reactions?: MessageReaction[];
    agentName?: string;
    agentIcon?: string;
    approvalRequest?: EmailApprovalRequest;
    suggestions?: string[];
}

interface MessageReaction {
    emoji: string;
    count: number;
    users: string[];
}

interface EnhancedMessageBubbleProps {
    message: Message;
    onReact?: (messageId: string, emoji: string) => void;
    onCopy?: (content: string) => void;
    onReply?: (messageId: string) => void;
    onApprove?: (requestId: string, modifications?: any) => Promise<void> | void;
    onDecline?: (requestId: string) => void;
    onSuggestionClick?: (suggestion: string) => void;
}

// Function to parse and format markdown-like text with better styling
const formatMarkdownText = (text: string): JSX.Element => {
    const lines = text.split('\n');
    const elements: JSX.Element[] = [];

    let inCodeBlock = false;
    let codeBlockContent: string[] = [];

    lines.forEach((line, index) => {
        // Handle code blocks
        if (line.trim().startsWith('```')) {
            if (inCodeBlock) {
                // End code block
                elements.push(
                    <pre key={`code-${index}`} className="bg-slate-900 text-slate-50 rounded-lg p-4 my-3 overflow-x-auto shadow-sm border border-slate-800">
                        <code className="text-xs font-mono">
                            {codeBlockContent.join('\n')}
                        </code>
                    </pre>
                );
                codeBlockContent = [];
                inCodeBlock = false;
            } else {
                inCodeBlock = true;
            }
            return;
        }

        if (inCodeBlock) {
            codeBlockContent.push(line);
            return;
        }

        // Format inline code
        let formattedLine = line.replace(/`([^`]+)`/g, '<code class="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-xs font-mono text-blue-600 dark:text-blue-400 border border-slate-200 dark:border-slate-700">$1</code>');

        // Format bold text - EXTRA BOLD for emphasis
        formattedLine = formattedLine.replace(/\*\*(.*?)\*\*/g, '<strong class="font-extrabold text-slate-900 dark:text-white tracking-wide">$1</strong>');

        // Format italic text
        formattedLine = formattedLine.replace(/\*(.*?)\*/g, '<em class="italic text-slate-700 dark:text-slate-300">$1</em>');

        // Format links
        formattedLine = formattedLine.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 dark:text-blue-400 font-medium hover:underline underline-offset-2" target="_blank" rel="noopener noreferrer">$1</a>');

        // Handle headers
        if (/^\s*#{1,6}\s/.test(line)) {
            const match = line.match(/^\s*(#{1,6})/);
            const level = match ? match[1].length : 1;
            const content = line.replace(/^\s*#{1,6}\s/, '');

            let classes = '';
            // Gradient text for H1 for "Premium" feel
            switch (level) {
                case 1:
                    // Using inline-block so bg-clip works correctly
                    elements.push(
                        <div key={`${index}-header`} className="mb-4 mt-6 border-b pb-2 border-slate-200 dark:border-slate-700">
                            <span className="text-2xl font-extrabold bg-gradient-to-r from-blue-700 to-purple-600 bg-clip-text text-transparent inline-block" dangerouslySetInnerHTML={{ __html: content }}></span>
                        </div>
                    );
                    return;
                case 2: classes = 'text-xl font-bold mb-3 mt-5 text-slate-800 dark:text-slate-100 tracking-tight'; break;
                case 3: classes = 'text-lg font-bold mb-2 mt-4 text-slate-700 dark:text-slate-200'; break;
                case 4: classes = 'text-base font-bold mb-2 mt-3 text-slate-600 dark:text-slate-300'; break;
                case 5: classes = 'text-sm font-bold mb-1 mt-2 uppercase tracking-wide text-slate-500 dark:text-slate-400'; break;
                default: classes = 'text-sm font-bold mb-1';
            }

            elements.push(
                <div key={`${index}-header`} className={classes} dangerouslySetInnerHTML={{ __html: content }}></div>
            );
            return;
        }

        // Handle numbered lists
        if (/^\d+\.\s/.test(line)) {
            const content = line.replace(/^\d+\.\s/, '');
            elements.push(
                <div key={index} className="mb-3 pl-4 flex items-start gap-3">
                    <span className="flex-shrink-0 flex items-center justify-center size-5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-bold text-[10px] border border-blue-100 dark:border-blue-800 mt-0.5">
                        {line.match(/^\d+/)?.[0]}
                    </span>
                    <span className="text-slate-700 dark:text-slate-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: content }}></span>
                </div>
            );
            return;
        }

        // Handle bullet points (-, *, or •)
        if (/^\s*[-*•]\s/.test(line) || /^\s*•/.test(line)) {
            const indent = line.search(/[-*•]/);
            const content = line.replace(/^\s*[-*•]\s*/, '');
            if (!content.trim()) return; // Skip empty bullet lines (standalone •)
            elements.push(
                <div key={index} className="mb-2 flex items-start gap-2.5" style={{ paddingLeft: `${indent * 12}px` }}>
                    <span className="text-blue-500 dark:text-blue-400 text-lg leading-none mt-[-2px]">•</span>
                    <span className="text-slate-700 dark:text-slate-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: content }}></span>
                </div>
            );
            return;
        }

        // Empty lines
        if (line.trim() === '') {
            elements.push(<div key={index} className="h-3"></div>);
            return;
        }

        // Regular text
        elements.push(
            <div key={index} className="mb-1.5 text-slate-600 dark:text-slate-300 leading-7" dangerouslySetInnerHTML={{ __html: formattedLine }}></div>
        );
    });

    return <>{elements}</>;
};

export default function EnhancedMessageBubble({ message, onReact, onCopy, onReply, onApprove, onDecline, onSuggestionClick }: EnhancedMessageBubbleProps) {
    // Debug log to trace approval rendering
    if (message.approvalRequest) {
        console.log('[BUBBLE] Rendering bubble with approval request:', message.id, message.approvalRequest);
    }

    const [showActions, setShowActions] = useState(false);
    const [showReactions, setShowReactions] = useState(false);
    const [copied, setCopied] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editSubject, setEditSubject] = useState(message.approvalRequest?.draft.subject || '');
    const [editBody, setEditBody] = useState(message.approvalRequest?.draft.body || '');
    const [actionStatus, setActionStatus] = useState<'idle' | 'approving' | 'approved' | 'declining' | 'declined'>('idle');

    const commonReactions = ['👍', '❤️', '🎉', '🤔', '👀', '✅'];

    const handleCopy = () => {
        if (onCopy) {
            onCopy(message.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } else {
            navigator.clipboard.writeText(message.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleReact = (emoji: string) => {
        if (onReact) {
            onReact(message.id, emoji);
        }
        setShowReactions(false);
    };

    return (
        <div
            className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'} group animate-in fade-in slide-in-from-bottom-2 duration-300`}
            onMouseEnter={() => setShowActions(true)}
            onMouseLeave={() => {
                setShowActions(false);
                setShowReactions(false);
            }}
        >
            {message.role === 'agent' && (
                <div className="relative shrink-0">
                    <div className={`size-9 rounded-full ${message.agentIcon || 'bg-gradient-to-br from-blue-600 to-purple-600'} flex items-center justify-center text-white shadow-md`}>
                        <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                    </div>
                    {message.agentName && (
                        <div className="absolute -bottom-1 -right-1 size-4 rounded-full bg-green-500 border-2 border-white dark:border-[#0d121b] flex items-center justify-center">
                            <span className="material-symbols-outlined text-white text-[10px]">check</span>
                        </div>
                    )}
                </div>
            )}

            <div className="flex flex-col gap-1 max-w-[75%]">
                {/* Agent name tag for multi-agent responses */}
                {message.role === 'agent' && message.agentName && (
                    <div className="flex items-center gap-2 px-2">
                        <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">{message.agentName}</span>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500">AI Agent</span>
                    </div>
                )}

                <div className="relative">
                    {/* Message bubble */}
                    <div className={`${message.role === 'user'
                        ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg'
                        : 'bg-white dark:bg-[#1a202c] shadow-md border border-[#e7ebf3] dark:border-[#2d3748]'
                        } rounded-2xl ${message.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'} p-4 transition-all`}>
                        {/* Content */}
                        <div className={`text-sm leading-relaxed ${message.role === 'agent' ? 'text-[#0d121b] dark:text-white' : 'text-white'}`}>
                            {message.role === 'agent' ? formatMarkdownText(message.content) : message.content}
                        </div>

                        {/* Citations */}
                        {message.citations && message.citations.length > 0 && (
                            <div className="mt-4 pt-3 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                <div className="text-xs font-semibold text-[#6b7280] dark:text-[#9ca3af] mb-2 flex items-center gap-1">
                                    <span className="material-symbols-outlined text-[14px]">library_books</span>
                                    Sources
                                </div>
                                <div className="space-y-1">
                                    {message.citations.map((citation, idx) => (
                                        <div
                                            key={idx}
                                            className="text-xs text-[#6b7280] dark:text-[#9ca3af] flex items-center gap-2 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-blue-600 dark:hover:text-blue-400 transition-colors cursor-pointer group/citation"
                                        >
                                            <span className="material-symbols-outlined text-[14px] group-hover/citation:scale-110 transition-transform">article</span>
                                            <span className="flex-1">{citation.source}</span>
                                            <span className="text-[10px] opacity-60">Page {citation.page}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Inline Approval UI */}
                        {message.approvalRequest && (
                            <div className="mt-4 pt-4 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 mb-3 border border-blue-100 dark:border-blue-800">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-[18px]">mail</span>
                                        <span className="text-xs font-bold text-blue-800 dark:text-blue-200">Email Draft</span>
                                    </div>
                                    {isEditing ? (
                                        <div className="flex flex-col gap-3">
                                            <input
                                                type="text"
                                                value={editSubject}
                                                onChange={(e) => setEditSubject(e.target.value)}
                                                className="w-full px-2 py-1 text-sm font-medium border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                                placeholder="Subject"
                                            />
                                            <textarea
                                                value={editBody}
                                                onChange={(e) => setEditBody(e.target.value)}
                                                className="w-full h-32 px-2 py-1 text-xs text-slate-600 dark:text-slate-400 border border-blue-200 dark:border-blue-700 rounded bg-white dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                                                placeholder="Email Body"
                                            />
                                        </div>
                                    ) : (
                                        <>
                                            <div className="text-sm font-medium text-slate-900 dark:text-white mb-1">
                                                {editSubject}
                                            </div>
                                            <div className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
                                                {editBody}
                                            </div>
                                        </>
                                    )}
                                </div>
                                <div className="flex gap-2">
                                    {actionStatus === 'approved' && (
                                        <div className="flex-1 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-2 border border-green-100 dark:border-green-900/50">
                                            <span className="material-symbols-outlined text-[18px]">check_circle</span>
                                            Approved & Sent
                                        </div>
                                    )}

                                    {actionStatus === 'declined' && (
                                        <div className="flex-1 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-2 border border-red-100 dark:border-red-900/50">
                                            <span className="material-symbols-outlined text-[18px]">cancel</span>
                                            Declined
                                        </div>
                                    )}

                                    {actionStatus === 'idle' || actionStatus === 'approving' || actionStatus === 'declining' ? (
                                        <>
                                            {onApprove && !isEditing && (
                                                <>
                                                    <button
                                                        onClick={async () => {
                                                            setActionStatus('approving');
                                                            try {
                                                                await onApprove(message.approvalRequest!.request_id);
                                                                setActionStatus('approved');
                                                            } catch (error) {
                                                                console.error("Error approving:", error);
                                                                setActionStatus('idle');
                                                            }
                                                        }}
                                                        disabled={actionStatus !== 'idle'}
                                                        className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs font-semibold py-2 rounded-lg shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-1.5 disabled:opacity-75 disabled:cursor-not-allowed"
                                                    >
                                                        {actionStatus === 'approving' ? (
                                                            <>
                                                                <span className="size-3 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block"></span>
                                                                Sending...
                                                            </>
                                                        ) : (
                                                            <>
                                                                <span className="material-symbols-outlined text-[16px]">check_circle</span>
                                                                Approve & Send
                                                            </>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={() => setIsEditing(true)}
                                                        disabled={actionStatus !== 'idle'}
                                                        className="px-3 bg-white dark:bg-[#1a202c] border border-blue-200 dark:border-blue-900/50 text-blue-600 dark:text-blue-400 text-xs font-semibold py-2 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                                                    >
                                                        <span className="material-symbols-outlined text-[16px]">edit</span>
                                                        Edit
                                                    </button>
                                                </>
                                            )}
                                            {onApprove && isEditing && (
                                                <>
                                                    <button
                                                        onClick={async () => {
                                                            setActionStatus('approving');
                                                            try {
                                                                await onApprove(message.approvalRequest!.request_id, {
                                                                    ...message.approvalRequest!.draft,
                                                                    subject: editSubject,
                                                                    body: editBody
                                                                });
                                                                setActionStatus('approved');
                                                                setIsEditing(false);
                                                            } catch (error) {
                                                                console.error("Error saving:", error);
                                                                setActionStatus('idle');
                                                            }
                                                        }}
                                                        disabled={actionStatus !== 'idle'}
                                                        className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white text-xs font-semibold py-2 rounded-lg shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-1.5 disabled:opacity-75 disabled:cursor-not-allowed"
                                                    >
                                                        {actionStatus === 'approving' ? (
                                                            <>
                                                                <span className="size-3 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block"></span>
                                                                Saving...
                                                            </>
                                                        ) : (
                                                            <>
                                                                <span className="material-symbols-outlined text-[16px]">save</span>
                                                                Save & Send
                                                            </>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            setIsEditing(false);
                                                            setEditSubject(message.approvalRequest!.draft.subject);
                                                            setEditBody(message.approvalRequest!.draft.body);
                                                        }}
                                                        disabled={actionStatus !== 'idle'}
                                                        className="px-3 bg-white dark:bg-[#1a202c] border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 text-xs font-semibold py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
                                                    >
                                                        Cancel
                                                    </button>
                                                </>
                                            )}
                                            {onDecline && !isEditing && (
                                                <button
                                                    onClick={async () => {
                                                        setActionStatus('declining');
                                                        try {
                                                            await onDecline(message.approvalRequest!.request_id);
                                                            setActionStatus('declined');
                                                        } catch (error) {
                                                            setActionStatus('idle');
                                                        }
                                                    }}
                                                    disabled={actionStatus !== 'idle'}
                                                    className="px-4 bg-white dark:bg-[#1a202c] border border-gray-200 dark:border-gray-700 text-red-600 dark:text-red-400 text-xs font-semibold py-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                                                >
                                                    {actionStatus === 'declining' ? (
                                                        <span className="size-3 border-2 border-red-600/30 border-t-red-600 rounded-full animate-spin inline-block"></span>
                                                    ) : (
                                                        <>
                                                            <span className="material-symbols-outlined text-[16px]">cancel</span>
                                                            Decline
                                                        </>
                                                    )}
                                                </button>
                                            )}
                                        </>
                                    ) : null}
                                </div>
                            </div>
                        )}

                        {/* Reactions */}
                        {message.reactions && message.reactions.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-3 pt-2 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                {message.reactions.map((reaction, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => handleReact(reaction.emoji)}
                                        className="flex items-center gap-1 px-2 py-1 bg-slate-50 dark:bg-slate-800 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs"
                                        title={reaction.users.join(', ')}
                                    >
                                        <span>{reaction.emoji}</span>
                                        <span className="text-[10px] font-semibold text-slate-600 dark:text-slate-400">{reaction.count}</span>
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Timestamp */}
                        <div className={`text-[10px] mt-2.5 flex items-center gap-2 ${message.role === 'user' ? 'text-white/70 justify-end' : 'text-[#9ca3af]'}`}>
                            <span>{message.timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
                            {message.role === 'agent' && (
                                <>
                                    <span>•</span>
                                    <span className="flex items-center gap-1">
                                        <span className="material-symbols-outlined text-[10px]">verified</span>
                                        AI Generated
                                    </span>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Suggestions */}
                    {message.suggestions && message.suggestions.length > 0 && (
                        <div className="flex flex-col gap-2 mt-3 animate-in fade-in slide-in-from-top-1 duration-500 delay-300">
                            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 pl-1">
                                <span className="material-symbols-outlined text-[14px]">lightbulb</span>
                                <span className="font-medium">Suggested follow-ups</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {message.suggestions.map((suggestion, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => onSuggestionClick?.(suggestion)}
                                        className="text-left text-xs bg-white dark:bg-[#1a202c] border border-blue-200 dark:border-blue-900/50 text-slate-700 dark:text-slate-300 px-3 py-2 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-300 dark:hover:border-blue-700 hover:text-blue-700 dark:hover:text-blue-200 transition-all shadow-sm hover:shadow-md active:scale-95"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Action buttons */}
                    {showActions && (
                        <div className={`absolute ${message.role === 'user' ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'} top-2 flex items-center gap-1 px-2 animate-in fade-in slide-in-from-right-2 duration-200`}>
                            {/* Copy button */}
                            <button
                                onClick={handleCopy}
                                className="p-1.5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg shadow-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                                title={copied ? 'Copied!' : 'Copy message'}
                            >
                                <span className="material-symbols-outlined text-[16px] text-slate-600 dark:text-slate-400">
                                    {copied ? 'check' : 'content_copy'}
                                </span>
                            </button>

                            {/* React button */}
                            <div className="relative">
                                <button
                                    onClick={() => setShowReactions(!showReactions)}
                                    className="p-1.5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg shadow-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                                    title="Add reaction"
                                >
                                    <span className="material-symbols-outlined text-[16px] text-slate-600 dark:text-slate-400">add_reaction</span>
                                </button>

                                {/* Reaction picker */}
                                {showReactions && (
                                    <div className="absolute top-full mt-1 right-0 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg shadow-xl p-2 flex gap-1 animate-in fade-in slide-in-from-top-2 duration-200 z-10">
                                        {commonReactions.map((emoji) => (
                                            <button
                                                key={emoji}
                                                onClick={() => handleReact(emoji)}
                                                className="p-2 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors text-lg hover:scale-125 transition-transform"
                                            >
                                                {emoji}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Reply button */}
                            {onReply && (
                                <button
                                    onClick={() => onReply(message.id)}
                                    className="p-1.5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg shadow-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                                    title="Reply"
                                >
                                    <span className="material-symbols-outlined text-[16px] text-slate-600 dark:text-slate-400">reply</span>
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {message.role === 'user' && (
                <div className="size-9 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center shrink-0 shadow-md">
                    <span className="material-symbols-outlined text-white text-[18px]">person</span>
                </div>
            )}
        </div>
    );
}
