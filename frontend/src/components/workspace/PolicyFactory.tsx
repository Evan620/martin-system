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
            case 'zero_draft': return 'border-t-blue-500';
            case 'rap_mode': return 'border-t-purple-500';
            case 'declaration_txt': return 'border-t-emerald-500';
            default: return 'border-t-slate-500';
        }
    };

    return (
        <div className="h-full flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-display font-bold text-slate-900 dark:text-white">Policy & Content Factory</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Manufacture, Refine, and Finalize Technical Outputs</p>
                </div>
                <button className="clickable-scale px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-teal-900/20 transition-all flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px]">add</span>
                    New Zero Draft
                </button>
            </div>

            {/* Factory Floor (Kanban) */}
            <div className="grid grid-cols-3 gap-6 h-full overflow-hidden">
                {['zero_draft', 'rap_mode', 'declaration_txt'].map((type) => (
                    <div key={type} className="flex flex-col h-full bg-slate-50 dark:bg-slate-800/20 rounded-2xl border border-slate-100 dark:border-slate-700/50 overflow-hidden">
                        {/* Column Header */}
                        <div className={`p-4 bg-white dark:bg-slate-800 border-b border-slate-100 dark:border-slate-700 border-t-4 ${getColumnColor(type)}`}>
                            <div className="flex justify-between items-center">
                                <h3 className="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-xs">{getColumnTitle(type)}</h3>
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
                                    className="clickable-scale p-4 cursor-pointer hover:border-teal-500/50 hover:shadow-md transition-all group"
                                    onClick={() => setActiveDraft(draft)}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <Badge variant={draft.type === 'zero_draft' ? 'info' : draft.type === 'rap_mode' ? 'warning' : 'success'} size="sm" className="bg-opacity-10">
                                            {draft.status}
                                        </Badge>
                                        <span className="text-[10px] text-slate-400 font-bold">{draft.lastUpdated}</span>
                                    </div>
                                    <h4 className="font-bold text-sm text-slate-900 dark:text-white mb-2 leading-tight group-hover:text-teal-500 transition-colors">
                                        {draft.title}
                                    </h4>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-3">
                                        {draft.content_preview}
                                    </p>
                                    <div className="flex items-center gap-2 border-t border-slate-50 dark:border-slate-800 pt-3">
                                        <Avatar size="xs" fallback="AI" className="bg-slate-100 dark:bg-slate-700 text-slate-500" />
                                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">{draft.author}</span>
                                    </div>
                                </Card>
                            ))}
                            {/* Empty State placeholder */}
                            {drafts.filter(d => d.type === type).length === 0 && (
                                <div className="h-32 flex flex-col items-center justify-center text-slate-400 opacity-50 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
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
                <div className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
                    <div className="bg-white dark:bg-[#1a202c] w-full max-w-6xl h-[80vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        {/* Modal Header */}
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center bg-white dark:bg-[#1a202c]">
                            <div className="flex items-center gap-4">
                                <div className="p-2 bg-teal-50 dark:bg-teal-900/20 rounded-lg text-teal-600">
                                    <span className="material-symbols-outlined">edit_document</span>
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg text-slate-900 dark:text-white">{activeDraft.title}</h3>
                                    <p className="text-xs text-slate-500">Editing in {activeDraft.type === 'zero_draft' ? 'Zero Draft' : activeDraft.type === 'rap_mode' ? 'Rapporteur' : 'Declaration'} Mode</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Auto-saved 2m ago</span>
                                <button className="clickable-scale px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-lg font-bold text-xs hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                                    Share
                                </button>
                                <button className="clickable-scale px-4 py-2 bg-teal-600 text-white rounded-lg font-bold text-xs hover:bg-teal-500 transition-colors">
                                    Save & Close
                                </button>
                                <button
                                    onClick={() => setActiveDraft(null)}
                                    className="clickable-scale p-2 text-slate-400 hover:text-slate-600 transition-colors"
                                >
                                    <span className="material-symbols-outlined">close</span>
                                </button>
                            </div>
                        </div>

                        {/* Modal Body: Split View */}
                        <div className="flex-1 flex overflow-hidden">
                            {/* Left: AI Context / Chat */}
                            <div className="w-1/3 bg-slate-50 dark:bg-[#0d121b] border-r border-slate-100 dark:border-slate-700 flex flex-col">
                                <div className="p-4 border-b border-slate-100 dark:border-slate-800">
                                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <span className="material-symbols-outlined text-[16px]">smart_toy</span>
                                        Context & Research
                                    </h4>
                                </div>
                                <div className="flex-1 p-4 overflow-y-auto">
                                    <div className="bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-100 dark:border-slate-700 mb-3">
                                        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                                            Based on the transcript from "Session 4", here is the suggested paragraph for the Energy Clause.
                                        </p>
                                    </div>
                                    {/* Mock Chat Input */}
                                </div>
                                <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-[#1a202c]">
                                    <input
                                        type="text"
                                        placeholder="Ask AI to refine text..."
                                        className="w-full text-xs bg-slate-50 dark:bg-slate-800 border-none rounded-lg p-3 focus:ring-1 focus:ring-teal-500"
                                    />
                                </div>
                            </div>

                            {/* Right: Document Editor */}
                            <div className="flex-1 bg-white dark:bg-[#1a202c] overflow-y-auto p-12">
                                <div className="max-w-3xl mx-auto space-y-6 text-slate-800 dark:text-slate-200 font-serif leading-loose">
                                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-8">{activeDraft.title}</h1>
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
