import { Card, Badge, Avatar } from '../../components/ui'
// import { useSelector } from 'react-redux';
// import { RootState } from '../../store';
import PolicyFactory from '../../components/workspace/PolicyFactory'
import CopilotChat from '../../components/workspace/CopilotChat'
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { meetings, twgs } from '../../services/api'

import CreateMeetingModal from '../../components/schedule/CreateMeetingModal'

export default function TwgWorkspace() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    // const user = useSelector((state: RootState) => state.auth.user);
    const twgId = id || ''; // meaningful fallback or error handling?

    // Real Data State
    const [loading, setLoading] = useState(true);
    const [events, setEvents] = useState<any[]>([]);
    const [twg, setTwg] = useState<any>(null);

    // Modal State
    const [isScheduling, setIsScheduling] = useState(false)
    const [isCopilotExpanded, setIsCopilotExpanded] = useState(false)

    // Pagination State for Meetings
    const MEETINGS_PER_PAGE = 5;
    const [meetingsPage, setMeetingsPage] = useState(0);

    // Load Meetings
    const loadMeetings = async () => {
        if (!twgId) return;
        try {
            setLoading(true);
            const response = await meetings.list();
            // Filter client-side for now
            const twgMeetings = response.data.filter((m: any) => m.twg_id === twgId);

            // Intelligent Sort: Upcoming (ASC) then Past (DESC)
            const now = new Date();
            const upcoming = twgMeetings.filter((m: any) => new Date(m.scheduled_at) >= now);
            const past = twgMeetings.filter((m: any) => new Date(m.scheduled_at) < now);

            upcoming.sort((a: any, b: any) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());
            past.sort((a: any, b: any) => new Date(b.scheduled_at).getTime() - new Date(a.scheduled_at).getTime());

            const sortedMeetings = [...upcoming, ...past];
            setEvents(sortedMeetings);
        } catch (error) {
            console.error("Failed to load meetings", error);
        } finally {
            setLoading(false);
        }
    }

    const loadTwgDetails = async () => {
        if (!twgId) return;
        try {
            const response = await twgs.get(twgId);
            setTwg(response.data);
        } catch (error) {
            console.error("Failed to load TWG", error);
        }
    }

    useEffect(() => {
        loadMeetings();
        loadTwgDetails();
    }, [twgId]);


    const [activeTab, setActiveTab] = useState<'overview' | 'factory'>('overview');



    // Calculate Next Meeting from events
    const nextMeeting = events.find(m => new Date(m.scheduled_at + 'Z') > new Date());
    const nextMeetingDate = nextMeeting
        ? new Date(nextMeeting.scheduled_at + 'Z').toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : 'None Scheduled';

    return (
        <>
            <div className="flex h-[calc(100vh-140px)] gap-6">
                <div className="flex-1 space-y-6">
                    {/* Banner Section */}
                    <div className="relative h-56 rounded-2xl overflow-hidden bg-gradient-to-br from-blue-900 via-blue-950 to-slate-950 border border-slate-800 shadow-2xl">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_-20%,_var(--tw-gradient-stops))] from-blue-500/20 via-transparent to-transparent"></div>

                        <div className="relative z-10 h-full flex flex-col justify-between p-8">
                            <div className="flex justify-between items-start">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">PILLAR: {twg?.pillar?.toUpperCase().replace('_', ' ') || 'LOADING...'}</Badge>
                                        <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-bold">ECOWAS SUMMIT '24</Badge>
                                    </div>
                                    <h1 className="text-4xl font-display font-bold text-white tracking-tight">{twg?.name || 'Loading TWG...'}</h1>
                                    <p className="text-blue-200/70 text-sm max-w-2xl leading-relaxed">
                                        Strategic coordination for regional power pool integration and sustainable energy transition frameworks.
                                    </p>
                                </div>

                                <div className="flex gap-3">
                                    <button className="p-2.5 bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-xl text-white transition-all">
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                        </svg>
                                    </button>
                                    <button
                                        onClick={() => setIsScheduling(true)}
                                        className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-lg shadow-blue-900/40 transition-all flex items-center gap-2"
                                    >
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                                        New Meeting
                                    </button>
                                </div>
                            </div>

                            {/* Governance Row */}
                            <div className="flex gap-8 pt-6 border-t border-white/10">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold border border-blue-500/30">
                                        {twg?.political_lead?.full_name?.charAt(0) || 'P'}
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-blue-300/70 font-bold tracking-wider uppercase">Political Lead</p>
                                        <p className="text-sm font-bold text-white">{twg?.political_lead?.full_name || 'Unassigned'}</p>
                                    </div>
                                </div>

                                {/* Technical Lead */}
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold border border-emerald-500/30">
                                        {twg?.technical_lead?.full_name?.charAt(0) || 'T'}
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-emerald-300/70 font-bold tracking-wider uppercase">Technical Lead</p>
                                        <p className="text-sm font-bold text-white">{twg?.technical_lead?.full_name || 'Unassigned'}</p>
                                    </div>
                                </div>
                                <div className="ml-auto flex items-center gap-6">
                                    <div className="text-right">
                                        <p className="text-[10px] uppercase font-black text-slate-500 tracking-widest">Next Meeting</p>
                                        <p className="text-sm font-bold text-white">{nextMeetingDate}</p>
                                    </div>
                                    <div className="h-8 w-px bg-white/10"></div>
                                    <div className="flex -space-x-2">
                                        {(twg?.members || []).slice(0, 4).map((m: any, i: number) => (
                                            <Avatar
                                                key={m.id || i}
                                                fallback={m.full_name?.split(' ').map((n: string) => n[0]).join('').substring(0, 2) || 'U'}
                                                size="sm"
                                                className="ring-2 ring-blue-900 bg-slate-700 text-slate-200 cursor-pointer"
                                                title={`${m.full_name} (${m.role?.replace('TWG_', '')})`}
                                            />
                                        ))}
                                        {(twg?.members?.length || 0) > 4 && (
                                            <div className="w-8 h-8 rounded-full bg-blue-600 border-2 border-blue-900 flex items-center justify-center text-[10px] font-black text-white">
                                                +{(twg?.members?.length || 0) - 4}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Quick Stats Grid */}
                    <div className="grid grid-cols-4 gap-6">
                        <Card className="p-5 flex items-center gap-4 group hover:border-blue-500/50 transition-all">
                            <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Meetings Held</p>
                                <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">
                                    {twg?.stats?.meetings_held ?? '-'}
                                </h3>
                            </div>
                        </Card>
                        <Card className="p-5 flex items-center gap-4 group hover:border-orange-500/50 transition-all">
                            <div className="p-3 rounded-xl bg-orange-50 dark:bg-orange-900/20 text-orange-500 dark:text-orange-400">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Open Actions</p>
                                <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">
                                    {twg?.stats?.open_actions ?? '-'}
                                </h3>
                            </div>
                        </Card>
                        <Card className="p-5 flex items-center gap-4 group hover:border-emerald-500/50 transition-all">
                            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Pipeline Projects</p>
                                <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">
                                    {twg?.stats?.pipeline_projects ?? '-'}
                                </h3>
                            </div>
                        </Card>
                        <Card className="p-5 flex items-center gap-4 group hover:border-purple-500/50 transition-all">
                            <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Resources Out</p>
                                <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">
                                    {twg?.stats?.resources_count ?? '-'}
                                </h3>
                            </div>
                        </Card>
                    </div>

                    {/* Workspace Tabs */}
                    <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
                        <div className="flex gap-6">
                            <button
                                onClick={() => setActiveTab('overview')}
                                className={`pb - 3 text - sm font - bold transition - all border - b - 2 ${activeTab === 'overview'
                                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    } `}
                            >
                                Overview & Operations
                            </button>
                            <button
                                onClick={() => setActiveTab('factory')}
                                className={`pb - 3 text - sm font - bold transition - all border - b - 2 ${activeTab === 'factory'
                                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    } `}
                            >
                                Policy & Content Factory
                            </button>
                        </div>
                    </div>

                    {/* Content switching */}
                    {activeTab === 'overview' && (
                        <>
                            <div className="grid grid-cols-12 gap-6">
                                {/* Meeting Tracker */}
                                <div className="col-span-12 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <h2 className="text-xl font-display font-bold text-slate-900 dark:text-white transition-colors">Meeting History & Schedule</h2>
                                        <button className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors uppercase tracking-widest">Full Calendar →</button>
                                    </div>
                                    <Card className="p-0 overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-none border-slate-100 dark:border-dark-border transition-colors">
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-left text-sm border-collapse">
                                                <thead>
                                                    <tr className="bg-slate-50 dark:bg-slate-800/50 text-[10px] font-black text-slate-400 uppercase tracking-widest transition-colors">
                                                        <th className="px-6 py-4">Meeting Date / Title</th>
                                                        <th className="px-6 py-4">Type</th>
                                                        <th className="px-6 py-4">Status</th>
                                                        <th className="px-6 py-4 text-center">Resources</th>
                                                        <th className="px-6 py-4 text-right">Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 transition-colors">
                                                    {events.length === 0 && !loading && (
                                                        <tr>
                                                            <td colSpan={5} className="text-center py-8 text-slate-500 italic">
                                                                No meetings scheduled.
                                                            </td>
                                                        </tr>
                                                    )}
                                                    {loading && (
                                                        <tr>
                                                            <td colSpan={5} className="text-center py-8 text-blue-500 font-bold">
                                                                Loading schedule...
                                                            </td>
                                                        </tr>
                                                    )}
                                                    {events
                                                        .slice(meetingsPage * MEETINGS_PER_PAGE, (meetingsPage + 1) * MEETINGS_PER_PAGE)
                                                        .map((m, i) => (
                                                            <tr key={m.id || i} className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors group">
                                                                <td className="px-6 py-4">
                                                                    <div className="flex items-center gap-2">
                                                                        <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">{m.title}</div>
                                                                        {['in_progress', 'IN_PROGRESS'].includes(m.status) && (
                                                                            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" title="Meeting is Live" />
                                                                        )}
                                                                    </div>
                                                                    <div className="text-[10px] text-slate-400 uppercase font-black">
                                                                        {/* Convert UTC to local timezone for display */}
                                                                        {new Date(m.scheduled_at + 'Z').toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                                                    </div>
                                                                </td>
                                                                <td className="px-6 py-4">
                                                                    <Badge variant="neutral" size="sm" className="font-bold">{m.type || 'Session'}</Badge>
                                                                </td>
                                                                <td className="px-6 py-4">
                                                                    <Badge variant={m.status === 'scheduled' ? 'info' : m.status === 'completed' ? 'success' : 'warning'} size="sm" className="font-bold tracking-tighter uppercase">
                                                                        {m.status || 'Scheduled'}
                                                                    </Badge>
                                                                </td>
                                                                <td className="px-6 py-4">
                                                                    <div className="flex justify-center gap-2">
                                                                        {/* Simple indicators for now until backend eagerly loads metadata */}
                                                                        <div title="Agenda" className="p-1.5 rounded-lg border bg-blue-50 border-blue-100 text-blue-600 dark:bg-blue-900/20 dark:border-blue-900/30 dark:text-blue-400 cursor-pointer hover:scale-110 transition-all">
                                                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                                                        </div>
                                                                        <div title="Participants" className="p-1.5 rounded-lg border bg-slate-50 border-slate-100 text-slate-300 dark:bg-slate-800 dark:border-slate-700/50 opacity-50 transition-all">
                                                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                                                                        </div>
                                                                    </div>
                                                                </td>
                                                                <td className="px-6 py-4 text-right">
                                                                    <button
                                                                        onClick={() => navigate(`/meetings/${m.id}`, { state: { from: 'twg-workspace' } })}
                                                                        className="text-[10px] font-black text-blue-600 hover:text-blue-700 uppercase tracking-widest transition-all"
                                                                    >
                                                                        View Details
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                </tbody>
                                            </table>
                                        </div>
                                        {/* Pagination Controls */}
                                        {events.length > MEETINGS_PER_PAGE && (
                                            <div className="flex items-center justify-between px-6 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30">
                                                <span className="text-xs text-slate-500">
                                                    Showing {meetingsPage * MEETINGS_PER_PAGE + 1}-{Math.min((meetingsPage + 1) * MEETINGS_PER_PAGE, events.length)} of {events.length}
                                                </span>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => setMeetingsPage(p => Math.max(0, p - 1))}
                                                        disabled={meetingsPage === 0}
                                                        className="px-3 py-1.5 text-xs font-bold rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                                    >
                                                        Previous
                                                    </button>
                                                    <button
                                                        onClick={() => setMeetingsPage(p => Math.min(Math.ceil(events.length / MEETINGS_PER_PAGE) - 1, p + 1))}
                                                        disabled={meetingsPage >= Math.ceil(events.length / MEETINGS_PER_PAGE) - 1}
                                                        className="px-3 py-1.5 text-xs font-bold rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                                    >
                                                        Next
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </Card>
                                </div>

                                {/* Action Items List */}
                                <div className="col-span-7 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <h2 className="text-lg font-bold text-slate-900 dark:text-white transition-colors">Critical Action Items</h2>
                                        <button className="text-xs font-bold text-slate-500 hover:text-slate-700 transition-colors uppercase">View All</button>
                                    </div>
                                    <div className="space-y-3">
                                        {(!twg?.action_items || twg.action_items.length === 0) && (
                                            <div className="p-8 text-center bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-200 dark:border-slate-700">
                                                <p className="text-sm text-slate-500 italic">No action items pending.</p>
                                            </div>
                                        )}
                                        {twg?.action_items?.slice(0, 5).map((action: any, i: number) => (
                                            <Card key={action.id || i} className="p-4 flex items-center gap-4 hover:border-blue-500/30 transition-all cursor-pointer group">
                                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs ${action.status === 'overdue' ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-400'} transition-colors`}>
                                                    0{i + 1}
                                                </div>
                                                <div className="flex-1">
                                                    <h4 className="font-bold text-sm text-slate-900 dark:text-white transition-colors capitalize">{action.description}</h4>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <Avatar size="xs" fallback={action.owner?.full_name?.split(' ').map((n: string) => n[0]).join('') || 'U'} />
                                                        <span className="text-[10px] text-slate-500 font-bold uppercase">
                                                            {action.owner?.full_name || 'Unassigned'} • Due {new Date(action.due_date).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                </div>
                                                <Badge variant={action.status === 'in_progress' ? 'info' : action.status === 'overdue' ? 'danger' : 'neutral'} size="sm" className="font-bold uppercase tracking-tighter">
                                                    {action.status?.replace('_', ' ')}
                                                </Badge>
                                            </Card>
                                        ))}
                                    </div>
                                </div>

                                {/* Document Repository */}
                                <div className="col-span-5 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <h2 className="text-lg font-bold text-slate-900 dark:text-white transition-colors">Document Library</h2>
                                    </div>
                                    <Card className="p-4 space-y-5">
                                        <div>
                                            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Recent Documents</h4>
                                            <div className="space-y-2">
                                                {(!twg?.documents || twg.documents.length === 0) && (
                                                    <p className="text-xs text-slate-500 italic">No documents uploaded.</p>
                                                )}
                                                {twg?.documents?.slice(0, 5).map((doc: any) => (
                                                    <div key={doc.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group cursor-pointer">
                                                        <svg className={`w-5 h-5 ${doc.file_type?.includes('pdf') ? 'text-red-500' : 'text-blue-500'} transition-colors`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                        </svg>
                                                        <div className="min-w-0 flex-1">
                                                            <div className="text-xs font-medium text-slate-600 dark:text-slate-400 truncate">{doc.file_name}</div>
                                                            <div className="text-[10px] text-slate-400">
                                                                {doc.stage?.replace('_', ' ').toUpperCase()} • {new Date(doc.created_at).toLocaleDateString()}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setActiveTab('factory')}
                                            className="w-full py-2 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-lg text-xs font-bold text-slate-500 hover:text-slate-700 transition-all active:scale-95"
                                        >
                                            Open Full Repository →
                                        </button>
                                    </Card>
                                </div>
                            </div>

                        </>
                    )}

                    {activeTab === 'factory' && (
                        <PolicyFactory />
                    )}
                </div>

                {/* AI Copilot Sidebar */}

                {/* AI Copilot Sidebar */}
                <div className={`${isCopilotExpanded ? 'w-[45%]' : 'w-80'} flex flex-col gap-6 transition-all duration-300 ease-in-out shrink-0`}>
                    <Card className="flex-1 flex flex-col p-0 overflow-hidden bg-white dark:bg-dark-card border-slate-100 dark:border-dark-border transition-colors h-[calc(100vh-140px)] shadow-xl shadow-blue-900/5">
                        <CopilotChat
                            twgId={twgId}
                            twgName={twg?.name}
                            isExpanded={isCopilotExpanded}
                            onToggleExpand={() => setIsCopilotExpanded(!isCopilotExpanded)}
                        />
                    </Card>
                </div>
            </div>
            {/* Modals */}
            <CreateMeetingModal
                isOpen={isScheduling}
                onClose={() => setIsScheduling(false)}
                twgId={twgId}
                onSuccess={loadMeetings}
            />
        </>
    )
}
