import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { agentService } from '../../services/agentService';

interface DocumentApprovalModalProps {
    approvalRequest: any;
    onResolve: (approved: boolean, result?: any) => void;
}

export default function DocumentApprovalModal({ approvalRequest, onResolve }: DocumentApprovalModalProps) {
    const { request_id, draft, message } = approvalRequest;

    // Editable state
    const [title, setTitle] = useState(draft.title || '');
    const [content, setContent] = useState(draft.content || '');
    // const [tags, setTags] = useState(draft.tags || []);
    const [tags] = useState(draft.tags || []);

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [viewMode, setViewMode] = useState<'edit' | 'preview'>('preview');

    const handleApprove = async () => {
        setIsSubmitting(true);
        try {
            const result = await agentService.approveDocument(request_id, {
                title,
                content,
                document_type: draft.document_type,
                file_name: draft.file_name,
                tags
            });
            onResolve(true, result);
        } catch (error) {
            console.error("Failed to approve document:", error);
            // Optionally show error toast here
            setIsSubmitting(false);
        }
    };

    const handleDecline = () => {
        onResolve(false);
    };

    return (
        <div className="fixed inset-0 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200" style={{ background: 'color-mix(in srgb, var(--ink-900) 45%, transparent)' }}>
            <div className="w-full max-w-4xl flex flex-col max-h-[90vh] overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>

                {/* Header */}
                <div className="p-6 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-0.5" style={{ borderRadius: 'var(--radius-ctl)', fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                {draft.document_type || 'Document'} Approval
                            </span>
                            <span className="material-symbols-outlined text-sm" style={{ color: 'var(--ink-400)' }}>lock</span>
                        </div>
                        <h2 className="text-xl font-bold" style={{ color: 'var(--ink-900)' }}>Review Draft Document</h2>
                        <p className="text-sm" style={{ color: 'var(--ink-500)' }}>{message}</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setViewMode('edit')}
                            className="px-3 py-1.5 text-xs font-medium transition-colors clickable-scale"
                            style={{
                                borderRadius: 'var(--radius-ctl)',
                                background: viewMode === 'edit' ? 'var(--accent-soft)' : 'transparent',
                                color: viewMode === 'edit' ? 'var(--accent)' : 'var(--ink-600)',
                            }}
                        >
                            Edit
                        </button>
                        <button
                            onClick={() => setViewMode('preview')}
                            className="px-3 py-1.5 text-xs font-medium transition-colors clickable-scale"
                            style={{
                                borderRadius: 'var(--radius-ctl)',
                                background: viewMode === 'preview' ? 'var(--accent-soft)' : 'transparent',
                                color: viewMode === 'preview' ? 'var(--accent)' : 'var(--ink-600)',
                            }}
                        >
                            Preview
                        </button>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
                    <div className="space-y-4">

                        {/* Title Field (Always Editable) */}
                        <div>
                            <label className="block text-xs mb-1" style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, color: 'var(--ink-500)' }}>Document Title</label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full px-4 py-2 text-sm font-medium focus:ring-2 outline-none"
                                style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-900)' }}
                            />
                        </div>

                        {/* Main Editor/Preview */}
                        <div className="min-h-[400px]" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                            {viewMode === 'edit' ? (
                                <textarea
                                    value={content}
                                    onChange={(e) => setContent(e.target.value)}
                                    className="w-full h-full min-h-[400px] p-6 bg-transparent outline-none resize-none font-mono text-sm leading-relaxed"
                                    style={{ color: 'var(--ink-700)' }}
                                    placeholder="# Start typing..."
                                />
                            ) : (
                                <div className="prose prose-sm dark:prose-invert max-w-none p-6">
                                    <ReactMarkdown>{content}</ReactMarkdown>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-6 flex items-center justify-between" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
                    <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--ink-500)' }}>
                        <span className="material-symbols-outlined text-sm">info</span>
                        <span>Approving will save this to the Document Registry.</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleDecline}
                            disabled={isSubmitting}
                            className="px-4 py-2 text-sm font-medium transition-colors clickable-scale"
                            style={{ borderRadius: 'var(--radius-ctl)', color: 'var(--ink-600)', background: 'transparent' }}
                        >
                            Decline & Stop
                        </button>
                        <button
                            onClick={handleApprove}
                            disabled={isSubmitting}
                            className={`
                                relative overflow-hidden px-6 py-2 text-sm font-bold transition-all
                                ${isSubmitting ? 'cursor-not-allowed' : 'hover:scale-105 active:scale-95'}
                            `}
                            style={{ borderRadius: 'var(--radius-ctl)', background: 'var(--accent)', color: 'var(--accent-ink)', opacity: isSubmitting ? 0.6 : 1 }}
                        >
                            {isSubmitting ? (
                                <span className="flex items-center gap-2">
                                    <span className="material-symbols-outlined animate-spin text-sm">sync</span>
                                    Saving...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">check_circle</span>
                                    Approve and Save
                                </span>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
