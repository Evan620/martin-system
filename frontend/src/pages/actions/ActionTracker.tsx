import { useState, useEffect, useCallback } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import { UserRole } from '../../types/auth'
import api, { actionItems, twgs } from '../../services/api'

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

interface TwgOption {
    id: string
    name: string
}

interface OwnerOption {
    id: string
    full_name: string
}

const STATUS_TRANSITIONS: Record<string, string[]> = {
    PENDING: ['IN_PROGRESS', 'COMPLETED'],
    IN_PROGRESS: ['COMPLETED', 'PENDING'],
    OVERDUE: ['IN_PROGRESS', 'COMPLETED'],
    COMPLETED: [],
}

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
    PENDING:     { label: 'To Do',       color: 'var(--ink-500)',  bg: 'var(--ink-50)' },
    IN_PROGRESS: { label: 'In Progress', color: 'var(--amber)',    bg: 'color-mix(in srgb, var(--amber) 12%, transparent)' },
    OVERDUE:     { label: 'Overdue',     color: 'var(--terra)',    bg: 'color-mix(in srgb, var(--terra) 12%, transparent)' },
    COMPLETED:   { label: 'Completed',   color: 'var(--sage)',     bg: 'color-mix(in srgb, var(--sage) 12%, transparent)' },
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

    // Facilitator-only cross-TWG / cross-owner filters. The backend enforces
    // its own access guards on twg_id / owner_id; these selectors are also
    // gated in the UI so plain members never see them.
    const [twgFilter, setTwgFilter] = useState<string>('')
    const [ownerFilter, setOwnerFilter] = useState<string>('')
    const [twgOptions, setTwgOptions] = useState<TwgOption[]>([])
    const [ownerOptions, setOwnerOptions] = useState<OwnerOption[]>([])

    // Load the TWG list for the selector (facilitators / admins / leads only).
    useEffect(() => {
        if (!isFacilitator) return
        twgs.dropdown()
            .then(res => setTwgOptions(res.data || []))
            .catch(err => console.error('Failed to load TWGs:', err))
    }, [isFacilitator])

    // Owners are TWG-scoped: load members of the selected TWG. Clearing the TWG
    // also clears the owner selection so we never send a stale owner_id.
    useEffect(() => {
        if (!isFacilitator || !twgFilter) {
            setOwnerOptions([])
            setOwnerFilter('')
            return
        }
        twgs.listMembers(twgFilter)
            .then(res => setOwnerOptions(
                (res.data || []).map((m: any) => ({ id: m.id, full_name: m.full_name }))
            ))
            .catch(err => console.error('Failed to load TWG members:', err))
    }, [isFacilitator, twgFilter])

    const fetchData = useCallback(async () => {
        try {
            const params: Record<string, any> = {}
            if (statusFilter) params.status = statusFilter
            // Facilitator cross-cutting filters take precedence over mine_only.
            if (isFacilitator && (twgFilter || ownerFilter)) {
                if (twgFilter) params.twg_id = twgFilter
                if (ownerFilter) params.owner_id = ownerFilter
            } else if (mineOnly) {
                params.mine_only = true
            }

            const summaryParams: Record<string, any> = {}
            if (isFacilitator && twgFilter) summaryParams.twg_id = twgFilter

            const [itemsRes, summaryRes] = await Promise.all([
                api.get('/action-items/', { params }),
                api.get('/action-items/summary', { params: summaryParams }),
            ])
            setItems(itemsRes.data)
            setSummary(summaryRes.data)
        } catch (err) {
            console.error('Failed to fetch action items:', err)
        } finally {
            setLoading(false)
        }
    }, [statusFilter, mineOnly, isFacilitator, twgFilter, ownerFilter])

    useEffect(() => { fetchData() }, [fetchData])

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
        if (!dateStr) return '—'
        const d = new Date(dateStr)
        const today = new Date()
        const diff = Math.ceil((d.getTime() - today.getTime()) / 86400000)
        if (diff === 0) return 'Today'
        if (diff === 1) return 'Tomorrow'
        if (diff < 0 && diff > -7) return `${Math.abs(diff)}d ago`
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }

    const isDateOverdue = (dateStr: string | null, status: string) => {
        if (!dateStr || status === 'COMPLETED') return false
        return new Date(dateStr) < new Date()
    }

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 256 }}>
                <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--accent)' }} />
            </div>
        )
    }

    const stats = [
        { label: 'Overdue',     value: summary?.overdue ?? 0,      sub: 'need attention',                         accent: 'var(--terra)' },
        { label: 'In Progress', value: summary?.in_progress ?? 0,  sub: `${summary?.due_this_week ?? 0} due this week`, accent: 'var(--amber)' },
        { label: 'To Do',       value: summary?.pending ?? 0,       sub: 'open items',                             accent: 'var(--ink-500)' },
        { label: 'Completed',   value: summary?.completed ?? 0,    sub: `${summary?.completed_this_week ?? 0} this week`, accent: 'var(--sage)' },
    ]

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>

            {/* Page header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, color: 'var(--ink-500)', marginBottom: 6 }}>
                    Action Tracker
                </div>
                <h1 style={{ fontFamily: "'Geist', system-ui, sans-serif", fontWeight: 800, fontSize: 18, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                    {isFacilitator ? 'Actions' : 'My Actions'}
                </h1>
            </div>

            {/* Stats strip */}
            <div
                className="stats-strip"
                style={{
                    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    padding: '20px 28px', marginBottom: 24, gap: 0,
                }}
            >
                {stats.map((s, i) => (
                    <div
                        key={s.label}
                        onClick={() => setStatusFilter(
                            s.label === 'Overdue' ? (statusFilter === 'OVERDUE' ? '' : 'OVERDUE') :
                            s.label === 'In Progress' ? (statusFilter === 'IN_PROGRESS' ? '' : 'IN_PROGRESS') :
                            s.label === 'To Do' ? (statusFilter === 'PENDING' ? '' : 'PENDING') :
                            (statusFilter === 'COMPLETED' ? '' : 'COMPLETED')
                        )}
                        style={{
                            paddingLeft: i > 0 ? 24 : 0,
                            paddingRight: i < 3 ? 24 : 0,
                            borderRight: i < 3 ? '1px solid var(--border)' : 'none',
                            cursor: 'pointer',
                        }}
                    >
                        <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600 }}>{s.label}</div>
                        <div style={{ fontFamily: "'Geist Mono', monospace", fontWeight: 800, fontSize: 28, color: s.accent, letterSpacing: '-0.02em', marginTop: 4, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{s.value}</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 4 }}>{s.sub}</div>
                    </div>
                ))}
            </div>

            {/* Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {/* Status filter pills */}
                    {[{ key: '', label: 'All' }, { key: 'PENDING', label: 'To Do' }, { key: 'IN_PROGRESS', label: 'In Progress' }, { key: 'OVERDUE', label: 'Overdue' }, { key: 'COMPLETED', label: 'Completed' }].map(f => (
                        <button
                            key={f.key}
                            onClick={() => setStatusFilter(f.key)}
                            style={{
                                fontSize: 12, padding: '5px 12px', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 500,
                                background: statusFilter === f.key ? 'var(--accent)' : 'var(--surface)',
                                border: `1px solid ${statusFilter === f.key ? 'var(--accent)' : 'var(--border)'}`,
                                color: statusFilter === f.key ? 'var(--accent-ink)' : 'var(--ink-600)',
                            }}
                        >
                            {f.label}
                            {f.key && (
                                <span style={{ marginLeft: 6, fontSize: 10, opacity: 0.7 }}>
                                    {f.key === 'PENDING' ? summary?.pending ?? 0
                                     : f.key === 'IN_PROGRESS' ? summary?.in_progress ?? 0
                                     : f.key === 'OVERDUE' ? summary?.overdue ?? 0
                                     : summary?.completed ?? 0}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {/* Facilitator-only: filter by TWG and by owner. */}
                    {isFacilitator && (
                        <>
                            <select
                                value={twgFilter}
                                onChange={e => { setTwgFilter(e.target.value); setMineOnly(false) }}
                                style={{
                                    fontSize: 12, padding: '5px 10px', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 500,
                                    background: twgFilter ? 'var(--accent-soft)' : 'var(--surface)',
                                    border: `1px solid ${twgFilter ? 'var(--accent)' : 'var(--border)'}`,
                                    color: 'var(--ink-700)',
                                }}
                            >
                                <option value="">All TWGs</option>
                                {twgOptions.map(t => (
                                    <option key={t.id} value={t.id}>{t.name}</option>
                                ))}
                            </select>
                            <select
                                value={ownerFilter}
                                onChange={e => { setOwnerFilter(e.target.value); setMineOnly(false) }}
                                disabled={!twgFilter}
                                title={!twgFilter ? 'Select a TWG to filter by owner' : undefined}
                                style={{
                                    fontSize: 12, padding: '5px 10px', cursor: twgFilter ? 'pointer' : 'not-allowed', fontFamily: 'inherit', fontWeight: 500,
                                    background: ownerFilter ? 'var(--accent-soft)' : 'var(--surface)',
                                    border: `1px solid ${ownerFilter ? 'var(--accent)' : 'var(--border)'}`,
                                    color: 'var(--ink-700)',
                                    opacity: twgFilter ? 1 : 0.5,
                                }}
                            >
                                <option value="">All owners</option>
                                {ownerOptions.map(o => (
                                    <option key={o.id} value={o.id}>{o.full_name}</option>
                                ))}
                            </select>
                        </>
                    )}
                    <button
                        onClick={() => { setMineOnly(!mineOnly); if (!mineOnly) { setTwgFilter(''); setOwnerFilter('') } }}
                        style={{
                            fontSize: 12, padding: '5px 14px', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 500,
                            background: mineOnly ? 'var(--accent)' : 'transparent',
                            border: `1px solid ${mineOnly ? 'var(--accent)' : 'var(--border)'}`,
                            color: mineOnly ? 'var(--accent-ink)' : 'var(--ink-600)',
                        }}
                    >
                        My Items
                    </button>
                </div>
            </div>

            {/* Table */}
            <div className="resp-table-mobile" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
                {/* Header */}
                <div
                    className="resp-thead"
                    style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 150px 110px 90px 110px 130px',
                        padding: '10px 16px',
                        background: 'var(--surface-2)',
                        borderBottom: '1px solid var(--border)',
                    }}
                >
                    {['Description', 'Owner', 'Due Date', 'Priority', 'Status', 'Actions'].map(col => (
                        <div key={col} style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600 }}>
                            {col}
                        </div>
                    ))}
                </div>

                {/* Rows */}
                {items.length === 0 ? (
                    <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--ink-400)' }}>
                        <p style={{ fontSize: 15, fontWeight: 500, margin: 0 }}>No action items</p>
                        <p style={{ fontSize: 13, marginTop: 4 }}>
                            {statusFilter ? 'No items match this filter.' : 'Action items are created from meeting minutes.'}
                        </p>
                    </div>
                ) : (
                    items.map((item, idx) => {
                        const isCompleted = item.status === 'COMPLETED'
                        const dueDateOverdue = isDateOverdue(item.due_date, item.status)
                        const transitions = STATUS_TRANSITIONS[item.status] || []
                        const meta = STATUS_META[item.status] || STATUS_META.PENDING
                        const isLast = idx === items.length - 1

                        return (
                            <div
                                key={item.id}
                                className="resp-row"
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: '1fr 150px 110px 90px 110px 130px',
                                    padding: '13px 16px',
                                    borderBottom: isLast ? 'none' : '1px solid var(--border)',
                                    alignItems: 'center',
                                    opacity: isCompleted ? 0.55 : 1,
                                    transition: 'background 0.1s',
                                }}
                                onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                            >
                                {/* Description */}
                                <div data-label="primary" style={{ fontSize: 13, color: 'var(--ink-900)', textDecoration: isCompleted ? 'line-through' : 'none', paddingRight: 16, lineHeight: 1.4 }}>
                                    {item.description}
                                </div>

                                {/* Owner */}
                                <div data-label="Owner" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <div style={{
                                        width: 26, height: 26, borderRadius: '50%',
                                        background: 'var(--accent-soft)', color: 'var(--accent)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontSize: 10, fontWeight: 600, flexShrink: 0,
                                    }}>
                                        {getInitials(item.owner?.full_name)}
                                    </div>
                                    <span style={{ fontSize: 12, color: 'var(--ink-600)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {item.owner?.full_name || 'Unassigned'}
                                    </span>
                                </div>

                                {/* Due Date */}
                                <div data-label="Due" style={{
                                    fontFamily: "'Geist Mono', monospace",
                                    fontSize: 11,
                                    fontWeight: dueDateOverdue ? 600 : 400,
                                    color: dueDateOverdue ? 'var(--terra)' : 'var(--ink-500)',
                                }}>
                                    {formatDate(item.due_date)}
                                </div>

                                {/* Priority */}
                                <div data-label="Priority" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <div style={{
                                        width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                                        background: item.priority?.toUpperCase() === 'HIGH' ? 'var(--terra)'
                                            : item.priority?.toUpperCase() === 'MEDIUM' ? 'var(--amber)'
                                            : 'var(--ink-300)',
                                    }} />
                                    <span style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'capitalize' }}>
                                        {item.priority?.toLowerCase() || 'normal'}
                                    </span>
                                </div>

                                {/* Status badge */}
                                <div data-label="Status">
                                    <span style={{
                                        fontSize: 8, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em',
                                        padding: '3px 8px', borderRadius: 999,
                                        background: meta.bg, color: meta.color,
                                        whiteSpace: 'nowrap', display: 'inline-block',
                                    }}>
                                        {meta.label}
                                    </span>
                                </div>

                                {/* Actions */}
                                <div data-label="Move to" style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                                    {transitions.map(next => {
                                        const nextMeta = STATUS_META[next] || STATUS_META.PENDING
                                        return (
                                            <button
                                                key={next}
                                                onClick={() => handleStatusChange(item.id, next)}
                                                disabled={updatingId === item.id}
                                                style={{
                                                    fontSize: 10, padding: '3px 9px', cursor: 'pointer',
                                                    fontFamily: 'inherit', fontWeight: 500,
                                                    background: 'transparent',
                                                    border: `1px solid ${nextMeta.color}`,
                                                    color: nextMeta.color,
                                                    opacity: updatingId === item.id ? 0.4 : 1,
                                                    whiteSpace: 'nowrap',
                                                }}
                                            >
                                                {updatingId === item.id ? '…' : nextMeta.label}
                                            </button>
                                        )
                                    })}
                                </div>
                            </div>
                        )
                    })
                )}
            </div>

            {/* Footer count */}
            {items.length > 0 && (
                <div style={{ marginTop: 10, fontSize: 11, color: 'var(--ink-400)', textAlign: 'right' }}>
                    {items.length} item{items.length !== 1 ? 's' : ''}
                    {statusFilter && ` · filtered by ${STATUS_META[statusFilter]?.label || statusFilter}`}
                </div>
            )}
        </div>
    )
}
