import { useState, useEffect } from 'react';
import { useAppSelector } from '../../hooks/useRedux';
import { format } from 'date-fns';
import CalendarGrid from '../common/CalendarGrid';
interface SupervisorState {
    last_refresh: string;
    total_twgs: number;
    total_meetings: number;
    total_documents: number;
    total_projects: number;
    active_conflicts: ConflictSnapshot[];
    calendar: MeetingSnapshot[];
    documents: DocumentSnapshot[];
    projects: ProjectSnapshot[];
    twg_summaries: Record<string, TWGSummary>;
}

interface MeetingSnapshot {
    id: string;
    title: string;
    scheduled_at: string;
    twg_name: string;
    has_conflicts: boolean;
    status: string;
}

interface DocumentSnapshot {
    id: string;
    file_name: string;
    twg_name: string;
    file_type: string;
    created_at: string;
    version: number;
    has_newer_version: boolean;
    parent_document_id: string | null;
}

interface ProjectSnapshot {
    id: string;
    name: string;
    twg_name: string;
    status: string;
    investment_size: number;
    readiness_score: number;
}

interface ConflictSnapshot {
    id: string;
    description: string;
    severity: string;
}

interface TWGSummary {
    twg_name: string;
    total_meetings: number;
    upcoming_meetings: number;
    total_documents: number;
    total_projects: number;
}

const API_Base = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function GlobalStateDashboard() {
    const { token } = useAppSelector((state) => state.auth);
    const [state, setState] = useState<SupervisorState | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'calendar' | 'documents' | 'projects'>('overview');
    const [calendarDate, setCalendarDate] = useState(new Date());

    const fetchState = async () => {
        try {
            const response = await fetch(`${API_Base}/supervisor/state`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!response.ok) throw new Error('Failed to fetch state');
            const data = await response.json();
            setState(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        try {
            await fetch(`${API_Base}/supervisor/state/refresh`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            });
            await fetchState();
        } catch (err) {
            console.error(err);
        } finally {
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchState();
        // Optional: Poll every 30s
        const interval = setInterval(fetchState, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div className="p-4 text-center">Loading Global State...</div>;
    if (error) return <div className="p-4 text-center text-red-500">Error: {error}</div>;
    if (!state) return null;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden mb-6">
            {/* Header */}
            <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-teal-500">language</span>
                    <h2 className="font-semibold text-slate-900 dark:text-white">Supervisor Global State</h2>
                    <span className="text-xs text-slate-500 ml-2">
                        Updated: {format(new Date(state.last_refresh), 'HH:mm:ss')}
                    </span>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className={`clickable-scale p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition ${refreshing ? 'animate-spin' : ''}`}
                >
                    <span className="material-symbols-outlined text-slate-500">refresh</span>
                </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-100 dark:border-slate-700">
                {['overview', 'calendar', 'documents', 'projects'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab as any)}
                        className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition
                            ${activeTab === tab
                                ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="p-4 h-[400px] overflow-y-auto">

                {/* OVERVIEW TAB */}
                {activeTab === 'overview' && (
                    <div className="space-y-6">
                        {/* KPI Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <StatCard label="Total Meetings" value={state.total_meetings} icon="event" color="teal" />
                            <StatCard label="Documents" value={state.total_documents} icon="description" color="emerald" />
                            <StatCard label="Pipeline Projects" value={state.total_projects} icon="rocket_launch" color="teal" />
                            <StatCard label="Active Conflicts" value={state.active_conflicts.length} icon="warning" color="amber" />
                        </div>

                        {/* Recent Activity / Conflicts */}
                        {state.active_conflicts.length > 0 && (
                            <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg border border-amber-200 dark:border-amber-800">
                                <h3 className="text-sm font-bold text-amber-800 dark:text-amber-200 mb-2 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">warning</span>
                                    Active Conflicts
                                </h3>
                                <ul className="space-y-2">
                                    {state.active_conflicts.map(c => (
                                        <li key={c.id} className="text-xs text-amber-900 dark:text-amber-100 flex justify-between">
                                            <span>{c.description}</span>
                                            <span className="uppercase font-bold text-[10px] bg-amber-200 dark:bg-amber-800 px-1 rounded">{c.severity}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* TWG Summaries */}
                        <div>
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">TWG Activity</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {Object.values(state.twg_summaries).map(twg => (
                                    <div key={twg.twg_name} className="flex justify-between items-center p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg text-sm">
                                        <span className="font-medium text-slate-800 dark:text-white">{twg.twg_name}</span>
                                        <div className="flex gap-3 text-slate-500 text-xs">
                                            <span title="Meetings">📅 {twg.total_meetings}</span>
                                            <span title="Docs">📄 {twg.total_documents}</span>
                                            <span title="Projects">🚀 {twg.total_projects}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* CALENDAR TAB */}
                {activeTab === 'calendar' && (
                    <div className="h-[500px] -m-4">
                        <CalendarGrid
                            events={state.calendar.map(m => ({
                                id: m.id,
                                title: m.title,
                                scheduled_at: new Date(m.scheduled_at),
                                type: 'in_person', // Global state doesn't differentiate yet, default to in_person
                                status: m.status,
                                twg_name: m.twg_name,
                                has_conflicts: m.has_conflicts
                            }))}
                            currentDate={calendarDate}
                            onMonthChange={setCalendarDate}
                            isLoading={false}
                        />
                    </div>
                )}

                {/* DOCUMENTS TAB */}
                {activeTab === 'documents' && (
                    <table className="w-full text-left text-sm">
                        <thead className="text-xs uppercase text-slate-500 bg-slate-50 dark:bg-slate-700">
                            <tr>
                                <th className="px-3 py-2">Document</th>
                                <th className="px-3 py-2">Version</th>
                                <th className="px-3 py-2">TWG</th>
                                <th className="px-3 py-2">Type</th>
                                <th className="px-3 py-2">Date</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                            {state.documents.map(doc => (
                                <tr key={doc.id} className={`hover:bg-slate-50 dark:hover:bg-slate-700/50 ${doc.has_newer_version ? 'opacity-50 grayscale' : ''}`}>
                                    <td className="px-3 py-2 font-medium text-slate-900 dark:text-white">
                                        <div className="flex items-center gap-2">
                                            {doc.file_name}
                                            {doc.has_newer_version && (
                                                <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded border border-amber-200">OUTDATED</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-3 py-2 text-slate-500">
                                        <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full font-mono">
                                            v{doc.version}
                                        </span>
                                    </td>
                                    <td className="px-3 py-2 text-slate-500">{doc.twg_name || 'General'}</td>
                                    <td className="px-3 py-2 text-slate-500 uppercase text-xs">{doc.file_type.split('/')[1] || 'FILE'}</td>
                                    <td className="px-3 py-2 text-slate-500">{format(new Date(doc.created_at), 'MMM dd')}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                {/* PROJECTS TAB */}
                {activeTab === 'projects' && (
                    <div className="space-y-3">
                        {state.projects.map(p => (
                            <div key={p.id} className="p-3 border border-slate-100 dark:border-slate-700 rounded-lg flex justify-between items-center">
                                <div>
                                    <div className="text-sm font-semibold text-slate-900 dark:text-white">{p.name}</div>
                                    <div className="text-xs text-slate-500">{p.twg_name}</div>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm font-mono font-medium text-teal-600 dark:text-teal-400">
                                        ${Number(p.investment_size).toLocaleString()}
                                    </div>
                                    <div className="text-xs flex items-center gap-1 justify-end text-slate-500">
                                        <span>Score: {p.readiness_score}/10</span>
                                        <span className={`w-2 h-2 rounded-full ${p.status === 'bankable' ? 'bg-green-500' :
                                            p.status === 'presented' ? 'bg-purple-500' : 'bg-slate-300'
                                            }`} />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function StatCard({ label, value, icon, color }: { label: string, value: number, icon: string, color: string }) {
    const colorClasses: Record<string, string> = {
        teal: "text-teal-600 bg-teal-100 dark:bg-teal-900/30 dark:text-teal-400",
        emerald: "text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400",
        amber: "text-amber-600 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400",
    };

    return (
        <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-700/30 border border-slate-100 dark:border-slate-700/50 flex flex-col items-center justify-center text-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center mb-2 ${colorClasses[color]}`}>
                <span className="material-symbols-outlined text-sm">{icon}</span>
            </div>
            <div className="text-2xl font-bold text-slate-800 dark:text-white">{value}</div>
            <div className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">{label}</div>
        </div>
    );
}
