import { useEffect, useState } from 'react';
import ModernLayout from '../../layouts/ModernLayout';
import { getDashboardStats, getTimeline, exportDashboardReport, DashboardStats, TimelineItem } from '../../services/dashboardService';

export default function Dashboard() {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [timeline, setTimeline] = useState<TimelineItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        async function fetchData() {
            try {
                const [statsData, timelineData] = await Promise.all([
                    getDashboardStats(),
                    getTimeline()
                ]);
                setStats(statsData);
                setTimeline(timelineData);
            } catch (error) {
                console.error("Error fetching dashboard data:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    const handleExport = async () => {
        try {
            setExporting(true);
            await exportDashboardReport();
        } catch (error) {
            console.error("Error exporting report:", error);
        } finally {
            setExporting(false);
        }
    };

    const formatCountdown = (dateString: string | null) => {
        if (!dateString) return "TBD";
        const date = new Date(dateString);
        const now = new Date();
        const diff = date.getTime() - now.getTime();
        const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
        if (days < 0) return "Started";
        if (days === 0) return "Today";
        return `${days} Days`;
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    if (loading) {
        return (
            <ModernLayout>
                <div className="flex items-center justify-center min-h-[60vh]">
                    <div className="flex flex-col items-center gap-4">
                        <div className="size-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-[#4c669a] font-medium">Loading Intelligence Dashboard...</p>
                    </div>
                </div>
            </ModernLayout>
        );
    }

    return (
        <ModernLayout>
            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <div>
                    <h1 className="text-3xl md:text-4xl font-black text-[#0d121b] dark:text-white tracking-tight mb-1">Summit Overview Dashboard</h1>
                    <p className="text-[#4c669a] dark:text-[#a0aec0] font-medium">2024 ECOWAS Session • Admin View</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleExport}
                        disabled={exporting}
                        className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-[#2d3748] border border-[#cfd7e7] dark:border-[#4a5568] rounded-lg text-sm font-medium text-[#0d121b] dark:text-white hover:bg-gray-50 dark:hover:bg-[#4a5568] transition-colors shadow-sm disabled:opacity-50"
                    >
                        <span className="material-symbols-outlined text-[20px]">
                            {exporting ? 'sync' : 'download'}
                        </span>
                        {exporting ? 'Exporting...' : 'Export Report'}
                    </button>
                </div>
            </div>

            {/* KPI Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                {/* Active TWGs */}
                <div className="bg-white dark:bg-[#1a202c] p-6 rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col justify-between h-40 relative group overflow-hidden">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-semibold mb-1 uppercase tracking-wider">Active TWGs</p>
                            <h3 className="text-4xl font-black text-[#0d121b] dark:text-white">{stats?.metrics.active_twgs || 0}</h3>
                        </div>
                        <div className="size-12 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-[#1152d4] dark:text-[#60a5fa] border border-blue-100 dark:border-blue-800/20 shadow-sm group-hover:scale-110 transition-transform duration-300">
                            <span className="material-symbols-outlined text-[28px]">groups</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-xs font-bold bg-emerald-50 dark:bg-emerald-900/20 w-fit px-3 py-1.5 rounded-full">
                        <span className="material-symbols-outlined text-[16px]">trending_up</span>
                        <span>Tracking Pulse</span>
                    </div>
                </div>

                {/* Deals in Pipeline */}
                <div className="bg-white dark:bg-[#1a202c] p-6 rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col justify-between h-40 relative group overflow-hidden">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-semibold mb-1 uppercase tracking-wider">Deals in Pipeline</p>
                            <h3 className="text-4xl font-black text-[#0d121b] dark:text-white">{stats?.metrics.deals_in_pipeline || 0}</h3>
                        </div>
                        <div className="size-12 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-500 dark:text-blue-400 border border-blue-100 dark:border-blue-800/20 shadow-sm group-hover:scale-110 transition-transform duration-300">
                            <span className="material-symbols-outlined text-[28px]">handshake</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-blue-600 dark:text-blue-400 text-xs font-bold bg-blue-50 dark:bg-blue-900/20 w-fit px-3 py-1.5 rounded-full">
                        <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                        <span>{stats?.pipeline.final_review || 0} Ready for Review</span>
                    </div>
                </div>

                {/* Pending Approvals */}
                <div className="bg-white dark:bg-[#1a202c] p-6 rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col justify-between h-40 relative group overflow-hidden">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-semibold mb-1 uppercase tracking-wider">Pending Tasks</p>
                            <h3 className="text-4xl font-black text-[#0d121b] dark:text-white">{stats?.metrics.pending_approvals || 0}</h3>
                        </div>
                        <div className="size-12 rounded-xl bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center text-amber-500 border border-amber-100 dark:border-amber-800/20 shadow-sm group-hover:scale-110 transition-transform duration-300">
                            <span className="material-symbols-outlined text-[28px]">pending_actions</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400 text-xs font-bold bg-amber-50 dark:bg-amber-900/20 w-fit px-3 py-1.5 rounded-full">
                        <span className="material-symbols-outlined text-[14px]">warning</span>
                        <span>Action Required</span>
                    </div>
                </div>

                {/* Next Plenary */}
                <div className="bg-[#1152d4] p-6 rounded-2xl border border-[#1152d4] shadow-md flex flex-col justify-between h-40 relative group overflow-hidden text-white">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-white/80 text-sm font-semibold mb-1 uppercase tracking-wider">Next Major Event</p>
                            <h3 className="text-4xl font-black text-white">{formatCountdown(stats?.metrics.next_plenary.date || null)}</h3>
                        </div>
                        <div className="size-12 rounded-xl bg-white/20 flex items-center justify-center text-white border border-white/20 shadow-sm group-hover:scale-110 transition-transform duration-300">
                            <span className="material-symbols-outlined text-[28px]">event_available</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-white text-xs font-bold bg-white/20 w-fit px-3 py-1.5 rounded-full backdrop-blur-sm">
                        <span className="material-symbols-outlined text-[16px] text-white">calendar_month</span>
                        <span className="text-white truncate max-w-[120px]">{stats?.metrics.next_plenary.date ? formatDate(stats.metrics.next_plenary.date) : stats?.metrics.next_plenary.title}</span>
                    </div>
                </div>
            </div>

            {/* Main Dashboard Content Area */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Left Column: Pipeline & TWG Grid (Span 2) */}
                <div className="xl:col-span-2 flex flex-col gap-8">
                    {/* Pipeline Funnel Section */}
                    <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">Deal Progression by Stage</h3>
                            <button className="text-sm text-primary font-medium hover:underline">View Pipeline</button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
                            {/* Connecting Line (Desktop) */}
                            <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-[#e7ebf3] dark:bg-[#2d3748] -z-0"></div>

                            {/* Stage 1 */}
                            <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded-full bg-blue-200"></div>
                                    <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Drafting</span>
                                </div>
                                <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                    <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: `${(stats?.pipeline.drafting || 0) / (stats?.pipeline.total || 1) * 100}%` }}></div>
                                </div>
                                <div>
                                    <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">{stats?.pipeline.drafting || 0}</span>
                                    <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Active drafts</span>
                                </div>
                            </div>

                            {/* Stage 2 */}
                            <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded-full bg-blue-400"></div>
                                    <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Negotiation</span>
                                </div>
                                <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                    <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${(stats?.pipeline.negotiation || 0) / (stats?.pipeline.total || 1) * 100}%` }}></div>
                                </div>
                                <div>
                                    <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">{stats?.pipeline.negotiation || 0}</span>
                                    <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">In discussion</span>
                                </div>
                            </div>

                            {/* Stage 3 */}
                            <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded-full bg-indigo-500"></div>
                                    <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Final Review</span>
                                </div>
                                <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                    <div className="h-full bg-indigo-600 rounded-full transition-all duration-500" style={{ width: `${(stats?.pipeline.final_review || 0) / (stats?.pipeline.total || 1) * 100}%` }}></div>
                                </div>
                                <div>
                                    <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">{stats?.pipeline.final_review || 0}</span>
                                    <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Pending sign-off</span>
                                </div>
                            </div>

                            {/* Stage 4 */}
                            <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                <div className="flex items-center gap-2">
                                    <div className="size-3 rounded-full bg-emerald-500"></div>
                                    <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Signed</span>
                                </div>
                                <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${(stats?.pipeline.signed || 0) / (stats?.pipeline.total || 1) * 100}%` }}></div>
                                </div>
                                <div>
                                    <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">{stats?.pipeline.signed || 0}</span>
                                    <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Completed</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* TWG Status Grid */}
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">Technical Working Groups Status</h3>
                            <div className="flex gap-2">
                                <button className="p-2 text-[#0d121b] dark:text-[#a0aec0] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <span className="material-symbols-outlined">filter_list</span>
                                </button>
                                <button className="p-2 text-[#0d121b] dark:text-[#a0aec0] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <span className="material-symbols-outlined">grid_view</span>
                                </button>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {stats?.twg_health.map((twg) => (
                                <div key={twg.id} className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4">
                                        <div className={`text-xs font-bold px-2 py-1 rounded ${twg.status === 'active'
                                            ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
                                            }`}>
                                            {twg.status.toUpperCase()}
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-4 mb-4">
                                        <div className="size-12 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-primary shrink-0">
                                            <span className="material-symbols-outlined">{
                                                twg.pillar.toLowerCase() === 'minerals' ? 'diamond' :
                                                    twg.pillar.toLowerCase() === 'energy' ? 'bolt' :
                                                        twg.pillar.toLowerCase() === 'agribusiness' ? 'agriculture' :
                                                            twg.pillar.toLowerCase() === 'digital' ? 'terminal' :
                                                                'groups'
                                            }</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white text-lg">{twg.name}</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Lead: {twg.lead}</p>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-[#4c669a] dark:text-[#a0aec0]">Pillar Performance</span>
                                                <span className="font-bold text-[#0d121b] dark:text-white">{twg.completion}%</span>
                                            </div>
                                            <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                                <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${twg.completion}%` }}></div>
                                            </div>
                                        </div>
                                        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-3 flex items-start gap-2 border border-indigo-100 dark:border-indigo-800/30">
                                            <span className="material-symbols-outlined text-indigo-500 text-sm mt-0.5">auto_awesome</span>
                                            <div>
                                                <p className="text-xs text-[#0d121b] dark:text-white font-medium">System Status</p>
                                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">
                                                    {twg.status === 'active' ? 'TWG is operating within parameters.' : 'Activity requested – potential blocker identified.'}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex justify-end pt-2 border-t border-[#f0f2f5] dark:border-[#2d3748]">
                                            <button className="text-sm text-primary font-medium hover:text-blue-700 flex items-center gap-1">
                                                View TWG Details <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right Column: Timeline & Action Center (Span 1) */}
                <div className="flex flex-col gap-8">
                    {/* Upcoming Deadlines */}
                    <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm p-6 flex-1">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">Live Timeline</h3>
                            <span className="material-symbols-outlined text-[#4c669a]">schedule</span>
                        </div>
                        <div className="space-y-6 relative">
                            {/* Vertical line */}
                            <div className="absolute left-[27px] top-4 bottom-4 w-0.5 bg-[#e7ebf3] dark:bg-[#2d3748] -z-0"></div>

                            {timeline.length > 0 ? timeline.map((item, index) => {
                                const date = new Date(item.date);
                                const month = date.toLocaleString('en-US', { month: 'short' });
                                const day = date.getDate();

                                return (
                                    <div key={index} className="flex gap-4 relative z-10">
                                        <div className="flex flex-col items-center gap-1 w-14 shrink-0 bg-white dark:bg-[#1a202c]">
                                            <span className={`text-xs font-bold uppercase ${item.status === 'critical' ? 'text-red-500' : 'text-primary'}`}>{month}</span>
                                            <span className="text-xl font-black text-[#0d121b] dark:text-white">{day}</span>
                                        </div>
                                        <div className={`pb-6 ${index !== timeline.length - 1 ? 'border-b border-[#f0f2f5] dark:border-[#2d3748]' : ''} w-full`}>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white text-sm">{item.title}</h4>
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mt-1">{item.twg}</p>
                                            <div className="mt-2 flex items-center gap-2">
                                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${item.status === 'critical'
                                                    ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                                                    }`}>
                                                    {item.status.toUpperCase()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            }) : (
                                <div className="text-center py-8">
                                    <p className="text-[#4c669a] text-sm italic">No upcoming events scheduled.</p>
                                </div>
                            )}
                        </div>
                        <button className="w-full mt-6 py-2 text-sm text-[#0d121b] dark:text-[#a0aec0] font-medium border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg hover:bg-gray-50 dark:hover:bg-[#2d3748] transition-colors">
                            View All Events
                        </button>
                    </div>

                    {/* Action Center */}
                    <div className="bg-primary/5 dark:bg-primary/10 rounded-xl border border-primary/20 p-6">
                        <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-4">Quick Actions</h3>
                        <div className="grid grid-cols-2 gap-3">
                            <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">article</span>
                                <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Generate Report</span>
                            </button>
                            <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">broadcast_on_personal</span>
                                <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Broadcast Msg</span>
                            </button>
                            <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">smart_toy</span>
                                <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Run AI Analysis</span>
                            </button>
                            <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">person_add</span>
                                <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Invite Lead</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </ModernLayout>
    );
}
