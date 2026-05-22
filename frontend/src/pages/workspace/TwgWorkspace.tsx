import { useSelector } from 'react-redux';
import { RootState } from '../../store';
import { UserRole } from '../../types/auth';
import PolicyFactory from '../../components/workspace/PolicyFactory'
import TwgMemberManager from '../../components/workspace/TwgMemberManager'
import SubgroupsManager from '../../components/workspace/SubgroupsManager'
import SubgroupDetail from '../../components/workspace/SubgroupDetail'
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { meetings, twgs } from '../../services/api'

import CreateMeetingModal from '../../components/schedule/CreateMeetingModal'
import { parseUTCDate } from '../../utils/dates'

export default function TwgWorkspace() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const user = useSelector((state: RootState) => state.auth.user);
    const twgId = id || '';

    // Check if user can manage members
    const isAdmin = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD;
    const canManageMembers = isAdmin || user?.role === UserRole.FACILITATOR;
    const canCreateMeetings = isAdmin || user?.role === UserRole.FACILITATOR;

    // Real Data State
    const [loading, setLoading] = useState(true);
    const [events, setEvents] = useState<any[]>([]);
    const [twg, setTwg] = useState<any>(null);

    // Modal State
    const [isScheduling, setIsScheduling] = useState(false)

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
            const twgMeetings = response.data.filter((m: any) => m.twg_id === twgId && m.status !== 'CANCELLED');

            // Intelligent Sort: Upcoming (ASC) then Past (DESC)
            const now = new Date();
            const upcoming = twgMeetings.filter((m: any) => parseUTCDate(m.scheduled_at) >= now);
            const past = twgMeetings.filter((m: any) => parseUTCDate(m.scheduled_at) < now);

            upcoming.sort((a: any, b: any) => parseUTCDate(a.scheduled_at).getTime() - parseUTCDate(b.scheduled_at).getTime());
            past.sort((a: any, b: any) => parseUTCDate(b.scheduled_at).getTime() - parseUTCDate(a.scheduled_at).getTime());

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


    const [activeTab, setActiveTab] = useState<'overview' | 'factory' | 'members' | 'subgroups' | 'documents' | 'actions'>('overview');
    const [activeSubgroup, setActiveSubgroup] = useState<any>(null);
    const [hoveredRow, setHoveredRow] = useState<string | null>(null);



    // Calculate Next Meeting from events
    const nextMeeting = events.find(m => parseUTCDate(m.scheduled_at) > new Date());
    const nextMeetingDate = nextMeeting
        ? parseUTCDate(nextMeeting.scheduled_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : 'None Scheduled';

    const getStatusDotColor = (status: string) => {
        if (status === 'completed') return 'var(--sage)';
        if (status === 'scheduled') return 'var(--amber)';
        if (['in_progress', 'IN_PROGRESS'].includes(status)) return 'var(--terra)';
        return 'var(--ink-300)';
    };

    return (
        <>
            <div className="flex flex-col lg:flex-row h-auto lg:h-[calc(100vh-140px)] gap-4">
                <div className="flex-1 min-w-0 space-y-4 overflow-y-auto">
                    {/* Header Section */}
                    <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '24px 32px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                            <div>
                                <h1 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 28, fontWeight: 600, color: 'var(--ink-900)', lineHeight: 1.2, margin: 0 }}>
                                    {twg?.name || 'Loading TWG...'}
                                </h1>
                            </div>
                            <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                                {canCreateMeetings && (
                                    <button
                                        onClick={() => setIsScheduling(true)}
                                        style={{ padding: '8px 16px', background: 'var(--accent)', color: 'var(--accent-ink)', fontSize: 13, fontWeight: 500, border: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", display: 'flex', alignItems: 'center', gap: 6 }}
                                    >
                                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                                        New Meeting
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Governance Row */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, paddingTop: 16, marginTop: 16, borderTop: '1px solid var(--border)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{ width: 32, height: 32, borderRadius: 32, background: 'var(--accent-soft)', color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, fontFamily: "'Geist Mono', monospace" }}>
                                    {twg?.political_lead?.full_name?.charAt(0) || 'P'}
                                </div>
                                <div>
                                    <p style={{ fontSize: 9, color: 'var(--ink-500)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Political Lead</p>
                                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-900)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{twg?.political_lead?.full_name || 'Unassigned'}</p>
                                </div>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{ width: 32, height: 32, borderRadius: 32, background: 'var(--accent-soft)', color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, fontFamily: "'Geist Mono', monospace" }}>
                                    {twg?.technical_lead?.full_name?.charAt(0) || 'T'}
                                </div>
                                <div>
                                    <p style={{ fontSize: 9, color: 'var(--ink-500)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Technical Lead</p>
                                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-900)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{twg?.technical_lead?.full_name || 'Unassigned'}</p>
                                </div>
                            </div>

                            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
                                <div style={{ textAlign: 'right' }}>
                                    <p style={{ fontSize: 9, color: 'var(--ink-500)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Next Meeting</p>
                                    <p style={{ fontSize: 12, color: 'var(--ink-900)', fontFamily: "'Geist Mono', monospace", margin: 0 }}>{nextMeetingDate}</p>
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--ink-500)', border: '1px solid var(--border)', padding: '2px 8px', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                    {twg?.members?.length || 0} members
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* LedgerStat Strip */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
                        {[
                            { label: 'MEETINGS', value: twg?.stats?.meetings_held ?? '-', note: 'Total held' },
                            { label: 'ACTIONS', value: twg?.stats?.open_actions ?? '-', note: 'Open items' },
                            { label: 'PIPELINE', value: twg?.stats?.pipeline_projects ?? '-', note: 'Active projects' },
                            { label: 'RESOURCES', value: twg?.stats?.resources_count ?? '-', note: 'Documents' },
                        ].map((stat, i) => (
                            <div key={stat.label} style={{ padding: '20px 24px', borderLeft: i > 0 ? '1px solid var(--border)' : 'none' }}>
                                <div style={{ fontSize: 28, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                                    {stat.value}
                                </div>
                                <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginTop: 6, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                    {stat.label}
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--ink-400)', marginTop: 2, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                    {stat.note}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Tab Bar */}
                    <div style={{ borderBottom: '1px solid var(--border)', display: 'flex', gap: 0 }}>
                        {([
                            { key: 'overview', label: 'Meetings & Schedule' },
                            { key: 'actions', label: 'Action Items' },
                            { key: 'documents', label: 'Documents' },
                            { key: 'members', label: 'Members' },
                            { key: 'subgroups', label: 'Subgroups' },
                        ] as const).map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => tab.key === 'subgroups' ? (setActiveTab('subgroups'), setActiveSubgroup(null)) : setActiveTab(tab.key)}
                                style={{
                                    paddingBottom: 12,
                                    paddingTop: 12,
                                    paddingLeft: 16,
                                    paddingRight: 16,
                                    fontSize: 13,
                                    fontWeight: 500,
                                    fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                                    background: 'none',
                                    border: 'none',
                                    borderBottom: activeTab === tab.key ? '2px solid var(--accent)' : '2px solid transparent',
                                    color: activeTab === tab.key ? 'var(--accent)' : 'var(--ink-500)',
                                    cursor: 'pointer',
                                    marginBottom: -1,
                                }}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Content switching */}
                    {activeTab === 'overview' && (
                        <>
                            <div className="grid grid-cols-12 gap-6">
                                {/* Meeting Tracker */}
                                <div className="col-span-12 space-y-4">
                                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                        <button onClick={() => navigate('/schedule')} style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.08em', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Full Calendar →</button>
                                    </div>
                                    <div style={{ border: '1px solid var(--border)', background: 'var(--surface)', overflow: 'hidden' }}>
                                        {/* Table Header */}
                                        <div style={{ display: 'grid', gridTemplateColumns: '2fr 0.8fr 1fr 1fr 0.8fr', background: 'var(--ink-50)', padding: '10px 24px', borderBottom: '1px solid var(--border)' }}>
                                            {['Meeting Date / Title', 'Type', 'Status', 'Resources', 'Action'].map((h, i) => (
                                                <div key={h} style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", textAlign: i === 3 ? 'center' : i === 4 ? 'right' : 'left' }}>
                                                    {h}
                                                </div>
                                            ))}
                                        </div>

                                        {events.length === 0 && !loading && (
                                            <div style={{ padding: '32px 24px', textAlign: 'center', color: 'var(--ink-500)', fontSize: 13, fontStyle: 'italic', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                                No meetings scheduled.
                                            </div>
                                        )}
                                        {loading && (
                                            <div style={{ padding: '32px 24px', textAlign: 'center', color: 'var(--accent)', fontSize: 13, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                                Loading schedule...
                                            </div>
                                        )}

                                        {events
                                            .slice(meetingsPage * MEETINGS_PER_PAGE, (meetingsPage + 1) * MEETINGS_PER_PAGE)
                                            .map((m, i) => (
                                                <div
                                                    key={m.id || i}
                                                    style={{
                                                        display: 'grid',
                                                        gridTemplateColumns: '2fr 0.8fr 1fr 1fr 0.8fr',
                                                        padding: '14px 24px',
                                                        borderTop: '1px solid var(--border)',
                                                        alignItems: 'center',
                                                        background: hoveredRow === (m.id || String(i)) ? 'var(--accent-soft)' : 'transparent',
                                                        cursor: 'pointer',
                                                    }}
                                                    onMouseEnter={() => setHoveredRow(m.id || String(i))}
                                                    onMouseLeave={() => setHoveredRow(null)}
                                                >
                                                    <div>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                            <span style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 14, fontWeight: 500, color: hoveredRow === (m.id || String(i)) ? 'var(--accent)' : 'var(--ink-900)' }}>
                                                                {m.title}
                                                            </span>
                                                            {['in_progress', 'IN_PROGRESS'].includes(m.status) && (
                                                                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" title="Meeting is Live" />
                                                            )}
                                                        </div>
                                                        <div style={{ fontSize: 11, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace", marginTop: 2 }}>
                                                            {parseUTCDate(m.scheduled_at).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                                        </div>
                                                    </div>
                                                    <div style={{ fontSize: 12, color: 'var(--ink-600)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                                        {m.type || 'Session'}
                                                    </div>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                        <div style={{ width: 6, height: 6, borderRadius: 6, background: getStatusDotColor(m.status), flexShrink: 0 }} />
                                                        <span style={{ fontSize: 12, color: 'var(--ink-700)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", textTransform: 'capitalize' }}>
                                                            {m.status || 'Scheduled'}
                                                        </span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
                                                        <div title="Agenda" style={{ padding: '4px 6px', border: '1px solid var(--border)', color: 'var(--accent)', cursor: 'pointer', background: 'var(--accent-soft)' }}>
                                                            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                                        </div>
                                                        <div title="Participants" style={{ padding: '4px 6px', border: '1px solid var(--border)', color: 'var(--ink-300)', cursor: 'default', opacity: 0.5 }}>
                                                            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                                                        </div>
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <button
                                                            onClick={() => navigate(`/meetings/${m.id}`, { state: { from: 'twg-workspace' } })}
                                                            style={{ fontSize: 12, fontWeight: 500, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}
                                                        >
                                                            View Details
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}

                                        {/* Pagination Controls */}
                                        {events.length > MEETINGS_PER_PAGE && (
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border)', padding: '12px 24px' }}>
                                                <span style={{ fontSize: 12, color: 'var(--ink-500)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                                    Showing {meetingsPage * MEETINGS_PER_PAGE + 1}–{Math.min((meetingsPage + 1) * MEETINGS_PER_PAGE, events.length)} of {events.length}
                                                </span>
                                                <div style={{ display: 'flex', gap: 8 }}>
                                                    <button
                                                        onClick={() => setMeetingsPage(p => Math.max(0, p - 1))}
                                                        disabled={meetingsPage === 0}
                                                        style={{ padding: '4px 12px', fontSize: 12, fontWeight: 500, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--ink-600)', cursor: meetingsPage === 0 ? 'not-allowed' : 'pointer', opacity: meetingsPage === 0 ? 0.4 : 1, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}
                                                    >
                                                        Previous
                                                    </button>
                                                    <button
                                                        onClick={() => setMeetingsPage(p => Math.min(Math.ceil(events.length / MEETINGS_PER_PAGE) - 1, p + 1))}
                                                        disabled={meetingsPage >= Math.ceil(events.length / MEETINGS_PER_PAGE) - 1}
                                                        style={{ padding: '4px 12px', fontSize: 12, fontWeight: 500, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--ink-600)', cursor: meetingsPage >= Math.ceil(events.length / MEETINGS_PER_PAGE) - 1 ? 'not-allowed' : 'pointer', opacity: meetingsPage >= Math.ceil(events.length / MEETINGS_PER_PAGE) - 1 ? 0.4 : 1, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}
                                                    >
                                                        Next
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                            </div>

                        </>
                    )}

                    {activeTab === 'actions' && (() => {
                        const DEMO_ACTIONS = [
                            { id: 'd1', description: 'Complete the regional broadband assessment for the remaining 7 countries.', owner: null, due_date: '2026-04-30', status: 'pending' },
                            { id: 'd2', description: 'Prepare a comprehensive progress report for presentation at the ECOWAS Digital Ministers Summit.', owner: null, due_date: '2026-07-14', status: 'completed' },
                            { id: 'd3', description: "Oversee the launch of the e-Government portal harmonization pilot in Senegal, Côte d'Ivoire, and Ghana.", owner: null, due_date: '2026-05-31', status: 'completed' },
                            { id: 'd4', description: 'Explore World Bank funding for the digital skills program, with connection support from Dr. Diallo.', owner: null, due_date: '1970-01-01', status: 'completed' },
                            { id: 'd5', description: 'Coordinate with the Secretariat on the logistics for the Abuja workshop.', owner: null, due_date: '1970-01-01', status: 'completed' },
                        ];
                        const actionItems: any[] = (twg?.action_items && twg.action_items.length > 0) ? twg.action_items : DEMO_ACTIONS;
                        const dotColor = (s: string) => s === 'completed' ? 'var(--sage)' : s === 'overdue' ? 'var(--terra)' : s === 'in_progress' ? 'var(--accent)' : 'var(--amber)';
                        const fmtDue = (d: string) => { const dt = new Date(d); return dt.getFullYear() < 2000 ? '—' : dt.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' }); };
                        return (
                            <div style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
                                <div style={{ display: 'grid', gridTemplateColumns: '48px 1fr 140px', background: 'var(--ink-50)', padding: '10px 24px', borderBottom: '1px solid var(--border)' }}>
                                    {['#', 'Description', 'Status'].map((h, i) => (
                                        <div key={h} style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", textAlign: i === 2 ? 'right' : 'left' }}>{h}</div>
                                    ))}
                                </div>
                                {actionItems.map((action: any, i: number) => (
                                    <div key={action.id || i} style={{ display: 'grid', gridTemplateColumns: '48px 1fr 140px', alignItems: 'center', padding: '16px 24px', borderBottom: i < actionItems.length - 1 ? '1px solid var(--border)' : 'none' }}>
                                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-400)', fontFamily: "'Geist Mono', monospace" }}>
                                            {String(i + 1).padStart(2, '0')}
                                        </div>
                                        <div>
                                            <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-900)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{action.description}</p>
                                            <p style={{ fontSize: 11, color: 'var(--ink-500)', margin: '4px 0 0', fontFamily: "'Geist Mono', monospace" }}>
                                                {action.owner?.full_name || 'Unassigned'} · Due {fmtDue(action.due_date)}
                                            </p>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                                            <div style={{ width: 6, height: 6, borderRadius: 6, background: dotColor(action.status), flexShrink: 0 }} />
                                            <span style={{ fontSize: 11, color: 'var(--ink-600)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                                {action.status?.replace('_', ' ')}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        );
                    })()}

                    {activeTab === 'factory' && (
                        <PolicyFactory />
                    )}

                    {activeTab === 'documents' && (
                        <div style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid var(--border)', background: 'var(--ink-50)' }}>
                                <span style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Recent Documents</span>
                                <button
                                    onClick={() => navigate(`/documents?twg=${twgId}`)}
                                    style={{ fontSize: 11, fontWeight: 500, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}
                                >
                                    Open Full Repository →
                                </button>
                            </div>
                            {(!twg?.documents || twg.documents.length === 0) ? (
                                <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--ink-400)', fontSize: 13, fontStyle: 'italic', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                    No documents uploaded yet.
                                </div>
                            ) : twg.documents.map((doc: any, i: number) => (
                                <div key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 24px', borderBottom: i < twg.documents.length - 1 ? '1px solid var(--border)' : 'none', cursor: 'pointer' }}>
                                    <svg style={{ width: 18, height: 18, color: doc.file_type?.includes('pdf') ? 'var(--terra)' : 'var(--accent)', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-900)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{doc.file_name}</p>
                                        <p style={{ fontSize: 10, color: 'var(--ink-400)', margin: '3px 0 0', fontFamily: "'Geist Mono', monospace" }}>
                                            {doc.stage?.replace('_', ' ').toUpperCase()} · {new Date(doc.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <span style={{ fontSize: 16, color: 'var(--ink-300)' }}>›</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {activeTab === 'members' && (
                        <TwgMemberManager
                            twgId={twgId}
                            twgName={twg?.name}
                            canEdit={canManageMembers && twg?.group_type !== 'leads_council'}
                            isAutoManaged={twg?.group_type === 'leads_council'}
                        />
                    )}

                    {activeTab === 'subgroups' && (
                        activeSubgroup ? (
                            <SubgroupDetail
                                twgId={twgId}
                                twgName={twg?.name || ''}
                                subgroup={activeSubgroup}
                                canEdit={canManageMembers}
                                onBack={() => setActiveSubgroup(null)}
                            />
                        ) : (
                            <SubgroupsManager
                                twgId={twgId}
                                canEdit={canManageMembers}
                                onOpenSubgroup={(sg) => setActiveSubgroup(sg)}
                            />
                        )
                    )}
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
