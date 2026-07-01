import { useState } from 'react';
import { Card, Badge, Avatar } from '../../components/ui';

interface Draft {
    id: string;
    title: string;
    type: 'zero_draft' | 'rap_mode' | 'declaration_txt' | 'final';
    lastUpdated: string;
    author: string;
    status: 'Drafting' | 'Review' | 'Approved';
    content_preview: string;
}

export default function PolicyFactory() {
    const [activeDraft, setActiveDraft] = useState<Draft | null>(null);

    // Mock Data reflecting the new Backend Enum
    const drafts: Draft[] = [
        {
            id: 'd1',
            title: 'Energy Transition Zero Draft v1',
            type: 'zero_draft',
            lastUpdated: '2 hours ago',
            author: 'System (AI)',
            status: 'Drafting',
            content_preview: 'The transition to renewable energy sources must be prioritized...'
        },
        {
            id: 'd2',
            title: 'Technical Note: Cross-Border Grids',
            type: 'rap_mode',
            lastUpdated: '1 day ago',
            author: 'Rapporteur Mode',
            status: 'Review',
            content_preview: 'Summary of technical session on voltage harmonization...'
        },
        {
            id: 'd3',
            title: 'Abuja Declaration: Energy Clause',
            type: 'declaration_txt',
            lastUpdated: '3 days ago',
            author: 'Secretariat Lead',
            status: 'Approved',
            content_preview: 'WE, the Heads of State, DECLARE our commitment to...'
        }
    ];

    const getColumnTitle = (type: string) => {
        switch (type) {
            case 'zero_draft': return 'Zero Drafts (AI Gen)';
            case 'rap_mode': return 'Rapporteur Outputs';
            case 'declaration_txt': return 'Declaration Language';
            default: return 'Final Documents';
        }
    };

    const getColumnColor = (type: string) => {
        switch (type) {
            case 'zero_draft': return 'var(--accent)';
            case 'rap_mode': return 'var(--navy)';
            case 'declaration_txt': return 'var(--sage)';
            default: return 'var(--ink-500)';
        }
    };

    return (
        <div className="h-full flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>Policy & Content Factory</h2>
                    <p className="text-sm" style={{ color: 'var(--ink-500)' }}>Manufacture, Refine, and Finalize Technical Outputs</p>
                </div>
                <button
                    className="clickable-scale px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                >
                    <span className="material-symbols-outlined text-[20px]">add</span>
                    New Zero Draft
                </button>
            </div>

            {/* Factory Floor (Kanban) */}
            <div className="grid grid-cols-3 gap-6 h-full overflow-hidden">
                {['zero_draft', 'rap_mode', 'declaration_txt'].map((type) => (
                    <div
                        key={type}
                        className="flex flex-col h-full overflow-hidden"
                        style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}
                    >
                        {/* Column Header */}
                        <div
                            className="p-4"
                            style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', borderTop: `4px solid ${getColumnColor(type)}` }}
                        >
                            <div className="flex justify-between items-center">
                                <h3 className="qp-eyebrow" style={{ fontSize: '11px' }}>{getColumnTitle(type)}</h3>
                                <Badge variant="neutral" size="sm" className="font-black">
                                    {drafts.filter(d => d.type === type).length}
                                </Badge>
                            </div>
                        </div>

                        {/* Column Content */}
                        <div className="flex-1 p-3 space-y-3 overflow-y-auto custom-scrollbar">
                            {drafts.filter(d => d.type === type).map((draft) => (
                                <Card
                                    key={draft.id}
                                    className="clickable-scale p-4 cursor-pointer hover:shadow-md transition-all group"
                                    onClick={() => setActiveDraft(draft)}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <Badge variant={draft.type === 'zero_draft' ? 'info' : draft.type === 'rap_mode' ? 'warning' : 'success'} size="sm" className="bg-opacity-10">
                                            {draft.status}
                                        </Badge>
                                        <span className="text-[10px] font-bold" style={{ color: 'var(--ink-400)' }}>{draft.lastUpdated}</span>
                                    </div>
                                    <h4
                                        className="font-bold text-sm mb-2 leading-tight transition-colors group-hover:[color:var(--accent)]"
                                        style={{ color: 'var(--ink-900)' }}
                                    >
                                        {draft.title}
                                    </h4>
                                    <p className="text-xs line-clamp-2 mb-3" style={{ color: 'var(--ink-500)' }}>
                                        {draft.content_preview}
                                    </p>
                                    <div className="flex items-center gap-2 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
                                        <Avatar size="xs" fallback="AI" style={{ background: 'var(--surface-2)', color: 'var(--ink-500)' }} />
                                        <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: 'var(--ink-500)' }}>{draft.author}</span>
                                    </div>
                                </Card>
                            ))}
                            {/* Empty State placeholder */}
                            {drafts.filter(d => d.type === type).length === 0 && (
                                <div
                                    className="h-32 flex flex-col items-center justify-center opacity-70 border-2 border-dashed rounded-xl"
                                    style={{ color: 'var(--ink-400)', borderColor: 'var(--border)', borderRadius: 'var(--radius-ctl)' }}
                                >
                                    <span className="material-symbols-outlined text-3xl mb-1">post_add</span>
                                    <span className="text-xs font-bold uppercase">No Items</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Editor Modal (Mock) */}
            {activeDraft && (
                <div className="fixed inset-0 z-[100] backdrop-blur-sm flex items-center justify-center p-6" style={{ background: 'rgba(0,0,0,0.5)' }}>
                    <div
                        className="w-full max-w-6xl h-[80vh] shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200"
                        style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}
                    >
                        {/* Modal Header */}
                        <div
                            className="px-6 py-4 flex justify-between items-center"
                            style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}
                        >
                            <div className="flex items-center gap-4">
                                <div className="p-2 rounded-lg" style={{ background: 'var(--accent-soft)', color: 'var(--accent)', borderRadius: 'var(--radius-ctl)' }}>
                                    <span className="material-symbols-outlined">edit_document</span>
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg" style={{ color: 'var(--ink-900)' }}>{activeDraft.title}</h3>
                                    <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Editing in {activeDraft.type === 'zero_draft' ? 'Zero Draft' : activeDraft.type === 'rap_mode' ? 'Rapporteur' : 'Declaration'} Mode</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--ink-400)' }}>Auto-saved 2m ago</span>
                                <button
                                    className="clickable-scale px-4 py-2 rounded-lg font-bold text-xs transition-colors"
                                    style={{ background: 'var(--surface-2)', color: 'var(--ink-700)', borderRadius: 'var(--radius-ctl)' }}
                                >
                                    Share
                                </button>
                                <button
                                    className="clickable-scale px-4 py-2 rounded-lg font-bold text-xs transition-colors"
                                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                                >
                                    Save & Close
                                </button>
                                <button
                                    onClick={() => setActiveDraft(null)}
                                    className="clickable-scale p-2 transition-colors hover:[color:var(--ink-700)]"
                                    style={{ color: 'var(--ink-400)' }}
                                >
                                    <span className="material-symbols-outlined">close</span>
                                </button>
                            </div>
                        </div>

                        {/* Modal Body: Split View */}
                        <div className="flex-1 flex overflow-hidden">
                            {/* Left: AI Context / Chat */}
                            <div className="w-1/3 flex flex-col" style={{ background: 'var(--surface-2)', borderRight: '1px solid var(--border)' }}>
                                <div className="p-4" style={{ borderBottom: '1px solid var(--border)' }}>
                                    <h4 className="qp-eyebrow flex items-center gap-2" style={{ fontSize: '11px' }}>
                                        <span className="material-symbols-outlined text-[16px]">smart_toy</span>
                                        Context & Research
                                    </h4>
                                </div>
                                <div className="flex-1 p-4 overflow-y-auto">
                                    <div className="p-3 rounded-lg mb-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)' }}>
                                        <p className="text-xs leading-relaxed" style={{ color: 'var(--ink-600)' }}>
                                            Based on the transcript from "Session 4", here is the suggested paragraph for the Energy Clause.
                                        </p>
                                    </div>
                                    {/* Mock Chat Input */}
                                </div>
                                <div className="p-4" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
                                    <input
                                        type="text"
                                        placeholder="Ask AI to refine text..."
                                        className="w-full text-xs border-none rounded-lg p-3 focus:ring-1"
                                        style={{ background: 'var(--surface-2)', color: 'var(--ink-800)', borderRadius: 'var(--radius-ctl)' }}
                                    />
                                </div>
                            </div>

                            {/* Right: Document Editor */}
                            <div className="flex-1 overflow-y-auto p-12" style={{ background: 'var(--surface)' }}>
                                <div className="max-w-3xl mx-auto space-y-6 font-serif leading-loose" style={{ color: 'var(--ink-800)' }}>
                                    <h1 className="text-3xl font-bold mb-8" style={{ color: 'var(--ink-900)' }}>{activeDraft.title}</h1>
                                    <p>
                                        {activeDraft.content_preview}
                                    </p>
                                    <p>
                                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
                                    </p>
                                    <p>
                                        Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
