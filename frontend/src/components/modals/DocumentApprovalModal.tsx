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
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-[#1e293b] w-full max-w-4xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden border border-slate-200 dark:border-slate-700">

                {/* Header */}
                <div className="p-6 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
                                {draft.document_type || 'Document'} Approval
                            </span>
                            <span className="material-symbols-outlined text-sm text-slate-400">lock</span>
                        </div>
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Review Draft Document</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">{message}</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setViewMode('edit')}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors clickable-scale ${viewMode === 'edit'
                                ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300'
                                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                                }`}
                        >
                            Edit
                        </button>
                        <button
                            onClick={() => setViewMode('preview')}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors clickable-scale ${viewMode === 'preview'
                                ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300'
                                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                                }`}
                        >
                            Preview
                        </button>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto p-6 bg-slate-50 dark:bg-[#0f172a]">
                    <div className="space-y-4">

                        {/* Title Field (Always Editable) */}
                        <div>
                            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Document Title</label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm font-medium focus:ring-2 focus:ring-teal-500 outline-none"
                            />
                        </div>

                        {/* Main Editor/Preview */}
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm min-h-[400px]">
                            {viewMode === 'edit' ? (
                                <textarea
                                    value={content}
                                    onChange={(e) => setContent(e.target.value)}
                                    className="w-full h-full min-h-[400px] p-6 bg-transparent outline-none resize-none font-mono text-sm leading-relaxed text-slate-700 dark:text-slate-300"
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
                <div className="p-6 border-t border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="material-symbols-outlined text-sm">info</span>
                        <span>Approving will save this to the Document Registry.</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleDecline}
                            disabled={isSubmitting}
                            className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors clickable-scale"
                        >
                            Decline & Stop
                        </button>
                        <button
                            onClick={handleApprove}
                            disabled={isSubmitting}
                            className={`
                                relative overflow-hidden px-6 py-2 rounded-xl text-sm font-bold text-white shadow-lg shadow-teal-500/30 transition-all
                                ${isSubmitting ? 'bg-teal-400 cursor-not-allowed' : 'bg-gradient-to-r from-teal-600 to-teal-700 hover:scale-105 active:scale-95'}
                            `}
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
