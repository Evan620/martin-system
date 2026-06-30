import { useState, useEffect } from 'react'
import { subgroups as subgroupsApi, twgs as twgsApi } from '../../services/api'

interface SubGroupMember {
    id: string
    full_name: string
    email: string
}

interface SubGroupDoc {
    id: string
    file_name: string
    file_type: string
    created_at: string
    is_confidential: boolean
}

interface SubGroup {
    id: string
    name: string
    description: string | null
    lead_id: string | null
    lead: SubGroupMember | null
    members: SubGroupMember[]
    member_count: number
    document_count: number
    status: string
    // Additive R4 health fields (carried on the subgroup object from the list response)
    health_status?: 'healthy' | 'at_risk' | 'stalled'
    last_active_at?: string | null
    days_since_active?: number | null
}

const HEALTH_BADGE: Record<string, { label: string; cls: string }> = {
    healthy: { label: 'Healthy', cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
    at_risk: { label: 'At risk', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
    stalled: { label: 'Stalled', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
}

function lastActiveLabel(sg: SubGroup): string {
    if (sg.days_since_active === 0) return 'Active today'
    if (typeof sg.days_since_active === 'number') return `Active ${sg.days_since_active}d ago`
    if (sg.last_active_at) return `Active ${new Date(sg.last_active_at).toLocaleDateString()}`
    return 'No activity yet'
}

interface SubgroupDetailProps {
    twgId: string
    twgName: string
    subgroup: SubGroup
    canEdit: boolean
    onBack: () => void
}

export default function SubgroupDetail({ twgId, twgName, subgroup: initialSubgroup, canEdit, onBack }: SubgroupDetailProps) {
    const [activeTab, setActiveTab] = useState<'members' | 'documents'>('members')
    const [sg] = useState<SubGroup>(initialSubgroup)
    const [members, setMembers] = useState<SubGroupMember[]>([])
    const [docs, setDocs] = useState<SubGroupDoc[]>([])
    const [twgMembers, setTwgMembers] = useState<SubGroupMember[]>([])
    const [loadingMembers, setLoadingMembers] = useState(true)
    const [loadingDocs, setLoadingDocs] = useState(false)
    const [showAddMember, setShowAddMember] = useState(false)
    const [selectedUserId, setSelectedUserId] = useState('')
    const [adding, setAdding] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const loadMembers = async () => {
        try {
            setLoadingMembers(true)
            const res = await subgroupsApi.listMembers(twgId, sg.id)
            setMembers(res.data)
        } catch {
            setError('Failed to load members.')
        } finally {
            setLoadingMembers(false)
        }
    }

    const loadDocs = async () => {
        try {
            setLoadingDocs(true)
            const res = await subgroupsApi.listDocuments(twgId, sg.id)
            setDocs(res.data)
        } catch {
            setError('Failed to load documents.')
        } finally {
            setLoadingDocs(false)
        }
    }

    const loadTwgMembers = async () => {
        try {
            const res = await twgsApi.listMembers(twgId)
            setTwgMembers(res.data)
        } catch {}
    }

    useEffect(() => {
        loadMembers()
        loadTwgMembers()
    }, [sg.id])

    useEffect(() => {
        if (activeTab === 'documents') loadDocs()
    }, [activeTab])

    const availableToAdd = twgMembers.filter(m => !members.some(sm => sm.id === m.id))

    const handleAddMember = async () => {
        if (!selectedUserId) return
        try {
            setAdding(true)
            setError(null)
            await subgroupsApi.addMember(twgId, sg.id, selectedUserId)
            setSelectedUserId('')
            setShowAddMember(false)
            await loadMembers()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to add member.')
        } finally {
            setAdding(false)
        }
    }

    const handleRemoveMember = async (userId: string) => {
        try {
            setError(null)
            await subgroupsApi.removeMember(twgId, sg.id, userId)
            await loadMembers()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to remove member.')
        }
    }

    return (
        <div className="space-y-4">
            {/* Back link */}
            <button
                onClick={onBack}
                className="text-sm text-teal-600 hover:text-teal-500 font-bold transition-colors"
            >
                ← Back to Subgroups
            </button>

            {/* Header */}
            <div>
                <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-xl font-display font-bold text-slate-900 dark:text-white">{sg.name}</h3>
                    {sg.health_status && HEALTH_BADGE[sg.health_status] && (
                        <span
                            title="Effectiveness signal: based on recent activity and action-item closure"
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${HEALTH_BADGE[sg.health_status].cls}`}
                        >
                            {HEALTH_BADGE[sg.health_status].label}
                        </span>
                    )}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                    {sg.lead && <>Lead: {sg.lead.full_name} &nbsp;·&nbsp; </>}
                    {twgName}
                    {(sg.last_active_at !== undefined || sg.days_since_active !== undefined) && (
                        <> &nbsp;·&nbsp; {lastActiveLabel(sg)}</>
                    )}
                </p>
                {sg.description && (
                    <p className="text-sm text-slate-500 mt-2 italic">{sg.description}</p>
                )}
            </div>

            {/* Inner tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700">
                <div className="flex gap-6">
                    {(['members', 'documents'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-3 text-sm font-bold transition-all border-b-2 capitalize ${activeTab === tab
                                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {error && (
                <p className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{error}</p>
            )}

            {/* Members tab */}
            {activeTab === 'members' && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500">{members.length} member{members.length !== 1 ? 's' : ''}</span>
                        {canEdit && (
                            <button
                                onClick={() => setShowAddMember(!showAddMember)}
                                className="text-sm font-bold text-teal-600 hover:text-teal-500 transition-colors uppercase tracking-widest"
                            >
                                {showAddMember ? 'Cancel' : '+ Add Member'}
                            </button>
                        )}
                    </div>

                    {/* Add member form */}
                    {showAddMember && (
                        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-700">
                            <p className="text-xs text-slate-500">Select from existing TWG members:</p>
                            <select
                                value={selectedUserId}
                                onChange={e => setSelectedUserId(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                            >
                                <option value="">-- Select a member --</option>
                                {availableToAdd.map(m => (
                                    <option key={m.id} value={m.id}>{m.full_name} ({m.email})</option>
                                ))}
                            </select>
                            {availableToAdd.length === 0 && (
                                <p className="text-xs text-slate-400">All TWG members are already in this subgroup.</p>
                            )}
                            <button
                                onClick={handleAddMember}
                                disabled={adding || !selectedUserId}
                                className="clickable-scale px-4 py-2 bg-teal-600 text-white text-sm font-bold rounded-lg hover:bg-teal-500 disabled:opacity-50 transition-colors"
                            >
                                {adding ? 'Adding...' : 'Add'}
                            </button>
                        </div>
                    )}

                    {/* Member list */}
                    {loadingMembers ? (
                        <p className="text-slate-500 text-sm">Loading...</p>
                    ) : members.length === 0 ? (
                        <p className="text-slate-400 text-sm text-center py-8">No members yet.</p>
                    ) : (
                        <div className="space-y-2">
                            {members.map(m => (
                                <div key={m.id} className="flex items-center justify-between px-4 py-3 rounded-xl bg-white dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
                                    <div>
                                        <span className="text-sm font-medium text-slate-900 dark:text-white">{m.full_name}</span>
                                        {sg.lead_id === m.id && (
                                            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 font-medium">Lead</span>
                                        )}
                                        <p className="text-xs text-slate-400">{m.email}</p>
                                    </div>
                                    {canEdit && sg.lead_id !== m.id && (
                                        <button
                                            onClick={() => handleRemoveMember(m.id)}
                                            className="text-xs text-red-500 hover:text-red-400 font-medium transition-colors"
                                        >
                                            Remove
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Documents tab */}
            {activeTab === 'documents' && (
                <div className="space-y-2">
                    {loadingDocs ? (
                        <p className="text-slate-500 text-sm">Loading...</p>
                    ) : docs.length === 0 ? (
                        <p className="text-slate-400 text-sm text-center py-8">No documents in this subgroup yet.</p>
                    ) : (
                        docs.map(doc => (
                            <div key={doc.id} className="flex items-center justify-between px-4 py-3 rounded-xl bg-white dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
                                <div>
                                    <p className="text-sm font-medium text-slate-900 dark:text-white">{doc.file_name}</p>
                                    <p className="text-xs text-slate-400">{doc.file_type} · {new Date(doc.created_at).toLocaleDateString()}</p>
                                </div>
                                {doc.is_confidential && (
                                    <span className="text-xs text-slate-400 font-medium">Confidential</span>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}
