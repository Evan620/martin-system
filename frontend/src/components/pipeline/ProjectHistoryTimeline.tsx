import React from 'react';
import api from '../../services/api';

interface StatusHistoryEntry {
    id: string;
    previous_status: string | null;
    new_status: string;
    change_date: string;
    changed_by: {
        id?: string;
        name: string;
        email?: string;
    };
    notes?: string;
}

interface ProjectHistoryTimelineProps {
    projectId: string;
}

export const ProjectHistoryTimeline: React.FC<ProjectHistoryTimelineProps> = ({ projectId }) => {
    const [history, setHistory] = React.useState<StatusHistoryEntry[]>([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await api.get(`/pipeline/${projectId}/history`);
                setHistory(response.data.history || []);
            } catch (err) {
                setError('Failed to load project history');
                console.error('Error fetching history:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, [projectId]);

    const getStatusColor = (status: string) => {
        const s = status.toLowerCase();
        if (s.includes('approved') || s.includes('summit_ready') || s.includes('bankable')) {
            return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
        }
        if (s.includes('review')) {
            return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
        }
        if (s.includes('revision') || s.includes('needs')) {
            return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
        }
        if (s.includes('declined')) {
            return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
        }
        if (s.includes('deal_room')) {
            return 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300';
        }
        return 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300';
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    };

    const formatStatus = (status: string) => {
        return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
                <span className="material-symbols-outlined text-4xl text-red-600 dark:text-red-400 mb-2">error</span>
                <p className="text-red-800 dark:text-red-300">{error}</p>
            </div>
        );
    }

    if (history.length === 0) {
        return (
            <div className="bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-300 dark:border-slate-600 rounded-xl p-12 text-center">
                <span className="material-symbols-outlined text-4xl text-slate-400 mb-4">history</span>
                <p className="text-slate-600 dark:text-slate-400">No status changes recorded yet.</p>
                <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">Status changes will appear here as the project progresses.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined">history</span>
                    Status History
                </h3>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                    {history.length} {history.length === 1 ? 'change' : 'changes'}
                </span>
            </div>

            <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-700"></div>

                {/* Timeline entries */}
                <div className="space-y-6">
                    {history.map((entry, index) => (
                        <div key={entry.id} className="relative flex gap-4">
                            {/* Timeline dot */}
                            <div className="relative z-10 flex-shrink-0">
                                <div className="w-12 h-12 rounded-full bg-white dark:bg-slate-800 border-2 border-teal-500 dark:border-teal-400 flex items-center justify-center shadow-sm">
                                    <span className="material-symbols-outlined text-teal-600 dark:text-teal-400 text-xl">
                                        {index === 0 ? 'radio_button_checked' : 'circle'}
                                    </span>
                                </div>
                            </div>

                            {/* Content card */}
                            <div className="flex-1 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {entry.previous_status && (
                                            <>
                                                <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(entry.previous_status)}`}>
                                                    {formatStatus(entry.previous_status)}
                                                </span>
                                                <span className="material-symbols-outlined text-slate-400 text-sm">arrow_forward</span>
                                            </>
                                        )}
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(entry.new_status)}`}>
                                            {formatStatus(entry.new_status)}
                                        </span>
                                    </div>
                                    <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap ml-2">
                                        {formatDate(entry.change_date)}
                                    </span>
                                </div>

                                <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                    <span className="material-symbols-outlined text-sm">person</span>
                                    <span>{entry.changed_by.name}</span>
                                    {entry.changed_by.email && (
                                        <span className="text-slate-400 dark:text-slate-500">• {entry.changed_by.email}</span>
                                    )}
                                </div>

                                {entry.notes && (
                                    <div className="mt-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 rounded p-2">
                                        <span className="font-medium">Note:</span> {entry.notes}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
