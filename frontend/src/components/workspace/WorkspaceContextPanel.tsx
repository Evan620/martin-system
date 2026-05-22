import { useState, useEffect } from 'react';
import api from '../../services/api';
import { parseUTCDate } from '../../utils/dates';

interface WorkspaceContextPanelProps {
    twgName: string;
    twgId?: string;
    onInsertContext?: (contextType: string, data: any) => void;
}

interface Meeting {
    id: string;
    title: string;
    date: string;
    status: 'upcoming' | 'completed';
    hasMinutes?: boolean;
    hasAgenda?: boolean;
}

interface ActionItem {
    id: string;
    task: string;
    assignee: string;
    dueDate: string;
    status: 'not_started' | 'in_progress' | 'overdue' | 'completed';
}

interface Document {
    id: string;
    name: string;
    type: 'template' | 'output' | 'resource';
    uploadedAt: string;
}

const f = "'Geist', 'Inter', system-ui, sans-serif";
const mono = "'Geist Mono', monospace";

export default function WorkspaceContextPanel({ twgName, twgId, onInsertContext }: WorkspaceContextPanelProps) {
    const [activeTab, setActiveTab] = useState<'meetings' | 'actions' | 'documents'>('meetings');
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [hoveredRow, setHoveredRow] = useState<string | null>(null);

    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [actions, setActions] = useState<ActionItem[]>([]);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!twgId) return;
        const fetchData = async () => {
            setLoading(true);
            const isSecretariat = twgId === 'secretariat';
            const params = isSecretariat ? {} : { twg_id: twgId };
            try {
                if (activeTab === 'meetings') {
                    const res = await api.get('/meetings', { params });
                    setMeetings(res.data.map((m: any) => ({
                        id: m.id,
                        title: m.title,
                        date: parseUTCDate(m.scheduled_at).toLocaleString(),
                        status: m.status === 'scheduled' ? 'upcoming' : 'completed',
                        hasAgenda: !!m.agenda,
                        hasMinutes: !!m.minutes,
                    })));
                } else if (activeTab === 'actions') {
                    const res = await api.get('/action-items', { params });
                    setActions(res.data.map((a: any) => ({
                        id: a.id,
                        task: a.description,
                        assignee: a.owner?.full_name || 'Unassigned',
                        dueDate: a.due_date ? new Date(a.due_date).toLocaleDateString() : 'No Date',
                        status: a.status.toLowerCase(),
                    })));
                } else if (activeTab === 'documents') {
                    const res = await api.get('/documents', { params });
                    setDocuments(res.data.map((d: any) => ({
                        id: d.id,
                        name: d.file_name,
                        type: d.file_type.includes('pdf') ? 'output' : 'template',
                        uploadedAt: new Date(d.created_at).toLocaleDateString(),
                    })));
                }
            } catch (error) {
                console.error('Failed to fetch context data', error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [twgId, activeTab]);

    const handleInsertContext = (type: string, item: any) => {
        if (onInsertContext) onInsertContext(type, item);
    };

    const statusDot = (status: string) => {
        const color =
            status === 'completed' || status === 'upcoming' ? 'var(--sage)' :
            status === 'overdue' ? 'var(--terra)' :
            status === 'in_progress' ? 'var(--accent)' : 'var(--ink-300)';
        return <span style={{ width: 6, height: 6, borderRadius: 6, background: color, display: 'inline-block', flexShrink: 0 }} />;
    };

    if (isCollapsed) {
        return (
            <div style={{ width: 40, background: 'var(--surface)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '12px 0', gap: 16 }}>
                <button
                    onClick={() => setIsCollapsed(false)}
                    style={{ padding: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)' }}
                    title="Expand context panel"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>chevron_left</span>
                </button>
                {(['event', 'task_alt', 'description'] as const).map(icon => (
                    <button key={icon} style={{ padding: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{icon}</span>
                    </button>
                ))}
            </div>
        );
    }

    const tabs: { key: 'meetings' | 'actions' | 'documents'; label: string; icon: string }[] = [
        { key: 'meetings', label: 'Meetings', icon: 'event' },
        { key: 'actions', label: 'Actions', icon: 'task_alt' },
        { key: 'documents', label: 'Docs', icon: 'description' },
    ];

    return (
        <div style={{ width: 260, background: 'var(--surface)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
            {/* Header */}
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', fontFamily: mono, marginBottom: 2 }}>Context</div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-900)', fontFamily: f }}>{twgName}</div>
                </div>
                <button
                    onClick={() => setIsCollapsed(true)}
                    style={{ padding: 4, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)' }}
                    title="Collapse"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>chevron_right</span>
                </button>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
                {tabs.map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        style={{
                            flex: 1, padding: '8px 4px', background: 'none', border: 'none',
                            borderBottom: activeTab === tab.key ? '2px solid var(--accent)' : '2px solid transparent',
                            color: activeTab === tab.key ? 'var(--accent)' : 'var(--ink-500)',
                            cursor: 'pointer', fontFamily: f, fontSize: 11, fontWeight: 500,
                            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
                            transition: 'color 0.15s',
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>{tab.icon}</span>
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
                {loading && (
                    <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                        <div className="animate-spin rounded-full" style={{ width: 20, height: 20, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', margin: '0 auto' }} />
                    </div>
                )}

                {!loading && activeTab === 'meetings' && (
                    meetings.length === 0 ? (
                        <div style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12, color: 'var(--ink-400)', fontStyle: 'italic', fontFamily: f }}>No meetings found.</div>
                    ) : meetings.map((meeting, i) => (
                        <div
                            key={meeting.id}
                            onClick={() => handleInsertContext('meeting', meeting)}
                            onMouseEnter={() => setHoveredRow(meeting.id)}
                            onMouseLeave={() => setHoveredRow(null)}
                            style={{
                                padding: '10px 16px',
                                borderBottom: i < meetings.length - 1 ? '1px solid var(--border)' : 'none',
                                cursor: 'pointer',
                                background: hoveredRow === meeting.id ? 'var(--accent-soft)' : 'transparent',
                                transition: 'background 0.12s',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                                <span style={{ fontSize: 12, fontWeight: 500, color: hoveredRow === meeting.id ? 'var(--accent)' : 'var(--ink-900)', fontFamily: f, lineHeight: 1.4, flex: 1 }}>
                                    {meeting.title}
                                </span>
                                {statusDot(meeting.status)}
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--ink-400)', fontFamily: mono }}>{meeting.date}</div>
                            {hoveredRow === meeting.id && (
                                <div style={{ marginTop: 6, fontSize: 10, color: 'var(--accent)', fontFamily: f, fontWeight: 500 }}>
                                    + Insert into chat
                                </div>
                            )}
                        </div>
                    ))
                )}

                {!loading && activeTab === 'actions' && (
                    actions.length === 0 ? (
                        <div style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12, color: 'var(--ink-400)', fontStyle: 'italic', fontFamily: f }}>No actions found.</div>
                    ) : actions.map((action, i) => (
                        <div
                            key={action.id}
                            onClick={() => handleInsertContext('action', action)}
                            onMouseEnter={() => setHoveredRow(action.id)}
                            onMouseLeave={() => setHoveredRow(null)}
                            style={{
                                padding: '10px 16px',
                                borderBottom: i < actions.length - 1 ? '1px solid var(--border)' : 'none',
                                cursor: 'pointer',
                                background: hoveredRow === action.id ? 'var(--accent-soft)' : 'transparent',
                                transition: 'background 0.12s',
                                display: 'flex', alignItems: 'flex-start', gap: 8,
                            }}
                        >
                            <div style={{ paddingTop: 3 }}>{statusDot(action.status)}</div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 12, fontWeight: 500, color: hoveredRow === action.id ? 'var(--accent)' : 'var(--ink-900)', fontFamily: f, lineHeight: 1.4, marginBottom: 3 }}>
                                    {action.task}
                                </div>
                                <div style={{ fontSize: 10, color: 'var(--ink-400)', fontFamily: mono }}>
                                    {action.assignee} · Due {action.dueDate}
                                </div>
                                {hoveredRow === action.id && (
                                    <div style={{ marginTop: 4, fontSize: 10, color: 'var(--accent)', fontFamily: f, fontWeight: 500 }}>+ Insert into chat</div>
                                )}
                            </div>
                        </div>
                    ))
                )}

                {!loading && activeTab === 'documents' && (
                    documents.length === 0 ? (
                        <div style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12, color: 'var(--ink-400)', fontStyle: 'italic', fontFamily: f }}>No documents found.</div>
                    ) : documents.map((doc, i) => (
                        <div
                            key={doc.id}
                            onClick={() => handleInsertContext('document', doc)}
                            onMouseEnter={() => setHoveredRow(doc.id)}
                            onMouseLeave={() => setHoveredRow(null)}
                            style={{
                                padding: '10px 16px',
                                borderBottom: i < documents.length - 1 ? '1px solid var(--border)' : 'none',
                                cursor: 'pointer',
                                background: hoveredRow === doc.id ? 'var(--accent-soft)' : 'transparent',
                                transition: 'background 0.12s',
                            }}
                        >
                            <div style={{ fontSize: 12, fontWeight: 500, color: hoveredRow === doc.id ? 'var(--accent)' : 'var(--ink-900)', fontFamily: f, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 3 }}>
                                {doc.name}
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--ink-400)', fontFamily: mono, textTransform: 'capitalize' }}>
                                {doc.type} · {doc.uploadedAt}
                            </div>
                            {hoveredRow === doc.id && (
                                <div style={{ marginTop: 4, fontSize: 10, color: 'var(--accent)', fontFamily: f, fontWeight: 500 }}>+ Insert into chat</div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Quick Insert footer */}
            <div style={{ padding: '10px 16px', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-400)', fontFamily: mono, marginBottom: 8 }}>Quick Insert</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                    {[
                        { label: 'Summary', type: 'summary', icon: 'summarize' },
                        { label: 'Stats', type: 'stats', icon: 'analytics' },
                    ].map(({ label, type, icon }) => (
                        <button
                            key={type}
                            onClick={() => handleInsertContext('template', { type })}
                            style={{
                                padding: '6px 8px', background: 'var(--ink-50)', border: '1px solid var(--border)',
                                cursor: 'pointer', fontFamily: f, fontSize: 11, color: 'var(--ink-700)',
                                display: 'flex', alignItems: 'center', gap: 4, transition: 'background 0.12s',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-soft)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'var(--ink-50)')}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 13, color: 'var(--accent)' }}>{icon}</span>
                            {label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
