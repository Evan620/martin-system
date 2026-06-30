import { useState, useEffect } from 'react'
import { subgroups as subgroupsApi } from '../../services/api'

interface SubGroup {
    id: string
    name: string
    description: string | null
    lead: { id: string; full_name: string; email: string } | null
    member_count: number
    document_count: number
    status: string
    // Additive R4 health fields (embedded in the list response)
    health_status?: 'healthy' | 'at_risk' | 'stalled'
    last_active_at?: string | null
    days_since_active?: number | null
}

// Maps a computed health status to a badge label + Tailwind classes,
// consistent with the existing status-pill styling in this component.
const HEALTH_BADGE: Record<string, { label: string; cls: string }> = {
    healthy: { label: 'Healthy', cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
    at_risk: { label: 'At risk', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
    stalled: { label: 'Stalled', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
}

function lastActiveLabel(sg: SubGroup): string | null {
    if (sg.days_since_active === 0) return 'Active today'
    if (typeof sg.days_since_active === 'number') {
        return `Active ${sg.days_since_active}d ago`
    }
    if (sg.last_active_at) {
        return `Active ${new Date(sg.last_active_at).toLocaleDateString()}`
    }
    return 'No activity yet'
}

interface SubgroupsManagerProps {
    twgId: string
    canEdit: boolean
    onOpenSubgroup: (sg: SubGroup) => void
}

export default function SubgroupsManager({ twgId, canEdit, onOpenSubgroup }: SubgroupsManagerProps) {
    const [sgList, setSgList] = useState<SubGroup[]>([])
    const [loading, setLoading] = useState(true)
    const [showCreate, setShowCreate] = useState(false)
    const [newName, setNewName] = useState('')
    const [newDesc, setNewDesc] = useState('')
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const load = async () => {
        try {
            setLoading(true)
            const res = await subgroupsApi.list(twgId)
            setSgList(res.data)
        } catch {
            setError('Failed to load subgroups.')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { load() }, [twgId])

    const handleCreate = async () => {
        if (!newName.trim()) return
        try {
            setCreating(true)
            setError(null)
            await subgroupsApi.create(twgId, { name: newName.trim(), description: newDesc.trim() || undefined })
            setNewName('')
            setNewDesc('')
            setShowCreate(false)
            await load()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to create subgroup.')
        } finally {
            setCreating(false)
        }
    }

    if (loading) {
        return <p className="text-slate-500 text-sm py-6">Loading subgroups...</p>
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="font-display" style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--ink-900)' }}>
                    Subgroups <span className="font-mono-geist" style={{ color: 'var(--ink-400)', fontWeight: 600, fontSize: 13, marginLeft: 4 }}>({sgList.length})</span>
                </h3>
                {canEdit && (
                    <button
                        onClick={() => setShowCreate(!showCreate)}
                        className="text-sm font-bold text-teal-600 hover:text-teal-500 transition-colors uppercase tracking-widest"
                    >
                        {showCreate ? 'Cancel' : '+ New Subgroup'}
                    </button>
                )}
            </div>

            {/* Create form */}
            {showCreate && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-700">
                    <input
                        type="text"
                        placeholder="Subgroup name *"
                        value={newName}
                        onChange={e => setNewName(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                    <input
                        type="text"
                        placeholder="Description (optional)"
                        value={newDesc}
                        onChange={e => setNewDesc(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                    {error && <p className="text-red-500 text-xs">{error}</p>}
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreate}
                            disabled={creating || !newName.trim()}
                            className="clickable-scale px-4 py-2 bg-teal-600 text-white text-sm font-bold rounded-lg hover:bg-teal-500 disabled:opacity-50 transition-colors"
                        >
                            {creating ? 'Creating...' : 'Create'}
                        </button>
                        <button
                            onClick={() => { setShowCreate(false); setError(null) }}
                            className="px-4 py-2 text-sm font-bold text-slate-500 hover:text-slate-700 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Empty state */}
            {sgList.length === 0 && !showCreate && (
                <div className="text-center py-12 text-slate-400">
                    <p className="text-sm">No subgroups yet.</p>
                    {canEdit && (
                        <p className="text-xs mt-1">Click "+ New Subgroup" to create one.</p>
                    )}
                </div>
            )}

            {/* Subgroup cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {sgList.map(sg => (
                    <div
                        key={sg.id}
                        className="clickable-scale qp-transition group"
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderRadius: 'var(--radius-card)', background: 'var(--surface)', border: '1px solid var(--border)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-2)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--surface)'; }}
                    >
                        <div className="min-w-0">
                            <div className="group-hover:text-teal-600 transition-colors truncate" style={{ fontWeight: 700, fontSize: 13, color: 'var(--ink-900)', letterSpacing: '-0.01em' }}>
                                {sg.name}
                            </div>
                            <div className="mt-0.5 flex items-center gap-2 flex-wrap" style={{ fontSize: 9, color: 'var(--ink-400)' }}>
                                {sg.lead && <span>Lead: {sg.lead.full_name}</span>}
                                <span>·</span>
                                <span className="font-mono-geist">{sg.member_count} member{sg.member_count !== 1 ? 's' : ''}</span>
                                <span>·</span>
                                <span className="font-mono-geist">{sg.document_count} doc{sg.document_count !== 1 ? 's' : ''}</span>
                                {lastActiveLabel(sg) && (<><span>·</span><span className="font-mono-geist">{lastActiveLabel(sg)}</span></>)}
                            </div>
                            {sg.description && (
                                <p className="mt-1 truncate max-w-md" style={{ fontSize: 11, color: 'var(--ink-500)' }}>{sg.description}</p>
                            )}
                        </div>
                        <div className="flex items-center gap-3 ml-4 shrink-0">
                            {sg.health_status && HEALTH_BADGE[sg.health_status] && (
                                <span title="Effectiveness signal: based on recent activity and action-item closure" className={`text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${HEALTH_BADGE[sg.health_status].cls}`}>
                                    {HEALTH_BADGE[sg.health_status].label}
                                </span>
                            )}
                            <span
                                className="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                                style={sg.status === 'active'
                                    ? { background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }
                                    : { background: 'var(--surface-2)', color: 'var(--ink-500)' }}
                            >
                                {sg.status}
                            </span>
                            <button
                                onClick={() => onOpenSubgroup(sg)}
                                className="transition-colors whitespace-nowrap"
                                style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)' }}
                            >
                                Open →
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
