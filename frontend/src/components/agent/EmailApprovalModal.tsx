import { useState } from 'react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

export interface EmailDraft {
    draft_id: string;
    to: string[];
    subject: string;
    body: string;
    html_body?: string;
    cc?: string[];
    bcc?: string[];
    attachments?: string[];
    created_at: string;
    context?: string;
}

export interface EmailApprovalRequest {
    request_id: string;
    draft: EmailDraft;
    message: string;
}

interface EmailApprovalModalProps {
    approvalRequest: EmailApprovalRequest;
    onApprove: (requestId: string, modifications?: EmailDraft) => void;
    onDecline: (requestId: string, reason?: string) => void;
    onClose: () => void;
}

export default function EmailApprovalModal({
    approvalRequest,
    onApprove,
    onDecline,
    onClose
}: EmailApprovalModalProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editedDraft, setEditedDraft] = useState<EmailDraft>(approvalRequest.draft);
    const [declineReason, setDeclineReason] = useState('');
    const [showDeclineInput, setShowDeclineInput] = useState(false);
    const [isApproving, setIsApproving] = useState(false);

    const handleApprove = async () => {
        setIsApproving(true);
        try {
            if (isEditing) {
                await onApprove(approvalRequest.request_id, editedDraft);
            } else {
                await onApprove(approvalRequest.request_id);
            }
        } finally {
            setIsApproving(false);
        }
    };

    const handleDecline = () => {
        onDecline(approvalRequest.request_id, declineReason || undefined);
    };

    const eyebrowStyle: React.CSSProperties = {
        display: 'block',
        fontSize: '10px',
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        fontWeight: 600,
        color: 'var(--ink-500)',
        marginBottom: '8px',
    };

    const inputStyle: React.CSSProperties = {
        width: '100%',
        padding: '8px 12px',
        borderRadius: 'var(--radius-ctl)',
        border: '1px solid var(--border)',
        background: 'var(--surface)',
        color: 'var(--ink-900)',
        fontSize: '14px',
        outline: 'none',
    };

    const readonlyBoxStyle: React.CSSProperties = {
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-ctl)',
        color: 'var(--ink-900)',
    };

    return (
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
            <div
                className="w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-full flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                            <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--accent-ink)' }}>mail</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold" style={{ color: 'var(--ink-900)' }}>Email Approval Required</h2>
                            <p className="text-xs" style={{ color: 'var(--ink-500)' }}>{approvalRequest.message}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="clickable-scale p-2 rounded-lg qp-transition"
                        style={{ color: 'var(--ink-500)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {/* Context */}
                    {approvalRequest.draft.context && (
                        <div
                            className="p-4"
                            style={{
                                background: 'var(--accent-soft)',
                                border: '1px solid color-mix(in srgb, var(--accent) 30%, var(--border))',
                                borderRadius: 'var(--radius-ctl)',
                            }}
                        >
                            <div className="flex items-start gap-2">
                                <span className="material-symbols-outlined text-[18px] mt-0.5" style={{ color: 'var(--accent)' }}>info</span>
                                <div>
                                    <div className="text-xs font-semibold mb-1" style={{ color: 'var(--ink-900)' }}>Context</div>
                                    <div className="text-sm" style={{ color: 'var(--ink-700)' }}>{approvalRequest.draft.context}</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Recipients */}
                    <div>
                        <label style={eyebrowStyle}>
                            To:
                        </label>
                        {isEditing ? (
                            <input
                                type="text"
                                value={editedDraft.to.join(', ')}
                                onChange={(e) => setEditedDraft({
                                    ...editedDraft,
                                    to: e.target.value.split(',').map(email => email.trim())
                                })}
                                style={inputStyle}
                            />
                        ) : (
                            <div className="flex flex-wrap gap-2">
                                {approvalRequest.draft.to.map((email, idx) => (
                                    <span key={idx} className="px-3 py-1 text-sm rounded-full" style={{ background: 'var(--surface-2)', color: 'var(--ink-900)' }}>
                                        {email}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* CC */}
                    {(approvalRequest.draft.cc || isEditing) && (
                        <div>
                            <label style={eyebrowStyle}>
                                CC:
                            </label>
                            {isEditing ? (
                                <input
                                    type="text"
                                    value={editedDraft.cc?.join(', ') || ''}
                                    onChange={(e) => setEditedDraft({
                                        ...editedDraft,
                                        cc: e.target.value ? e.target.value.split(',').map(email => email.trim()) : undefined
                                    })}
                                    placeholder="Optional CC recipients (comma-separated)"
                                    style={inputStyle}
                                />
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {approvalRequest.draft.cc?.map((email, idx) => (
                                        <span key={idx} className="px-3 py-1 text-sm rounded-full" style={{ background: 'var(--surface-2)', color: 'var(--ink-900)' }}>
                                            {email}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Subject */}
                    <div>
                        <label style={eyebrowStyle}>
                            Subject:
                        </label>
                        {isEditing ? (
                            <input
                                type="text"
                                value={editedDraft.subject}
                                onChange={(e) => setEditedDraft({ ...editedDraft, subject: e.target.value })}
                                style={inputStyle}
                            />
                        ) : (
                            <div className="px-3 py-2 text-sm font-medium" style={readonlyBoxStyle}>
                                {approvalRequest.draft.subject}
                            </div>
                        )}
                    </div>

                    {/* Body */}
                    <div>
                        <label style={eyebrowStyle}>
                            Message:
                        </label>
                        {isEditing ? (
                            <div className="rounded-lg overflow-hidden" style={{ background: 'var(--surface)', color: 'var(--ink-900)' }}>
                                <ReactQuill
                                    theme="snow"
                                    value={editedDraft.html_body || editedDraft.body}
                                    onChange={(content) => setEditedDraft({ ...editedDraft, html_body: content, body: content.replace(/<[^>]+>/g, '') })}
                                    className="h-64 mb-12"
                                />
                            </div>
                        ) : (
                            <div
                                className="px-4 py-3 text-sm max-h-64 overflow-y-auto prose dark:prose-invert max-w-none [&_.email-wrapper]:text-black [&_.email-wrapper]:!bg-white"
                                style={{ ...readonlyBoxStyle, color: 'var(--ink-700)' }}
                                dangerouslySetInnerHTML={{ __html: approvalRequest.draft.html_body || approvalRequest.draft.body.replace(/\n/g, '<br/>') }}
                            />
                        )}
                    </div>

                    {/* Attachments */}
                    {approvalRequest.draft.attachments && approvalRequest.draft.attachments.length > 0 && (
                        <div>
                            <label style={eyebrowStyle}>
                                Attachments:
                            </label>
                            <div className="space-y-2">
                                {approvalRequest.draft.attachments.map((file, idx) => (
                                    <div key={idx} className="flex items-center gap-2 px-3 py-2" style={readonlyBoxStyle}>
                                        <span className="material-symbols-outlined text-[18px]" style={{ color: 'var(--ink-500)' }}>attach_file</span>
                                        <span className="text-sm" style={{ color: 'var(--ink-900)' }}>{file.split('/').pop()}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Decline reason input */}
                    {showDeclineInput && (
                        <div
                            className="p-4"
                            style={{
                                background: 'color-mix(in srgb, var(--terra) 10%, transparent)',
                                border: '1px solid color-mix(in srgb, var(--terra) 30%, var(--border))',
                                borderRadius: 'var(--radius-ctl)',
                            }}
                        >
                            <label className="block text-xs font-semibold mb-2" style={{ color: 'var(--terra)' }}>
                                Reason for declining (optional):
                            </label>
                            <textarea
                                value={declineReason}
                                onChange={(e) => setDeclineReason(e.target.value)}
                                rows={3}
                                placeholder="Why are you declining this email?"
                                style={{ ...inputStyle, border: '1px solid color-mix(in srgb, var(--terra) 40%, var(--border))' }}
                            />
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                    <button
                        onClick={() => setIsEditing(!isEditing)}
                        className="clickable-scale flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg qp-transition"
                        style={{ color: 'var(--ink-700)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                        <span className="material-symbols-outlined text-[18px]">
                            {isEditing ? 'cancel' : 'edit'}
                        </span>
                        {isEditing ? 'Cancel Edit' : 'Edit Email'}
                    </button>

                    <div className="flex items-center gap-3">
                        {!showDeclineInput ? (
                            <>
                                <button
                                    onClick={() => setShowDeclineInput(true)}
                                    className="clickable-scale flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg qp-transition"
                                    style={{
                                        color: 'var(--terra)',
                                        background: 'color-mix(in srgb, var(--terra) 10%, transparent)',
                                        border: '1px solid color-mix(in srgb, var(--terra) 30%, var(--border))',
                                    }}
                                >
                                    <span className="material-symbols-outlined text-[18px]">cancel</span>
                                    Decline
                                </button>
                                <button
                                    onClick={handleApprove}
                                    disabled={isApproving}
                                    className={`clickable-scale flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg qp-transition ${isApproving ? 'opacity-75 cursor-not-allowed' : ''}`}
                                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
                                >
                                    {isApproving ? (
                                        <span className="size-4 rounded-full animate-spin" style={{ border: '2px solid color-mix(in srgb, var(--accent-ink) 30%, transparent)', borderTopColor: 'var(--accent-ink)' }}></span>
                                    ) : (
                                        <span className="material-symbols-outlined text-[18px]">send</span>
                                    )}
                                    {isApproving ? 'Sending...' : (isEditing ? 'Approve & Send (Modified)' : 'Approve & Send')}
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    onClick={() => {
                                        setShowDeclineInput(false);
                                        setDeclineReason('');
                                    }}
                                    className="clickable-scale px-4 py-2 text-sm font-medium rounded-lg qp-transition"
                                    style={{ color: 'var(--ink-500)' }}
                                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface)')}
                                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleDecline}
                                    className="clickable-scale flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg qp-transition"
                                    style={{ background: 'var(--terra)', color: '#ffffff' }}
                                >
                                    <span className="material-symbols-outlined text-[18px]">block</span>
                                    Confirm Decline
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
