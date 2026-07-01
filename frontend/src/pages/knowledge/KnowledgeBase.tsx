import { useState, useEffect, useMemo } from 'react'
import { Card, Badge, Avatar } from '../../components/ui'
import documentService, { Document, SearchResult } from '../../services/documentService'
import { useAppSelector } from '../../hooks/useRedux'
import { UserRole } from '../../types/auth'

const TABS = ['All', 'Documents', 'Confidential', 'Public'] as const
type Tab = typeof TABS[number]

const DATE_RANGES = [
    { label: 'All time', days: 0 },
    { label: 'Past month', days: 30 },
    { label: 'Past 6 months', days: 182 },
    { label: 'Past year', days: 365 },
]

function fileType(name: string): 'pdf' | 'doc' | 'ppt' {
    const n = name.toLowerCase()
    if (n.endsWith('.pdf')) return 'pdf'
    if (n.endsWith('.ppt') || n.endsWith('.pptx')) return 'ppt'
    return 'doc'
}

function initials(name?: string): string {
    if (!name) return '?'
    const parts = name.trim().split(/\s+/)
    return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
}

export default function KnowledgeBase() {
    const currentUser = useAppSelector((state) => state.auth.user)
    const isAdmin = currentUser?.role === UserRole.ADMIN || currentUser?.role === UserRole.SECRETARIAT_LEAD
    const userTwgIds = currentUser?.twg_ids || []

    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const [queryInput, setQueryInput] = useState('')
    const [query, setQuery] = useState('')
    const [activeTab, setActiveTab] = useState<Tab>('All')
    const [dateRangeIdx, setDateRangeIdx] = useState(0)
    const [selectedTwgIds, setSelectedTwgIds] = useState<string[]>([])

    const [fragments, setFragments] = useState<SearchResult[]>([])
    const [searchingFragments, setSearchingFragments] = useState(false)

    useEffect(() => {
        const fetchDocs = async () => {
            try {
                setLoading(true)
                const { data } = await documentService.listDocuments(undefined, 1, 1000)
                setDocuments(data)
            } catch (e) {
                console.error('Failed to load knowledge base documents:', e)
                setError('Unable to load documents. Please try again later.')
            } finally {
                setLoading(false)
            }
        }
        fetchDocs()
    }, [])

    // Distinct TWGs present in the corpus, for the Working Group filter
    const twgOptions = useMemo(() => {
        const map = new Map<string, string>()
        for (const doc of documents) {
            if (doc.twg?.id && doc.twg?.name) map.set(doc.twg.id, doc.twg.name)
        }
        return Array.from(map.entries()).map(([id, name]) => ({ id, name }))
    }, [documents])

    const filteredDocs = useMemo(() => {
        const now = Date.now()
        const range = DATE_RANGES[dateRangeIdx]
        const q = query.trim().toLowerCase()

        return documents
            .filter((doc) => {
                if (activeTab === 'Confidential' && !doc.is_confidential) return false
                if (activeTab === 'Public' && doc.is_confidential) return false

                if (range.days > 0) {
                    const age = now - new Date(doc.created_at).getTime()
                    if (age > range.days * 24 * 60 * 60 * 1000) return false
                }

                if (selectedTwgIds.length > 0) {
                    if (!doc.twg?.id || !selectedTwgIds.includes(doc.twg.id)) return false
                }

                if (q) {
                    const haystack = `${doc.file_name} ${doc.twg?.name || ''} ${doc.uploaded_by?.full_name || ''}`.toLowerCase()
                    if (!haystack.includes(q)) return false
                }

                return true
            })
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    }, [documents, activeTab, dateRangeIdx, selectedTwgIds, query])

    const topDocuments = filteredDocs.slice(0, 9)

    const runSearch = async (e: React.FormEvent) => {
        e.preventDefault()
        const q = queryInput.trim()
        setQuery(q)

        if (!q) {
            setFragments([])
            return
        }

        // Vector search requires a TWG namespace for non-admins (matches /documents behaviour)
        let searchTwgId: string | undefined
        if (!isAdmin && userTwgIds.length > 0) searchTwgId = userTwgIds[0]

        try {
            setSearchingFragments(true)
            const results = await documentService.searchDocuments(q, searchTwgId)
            setFragments(results)
        } catch (err) {
            console.error('Semantic search failed:', err)
            setFragments([])
        } finally {
            setSearchingFragments(false)
        }
    }

    const toggleTwg = (id: string) => {
        setSelectedTwgIds((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]))
    }

    const resetFilters = () => {
        setSelectedTwgIds([])
        setDateRangeIdx(0)
        setActiveTab('All')
    }

    const handleDownload = async (docId: string) => {
        try {
            await documentService.downloadDocument(docId)
        } catch (e) {
            console.error('Download failed:', e)
        }
    }

    return (
        <div className="max-w-6xl mx-auto space-y-8 py-4">
            {/* Search Header */}
            <div className="text-center space-y-6">
                <h1 className="text-4xl font-display font-bold qp-transition" style={{ color: 'var(--ink-900)' }}>Global Knowledge Base</h1>
                <form onSubmit={runSearch} className="max-w-2xl mx-auto relative group">
                    <div className="relative flex items-center p-1 qp-transition" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                        <div className="pl-4 pr-2" style={{ color: 'var(--ink-400)' }}>
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                        </div>
                        <input
                            type="text"
                            value={queryInput}
                            onChange={(e) => setQueryInput(e.target.value)}
                            placeholder="Search documents by name, working group, or owner..."
                            className="flex-1 bg-transparent border-0 py-3 text-lg focus:ring-0"
                            style={{ color: 'var(--ink-900)' }}
                        />
                        <div className="flex items-center gap-2 pr-2">
                            <button type="submit" className="clickable-scale font-bold py-2.5 px-6 transition-all flex items-center gap-2" style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}>
                                Search
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
                            </button>
                        </div>
                    </div>
                </form>

                <div className="flex justify-center gap-2 flex-wrap">
                    {TABS.map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className="clickable-scale px-4 py-1.5 rounded-full text-sm font-bold transition-all"
                            style={tab === activeTab
                                ? { background: 'var(--accent)', color: 'var(--accent-ink)' }
                                : { background: 'var(--surface-2)', color: 'var(--ink-500)' }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex flex-col lg:flex-row gap-8">
                {/* Filters Sidebar */}
                <aside className="hidden lg:block w-56 space-y-8 flex-shrink-0">
                    <div className="p-5 space-y-6 qp-transition" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-bold uppercase tracking-widest flex items-center gap-2" style={{ color: 'var(--ink-500)' }}>
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
                                Filters
                            </h3>
                            <button onClick={resetFilters} className="text-[10px] font-bold hover:underline" style={{ color: 'var(--accent)' }}>Reset</button>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-3">
                                <label className="text-[10px] font-bold uppercase" style={{ color: 'var(--ink-500)' }}>Date Range</label>
                                <select
                                    value={dateRangeIdx}
                                    onChange={(e) => setDateRangeIdx(Number(e.target.value))}
                                    className="w-full border-0 py-2 px-3 text-sm font-medium focus:ring-2 qp-transition"
                                    style={{ background: 'var(--surface-2)', color: 'var(--ink-900)', borderRadius: 'var(--radius-ctl)' }}
                                >
                                    {DATE_RANGES.map((r, i) => <option key={r.label} value={i}>{r.label}</option>)}
                                </select>
                            </div>

                            {twgOptions.length > 0 && (
                                <div className="space-y-3">
                                    <label className="text-[10px] font-bold uppercase" style={{ color: 'var(--ink-500)' }}>Working Group</label>
                                    <div className="space-y-2">
                                        {twgOptions.map(twg => {
                                            const checked = selectedTwgIds.includes(twg.id)
                                            return (
                                                <label key={twg.id} className="flex items-center gap-3 cursor-pointer group">
                                                    <input type="checkbox" className="sr-only" checked={checked} onChange={() => toggleTwg(twg.id)} />
                                                    <div className="w-4 h-4 rounded border transition-colors flex items-center justify-center" style={checked ? { background: 'var(--accent)', borderColor: 'var(--accent)' } : { background: 'var(--surface-2)', borderColor: 'var(--border)' }}>
                                                        {checked && <svg className="w-3 h-3" style={{ color: 'var(--accent-ink)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                                                    </div>
                                                    <span className="text-xs font-medium transition-colors" style={{ color: checked ? 'var(--ink-900)' : 'var(--ink-500)' }}>{twg.name}</span>
                                                </label>
                                            )
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </aside>

                {/* Results Area */}
                <div className="flex-1 space-y-8">
                    {/* Summary Card */}
                    <Card className="p-0 overflow-hidden shadow-none" style={{ background: 'var(--accent-soft)', border: '1px solid color-mix(in srgb, var(--accent) 30%, var(--border))' }}>
                        <div className="p-6 flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}>
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                            </div>
                            <div className="space-y-2">
                                <h3 className="font-bold tracking-wide" style={{ color: 'var(--ink-900)' }}>Knowledge Base</h3>
                                <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-700)' }}>
                                    {loading
                                        ? 'Loading your accessible documents...'
                                        : query
                                            ? <>Showing <span className="font-bold" style={{ color: 'var(--accent)' }}>{filteredDocs.length}</span> {filteredDocs.length === 1 ? 'document' : 'documents'} matching <span className="font-bold" style={{ color: 'var(--accent)' }}>"{query}"</span>{searchingFragments ? ' — running semantic search...' : fragments.length > 0 ? <> and <span className="font-bold">{fragments.length}</span> AI knowledge fragments.</> : '.'}</>
                                            : <>You have access to <span className="font-bold" style={{ color: 'var(--accent)' }}>{documents.length}</span> {documents.length === 1 ? 'document' : 'documents'} across the WAIIS working groups. Search above or filter to narrow your results.</>}
                                </p>
                            </div>
                        </div>
                    </Card>

                    {/* AI Knowledge Fragments (semantic search results) */}
                    {query && (searchingFragments || fragments.length > 0) && (
                        <div className="space-y-4">
                            <h2 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>AI Knowledge Fragments</h2>
                            {searchingFragments ? (
                                <Card className="p-6 text-sm" style={{ color: 'var(--ink-500)' }}>Searching document contents...</Card>
                            ) : (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {fragments.map((f, i) => (
                                        <Card key={i} className="p-4 space-y-2">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="text-[10px] font-bold uppercase truncate" style={{ color: 'var(--ink-500)' }}>{f.metadata.file_name}</span>
                                                <span className="text-[10px] font-bold whitespace-nowrap" style={{ color: 'var(--sage)' }}>{(f.score * 100).toFixed(0)}% match</span>
                                            </div>
                                            <p className="text-xs italic leading-relaxed line-clamp-3" style={{ color: 'var(--ink-500)' }}>"{f.metadata.text}"</p>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Documents */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>{query ? 'Matching Documents' : 'Recent Documents'}</h2>
                        </div>

                        {loading ? (
                            <Card className="p-12 text-center text-sm" style={{ color: 'var(--ink-400)' }}>Loading documents...</Card>
                        ) : error ? (
                            <Card className="p-12 text-center text-sm" style={{ color: 'var(--terra)' }}>{error}</Card>
                        ) : topDocuments.length === 0 ? (
                            <Card className="p-12 text-center space-y-2">
                                <svg className="w-10 h-10 mx-auto" style={{ color: 'var(--ink-300)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                <p className="text-sm font-bold" style={{ color: 'var(--ink-700)' }}>{documents.length === 0 ? 'No documents yet' : 'No documents match your filters'}</p>
                                <p className="text-xs" style={{ color: 'var(--ink-400)' }}>{documents.length === 0 ? 'Documents uploaded to working group libraries will appear here.' : 'Try clearing filters or adjusting your search.'}</p>
                            </Card>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                {topDocuments.map((doc) => {
                                    const type = fileType(doc.file_name)
                                    return (
                                        <Card key={doc.id} onClick={() => handleDownload(doc.id)} className="clickable-scale group transition-all cursor-pointer">
                                            <div className="space-y-4">
                                                <div className="flex justify-between items-start">
                                                    <div className="p-2 rounded-lg transition-colors" style={type === 'pdf'
                                                        ? { background: 'color-mix(in srgb, var(--terra) 12%, transparent)', color: 'var(--terra)' }
                                                        : type === 'doc'
                                                            ? { background: 'color-mix(in srgb, var(--navy) 12%, transparent)', color: 'var(--navy)' }
                                                            : { background: 'color-mix(in srgb, var(--amber) 12%, transparent)', color: 'var(--amber)' }}>
                                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                                    </div>
                                                    <Badge className="text-[8px] font-black tracking-widest" style={doc.is_confidential
                                                        ? { background: 'color-mix(in srgb, var(--amber) 14%, transparent)', color: 'var(--amber)', borderColor: 'color-mix(in srgb, var(--amber) 30%, transparent)' }
                                                        : { background: 'color-mix(in srgb, var(--sage) 14%, transparent)', color: 'var(--sage)', borderColor: 'color-mix(in srgb, var(--sage) 30%, transparent)' }}>
                                                        {doc.is_confidential ? 'CONFIDENTIAL' : 'PUBLIC'}
                                                    </Badge>
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-sm transition-colors leading-snug group-hover:opacity-80 line-clamp-2" style={{ color: 'var(--ink-900)' }}>{doc.file_name}</h4>
                                                    <p className="text-[10px] font-bold uppercase mt-1 tracking-tighter" style={{ color: 'var(--ink-400)' }}>{(doc.twg?.name || 'Global Secretariat')} • {new Date(doc.created_at).toLocaleDateString()}</p>
                                                </div>
                                                <div className="flex items-center justify-between pt-2">
                                                    <Avatar size="xs" fallback={initials(doc.uploaded_by?.full_name)} />
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleDownload(doc.id) }}
                                                        className="clickable-scale p-1.5 transition-colors"
                                                        style={{ color: 'var(--ink-400)' }}
                                                        title="Download"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                                    </button>
                                                </div>
                                            </div>
                                        </Card>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
