import { useState, useEffect, useRef } from 'react'
import ModernLayout from '../../layouts/ModernLayout'
import documentService, { Document, SearchResult } from '../../services/documentService'


export default function DocumentLibrary() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [ingesting, setIngesting] = useState<string | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState<SearchResult[]>([])
    const [isSearching, setIsSearching] = useState(false)

    // Filtering state
    const [activeLibraryTab, setActiveLibraryTab] = useState('all')
    const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([])
    const [selectedLabels, setSelectedLabels] = useState<string[]>([])
    const [sortBy, setSortBy] = useState<'date' | 'name'>('date')

    // Upload Modal State
    const [showUploadModal, setShowUploadModal] = useState(false)
    const [uploadStep, setUploadStep] = useState<'initial' | 'ready_to_ingest' | 'ingesting' | 'complete'>('initial')
    const [uploadedDocId, setUploadedDocId] = useState<string | null>(null)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [selectedTwgId, setSelectedTwgId] = useState<string>('')
    const [isConfidential, setIsConfidential] = useState(false)

    // Selection & Pagination State
    const [selectedDocs, setSelectedDocs] = useState<string[]>([])
    const [currentPage, setCurrentPage] = useState(1)
    const itemsPerPage = 10

    const fileInputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        try {
            setLoading(true)
            const docsData = await documentService.listDocuments()
            setDocuments(docsData)
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
            const results = await documentService.searchDocuments(searchQuery)
            setSearchResults(results)
        } catch (error) {
            console.error('Search failed:', error)
        }
    }

    const handleUpload = async () => {
        if (!selectedFile) return

        try {
            setUploading(true)
            const response = await documentService.uploadDocument(selectedFile, selectedTwgId || undefined, isConfidential)
            // Transition to ingestion steps
            setUploadedDocId(response.id)
            setUploadStep('ready_to_ingest')

            // Clear form but keep modal open
            setSelectedFile(null)
            setSelectedTwgId('')
            setIsConfidential(false)
            fetchData() // Refresh list background
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
            // Optionally update UI to show it's ingested
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
            await documentService.downloadDocument(docId)
        } catch (error) {
            console.error('Download failed:', error)
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
    }, [activeLibraryTab, selectedDocTypes, selectedLabels, searchQuery]);

    // Filtered documents for display
    const filteredAndSortedDocuments = documents.filter(doc => {
        // Library tab filter
        if (activeLibraryTab === 'recent') {
            const docDate = new Date(doc.created_at);
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            if (docDate < sevenDaysAgo) return false;
        }

        // Simple type mapping
        const docType = doc.file_name.toLowerCase().includes('minutes') ? 'Meeting Minutes' :
            doc.file_name.toLowerCase().includes('policy') ? 'Policy Drafts' :
                doc.file_name.toLowerCase().includes('budget') ? 'Reports' : 'Legal Documents';

        const typeMatch = selectedDocTypes.length === 0 || selectedDocTypes.includes(docType);

        // Label filter logic: Handle Confidential and Public explicitly
        const labelMatch = selectedLabels.length === 0 || (
            (selectedLabels.includes('Confidential') && doc.is_confidential) ||
            (selectedLabels.includes('Public') && !doc.is_confidential) ||
            (selectedLabels.includes('Internal') && !doc.is_confidential)
        );

        return typeMatch && labelMatch;
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
    const paginatedDocs = filteredAndSortedDocuments.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    const libraryItems = [
        { id: 'all', label: 'All Documents', icon: 'folder', count: documents.length },
        {
            id: 'recent', label: 'Recent', icon: 'schedule', count: documents.filter(d => {
                const dDate = new Date(d.created_at);
                const sevenAgo = new Date();
                sevenAgo.setDate(sevenAgo.getDate() - 7);
                return dDate >= sevenAgo;
            }).length
        },
        { id: 'starred', label: 'Starred', icon: 'star', count: 0 },
        { id: 'shared', label: 'Shared with Me', icon: 'share', count: 0 },
    ];

    const documentTypes = ['Meeting Minutes', 'Policy Drafts', 'Reports', 'Legal Documents', 'Presentations'];
    const labels = [
        { name: 'Confidential', color: 'red' },
        { name: 'Internal', color: 'amber' },
        { name: 'Public', color: 'emerald' },
    ];

    return (
        <ModernLayout>
            <div className="flex flex-col lg:flex-row gap-8 h-full">
                {/* Left Sidebar Filters */}
                <aside className="w-full lg:w-64 space-y-8">
                    <div>
                        <button
                            onClick={() => setShowUploadModal(true)}
                            className="w-full h-14 bg-[#1152d4] hover:bg-[#0d3ea8] text-white rounded-xl font-bold flex items-center justify-center gap-3 shadow-lg shadow-blue-500/20 transition-all active:scale-95"
                        >
                            <span className="material-symbols-outlined">upload_file</span>
                            Upload Document
                        </button>
                    </div>

                    <div className="space-y-6">
                        <section>
                            <p className="text-[11px] font-black text-[#8a9dbd] uppercase tracking-[0.2em] mb-4">Library</p>
                            <div className="space-y-1">
                                {libraryItems.map(item => (
                                    <button
                                        key={item.id}
                                        onClick={() => setActiveLibraryTab(item.id)}
                                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-bold transition-all ${activeLibraryTab === item.id ? 'bg-[#eef2ff] text-[#1152d4]' : 'text-[#4c669a] hover:bg-gray-50'}`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                                            {item.label}
                                        </div>
                                        {item.count !== null && <span className="text-[10px] font-black opacity-60">{item.count}</span>}
                                    </button>
                                ))}
                            </div>
                        </section>

                        <section>
                            <p className="text-[11px] font-black text-[#8a9dbd] uppercase tracking-[0.2em] mb-4">Document Types</p>
                            <div className="space-y-2">
                                {documentTypes.map(type => (
                                    <label key={type} className="flex items-center gap-3 cursor-pointer group">
                                        <input
                                            type="checkbox"
                                            checked={selectedDocTypes.includes(type)}
                                            onChange={() => toggleDocType(type)}
                                            className="size-4 rounded border-[#cfd7e7] text-[#1152d4] focus:ring-[#1152d4]"
                                        />
                                        <span className="text-sm font-bold text-[#4c669a] group-hover:text-[#1152d4] transition-colors">{type}</span>
                                    </label>
                                ))}
                            </div>
                        </section>

                        <section>
                            <p className="text-[11px] font-black text-[#8a9dbd] uppercase tracking-[0.2em] mb-4">Labels</p>
                            <div className="space-y-2">
                                {labels.map(label => (
                                    <button
                                        key={label.name}
                                        onClick={() => toggleLabel(label.name)}
                                        className="flex items-center gap-3 w-full group"
                                    >
                                        <span className={`size-3 rounded-full bg-${label.color}-500 shadow-sm shadow-${label.color}-500/30`}></span>
                                        <span className={`text-sm font-bold transition-colors ${selectedLabels.includes(label.name) ? 'text-[#1152d4]' : 'text-[#4c669a] group-hover:text-[#1152d4]'}`}>{label.name}</span>
                                    </button>
                                ))}
                            </div>
                        </section>
                    </div>
                </aside>

                {/* Main Content Area */}
                <div className="flex-1 space-y-6">
                    <div className="flex items-center justify-between">
                        <h1 className="text-2xl font-black text-[#0d121b] dark:text-white tracking-tight">All Documents</h1>
                        <div className="flex gap-2">
                            {selectedDocs.length > 0 && (
                                <button
                                    onClick={handleBulkDelete}
                                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-black uppercase tracking-wider hover:bg-red-700 transition-all shadow-lg shadow-red-500/20"
                                >
                                    <span className="material-symbols-outlined text-sm">delete_sweep</span>
                                    Delete {selectedDocs.length}
                                </button>
                            )}
                            <button
                                onClick={() => {
                                    setSelectedDocTypes([])
                                    setSelectedLabels([])
                                    setActiveLibraryTab('all')
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-xs font-black text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider hover:bg-gray-50 transition-all shadow-sm"
                            >
                                <span className="material-symbols-outlined text-sm">filter_list</span>
                                Clear Filters
                            </button>
                            <button
                                onClick={() => {
                                    if (sortBy === 'date') {
                                        setSortBy('name')
                                    } else {
                                        setSortBy('date')
                                    }
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-[#1152d4] border border-[#1152d4]/20 rounded-lg text-xs font-black text-white uppercase tracking-wider hover:bg-[#0d3ea8] transition-all shadow-lg shadow-blue-500/20"
                            >
                                <span className="material-symbols-outlined text-sm">sort</span>
                                Sort: {sortBy === 'date' ? 'Date' : 'Name'}
                            </button>
                        </div>
                    </div>

                    <form onSubmit={handleSearch} className="relative">
                        <input
                            type="search"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search by name, owner, or tag..."
                            className="w-full pl-12 pr-4 py-4 rounded-xl border border-[#e7ebf3] dark:border-[#4a5568] bg-white dark:bg-[#1a202c] text-sm focus:outline-none focus:ring-2 focus:ring-[#1152d4]/20 shadow-sm"
                        />
                        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-[#8a9dbd]">search</span>
                    </form>

                    {/* AI Knowledge Base Search Results */}
                    {isSearching && (
                        <div className="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-2xl p-6 animate-in slide-in-from-top-2 duration-300">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-sm font-black text-[#1152d4] flex items-center gap-2 uppercase tracking-wider">
                                    <span className="material-symbols-outlined text-[20px]">psychology</span>
                                    AI Knowledge Fragments
                                </h2>
                                <button onClick={() => { setIsSearching(false); setSearchQuery(''); }} className="text-[10px] font-black text-[#1152d4] hover:underline uppercase">Close Results</button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {searchResults.length > 0 ? (
                                    searchResults.map((result, idx) => (
                                        <div key={idx} className="bg-white dark:bg-[#1a202c] p-4 rounded-xl shadow-sm border border-[#e7ebf3] dark:border-[#2d3748] hover:border-[#1152d4]/30 transition-all">
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-[10px] font-black text-[#4c669a] uppercase truncate max-w-[150px]">{result.metadata.file_name}</span>
                                                <span className="text-[9px] font-black bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full">{(result.score * 100).toFixed(0)}% Match</span>
                                            </div>
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] italic line-clamp-2 leading-relaxed">"{result.metadata.text}"</p>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-bold">No matching semantic fragments discovered in the knowledge base.</p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Table View */}
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="border-b border-[#e7ebf3] dark:border-[#2d3748]">
                                    <th className="px-6 py-4 w-12 text-center">
                                        <input
                                            type="checkbox"
                                            checked={selectedDocs.length > 0 && selectedDocs.length === paginatedDocs.length}
                                            onChange={() => toggleSelectAll(paginatedDocs.map(d => d.id))}
                                            className="size-4 rounded border-[#cfd7e7] text-[#1152d4]"
                                        />
                                    </th>
                                    <th className="px-6 py-4 text-[11px] font-black text-[#8a9dbd] uppercase tracking-wider">Name</th>
                                    <th className="px-6 py-4 text-[11px] font-black text-[#8a9dbd] uppercase tracking-wider text-center">Owner</th>
                                    <th className="px-6 py-4 text-[11px] font-black text-[#8a9dbd] uppercase tracking-wider text-center">Modified</th>
                                    <th className="px-6 py-4 text-[11px] font-black text-[#8a9dbd] uppercase tracking-wider text-center text-center">RAG Sync</th>
                                    <th className="px-6 py-4 text-[11px] font-black text-[#8a9dbd] uppercase tracking-wider text-center">Label</th>
                                    <th className="px-6 py-4 w-24"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[#f0f2f5] dark:divide-[#2d3748]">
                                {loading ? (
                                    <tr><td colSpan={7} className="p-12 text-center text-[#4c669a] font-bold tracking-widest uppercase text-xs">Initializing Document Stream...</td></tr>
                                ) : paginatedDocs.length === 0 ? (
                                    <tr><td colSpan={7} className="p-12 text-center text-[#4c669a] font-bold">No documents match the current filters.</td></tr>
                                ) : paginatedDocs.map((doc) => (
                                    <tr key={doc.id} className={`hover:bg-blue-50/50 dark:hover:bg-blue-900/5 transition-colors group ${selectedDocs.includes(doc.id) ? 'bg-blue-50/30' : ''}`}>
                                        <td className="px-6 py-5 text-center">
                                            <input
                                                type="checkbox"
                                                checked={selectedDocs.includes(doc.id)}
                                                onChange={() => toggleSelect(doc.id)}
                                                className="size-4 rounded border-[#cfd7e7] text-[#1152d4]"
                                            />
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-4">
                                                <div className="size-10 rounded-lg bg-gray-50 flex items-center justify-center text-[#4c669a] group-hover:bg-[#1152d4] group-hover:text-white transition-all">
                                                    <span className="material-symbols-outlined text-[20px]">
                                                        {doc.file_name.endsWith('.pdf') ? 'picture_as_pdf' : 'description'}
                                                    </span>
                                                </div>
                                                <div>
                                                    <p className="font-bold text-[#0d121b] dark:text-white mb-0.5">{doc.file_name}</p>
                                                    <p className="text-[10px] font-bold text-[#8a9dbd] uppercase">{doc.file_name.toLowerCase().includes('minutes') ? 'Meeting Minutes' : 'Policy Draft'}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5 text-center text-[#4c669a] font-bold">
                                            {doc.uploaded_by?.full_name || 'System Admin'}
                                        </td>
                                        <td className="px-6 py-5 text-center text-[#4c669a] text-xs font-bold">
                                            {new Date(doc.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-5 text-center">
                                            <button
                                                onClick={() => handleIngest(doc.id)}
                                                disabled={ingesting === doc.id}
                                                className={`p-2 rounded-lg transition-all ${ingesting === doc.id ? 'text-[#1152d4] animate-spin' : 'text-[#8a9dbd] hover:text-[#1152d4] hover:bg-blue-50'}`}
                                                title="Ingest to RAG"
                                            >
                                                <span className="material-symbols-outlined text-[20px]">{ingesting === doc.id ? 'sync' : 'database_upload'}</span>
                                            </button>
                                        </td>
                                        <td className="px-6 py-5 text-center">
                                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${doc.is_confidential ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100'}`}>
                                                <span className={`size-1.5 rounded-full ${doc.is_confidential ? 'bg-red-600' : 'bg-emerald-600'} mr-2`}></span>
                                                {doc.is_confidential ? 'Confidential' : 'Public'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-5 text-right flex justify-end gap-1">
                                            <button
                                                onClick={() => handleDownload(doc.id)}
                                                className="p-2 text-[#8a9dbd] hover:text-[#1152d4] transition-colors"
                                                title="View/Download"
                                            >
                                                <span className="material-symbols-outlined text-[18px]">visibility</span>
                                            </button>
                                            <button
                                                onClick={() => handleDelete(doc.id)}
                                                className="p-2 text-[#8a9dbd] hover:text-red-600 transition-colors"
                                                title="Delete Asset"
                                            >
                                                <span className="material-symbols-outlined text-[18px]">delete</span>
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        {/* Pagination Footer */}
                        {totalPages > 1 && (
                            <div className="px-6 py-4 bg-gray-50/50 dark:bg-[#1a202c] border-t border-[#e7ebf3] dark:border-[#2d3748] flex items-center justify-between">
                                <p className="text-xs font-black text-[#8a9dbd] uppercase tracking-widest">
                                    Page {currentPage} of {totalPages}
                                </p>
                                <div className="flex gap-1">
                                    <button
                                        disabled={currentPage === 1}
                                        onClick={() => setCurrentPage(prev => prev - 1)}
                                        className="size-8 rounded-lg border border-[#cfd7e7] flex items-center justify-center text-[#4c669a] hover:bg-white disabled:opacity-30 transition-all"
                                    >
                                        <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                                    </button>
                                    {[...Array(totalPages)].map((_, i) => (
                                        <button
                                            key={i}
                                            onClick={() => setCurrentPage(i + 1)}
                                            className={`size-8 rounded-lg text-xs font-black transition-all ${currentPage === i + 1 ? 'bg-[#1152d4] text-white shadow-md shadow-blue-500/20' : 'border border-[#cfd7e7] text-[#4c669a] hover:bg-white'}`}
                                        >
                                            {i + 1}
                                        </button>
                                    ))}
                                    <button
                                        disabled={currentPage === totalPages}
                                        onClick={() => setCurrentPage(prev => prev + 1)}
                                        className="size-8 rounded-lg border border-[#cfd7e7] flex items-center justify-center text-[#4c669a] hover:bg-white disabled:opacity-30 transition-all"
                                    >
                                        <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Upload Modal */}
            {showUploadModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-3xl shadow-2xl border border-[#e7ebf3] dark:border-[#2d3748] w-full max-w-md overflow-hidden relative">
                        <div className="px-8 py-6 border-b border-[#e7ebf3] dark:border-[#2d3748] flex items-center justify-between">
                            <h3 className="font-black text-[#0d121b] dark:text-white uppercase tracking-tight">
                                {uploadStep === 'initial' ? 'Upload Knowledge Asset' :
                                    uploadStep === 'ready_to_ingest' ? 'Upload Successful' :
                                        uploadStep === 'ingesting' ? 'Ingesting Vectors' : 'Complete'}
                            </h3>
                            <button onClick={() => {
                                setShowUploadModal(false);
                                setUploadStep('initial');
                                setSelectedFile(null);
                            }} className="text-[#8a9dbd] hover:text-red-600 transition-colors">
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        <div className="p-8 space-y-6">
                            {uploadStep === 'initial' && (
                                <>
                                    <div
                                        onClick={() => fileInputRef.current?.click()}
                                        className="border-2 border-dashed border-[#cfd7e7] dark:border-[#4a5568] rounded-2xl p-10 text-center cursor-pointer hover:border-[#1152d4] hover:bg-blue-50/10 transition-all group"
                                    >
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            className="hidden"
                                            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                                        />
                                        <span className="material-symbols-outlined text-[56px] text-[#8a9dbd] group-hover:text-[#1152d4] mb-4 transition-colors">cloud_upload</span>
                                        <p className="text-sm font-bold text-[#0d121b] dark:text-white">{selectedFile ? selectedFile.name : 'Click to select or drag and drop'}</p>
                                        <p className="text-xs font-bold text-[#8a9dbd] mt-2 uppercase">PDF, DOCX, XLSX (Max 10MB)</p>
                                    </div>

                                    <div>
                                        <label className="block text-[11px] font-black text-[#8a9dbd] uppercase tracking-wider mb-2">Assign to TWG Knowledge Base</label>
                                        <select
                                            value={selectedTwgId}
                                            onChange={(e) => setSelectedTwgId(e.target.value)}
                                            className="w-full px-4 py-3 rounded-xl border border-[#cfd7e7] dark:border-[#4a5568] bg-white dark:bg-[#2d3748] text-sm font-bold text-[#4c669a] focus:outline-none focus:ring-2 focus:ring-[#1152d4]/20 appearance-none transition-all"
                                        >
                                            <option value="" disabled>Select Target Knowledge Base...</option>
                                            <option value="global">Global Secretariat (General)</option>
                                            <option value="energy">Energy & Infrastructure</option>
                                            <option value="agriculture">Agriculture & Food Systems</option>
                                            <option value="minerals">Critical Minerals & Industrialization</option>
                                            <option value="digital">Digital Economy & Transformation</option>
                                            <option value="protocol">Protocol & Logistics</option>
                                            <option value="resource_mobilization">Resource Mobilization</option>
                                        </select>
                                    </div>

                                    <div className="flex items-center gap-4 p-4 bg-red-50/50 dark:bg-red-900/10 rounded-2xl border border-red-50 dark:border-red-900/30">
                                        <input
                                            type="checkbox"
                                            id="confidential"
                                            checked={isConfidential}
                                            onChange={(e) => setIsConfidential(e.target.checked)}
                                            className="size-5 text-red-600 focus:ring-red-600 rounded-lg border-[#cfd7e7]"
                                        />
                                        <label htmlFor="confidential" className="text-xs font-black text-red-700 dark:text-red-400 uppercase tracking-wider cursor-pointer">Mark as CONFIDENTIAL</label>
                                    </div>

                                    <button
                                        onClick={handleUpload}
                                        disabled={!selectedFile || !selectedTwgId || uploading}
                                        className="w-full py-4 bg-[#1152d4] hover:bg-[#0d3ea8] text-white rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-blue-500/30 transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-3"
                                    >
                                        {uploading ? (
                                            <>
                                                <span className="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
                                                Uploading...
                                            </>
                                        ) : 'Upload Document'}
                                    </button>
                                </>
                            )}

                            {uploadStep === 'ready_to_ingest' && (
                                <div className="text-center space-y-6">
                                    <div className="size-20 bg-green-50 rounded-full flex items-center justify-center mx-auto">
                                        <span className="material-symbols-outlined text-[32px] text-green-600">check_circle</span>
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-black text-[#0d121b] dark:text-white">File Uploaded Successfully</h4>
                                        <p className="text-sm text-[#4c669a] mt-2 font-medium">
                                            The document is saved. Do you want to ingest it into the Knowledge Base for AI search?
                                        </p>
                                    </div>
                                    <button
                                        onClick={handleModalIngest}
                                        className="w-full py-4 bg-[#1152d4] hover:bg-[#0d3ea8] text-white rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-blue-500/30 transition-all active:scale-[0.98] flex items-center justify-center gap-3"
                                    >
                                        <span className="material-symbols-outlined">database_upload</span>
                                        Ingest to Knowledge Base
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowUploadModal(false);
                                            setUploadStep('initial');
                                        }}
                                        className="text-sm font-bold text-[#8a9dbd] hover:text-[#4c669a]"
                                    >
                                        Skip Ingestion (Store Only)
                                    </button>
                                </div>
                            )}

                            {uploadStep === 'ingesting' && (
                                <div className="text-center space-y-8 py-4">
                                    <div className="relative size-24 mx-auto">
                                        <div className="absolute inset-0 rounded-full border-4 border-[#eef2ff] border-t-[#1152d4] animate-spin"></div>
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-[32px] text-[#1152d4]">smart_toy</span>
                                        </div>
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-black text-[#0d121b] dark:text-white animate-pulse">Processing Vectors...</h4>
                                        <p className="text-sm text-[#4c669a] mt-2 font-medium">Reading content, generating embeddings, and updating Pinecone index.</p>
                                    </div>
                                </div>
                            )}

                            {uploadStep === 'complete' && (
                                <div className="text-center space-y-6">
                                    <div className="size-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto">
                                        <span className="material-symbols-outlined text-[32px] text-[#1152d4]">auto_awesome</span>
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-black text-[#0d121b] dark:text-white">Ingestion Complete!</h4>
                                        <p className="text-sm text-[#4c669a] mt-2 font-medium">
                                            Your document is now searchable by the AI agents.
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => {
                                            setShowUploadModal(false);
                                            setUploadStep('initial');
                                            fetchData();
                                        }}
                                        className="w-full py-4 bg-[#1152d4] hover:bg-[#0d3ea8] text-white rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-blue-500/30 transition-all active:scale-[0.98]"
                                    >
                                        Close
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </ModernLayout>
    )
}
