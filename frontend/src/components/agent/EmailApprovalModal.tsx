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

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-full bg-teal-600 flex items-center justify-center">
                            <span className="material-symbols-outlined text-white text-[20px]">mail</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-[#0d121b] dark:text-white">Email Approval Required</h2>
                            <p className="text-xs text-[#6b7280] dark:text-[#9ca3af]">{approvalRequest.message}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="clickable-scale p-2 hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
                    >
                        <span className="material-symbols-outlined text-[#6b7280]">close</span>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {/* Context */}
                    {approvalRequest.draft.context && (
                        <div className="bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-lg p-4">
                            <div className="flex items-start gap-2">
                                <span className="material-symbols-outlined text-teal-600 dark:text-teal-400 text-[18px] mt-0.5">info</span>
                                <div>
                                    <div className="text-xs font-semibold text-teal-900 dark:text-teal-100 mb-1">Context</div>
                                    <div className="text-sm text-teal-800 dark:text-teal-200">{approvalRequest.draft.context}</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Recipients */}
                    <div>
                        <label className="block text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-2">
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
                                className="w-full px-3 py-2 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg bg-white dark:bg-[#0d121b] text-sm text-[#0d121b] dark:text-white focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500"
                            />
                        ) : (
                            <div className="flex flex-wrap gap-2">
                                {approvalRequest.draft.to.map((email, idx) => (
                                    <span key={idx} className="px-3 py-1 bg-gray-100 dark:bg-[#2d3748] text-sm text-[#0d121b] dark:text-white rounded-full">
                                        {email}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* CC */}
                    {(approvalRequest.draft.cc || isEditing) && (
                        <div>
                            <label className="block text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-2">
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
                                    className="w-full px-3 py-2 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg bg-white dark:bg-[#0d121b] text-sm text-[#0d121b] dark:text-white focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500"
                                />
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {approvalRequest.draft.cc?.map((email, idx) => (
                                        <span key={idx} className="px-3 py-1 bg-gray-100 dark:bg-[#2d3748] text-sm text-[#0d121b] dark:text-white rounded-full">
                                            {email}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Subject */}
                    <div>
                        <label className="block text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-2">
                            Subject:
                        </label>
                        {isEditing ? (
                            <input
                                type="text"
                                value={editedDraft.subject}
                                onChange={(e) => setEditedDraft({ ...editedDraft, subject: e.target.value })}
                                className="w-full px-3 py-2 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg bg-white dark:bg-[#0d121b] text-sm text-[#0d121b] dark:text-white focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500"
                            />
                        ) : (
                            <div className="px-3 py-2 bg-gray-50 dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-sm text-[#0d121b] dark:text-white font-medium">
                                {approvalRequest.draft.subject}
                            </div>
                        )}
                    </div>

                    {/* Body */}
                    <div>
                        <label className="block text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-2">
                            Message:
                        </label>
                        {isEditing ? (
                            <div className="bg-white dark:bg-[#0d121b] text-black dark:text-white rounded-lg overflow-hidden">
                                <ReactQuill
                                    theme="snow"
                                    value={editedDraft.html_body || editedDraft.body}
                                    onChange={(content) => setEditedDraft({ ...editedDraft, html_body: content, body: content.replace(/<[^>]+>/g, '') })}
                                    className="h-64 mb-12"
                                />
                            </div>
                        ) : (
                            <div
                                className="px-4 py-3 bg-gray-50 dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-sm text-gray-900 dark:text-gray-100 max-h-64 overflow-y-auto prose dark:prose-invert max-w-none [&_.email-wrapper]:text-black [&_.email-wrapper]:!bg-white"
                                dangerouslySetInnerHTML={{ __html: approvalRequest.draft.html_body || approvalRequest.draft.body.replace(/\n/g, '<br/>') }}
                            />
                        )}
                    </div>

                    {/* Attachments */}
                    {approvalRequest.draft.attachments && approvalRequest.draft.attachments.length > 0 && (
                        <div>
                            <label className="block text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-2">
                                Attachments:
                            </label>
                            <div className="space-y-2">
                                {approvalRequest.draft.attachments.map((file, idx) => (
                                    <div key={idx} className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg">
                                        <span className="material-symbols-outlined text-[#6b7280] text-[18px]">attach_file</span>
                                        <span className="text-sm text-[#0d121b] dark:text-white">{file.split('/').pop()}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Decline reason input */}
                    {showDeclineInput && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                            <label className="block text-xs font-semibold text-red-900 dark:text-red-100 mb-2">
                                Reason for declining (optional):
                            </label>
                            <textarea
                                value={declineReason}
                                onChange={(e) => setDeclineReason(e.target.value)}
                                rows={3}
                                placeholder="Why are you declining this email?"
                                className="w-full px-3 py-2 border border-red-300 dark:border-red-700 rounded-lg bg-white dark:bg-[#1a202c] text-sm text-[#0d121b] dark:text-white focus:ring-2 focus:ring-red-500/30 focus:border-red-500"
                            />
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-[#e7ebf3] dark:border-[#2d3748] bg-gray-50 dark:bg-[#0d121b]">
                    <button
                        onClick={() => setIsEditing(!isEditing)}
                        className="clickable-scale flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
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
                                    className="clickable-scale flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg transition-all"
                                >
                                    <span className="material-symbols-outlined text-[18px]">cancel</span>
                                    Decline
                                </button>
                                <button
                                    onClick={handleApprove}
                                    disabled={isApproving}
                                    className={`clickable-scale flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-md hover:shadow-lg transition-all ${isApproving ? 'opacity-75 cursor-not-allowed' : ''}`}
                                >
                                    {isApproving ? (
                                        <span className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
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
                                    className="clickable-scale px-4 py-2 text-sm font-medium text-[#6b7280] dark:text-[#9ca3af] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleDecline}
                                    className="clickable-scale flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-md hover:shadow-lg transition-all"
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
