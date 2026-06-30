import { useEffect, useState } from 'react';
import { getAutonomousLog, AutonomousLogResponse } from '../../services/dashboardService';

export default function SupervisorActionsCard() {
    const [autonomousData, setAutonomousData] = useState<AutonomousLogResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchLog() {
            try {
                const data = await getAutonomousLog();
                setAutonomousData(data);
            } catch (error) {
                console.error("Error fetching autonomous log:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchLog();
    }, []);

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm p-6 flex items-center justify-center min-h-[200px]">
                <div className="flex flex-col items-center gap-2">
                    <div className="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-xs text-[#4c669a]">Loading autonomous actions...</p>
                </div>
            </div>
        );
    }

    if (!autonomousData) return null;

    return (
        <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-teal-500">smart_toy</span>
                    <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">Supervisor Autonomous Actions</h3>
                </div>
                <div className="flex items-center gap-2 bg-teal-50 dark:bg-teal-900/20 px-3 py-1 rounded-full border border-teal-100 dark:border-teal-800/30">
                    <span className="text-xs font-bold text-teal-700 dark:text-teal-300">
                        {(autonomousData.stats.resolution_rate * 100).toFixed(0)}% Auto-Resolution
                    </span>
                </div>
            </div>

            <div className="flex flex-col gap-6">
                {/* Stats Overview */}
                <div className="grid grid-cols-3 gap-4">
                    <div className="bg-[#f8fafc] dark:bg-[#2d3748] p-3 rounded-lg border border-[#e2e8f0] dark:border-[#4a5568]">
                        <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] uppercase font-bold tracking-wider mb-1">Detected</p>
                        <p className="text-xl font-black text-[#0d121b] dark:text-white">{autonomousData.stats.total_detected}</p>
                    </div>
                    <div className="bg-[#f0fdf4] dark:bg-[#22543d]/30 p-3 rounded-lg border border-[#bbf7d0] dark:border-[#2f855a]">
                        <p className="text-xs text-green-600 dark:text-green-400 uppercase font-bold tracking-wider mb-1">Resolved</p>
                        <p className="text-xl font-black text-green-700 dark:text-green-300">{autonomousData.stats.auto_resolved}</p>
                    </div>
                    <div className="bg-[#fff7ed] dark:bg-[#7b341e]/30 p-3 rounded-lg border border-[#fed7aa] dark:border-[#9c4221]">
                        <p className="text-xs text-orange-600 dark:text-orange-400 uppercase font-bold tracking-wider mb-1">Escalated</p>
                        <p className="text-xl font-black text-orange-700 dark:text-orange-300">{autonomousData.stats.escalated}</p>
                    </div>
                </div>

                {/* Activity Log */}
                <div>
                    <h4 className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">Recent Activity</h4>
                    <div className="space-y-3">
                        {autonomousData.conflicts.slice(0, 5).map((conflict) => (
                            <div key={conflict.id} className="flex gap-3 items-start p-3 hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors border border-transparent hover:border-[#e2e8f0] dark:hover:border-[#4a5568]">
                                <div className={`mt-0.5 size-2 rounded-full shrink-0 ${conflict.status === 'resolved' && JSON.stringify(conflict.resolution_log || []).includes('auto_resolved')
                                    ? 'bg-green-500'
                                    : 'bg-orange-500'
                                    }`}></div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-start mb-0.5">
                                        <p className="text-sm font-semibold text-[#0d121b] dark:text-white truncate pr-2">
                                            {conflict.conflict_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                        </p>
                                        <span className="text-[10px] text-[#4c669a] dark:text-[#a0aec0] shrink-0">
                                            {formatDate(conflict.detected_at)}
                                        </span>
                                    </div>
                                    <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] line-clamp-2 mb-1.5">{conflict.description}</p>

                                    {conflict.status === 'resolved' && JSON.stringify(conflict.resolution_log || []).includes('auto_resolved') ? (
                                        <div className="flex items-center gap-1.5 text-[10px] font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 w-fit px-2 py-0.5 rounded">
                                            <span className="material-symbols-outlined text-[12px]">check_circle</span>
                                            Auto-Resolved
                                        </div>
                                    ) : conflict.status === 'escalated' ? (
                                        <div className="flex items-center gap-1.5 text-[10px] font-medium text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 w-fit px-2 py-0.5 rounded">
                                            <span className="material-symbols-outlined text-[12px]">warning</span>
                                            Escalated to Admin
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        ))}
                        {autonomousData.conflicts.length === 0 && (
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] italic text-center py-4">No recent autonomous actions.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
