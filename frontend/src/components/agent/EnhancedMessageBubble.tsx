import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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

// Claude-style compact markdown renderer
const MarkdownContent = ({ content }: { content: string }) => (
    <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
            h1: ({ children }) => (
                <h1 className="text-base font-semibold mb-2 mt-3 first:mt-0 text-slate-900 dark:text-slate-100">{children}</h1>
            ),
            h2: ({ children }) => (
                <h2 className="text-[14px] font-semibold mb-1.5 mt-3 first:mt-0 text-slate-800 dark:text-slate-200">{children}</h2>
            ),
            h3: ({ children }) => (
                <h3 className="text-[13px] font-semibold mb-1 mt-2.5 first:mt-0 text-slate-700 dark:text-slate-300">{children}</h3>
            ),
            h4: ({ children }) => (
                <h4 className="text-[13px] font-medium mb-1 mt-2 first:mt-0 text-slate-600 dark:text-slate-300">{children}</h4>
            ),
            p: ({ children }) => (
                <p className="mb-1.5 last:mb-0 leading-[1.55]">{children}</p>
            ),
            strong: ({ children }) => (
                <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>
            ),
            em: ({ children }) => (
                <em className="italic">{children}</em>
            ),
            ul: ({ children }) => (
                <ul className="mb-1.5 space-y-0.5 pl-4 list-disc marker:text-slate-400 dark:marker:text-slate-500">{children}</ul>
            ),
            ol: ({ children }) => (
                <ol className="mb-1.5 space-y-0.5 pl-4 list-decimal marker:text-slate-400 dark:marker:text-slate-500">{children}</ol>
            ),
            li: ({ children }: any) => (
                <li className="pl-0.5 leading-[1.55]">{children}</li>
            ),
            a: ({ href, children }) => (
                <a
                    href={href}
                    className="text-teal-600 dark:text-teal-400 hover:underline underline-offset-2"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    {children}
                </a>
            ),
            code: ({ className, children }) => {
                const isBlock = className?.includes('language-');
                if (isBlock) {
                    return (
                        <pre className="bg-slate-100 dark:bg-slate-800/80 rounded-md p-3 my-2 overflow-x-auto text-[12px]">
                            <code className="font-mono">{children}</code>
                        </pre>
                    );
                }
                return (
                    <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-[12px] font-mono">
                        {children}
                    </code>
                );
            },
            pre: ({ children }) => <>{children}</>,
            blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-slate-300 dark:border-slate-600 pl-3 my-2 text-slate-500 dark:text-slate-400 italic">
                    {children}
                </blockquote>
            ),
            hr: () => <hr className="my-3 border-slate-200 dark:border-slate-700" />,
            table: ({ children }) => (
                <div className="my-2 overflow-x-auto rounded border border-slate-200 dark:border-slate-700">
                    <table className="w-full text-[12px]">{children}</table>
                </div>
            ),
            th: ({ children }) => (
                <th className="px-2 py-1.5 bg-slate-50 dark:bg-slate-800 text-left font-semibold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                    {children}
                </th>
            ),
            td: ({ children }) => (
                <td className="px-2 py-1.5 text-slate-600 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                    {children}
                </td>
            ),
        }}
    >
        {content}
    </ReactMarkdown>
);

export default function EnhancedMessageBubble({ message, onReact, onCopy, onReply, onApprove, onDecline, onSuggestionClick }: EnhancedMessageBubbleProps) {
    // Debug log to trace approval rendering
    if (message.approvalRequest) {
        console.log('[BUBBLE] Rendering bubble with approval request:', message.id, message.approvalRequest);
    }

    const [showActions, setShowActions] = useState(false);
    const [copied, setCopied] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editSubject, setEditSubject] = useState(message.approvalRequest?.draft.subject || '');
    const [editBody, setEditBody] = useState(message.approvalRequest?.draft.body || '');
    const [actionStatus, setActionStatus] = useState<'idle' | 'approving' | 'approved' | 'declining' | 'declined'>('idle');

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
        setShowActions(false);
    };

    return (
        <div
            className={`flex gap-2.5 ${message.role === 'user' ? 'justify-end' : 'justify-start'} group animate-in fade-in slide-in-from-bottom-2 duration-200`}
            onMouseEnter={() => setShowActions(true)}
            onMouseLeave={() => {
                setShowActions(false);
                setShowActions(false);
            }}
        >
            <div className={`flex flex-col gap-1 ${message.role === 'user' ? 'max-w-[72%] items-end' : 'max-w-[680px] w-full items-start'}`}>
                {/* Agent name tag */}
                {message.role === 'agent' && message.agentName && (
                    <div className="flex items-center gap-1.5">
                        <span className="size-1.5 rounded-full bg-[#7c3aed] flex-shrink-0"></span>
                        <span className="text-[11px] font-bold text-[#7c3aed] dark:text-[#a78bfa]">{message.agentName}</span>
                    </div>
                )}

                <div className="relative w-full">
                    {/* Message bubble */}
                    <div className={`${message.role === 'user'
                        ? 'bg-[#f3f4f6] dark:bg-[#1e2433] text-[#111827] dark:text-white rounded-[18px_18px_4px_18px] px-3.5 py-2.5 inline-block'
                        : 'text-[#111827] dark:text-slate-200 w-full'
                        } transition-all`}>
                        {/* Content */}
                        <div className={`text-[13px] ${message.role === 'user' ? 'leading-snug' : 'leading-[1.65]'}`}>
                            {message.role === 'agent' ? <MarkdownContent content={message.content} /> : message.content}
                        </div>


                        {/* Inline Approval UI */}
                        {message.approvalRequest && (
                            <div className="mt-4 pt-4 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                <div className="bg-teal-50 dark:bg-teal-900/20 rounded-lg p-3 mb-3 border border-teal-100 dark:border-teal-800">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="material-symbols-outlined text-teal-600 dark:text-teal-400 text-[18px]">mail</span>
                                        <span className="text-xs font-bold text-teal-800 dark:text-teal-200">Email Draft</span>
                                    </div>
                                    {isEditing ? (
                                        <div className="flex flex-col gap-3">
                                            <input
                                                type="text"
                                                value={editSubject}
                                                onChange={(e) => setEditSubject(e.target.value)}
                                                className="w-full px-2 py-1 text-sm font-medium border border-teal-200 dark:border-teal-700 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500 outline-none"
                                                placeholder="Subject"
                                            />
                                            <textarea
                                                value={editBody}
                                                onChange={(e) => setEditBody(e.target.value)}
                                                className="w-full h-32 px-2 py-1 text-xs text-slate-600 dark:text-slate-400 border border-teal-200 dark:border-teal-700 rounded bg-white dark:bg-slate-800 focus:ring-2 focus:ring-teal-500 outline-none resize-none"
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
                                                        className="clickable-scale flex-1 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold py-2 rounded-lg shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-1.5 disabled:opacity-75 disabled:cursor-not-allowed"
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
                                                        className="clickable-scale px-3 bg-white dark:bg-[#1a202c] border border-teal-200 dark:border-teal-900/50 text-teal-600 dark:text-teal-400 text-xs font-semibold py-2 rounded-lg hover:bg-teal-50 dark:hover:bg-teal-900/10 transition-colors flex items-center gap-1.5 disabled:opacity-50"
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
                                                        className="clickable-scale flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white text-xs font-semibold py-2 rounded-lg shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-1.5 disabled:opacity-75 disabled:cursor-not-allowed"
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

                    </div>

                    {/* Suggestions */}
                    {message.suggestions && message.suggestions.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2 animate-in fade-in duration-300">
                            {message.suggestions.map((suggestion, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => onSuggestionClick?.(suggestion)}
                                    className="clickable-scale text-left text-[11px] bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 px-2.5 py-1.5 rounded-lg hover:bg-teal-50 dark:hover:bg-teal-900/30 hover:border-teal-300 dark:hover:border-teal-700 hover:text-teal-600 dark:hover:text-teal-300 transition-colors"
                                >
                                    {suggestion}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Inline action buttons — shown on hover */}
                    {showActions && (
                        <div className="flex items-center gap-3 mt-1.5 animate-in fade-in duration-150">
                            <button
                                onClick={handleCopy}
                                className="flex items-center gap-1 text-[11px] text-[#d1d5db] dark:text-[#4b5563] hover:text-[#6b7280] dark:hover:text-[#9ca3af] transition-colors"
                                title={copied ? 'Copied!' : 'Copy'}
                            >
                                <span className="material-symbols-outlined text-[14px]">{copied ? 'check' : 'content_copy'}</span>
                                {copied ? 'Copied' : 'Copy'}
                            </button>
                            {onReply && (
                                <button
                                    onClick={() => onReply(message.id)}
                                    className="flex items-center gap-1 text-[11px] text-[#d1d5db] dark:text-[#4b5563] hover:text-[#6b7280] dark:hover:text-[#9ca3af] transition-colors"
                                    title="Retry"
                                >
                                    <span className="material-symbols-outlined text-[14px]">refresh</span>
                                    Retry
                                </button>
                            )}
                            <button
                                onClick={() => handleReact('👍')}
                                className="text-[11px] text-[#d1d5db] dark:text-[#4b5563] hover:text-[#6b7280] dark:hover:text-[#9ca3af] transition-colors"
                                title="Helpful"
                            >
                                👍
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
