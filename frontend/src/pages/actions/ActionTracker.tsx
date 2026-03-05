import { useState, useEffect, useCallback } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import { UserRole } from '../../types/auth'
import { Card, Badge, Avatar } from '../../components/ui'
import { actionItems } from '../../services/api'

interface ActionItemData {
    id: string
    description: string
    owner_id: string
    owner?: { full_name: string; email: string } | null
    due_date: string | null
    status: string
    priority: string
    meeting_id?: string | null
    twg_id: string
    created_at: string | null
    updated_at: string | null
    completed_at: string | null
}

interface SummaryData {
    pending: number
    in_progress: number
    completed: number
    overdue: number
    due_this_week: number
    completed_this_week: number
}

const STATUS_COLUMNS = [
    { key: 'PENDING', label: 'To Do', color: 'bg-slate-400' },
    { key: 'IN_PROGRESS', label: 'In Progress', color: 'bg-blue-600' },
    { key: 'OVERDUE', label: 'Overdue', color: 'bg-red-500' },
    { key: 'COMPLETED', label: 'Completed', color: 'bg-green-500' },
] as const

const PRIORITY_COLORS: Record<string, string> = {
    high: 'text-red-600 bg-red-50 dark:bg-red-900/30',
    medium: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30',
    low: 'text-green-600 bg-green-50 dark:bg-green-900/30',
}

const STATUS_TRANSITIONS: Record<string, string[]> = {
    PENDING: ['IN_PROGRESS', 'COMPLETED'],
    IN_PROGRESS: ['COMPLETED', 'PENDING'],
    OVERDUE: ['IN_PROGRESS', 'COMPLETED'],
    COMPLETED: [],
}

export default function ActionTracker() {
    const user = useSelector((state: RootState) => state.auth.user)
    const isFacilitator = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD || user?.role === UserRole.FACILITATOR

    const [items, setItems] = useState<ActionItemData[]>([])
    const [summary, setSummary] = useState<SummaryData | null>(null)
    const [loading, setLoading] = useState(true)
    const [statusFilter, setStatusFilter] = useState<string>('')
    const [mineOnly, setMineOnly] = useState(!isFacilitator)
    const [updatingId, setUpdatingId] = useState<string | null>(null)

    const fetchData = useCallback(async () => {
        try {
            const params: Record<string, any> = {}
            if (statusFilter) params.status = statusFilter
            if (mineOnly) params.mine_only = true

            const [itemsRes, summaryRes] = await Promise.all([
                actionItems.list(params),
                actionItems.summary(),
            ])
            setItems(itemsRes.data)
            setSummary(summaryRes.data)
        } catch (err) {
            console.error('Failed to fetch action items:', err)
        } finally {
            setLoading(false)
        }
    }, [statusFilter, mineOnly])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    const handleStatusChange = async (itemId: string, newStatus: string) => {
        setUpdatingId(itemId)
        try {
            await actionItems.update(itemId, { status: newStatus })
            await fetchData()
        } catch (err: any) {
            const detail = err?.response?.data?.detail || 'Failed to update status'
            alert(detail)
        } finally {
            setUpdatingId(null)
        }
    }

    const getInitials = (name?: string) => {
        if (!name) return '??'
        return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    }

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'No date'
        return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }

    const isRecentlyCreated = (createdAt: string | null) => {
        if (!createdAt) return false
        const diff = Date.now() - new Date(createdAt).getTime()
        return diff < 24 * 60 * 60 * 1000
    }

    const recentCount = items.filter(i => isRecentlyCreated(i.created_at)).length

    const stats = [
        { label: 'Open Items', value: summary ? summary.pending + summary.in_progress : 0, change: `${summary?.due_this_week || 0} due this week`, icon: ListIcon, color: 'text-blue-500' },
        { label: 'Overdue', value: summary?.overdue || 0, change: 'need attention', icon: AlertIcon, color: 'text-red-500' },
        { label: 'Completed (Week)', value: summary?.completed_this_week || 0, change: 'items done', icon: CheckIcon, color: 'text-green-500' },
    ]

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">
                        {isFacilitator ? 'Action Items Tracker' : 'My Action Items'}
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        {isFacilitator
                            ? 'Track and manage action items across your working groups'
                            : 'View and update your assigned action items'}
                    </p>
                </div>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {stats.map((stat) => (
                    <Card key={stat.label} className="p-5 flex items-start justify-between">
                        <div className="space-y-1">
                            <p className="text-xs font-bold text-slate-500 dark:text-slate-500 uppercase tracking-wider">{stat.label}</p>
                            <div className="flex items-baseline gap-2">
                                <h2 className="text-3xl font-display font-bold text-slate-900 dark:text-white transition-colors">{stat.value}</h2>
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${stat.color === 'text-red-500' ? 'bg-red-50 text-red-600 dark:bg-red-900/30' : 'bg-green-50 text-green-600 dark:bg-green-900/30'}`}>
                                    {stat.change}
                                </span>
                            </div>
                        </div>
                        <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl transition-colors">
                            <stat.icon className={`w-6 h-6 ${stat.color}`} />
                        </div>
                    </Card>
                ))}
            </div>

            {/* AI extraction alert — only show if recent items exist */}
            {recentCount > 0 && (
                <div className="bg-blue-600/10 border border-blue-500/20 rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        </div>
                        <div>
                            <h4 className="font-bold text-slate-900 dark:text-white transition-colors">New Action Items</h4>
                            <p className="text-xs text-slate-600 dark:text-slate-400">{recentCount} action item{recentCount > 1 ? 's' : ''} created in the last 24 hours</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Filter toolbar */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-dark-border pb-4 transition-colors">
                <div className="flex gap-3 items-center">
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-dark-card text-slate-700 dark:text-slate-300"
                    >
                        <option value="">All Statuses</option>
                        <option value="PENDING">To Do</option>
                        <option value="IN_PROGRESS">In Progress</option>
                        <option value="OVERDUE">Overdue</option>
                        <option value="COMPLETED">Completed</option>
                    </select>
                    <button
                        onClick={() => setMineOnly(!mineOnly)}
                        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${mineOnly ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-blue-500'}`}
                    >
                        My Items
                    </button>
                </div>
            </div>

            {/* Action Items List */}
            {items.length === 0 && !statusFilter ? (
                <div className="text-center py-16 text-slate-400">
                    <p className="text-lg font-medium">No action items yet</p>
                    <p className="text-sm mt-1">Action items will appear here once created from meeting minutes</p>
                </div>
            ) : (
                <Card className="overflow-hidden">
                    {/* Table Header */}
                    <div className="grid grid-cols-[1fr_140px_140px_120px_160px] gap-4 px-5 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        <span>Description</span>
                        <span>Owner</span>
                        <span>Due Date</span>
                        <span>Status</span>
                        <span>Actions</span>
                    </div>

                    {/* Rows */}
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                        {items.map((item) => {
                            const isOverdue = item.status === 'OVERDUE'
                            const isCompleted = item.status === 'COMPLETED'
                            const transitions = STATUS_TRANSITIONS[item.status] || []
                            const statusColor = STATUS_COLUMNS.find(c => c.key === item.status)

                            return (
                                <div
                                    key={item.id}
                                    className={`grid grid-cols-[1fr_140px_140px_120px_160px] gap-4 px-5 py-3.5 items-center transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30 ${isOverdue ? 'bg-red-50/40 dark:bg-red-900/5' : ''}`}
                                >
                                    {/* Description */}
                                    <div className="min-w-0">
                                        <span className={`text-sm leading-snug ${isCompleted ? 'text-slate-400 line-through' : 'text-slate-900 dark:text-white font-medium'}`}>
                                            {item.description}
                                        </span>
                                    </div>

                                    {/* Owner */}
                                    <div className="flex items-center gap-2 min-w-0">
                                        <Avatar size="sm" fallback={getInitials(item.owner?.full_name)} />
                                        <span className="text-xs text-slate-600 dark:text-slate-400 truncate">{item.owner?.full_name || 'Unassigned'}</span>
                                    </div>

                                    {/* Due Date */}
                                    <div className={`flex items-center gap-1.5 text-xs font-medium ${isOverdue ? 'text-red-500' : isCompleted ? 'text-slate-400' : 'text-slate-600 dark:text-slate-400'}`}>
                                        <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                                        {formatDate(item.due_date)}
                                    </div>

                                    {/* Status Badge */}
                                    <div>
                                        <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-1 rounded-full ${
                                            isCompleted ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : isOverdue ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                            : item.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                        }`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${statusColor?.color || 'bg-slate-400'}`}></span>
                                            {statusColor?.label || item.status}
                                        </span>
                                    </div>

                                    {/* Status Transition Buttons */}
                                    <div className="flex gap-1.5 flex-wrap">
                                        {transitions.map((nextStatus) => (
                                            <button
                                                key={nextStatus}
                                                onClick={() => handleStatusChange(item.id, nextStatus)}
                                                disabled={updatingId === item.id}
                                                className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-colors disabled:opacity-50 ${
                                                    nextStatus === 'COMPLETED'
                                                        ? 'border-green-300 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30'
                                                        : nextStatus === 'IN_PROGRESS'
                                                        ? 'border-blue-300 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30'
                                                        : 'border-slate-300 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'
                                                }`}
                                            >
                                                {updatingId === item.id ? '...' : nextStatus.replace('_', ' ')}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </Card>
            )}
        </div>
    )
}

function ListIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
    )
}

function AlertIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
    )
}

function CheckIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
    )
}
