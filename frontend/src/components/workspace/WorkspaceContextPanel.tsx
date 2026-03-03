import { useState, useEffect } from 'react';
import api from '../../services/api';
import { Card, Badge } from '../ui';
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

export default function WorkspaceContextPanel({ twgName, twgId, onInsertContext }: WorkspaceContextPanelProps) {
    const [activeTab, setActiveTab] = useState<'meetings' | 'actions' | 'documents'>('meetings');
    const [isCollapsed, setIsCollapsed] = useState(false);

    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [actions, setActions] = useState<ActionItem[]>([]);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!twgId) return;

        const fetchData = async () => {
            setLoading(true);
            // Secretariat sees all TWGs — omit twg_id filter
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
                        hasMinutes: !!m.minutes
                    })));
                } else if (activeTab === 'actions') {
                    const res = await api.get('/action-items', { params });
                    setActions(res.data.map((a: any) => ({
                        id: a.id,
                        task: a.description,
                        assignee: a.owner?.full_name || 'Unassigned',
                        dueDate: a.due_date ? new Date(a.due_date).toLocaleDateString() : 'No Date',
                        status: a.status.toLowerCase()
                    })));
                } else if (activeTab === 'documents') {
                    const res = await api.get('/documents', { params });
                    setDocuments(res.data.map((d: any) => ({
                        id: d.id,
                        name: d.file_name,
                        type: d.file_type.includes('pdf') ? 'output' : 'template',
                        uploadedAt: new Date(d.created_at).toLocaleDateString()
                    })));
                }
            } catch (error) {
                console.error("Failed to fetch context data", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [twgId, activeTab]);

    const handleInsertContext = (type: string, item: any) => {
        if (onInsertContext) {
            onInsertContext(type, item);
        }
    };

    if (isCollapsed) {
        return (
            <div className="w-12 bg-white dark:bg-[#1a202c] border-l border-[#e7ebf3] dark:border-[#2d3748] flex flex-col items-center py-4 gap-4">
                <button
                    onClick={() => setIsCollapsed(false)}
                    className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    title="Expand context panel"
                >
                    <span className="material-symbols-outlined text-slate-600 dark:text-slate-400">chevron_left</span>
                </button>
                <div className="flex flex-col gap-3">
                    <button className="p-2 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" title="Meetings">
                        <span className="material-symbols-outlined text-[20px]">event</span>
                    </button>
                    <button className="p-2 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" title="Actions">
                        <span className="material-symbols-outlined text-[20px]">task_alt</span>
                    </button>
                    <button className="p-2 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" title="Documents">
                        <span className="material-symbols-outlined text-[20px]">description</span>
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="w-80 bg-white dark:bg-[#1a202c] border-l border-[#e7ebf3] dark:border-[#2d3748] flex flex-col animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="p-4 border-b border-[#e7ebf3] dark:border-[#2d3748] flex items-center justify-between">
                <div>
                    <h3 className="font-semibold text-sm text-[#0d121b] dark:text-white">Workspace Context</h3>
                    <p className="text-xs text-[#6b7280] dark:text-[#9ca3af]">{twgName}</p>
                </div>
                <button
                    onClick={() => setIsCollapsed(true)}
                    className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition-colors"
                    title="Collapse panel"
                >
                    <span className="material-symbols-outlined text-[18px] text-slate-600 dark:text-slate-400">chevron_right</span>
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-[#e7ebf3] dark:border-[#2d3748]">
                <button
                    onClick={() => setActiveTab('meetings')}
                    className={`flex-1 px-4 py-3 text-xs font-semibold transition-colors ${activeTab === 'meetings'
                        ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                        : 'text-[#6b7280] dark:text-[#9ca3af] hover:text-[#0d121b] dark:hover:text-white'
                        }`}
                >
                    <span className="material-symbols-outlined text-[16px] block mx-auto mb-0.5">event</span>
                    Meetings
                </button>
                <button
                    onClick={() => setActiveTab('actions')}
                    className={`flex-1 px-4 py-3 text-xs font-semibold transition-colors ${activeTab === 'actions'
                        ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                        : 'text-[#6b7280] dark:text-[#9ca3af] hover:text-[#0d121b] dark:hover:text-white'
                        }`}
                >
                    <span className="material-symbols-outlined text-[16px] block mx-auto mb-0.5">task_alt</span>
                    Actions
                    {actions.filter(a => a.status === 'overdue').length > 0 && (
                        <span className="ml-1 inline-flex items-center justify-center w-4 h-4 text-[8px] font-bold text-white bg-red-500 rounded-full">
                            {actions.filter(a => a.status === 'overdue').length}
                        </span>
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('documents')}
                    className={`flex-1 px-4 py-3 text-xs font-semibold transition-colors ${activeTab === 'documents'
                        ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                        : 'text-[#6b7280] dark:text-[#9ca3af] hover:text-[#0d121b] dark:hover:text-white'
                        }`}
                >
                    <span className="material-symbols-outlined text-[16px] block mx-auto mb-0.5">description</span>
                    Docs
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                {loading && (
                    <div className="flex justify-center items-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                )}
                {!loading && activeTab === 'meetings' && (
                    <div className="space-y-3">
                        {meetings.map((meeting) => (
                            <Card
                                key={meeting.id}
                                className="p-3 hover:border-blue-500/30 transition-all cursor-pointer group"
                                onClick={() => handleInsertContext('meeting', meeting)}
                            >
                                <div className="flex items-start justify-between gap-2 mb-2">
                                    <h4 className="text-xs font-semibold text-[#0d121b] dark:text-white leading-tight flex-1">
                                        {meeting.title}
                                    </h4>
                                    <Badge
                                        variant={meeting.status === 'upcoming' ? 'info' : 'success'}
                                        size="sm"
                                        className="text-[8px] uppercase"
                                    >
                                        {meeting.status}
                                    </Badge>
                                </div>
                                <div className="flex items-center gap-1 text-[10px] text-[#6b7280] dark:text-[#9ca3af] mb-2">
                                    <span className="material-symbols-outlined text-[12px]">schedule</span>
                                    {meeting.date}
                                </div>
                                <div className="flex items-center gap-2">
                                    {meeting.hasAgenda && (
                                        <span className="text-[9px] px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded font-medium">
                                            Agenda
                                        </span>
                                    )}
                                    {meeting.hasMinutes && (
                                        <span className="text-[9px] px-2 py-0.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded font-medium">
                                            Minutes
                                        </span>
                                    )}
                                </div>
                                <div className="mt-2 pt-2 border-t border-[#e7ebf3] dark:border-[#2d3748] opacity-0 group-hover:opacity-100 transition-opacity">
                                    <div className="text-[9px] text-blue-600 dark:text-blue-400 font-semibold flex items-center gap-1">
                                        <span className="material-symbols-outlined text-[12px]">add_circle</span>
                                        Click to insert into chat
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}

                {!loading && activeTab === 'actions' && (
                    <div className="space-y-3">
                        {actions.map((action) => (
                            <Card
                                key={action.id}
                                className="p-3 hover:border-blue-500/30 transition-all cursor-pointer group"
                                onClick={() => handleInsertContext('action', action)}
                            >
                                <div className="flex items-start gap-2 mb-2">
                                    <div
                                        className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold ${action.status === 'overdue'
                                            ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                                            : action.status === 'in_progress'
                                                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                                            }`}
                                    >
                                        {action.status === 'completed' ? '✓' : '○'}
                                    </div>
                                    <div className="flex-1">
                                        <h4 className="text-xs font-medium text-[#0d121b] dark:text-white leading-tight mb-1">
                                            {action.task}
                                        </h4>
                                        <div className="flex items-center gap-2 text-[10px] text-[#6b7280] dark:text-[#9ca3af]">
                                            <span>{action.assignee}</span>
                                            <span>•</span>
                                            <span>Due {action.dueDate}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="pt-2 border-t border-[#e7ebf3] dark:border-[#2d3748] opacity-0 group-hover:opacity-100 transition-opacity">
                                    <div className="text-[9px] text-blue-600 dark:text-blue-400 font-semibold flex items-center gap-1">
                                        <span className="material-symbols-outlined text-[12px]">add_circle</span>
                                        Click to insert into chat
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}

                {!loading && activeTab === 'documents' && (
                    <div className="space-y-3">
                        {documents.map((doc) => (
                            <Card
                                key={doc.id}
                                className="p-3 hover:border-blue-500/30 transition-all cursor-pointer group"
                                onClick={() => handleInsertContext('document', doc)}
                            >
                                <div className="flex items-start gap-3">
                                    <div
                                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${doc.type === 'template'
                                            ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400'
                                            : doc.type === 'output'
                                                ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
                                                : 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                                            }`}
                                    >
                                        <span className="material-symbols-outlined text-[16px]">
                                            {doc.name.endsWith('.pdf')
                                                ? 'picture_as_pdf'
                                                : doc.name.endsWith('.xlsx')
                                                    ? 'table_chart'
                                                    : 'description'}
                                        </span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h4 className="text-xs font-medium text-[#0d121b] dark:text-white truncate mb-1">
                                            {doc.name}
                                        </h4>
                                        <div className="flex items-center gap-2 text-[10px] text-[#6b7280] dark:text-[#9ca3af]">
                                            <span className="capitalize">{doc.type}</span>
                                            <span>•</span>
                                            <span>{doc.uploadedAt}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-2 pt-2 border-t border-[#e7ebf3] dark:border-[#2d3748] opacity-0 group-hover:opacity-100 transition-opacity">
                                    <div className="text-[9px] text-blue-600 dark:text-blue-400 font-semibold flex items-center gap-1">
                                        <span className="material-symbols-outlined text-[12px]">add_circle</span>
                                        Click to reference in chat
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="p-3 border-t border-[#e7ebf3] dark:border-[#2d3748] bg-slate-50 dark:bg-slate-900/30">
                <div className="text-[9px] font-semibold text-[#6b7280] dark:text-[#9ca3af] uppercase tracking-wider mb-2">
                    Quick Insert
                </div>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        onClick={() => handleInsertContext('template', { type: 'summary' })}
                        className="p-2 text-left bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg hover:border-blue-500/30 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all group"
                    >
                        <span className="material-symbols-outlined text-[14px] text-blue-600 dark:text-blue-400 block mb-1">summarize</span>
                        <span className="text-[9px] font-medium text-[#0d121b] dark:text-white">Summary</span>
                    </button>
                    <button
                        onClick={() => handleInsertContext('template', { type: 'stats' })}
                        className="p-2 text-left bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg hover:border-blue-500/30 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all group"
                    >
                        <span className="material-symbols-outlined text-[14px] text-purple-600 dark:text-purple-400 block mb-1">analytics</span>
                        <span className="text-[9px] font-medium text-[#0d121b] dark:text-white">Stats</span>
                    </button>
                </div>
            </div>
        </div>
    );
}
