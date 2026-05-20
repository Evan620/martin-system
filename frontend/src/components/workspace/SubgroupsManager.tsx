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
                <h3 className="text-lg font-display font-bold text-slate-900 dark:text-white">
                    Subgroups <span className="text-slate-400 font-normal text-sm ml-1">({sgList.length})</span>
                </h3>
                {canEdit && (
                    <button
                        onClick={() => setShowCreate(!showCreate)}
                        className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors uppercase tracking-widest"
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
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                        type="text"
                        placeholder="Description (optional)"
                        value={newDesc}
                        onChange={e => setNewDesc(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {error && <p className="text-red-500 text-xs">{error}</p>}
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreate}
                            disabled={creating || !newName.trim()}
                            className="px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-colors"
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
            {sgList.map(sg => (
                <div
                    key={sg.id}
                    className="flex items-center justify-between p-4 rounded-xl bg-white dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-500 transition-all group"
                >
                    <div className="min-w-0">
                        <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors truncate">
                            {sg.name}
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2 flex-wrap">
                            {sg.lead && <span>Lead: {sg.lead.full_name}</span>}
                            <span>·</span>
                            <span>{sg.member_count} member{sg.member_count !== 1 ? 's' : ''}</span>
                            <span>·</span>
                            <span>{sg.document_count} doc{sg.document_count !== 1 ? 's' : ''}</span>
                        </div>
                        {sg.description && (
                            <p className="text-xs text-slate-500 mt-1 truncate max-w-md">{sg.description}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-3 ml-4 shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sg.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500'}`}>
                            {sg.status}
                        </span>
                        <button
                            onClick={() => onOpenSubgroup(sg)}
                            className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors whitespace-nowrap"
                        >
                            Open →
                        </button>
                    </div>
                </div>
            ))}
        </div>
    )
}
