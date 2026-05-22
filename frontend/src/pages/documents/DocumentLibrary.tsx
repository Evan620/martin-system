import { useState, useEffect, useRef } from 'react'

import documentService, { Document, SearchResult } from '../../services/documentService'
import { useAppSelector } from '../../hooks/useRedux'
import { UserRole } from '../../types/auth'
import { twgs as twgService } from '../../services/api'
import CoreWorkspace from '@/components/documents/CoreWorkspace';


export default function DocumentLibrary({ twgId }: { twgId?: string } = {}) {
    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [ingesting, setIngesting] = useState<string | null>(null)
    const [downloading, setDownloading] = useState<string | null>(null)
    const [translatingDoc, setTranslatingDoc] = useState<string | null>(null)
    const [translateMenuDoc, setTranslateMenuDoc] = useState<string | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState<SearchResult[]>([])
    const [isSearching, setIsSearching] = useState(false)

    // Filtering state
    const [activeLibraryTab, setActiveLibraryTab] = useState('all')
    const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([])
    const [selectedLabels, setSelectedLabels] = useState<string[]>([])
    const [selectedTwgFilter, setSelectedTwgFilter] = useState<string[]>([])
    const [sortBy, setSortBy] = useState<'date' | 'name'>('date')

    // Upload Modal State
    const [showUploadModal, setShowUploadModal] = useState(false)
    const [uploadStep, setUploadStep] = useState<'initial' | 'ready_to_ingest' | 'ingesting' | 'complete'>('initial')
    const [uploadedDocId, setUploadedDocId] = useState<string | null>(null)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [selectedTwgId, setSelectedTwgId] = useState<string>(twgId || '')
    const [isConfidential, setIsConfidential] = useState(false)
    const [selectedDocType, setSelectedDocType] = useState<string>('')
    const [customDocType, setCustomDocType] = useState<string>('')


    // Selection & Pagination State
    const [selectedDocs, setSelectedDocs] = useState<string[]>([])
    const [currentPage, setCurrentPage] = useState(1)
    const itemsPerPage = 10

    const fileInputRef = useRef<HTMLInputElement>(null)

    // Get current user for RBAC filtering
    const currentUser = useAppSelector((state) => state.auth.user)
    const isAdmin = currentUser?.role === UserRole.ADMIN || currentUser?.role === UserRole.SECRETARIAT_LEAD
    const userTwgIds = currentUser?.twg_ids || []

    // Fetch user's TWGs for dropdown
    const [allTwgs, setAllTwgs] = useState<any[]>([])

    useEffect(() => {
        const fetchTwgs = async () => {
            try {
                const response = await twgService.dropdown()
                setAllTwgs(response.data)
            } catch (error) {
                console.error('Failed to fetch TWGs:', error)
            }
        }
        fetchTwgs()
    }, [])

    // Filter TWGs based on user role, hiding non-core TWGs (protocol_logistics, resource_mobilization)
    const HIDDEN_PILLARS = ['protocol_logistics', 'resource_mobilization']
    const availableTwgs = (isAdmin ? allTwgs : allTwgs.filter((t: any) => userTwgIds.includes(t.id)))
        .filter((t: any) => !HIDDEN_PILLARS.includes(t.pillar))

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        try {
            setLoading(true)
            const { data } = await documentService.listDocuments(twgId, 1, 1000)
            setDocuments(data)
        } catch (error) {
            console.error('Error fetching data:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!searchQuery.trim()) {
            setSearchResults([])
            setIsSearching(false)
            return
        }

        try {
            setIsSearching(true)

            // RBAC Fix: Non-admins must specify a TWG ID for vector search
            // If we have a prop twgId, use it.
            // If not, and not admin, default to the user's first assigned TWG.
            let searchTargetTwgId = twgId;
            if (!isAdmin && !searchTargetTwgId && userTwgIds.length > 0) {
                searchTargetTwgId = userTwgIds[0];
            }

            const results = await documentService.searchDocuments(searchQuery, searchTargetTwgId)
            setSearchResults(results)
        } catch (error) {
            console.error('Search failed:', error)
        }
    }

    const handleUpload = async () => {
        if (!selectedFile) return

        // Determine final document type
        const finalDocType = selectedDocType === 'Other' ? customDocType : selectedDocType

        try {
            setUploading(true)
            const response = await documentService.uploadDocument(selectedFile, selectedTwgId || undefined, isConfidential, finalDocType || undefined)
            // Auto-ingest immediately after upload
            setUploadedDocId(response.id)
            setUploadStep('ingesting')

            // Clear form but keep modal open
            setSelectedFile(null)
            setSelectedTwgId('')
            setIsConfidential(false)
            setSelectedDocType('')
            setCustomDocType('')
            fetchData() // Refresh list background

            // Trigger ingestion automatically
            try {
                await documentService.ingestDocument(response.id)
                setUploadStep('complete')
                fetchData() // Refresh to show synced status
            } catch (ingestError) {
                console.error('Auto-ingestion failed:', ingestError)
                setUploadStep('ready_to_ingest') // Allow manual retry
            }
        } catch (error) {
            console.error('Upload failed:', error)
            alert('Upload failed. Please try again.')
        } finally {
            setUploading(false)
        }
    }

    const handleModalIngest = async () => {
        if (!uploadedDocId) return

        try {
            setUploadStep('ingesting')
            await documentService.ingestDocument(uploadedDocId)
            setUploadStep('complete')
        } catch (error) {
            console.error('Ingestion failed:', error)
            alert('Ingestion failed. You can retry from the list.')
            setUploadStep('ready_to_ingest') // Allow retry
        }
    }

    const handleIngest = async (docId: string) => {
        try {
            setIngesting(docId)
            await documentService.ingestDocument(docId)

            // Update local state to show as synced immediately
            setDocuments(prevDocs =>
                prevDocs.map(doc =>
                    doc.id === docId
                        ? { ...doc, ingested_at: new Date().toISOString() }
                        : doc
                )
            )

            alert('Document successfully ingested into the Knowledge Base RAG!')
        } catch (error) {
            console.error('Ingestion failed:', error)
            alert('Failed to ingest document. Check logs.')
        } finally {
            setIngesting(null)
        }
    }

    const handleDelete = async (docId: string) => {
        if (!window.confirm('Are you sure you want to delete this document? This action cannot be undone.')) return;

        try {
            await documentService.deleteDocument(docId);
            setDocuments(prev => prev.filter(d => d.id !== docId));
            setSelectedDocs(prev => prev.filter(id => id !== docId));
        } catch (error) {
            console.error('Delete failed:', error);
            alert('Failed to delete document.');
        }
    };

    const handleBulkDelete = async () => {
        if (selectedDocs.length === 0) return;
        if (!window.confirm(`Are you sure you want to delete ${selectedDocs.length} documents?`)) return;

        try {
            await documentService.bulkDeleteDocuments(selectedDocs);
            setDocuments(prev => prev.filter(d => !selectedDocs.includes(d.id)));
            setSelectedDocs([]);
        } catch (error) {
            console.error('Bulk delete failed:', error);
            alert('Failed to delete some documents.');
        }
    };

    const toggleSelect = (docId: string) => {
        setSelectedDocs(prev =>
            prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
        );
    };

    const toggleSelectAll = (ids: string[]) => {
        if (selectedDocs.length === ids.length) {
            setSelectedDocs([]);
        } else {
            setSelectedDocs(ids);
        }
    };

    const handleDownload = async (docId: string) => {
        try {
            setDownloading(docId)
            await documentService.downloadDocument(docId)
        } catch (error) {
            console.error('Download failed:', error)
        } finally {
            setDownloading(null)
        }
    }

    const handleTranslateDownload = async (docId: string, language: string) => {
        setTranslateMenuDoc(null)
        setTranslatingDoc(docId)
        try {
            await documentService.translateDownload(docId, language)
        } catch (error: any) {
            console.error('Translate download failed:', error)
            alert(error?.response?.data?.detail || 'Failed to translate document')
        } finally {
            setTranslatingDoc(null)
        }
    }

    const toggleDocType = (type: string) => {
        setSelectedDocTypes(prev =>
            prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
        )
    }

    const toggleLabel = (label: string) => {
        setSelectedLabels(prev =>
            prev.includes(label) ? prev.filter(l => l !== label) : [...prev, label]
        )
    }

    // Reset pagination on filter change
    useEffect(() => {
        setCurrentPage(1);
    }, [activeLibraryTab, selectedDocTypes, selectedLabels, selectedTwgFilter, searchQuery]);

    // Helper function to get document type (from stored metadata or auto-detect)
    const getDocumentType = (doc: Document): string => {
        // Check if document_type is stored in metadata_json
        if (doc.metadata_json?.document_type) {
            return doc.metadata_json.document_type;
        }
        // Fall back to auto-detection from filename
        return doc.file_name.toLowerCase().includes('minutes') ? 'Meeting Minutes' :
            doc.file_name.toLowerCase().includes('policy') ? 'Policy Drafts' :
                doc.file_name.toLowerCase().includes('budget') ? 'Reports' :
                    doc.file_name.toLowerCase().includes('presentation') ? 'Presentations' : 'Legal Documents';
    };

    // Filtered documents for display
    const filteredAndSortedDocuments = documents.filter(doc => {
        // Library tab filter
        if (activeLibraryTab === 'recent') {
            const docDate = new Date(doc.created_at);
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            if (docDate < sevenDaysAgo) return false;
        }

        // Get document type from stored metadata or auto-detect
        const docType = getDocumentType(doc);

        const typeMatch = selectedDocTypes.length === 0 || selectedDocTypes.includes(docType);

        // Label filter logic: Handle Confidential and Public explicitly
        const labelMatch = selectedLabels.length === 0 || (
            (selectedLabels.includes('Confidential') && doc.is_confidential) ||
            (selectedLabels.includes('Public') && !doc.is_confidential) ||
            (selectedLabels.includes('Internal') && !doc.is_confidential)
        );

        // TWG filter
        const twgMatch = selectedTwgFilter.length === 0 || (
            doc.twg_id ? selectedTwgFilter.includes(doc.twg_id) : false
        );

        return typeMatch && labelMatch && twgMatch;
    }).sort((a, b) => {
        if (sortBy === 'date') {
            const dateA = new Date(a.created_at).getTime();
            const dateB = new Date(b.created_at).getTime();
            return dateB - dateA;
        } else {
            return a.file_name.localeCompare(b.file_name);
        }
    });

    const totalPages = Math.ceil(filteredAndSortedDocuments.length / itemsPerPage);
    const paginatedDocs = filteredAndSortedDocuments.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

    const [mainTab, setMainTab] = useState<'library' | 'workspace'>('library');

    const libraryItems = [
        { id: 'all', label: 'All Documents', count: documents.length },
        {
            id: 'recent', label: 'Recent', count: documents.filter(d => {
                const dDate = new Date(d.created_at);
                const sevenAgo = new Date();
                sevenAgo.setDate(sevenAgo.getDate() - 7);
                return dDate >= sevenAgo;
            }).length
        },
        { id: 'starred', label: 'Starred', count: 0 },
    ];

    const documentTypes = ['Meeting Minutes', 'Policy Drafts', 'Reports', 'Legal Documents', 'Presentations'];
    const labels = [
        { name: 'Confidential', dotColor: 'var(--terra)' },
        { name: 'Internal', dotColor: 'var(--amber)' },
        { name: 'Public', dotColor: 'var(--sage)' },
    ];

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            {/* Page header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)', marginBottom: 6 }}>
                    Document library
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <h1 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        Documents
                    </h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        {selectedDocs.length > 0 && (
                            <button
                                onClick={handleBulkDelete}
                                style={{ background: 'var(--terra)', border: '1px solid var(--terra)', color: '#fff', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                            >
                                Delete {selectedDocs.length}
                            </button>
                        )}
                        <button
                            onClick={() => setShowUploadModal(true)}
                            style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>upload_file</span>
                            Upload
                        </button>
                    </div>
                </div>
            </div>

            {/* Tab switcher */}
            <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 24 }}>
                {[{ id: 'library', label: 'Document Library' }, { id: 'workspace', label: 'Core Workspace (Shared)' }].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setMainTab(tab.id as 'library' | 'workspace')}
                        style={{
                            background: 'transparent', border: 'none', borderBottom: mainTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
                            color: mainTab === tab.id ? 'var(--accent)' : 'var(--ink-500)', padding: '10px 16px', fontSize: 12, fontWeight: 600,
                            cursor: 'pointer', fontFamily: 'inherit', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: -1
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {mainTab === 'workspace' ? (
                <div>
                    <CoreWorkspace />
                </div>
            ) : (
                <div style={{ display: 'flex', gap: 24 }}>
                    {/* Left sidebar */}
                    <aside style={{ width: 220, flexShrink: 0 }}>
                        {/* Library nav */}
                        <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 8 }}>Library</div>
                            {libraryItems.map(item => (
                                <button
                                    key={item.id}
                                    onClick={() => setActiveLibraryTab(item.id)}
                                    style={{
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                        width: '100%', padding: '8px 12px',
                                        background: activeLibraryTab === item.id ? 'var(--accent-soft)' : 'transparent',
                                        border: 'none',
                                        borderLeft: activeLibraryTab === item.id ? '2px solid var(--accent)' : '2px solid transparent',
                                        color: activeLibraryTab === item.id ? 'var(--accent)' : 'var(--ink-600)',
                                        fontSize: 13, fontWeight: activeLibraryTab === item.id ? 600 : 400,
                                        cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', marginBottom: 2
                                    }}
                                >
                                    <span>{item.label}</span>
                                    <span style={{ fontSize: 10, color: 'var(--ink-400)', fontFamily: "'Geist Mono', monospace" }}>{item.count}</span>
                                </button>
                            ))}
                        </div>

                        {/* Document Types */}
                        <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 8 }}>Document Types</div>
                            {documentTypes.map(type => (
                                <label key={type} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={selectedDocTypes.includes(type)}
                                        onChange={() => toggleDocType(type)}
                                        style={{ accentColor: 'var(--accent)' }}
                                    />
                                    <span style={{ fontSize: 12, color: 'var(--ink-600)' }}>{type}</span>
                                </label>
                            ))}
                        </div>

                        {/* Labels */}
                        <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 8 }}>Labels</div>
                            {labels.map(label => (
                                <button
                                    key={label.name}
                                    onClick={() => toggleLabel(label.name)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0',
                                        background: 'transparent', border: 'none', cursor: 'pointer', width: '100%', fontFamily: 'inherit'
                                    }}
                                >
                                    <div style={{ width: 7, height: 7, borderRadius: '50%', background: label.dotColor, flexShrink: 0 }}></div>
                                    <span style={{ fontSize: 12, color: selectedLabels.includes(label.name) ? 'var(--accent)' : 'var(--ink-600)', fontWeight: selectedLabels.includes(label.name) ? 600 : 400 }}>
                                        {label.name}
                                    </span>
                                </button>
                            ))}
                        </div>

                        {/* TWG Filter */}
                        {availableTwgs.length > 0 && (
                            <div style={{ marginBottom: 20 }}>
                                <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 8 }}>TWG</div>
                                {availableTwgs.map((t: any) => (
                                    <label key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={selectedTwgFilter.includes(t.id)}
                                            onChange={() => setSelectedTwgFilter(prev =>
                                                prev.includes(t.id) ? prev.filter(id => id !== t.id) : [...prev, t.id]
                                            )}
                                            style={{ accentColor: 'var(--accent)' }}
                                        />
                                        <span style={{ fontSize: 12, color: 'var(--ink-600)' }} className="truncate">{t.name}</span>
                                    </label>
                                ))}
                            </div>
                        )}

                        {/* Clear / Sort */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <button
                                onClick={() => { setSelectedDocTypes([]); setSelectedLabels([]); setActiveLibraryTab('all'); }}
                                style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '6px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left' }}
                            >
                                Clear filters
                            </button>
                            <button
                                onClick={() => setSortBy(sortBy === 'date' ? 'name' : 'date')}
                                style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '6px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left' }}
                            >
                                Sort: {sortBy === 'date' ? 'Date' : 'Name'}
                            </button>
                        </div>
                    </aside>

                    {/* Main content */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                        {/* Search */}
                        <form onSubmit={handleSearch} style={{ position: 'relative', marginBottom: 16 }}>
                            <input
                                type="search"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search by name, owner, or tag..."
                                style={{
                                    width: '100%', padding: '10px 16px 10px 40px',
                                    background: 'var(--surface)', border: '1px solid var(--border)',
                                    fontSize: 13, color: 'var(--ink-900)', outline: 'none',
                                    fontFamily: 'inherit', boxSizing: 'border-box'
                                }}
                            />
                            <span className="material-symbols-outlined" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 18, color: 'var(--ink-400)' }}>search</span>
                        </form>

                        {/* AI Search Results */}
                        {isSearching && (
                            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 16, marginBottom: 16 }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                                    <span style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600 }}>
                                        AI Knowledge Fragments
                                    </span>
                                    <button onClick={() => { setIsSearching(false); setSearchQuery(''); }} style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}>
                                        Close
                                    </button>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                    {searchResults.length > 0 ? searchResults.map((result, idx) => (
                                        <div key={idx} style={{ background: 'var(--ink-50)', border: '1px solid var(--border)', padding: 12 }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                                <span style={{ fontSize: 10, color: 'var(--ink-500)', fontWeight: 600, textTransform: 'uppercase' }} className="truncate">{result.metadata.file_name}</span>
                                                <span style={{ fontSize: 10, color: 'var(--sage)', fontWeight: 600, whiteSpace: 'nowrap', marginLeft: 8 }}>{(result.score * 100).toFixed(0)}%</span>
                                            </div>
                                            <p style={{ fontSize: 11, color: 'var(--ink-600)', fontStyle: 'italic', margin: 0 }} className="line-clamp-2">"{result.metadata.text}"</p>
                                        </div>
                                    )) : (
                                        <p style={{ fontSize: 12, color: 'var(--ink-500)', margin: 0 }}>No matching fragments found.</p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Table */}
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', minWidth: 760, textAlign: 'left', fontSize: 13, borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ background: 'var(--ink-50)', borderBottom: '1px solid var(--border)' }}>
                                            <th style={{ padding: '10px 12px', width: 32 }}>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedDocs.length > 0 && selectedDocs.length === paginatedDocs.length}
                                                    onChange={() => toggleSelectAll(paginatedDocs.map(d => d.id))}
                                                    style={{ accentColor: 'var(--accent)' }}
                                                />
                                            </th>
                                            {['Document', 'Type', 'Context (TWG)', 'Owner', 'Date', 'RAG Sync', 'Label', ''].map(col => (
                                                <th key={col} style={{ padding: '10px 12px', fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{col}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {loading ? (
                                            <tr><td colSpan={9} style={{ padding: '48px 12px', textAlign: 'center', color: 'var(--ink-400)', fontSize: 13 }}>Loading documents...</td></tr>
                                        ) : paginatedDocs.length === 0 ? (
                                            <tr><td colSpan={9} style={{ padding: '48px 12px', textAlign: 'center', color: 'var(--ink-400)', fontSize: 13 }}>No documents match the current filters.</td></tr>
                                        ) : paginatedDocs.map((doc, idx) => (
                                            <tr
                                                key={doc.id}
                                                style={{
                                                    borderBottom: idx < paginatedDocs.length - 1 ? '1px solid var(--border)' : 'none',
                                                    background: selectedDocs.includes(doc.id) ? 'var(--accent-soft)' : 'transparent',
                                                }}
                                                onMouseEnter={e => { if (!selectedDocs.includes(doc.id)) (e.currentTarget as HTMLElement).style.background = 'var(--ink-50)' }}
                                                onMouseLeave={e => { if (!selectedDocs.includes(doc.id)) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                                            >
                                                <td style={{ padding: '10px 12px' }}>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedDocs.includes(doc.id)}
                                                        onChange={() => toggleSelect(doc.id)}
                                                        style={{ accentColor: 'var(--accent)' }}
                                                    />
                                                </td>
                                                <td style={{ padding: '10px 12px', maxWidth: 200 }}>
                                                    <button
                                                        onClick={() => handleDownload(doc.id)}
                                                        disabled={downloading === doc.id}
                                                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 8, opacity: downloading === doc.id ? 0.5 : 1 }}
                                                    >
                                                        <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--ink-400)', flexShrink: 0 }}>
                                                            {downloading === doc.id ? 'sync' : doc.file_name.endsWith('.pdf') ? 'picture_as_pdf' : 'description'}
                                                        </span>
                                                        <span style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500 }} className="truncate">{doc.file_name}</span>
                                                    </button>
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <span style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{getDocumentType(doc)}</span>
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <span style={{ fontSize: 11, color: 'var(--ink-600)', background: 'var(--ink-50)', border: '1px solid var(--border)', padding: '2px 8px' }}>
                                                        {doc.twg ? doc.twg.name : 'Global'}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '10px 12px', fontSize: 13, color: 'var(--ink-600)' }}>
                                                    {doc.uploaded_by?.full_name || 'System Admin'}
                                                </td>
                                                <td style={{ padding: '10px 12px', fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                                                    {new Date(doc.created_at).toLocaleDateString()}
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    {doc.ingested_at ? (
                                                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--sage)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                                            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--sage)' }}></div>
                                                            Synced
                                                        </span>
                                                    ) : (
                                                        <button
                                                            onClick={() => handleIngest(doc.id)}
                                                            disabled={ingesting === doc.id}
                                                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4, padding: 0 }}
                                                            title="Ingest to RAG"
                                                        >
                                                            <span className={`material-symbols-outlined ${ingesting === doc.id ? 'animate-spin' : ''}`} style={{ fontSize: 16 }}>
                                                                {ingesting === doc.id ? 'sync' : 'database_upload'}
                                                            </span>
                                                            Ingest
                                                        </button>
                                                    )}
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: doc.is_confidential ? 'var(--terra)' : 'var(--sage)' }}>
                                                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: doc.is_confidential ? 'var(--terra)' : 'var(--sage)' }}></div>
                                                        {doc.is_confidential ? 'Confidential' : 'Public'}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <div style={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                                                        <button onClick={() => handleDownload(doc.id)} disabled={downloading === doc.id} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }} title="Download">
                                                            <span className={`material-symbols-outlined ${downloading === doc.id ? 'animate-spin' : ''}`} style={{ fontSize: 16 }}>
                                                                {downloading === doc.id ? 'sync' : 'download'}
                                                            </span>
                                                        </button>
                                                        <div style={{ position: 'relative' }}>
                                                            <button
                                                                onClick={() => setTranslateMenuDoc(translateMenuDoc === doc.id ? null : doc.id)}
                                                                disabled={translatingDoc === doc.id}
                                                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }} title="Translate"
                                                            >
                                                                <span className={`material-symbols-outlined ${translatingDoc === doc.id ? 'animate-spin' : ''}`} style={{ fontSize: 16 }}>
                                                                    {translatingDoc === doc.id ? 'sync' : 'translate'}
                                                                </span>
                                                            </button>
                                                            {translateMenuDoc === doc.id && (
                                                                <>
                                                                    <div className="fixed inset-0 z-10" onClick={() => setTranslateMenuDoc(null)} />
                                                                    <div style={{ position: 'absolute', right: 0, top: '100%', zIndex: 20, background: 'var(--surface)', border: '1px solid var(--border)', minWidth: 160 }}>
                                                                        {[{ code: 'fr', label: 'Français (French)' }, { code: 'pt', label: 'Português (Portuguese)' }].map((lang) => (
                                                                            <button
                                                                                key={lang.code}
                                                                                onClick={() => handleTranslateDownload(doc.id, lang.code)}
                                                                                style={{ display: 'block', width: '100%', textAlign: 'left', padding: '8px 14px', fontSize: 12, color: 'var(--ink-700)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit' }}
                                                                            >
                                                                                {lang.label}
                                                                            </button>
                                                                        ))}
                                                                    </div>
                                                                </>
                                                            )}
                                                        </div>
                                                        <button onClick={() => handleDelete(doc.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }} title="Delete">
                                                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>delete</span>
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
                                    <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                                        Page {currentPage} of {totalPages}
                                    </span>
                                    <div style={{ display: 'flex', gap: 4 }}>
                                        <button disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)} style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '4px 10px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', opacity: currentPage === 1 ? 0.4 : 1 }}>
                                            Prev
                                        </button>
                                        {[...Array(totalPages)].map((_, i) => (
                                            <button key={i} onClick={() => setCurrentPage(i + 1)} style={{ background: currentPage === i + 1 ? 'var(--accent)' : 'var(--surface)', border: `1px solid ${currentPage === i + 1 ? 'var(--accent)' : 'var(--border)'}`, color: currentPage === i + 1 ? 'var(--accent-ink)' : 'var(--ink-600)', padding: '4px 8px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                                                {i + 1}
                                            </button>
                                        ))}
                                        <button disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)} style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '4px 10px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', opacity: currentPage === totalPages ? 0.4 : 1 }}>
                                            Next
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Upload Modal */}
            {showUploadModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 440, overflow: 'hidden' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: 0 }}>
                                {uploadStep === 'initial' ? 'Upload document' : uploadStep === 'ready_to_ingest' ? 'Upload successful' : uploadStep === 'ingesting' ? 'Processing...' : 'Complete'}
                            </h3>
                            <button onClick={() => { setShowUploadModal(false); setUploadStep('initial'); setSelectedFile(null); setSelectedDocType(''); setCustomDocType(''); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)', display: 'flex', padding: 4 }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>close</span>
                            </button>
                        </div>

                        <div style={{ padding: 24 }}>
                            {uploadStep === 'initial' && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                                    <div
                                        onClick={() => fileInputRef.current?.click()}
                                        style={{ border: '1px dashed var(--border)', padding: '32px 16px', textAlign: 'center', cursor: 'pointer' }}
                                    >
                                        <input type="file" ref={fileInputRef} className="hidden" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} />
                                        <span className="material-symbols-outlined" style={{ fontSize: 40, color: 'var(--ink-300)', display: 'block', marginBottom: 8 }}>cloud_upload</span>
                                        <p style={{ fontSize: 13, color: 'var(--ink-700)', margin: 0 }}>{selectedFile ? selectedFile.name : 'Click to select a file'}</p>
                                        <p style={{ fontSize: 11, color: 'var(--ink-400)', margin: '4px 0 0' }}>PDF, DOCX, XLSX (Max 10MB)</p>
                                    </div>

                                    <div>
                                        <label style={{ display: 'block', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 6 }}>Assign to TWG</label>
                                        <select value={selectedTwgId} onChange={(e) => setSelectedTwgId(e.target.value)} disabled={!!twgId} style={{ width: '100%', padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 13, color: 'var(--ink-700)', fontFamily: 'inherit', cursor: twgId ? 'not-allowed' : 'pointer', opacity: twgId ? 0.6 : 1 }}>
                                            <option value="" disabled>Select knowledge base...</option>
                                            {isAdmin && <option value="global">Global Secretariat</option>}
                                            {isAdmin ? (
                                                <>
                                                    <option value="energy">Energy Trade and Industrial Growth</option>
                                                    <option value="agriculture">Agribusiness and Food Systems Transformation</option>
                                                    <option value="minerals">Strategic Minerals and Natural Resource Development</option>
                                                    <option value="digital">Digital Transformation</option>
                                                </>
                                            ) : (
                                                availableTwgs.map((twg: any) => (<option key={twg.id} value={twg.id}>{twg.name}</option>))
                                            )}
                                        </select>
                                    </div>

                                    <div>
                                        <label style={{ display: 'block', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 6 }}>Document Type</label>
                                        <select value={selectedDocType} onChange={(e) => setSelectedDocType(e.target.value)} style={{ width: '100%', padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 13, color: 'var(--ink-700)', fontFamily: 'inherit', cursor: 'pointer' }}>
                                            <option value="" disabled>Select type...</option>
                                            <option value="Meeting Minutes">Meeting Minutes</option>
                                            <option value="Policy Drafts">Policy Drafts</option>
                                            <option value="Reports">Reports</option>
                                            <option value="Legal Documents">Legal Documents</option>
                                            <option value="Presentations">Presentations</option>
                                            <option value="Other">Other</option>
                                        </select>
                                        {selectedDocType === 'Other' && (
                                            <input type="text" value={customDocType} onChange={(e) => setCustomDocType(e.target.value)} placeholder="Enter document type..." style={{ marginTop: 8, width: '100%', padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 13, color: 'var(--ink-700)', fontFamily: 'inherit', boxSizing: 'border-box' }} />
                                        )}
                                    </div>

                                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                        <input type="checkbox" checked={isConfidential} onChange={(e) => setIsConfidential(e.target.checked)} style={{ accentColor: 'var(--terra)' }} />
                                        <span style={{ fontSize: 12, color: 'var(--terra)', fontWeight: 500 }}>Mark as CONFIDENTIAL</span>
                                    </label>

                                    <button onClick={handleUpload} disabled={!selectedFile || !selectedTwgId || uploading} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '10px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, opacity: !selectedFile || !selectedTwgId || uploading ? 0.5 : 1 }}>
                                        {uploading ? <><span className="material-symbols-outlined animate-spin" style={{ fontSize: 16 }}>progress_activity</span> Uploading...</> : 'Upload Document'}
                                    </button>
                                </div>
                            )}

                            {uploadStep === 'ready_to_ingest' && (
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'var(--accent-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 28, color: 'var(--sage)' }}>check_circle</span>
                                    </div>
                                    <h4 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 18, color: 'var(--ink-900)', margin: '0 0 8px' }}>File uploaded</h4>
                                    <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: '0 0 20px' }}>Ingest into Knowledge Base for AI search?</p>
                                    <button onClick={handleModalIngest} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '10px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 10 }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>database_upload</span>
                                        Ingest to Knowledge Base
                                    </button>
                                    <button onClick={() => { setShowUploadModal(false); setUploadStep('initial'); setSelectedDocType(''); setCustomDocType(''); }} style={{ fontSize: 12, color: 'var(--ink-500)', background: 'none', border: 'none', cursor: 'pointer' }}>
                                        Skip (store only)
                                    </button>
                                </div>
                            )}

                            {uploadStep === 'ingesting' && (
                                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                                    <div className="animate-spin rounded-full" style={{ width: 48, height: 48, border: '3px solid var(--border)', borderTopColor: 'var(--accent)', margin: '0 auto 16px' }}></div>
                                    <h4 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 18, color: 'var(--ink-900)', margin: '0 0 8px' }}>Processing vectors...</h4>
                                    <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: 0 }}>Generating embeddings and updating index.</p>
                                </div>
                            )}

                            {uploadStep === 'complete' && (
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'var(--accent-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 28, color: 'var(--accent)' }}>auto_awesome</span>
                                    </div>
                                    <h4 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 18, color: 'var(--ink-900)', margin: '0 0 8px' }}>Ingestion complete</h4>
                                    <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: '0 0 20px' }}>Your document is now searchable by AI agents.</p>
                                    <button onClick={() => { setShowUploadModal(false); setUploadStep('initial'); setSelectedDocType(''); setCustomDocType(''); fetchData(); }} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '10px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', width: '100%' }}>
                                        Close
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
