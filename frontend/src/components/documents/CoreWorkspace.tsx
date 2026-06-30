import { useEffect, useState } from 'react';
import { sharedDocuments, twgs as twgService } from '../../services/api';
import { useSelector } from 'react-redux';
import { RootState } from '../../store';
import SharedDocumentsManager from '../admin/SharedDocumentsManager';

interface CoreFile {
    id: string;
    name: string;
    mimeType: string;
    webViewLink: string;
    iconLink: string;
    thumbnailLink?: string;
    modifiedTime: string;
    size?: number;
    access_control?: string;
    scope?: string[];
}

const CoreWorkspace = () => {
    const [files, setFiles] = useState<CoreFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [error, setError] = useState<string | null>(null);
    const [showUpload, setShowUpload] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [selectedTwgFilter, setSelectedTwgFilter] = useState<string>('');
    const [allTwgs, setAllTwgs] = useState<any[]>([]);
    const [userLedTwgIds, setUserLedTwgIds] = useState<string[]>([]);

    const user = useSelector((state: RootState) => state.auth.user);
    const isAdmin = user?.role === 'ADMIN' || user?.role === 'SECRETARIAT_LEAD';
    const isFacilitator = user?.role === 'TWG_FACILITATOR';
    const isTwgLead = userLedTwgIds.length > 0;
    const canUpload = isAdmin || isFacilitator || isTwgLead;

    const loadFiles = async () => {
        setLoading(true);
        setError(null);
        try {
            // Use sharedDocuments.list() instead of documentService
            const response = await sharedDocuments.list();
            setFiles(response.data);
        } catch (err) {
            console.error("Failed to load core workspace files:", err);
            setError("Failed to load Core Workspace files. Please check connection.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadFiles();
    }, []);

    useEffect(() => {
        const fetchTwgs = async () => {
            try {
                const response = await twgService.list();
                setAllTwgs(response.data);

                // Check if user is a TWG lead (political or technical lead)
                const ledTwgIds: string[] = [];
                const userId = String(user?.id || '');

                console.log('Checking TWG lead status for user:', userId);

                response.data.forEach((twg: any) => {
                    const politicalLeadId = String(twg.political_lead?.id || '');
                    const technicalLeadId = String(twg.technical_lead?.id || '');

                    console.log(`TWG: ${twg.name}, political_lead_id: ${politicalLeadId}, technical_lead_id: ${technicalLeadId}`);

                    if (politicalLeadId === userId || technicalLeadId === userId) {
                        ledTwgIds.push(twg.id);
                        console.log(`User is lead of TWG: ${twg.name}`);
                    }
                });

                setUserLedTwgIds(ledTwgIds);
                console.log('Final ledTwgIds:', ledTwgIds);
            } catch (err) {
                console.error('Failed to fetch TWGs:', err);
            }
        };
        fetchTwgs();
    }, [user?.id]);

    const handleDelete = async (fileId: string, fileName: string, e: React.MouseEvent) => {
        e.preventDefault(); // Prevent opening the link
        e.stopPropagation();

        if (!confirm(`Are you sure you want to delete "${fileName}"?`)) {
            return;
        }

        setDeletingId(fileId);
        try {
            await sharedDocuments.delete(fileId);
            setFiles(files.filter(f => f.id !== fileId));
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete file');
        } finally {
            setDeletingId(null);
        }
    };

    const handleUploadSuccess = () => {
        setShowUpload(false);
        loadFiles();
    };

    const getIcon = (mimeType: string) => {
        if (mimeType.includes('spreadsheet')) return 'table_view';
        if (mimeType.includes('document')) return 'description';
        if (mimeType.includes('presentation')) return 'slideshow';
        if (mimeType.includes('pdf')) return 'picture_as_pdf';
        if (mimeType.includes('folder')) return 'folder';
        if (mimeType.includes('image')) return 'image';
        return 'article';
    };

    const getFileColor = (mimeType: string) => {
        if (mimeType.includes('spreadsheet')) return 'bg-green-50 hover:bg-green-100 border-green-200 text-green-700';
        if (mimeType.includes('document')) return 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700';
        if (mimeType.includes('presentation')) return 'bg-orange-50 hover:bg-orange-100 border-orange-200 text-orange-700';
        if (mimeType.includes('pdf')) return 'bg-red-50 hover:bg-red-100 border-red-200 text-red-700';
        if (mimeType.includes('image')) return 'bg-purple-50 hover:bg-purple-100 border-purple-200 text-purple-700';
        return 'bg-gray-50 hover:bg-gray-100 border-gray-200 text-gray-700';
    };

    const formatFileSize = (bytes?: number) => {
        if (!bytes) return '';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const HIDDEN_PILLARS = ['protocol_logistics', 'resource_mobilization'];
    const filterableTwgs = allTwgs.filter((t: any) => !HIDDEN_PILLARS.includes(t.pillar));

    const filteredFiles = selectedTwgFilter
        ? files.filter(file => {
            if (file.access_control === 'specific_twgs' && file.scope) {
                return file.scope.includes(selectedTwgFilter);
            }
            // "all_twgs" docs are visible regardless of filter
            return file.access_control === 'all_twgs';
        })
        : files;

    return (
        <div className="rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] bg-white dark:bg-[#1a202c] overflow-hidden">
            <div className="px-6 py-4 border-b border-[#e7ebf3] dark:border-[#2d3748] flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/30">
                <div>
                    <h3 className="font-display flex items-center gap-2" style={{ fontWeight: 800, letterSpacing: '-0.02em', fontSize: 16, color: 'var(--ink-900)' }}>
                        <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>cloud_circle</span>
                        Core Workspace
                    </h3>
                    <p className="mt-1" style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, color: 'var(--ink-500)' }}>
                        Shared Drive Documents
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {filterableTwgs.length > 0 && (
                        <select
                            value={selectedTwgFilter}
                            onChange={e => setSelectedTwgFilter(e.target.value)}
                            className="text-xs font-bold border border-[#cfd7e7] dark:border-[#4a5568] rounded-lg px-3 py-2 bg-white dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] focus:ring-teal-500 focus:border-teal-500"
                        >
                            <option value="">All TWGs</option>
                            {filterableTwgs.map((t: any) => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                        </select>
                    )}
                    {canUpload && (
                        <button
                            onClick={() => setShowUpload(!showUpload)}
                            className={`clickable-scale p-2 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all ${showUpload ? 'bg-red-50 text-red-600' : 'text-white'}`}
                            style={showUpload ? undefined : { background: 'var(--accent)' }}
                        >
                            <span className="material-symbols-outlined text-[18px]">{showUpload ? 'close' : 'add'}</span>
                            {showUpload ? 'Close' : 'Add Document'}
                        </button>
                    )}
                    <button
                        onClick={() => setViewMode('grid')}
                        className={`clickable-scale p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white dark:bg-[#4a5568] shadow-sm text-teal-600' : 'text-[#8a9dbd] hover:text-[#4c669a]'}`}
                    >
                        <span className="material-symbols-outlined text-[20px]">grid_view</span>
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={`clickable-scale p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white dark:bg-[#4a5568] shadow-sm text-teal-600' : 'text-[#8a9dbd] hover:text-[#4c669a]'}`}
                    >
                        <span className="material-symbols-outlined text-[20px]">view_list</span>
                    </button>
                    <button
                        onClick={loadFiles}
                        disabled={loading}
                        className="clickable-scale p-2 rounded-lg bg-gray-100 dark:bg-[#2d3748] text-[#8a9dbd] hover:text-teal-600 transition-all disabled:opacity-50"
                    >
                        <span className={`material-symbols-outlined text-[20px] ${loading ? 'animate-spin' : ''}`}>sync</span>
                    </button>
                </div>
            </div>

            {/* Admin Upload Section - Conditional */}
            {showUpload && canUpload && (
                <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748] bg-teal-50/20 dark:bg-teal-900/10 animate-in slide-in-from-top-2">
                    <SharedDocumentsManager onUploadSuccess={handleUploadSuccess} />
                </div>
            )}

            <div className="p-6">
                {error && (
                    <div className="p-4 rounded-xl bg-red-50 text-red-600 text-sm font-bold mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined">error</span>
                        {error}
                    </div>
                )}

                {loading && filteredFiles.length === 0 ? (
                    <div className="flex justify-center py-12">
                        <span className="material-symbols-outlined text-4xl text-teal-600 animate-spin">progress_activity</span>
                    </div>
                ) : filteredFiles.length === 0 ? (
                    <div className="text-center py-12 border-2 border-dashed border-[#cfd7e7] rounded-xl bg-gray-50/50">
                        <span className="material-symbols-outlined text-4xl text-[#8a9dbd] mb-2">folder_off</span>
                        <p className="font-bold text-xs tracking-tight" style={{ color: 'var(--ink-500)' }}>No core documents found.</p>
                        {canUpload && !showUpload && (
                            <button onClick={() => setShowUpload(true)} className="mt-4 text-xs font-bold text-teal-600 hover:underline uppercase">
                                Upload First Document
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                        {viewMode === 'grid' ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {filteredFiles.map((file) => (
                                    <div
                                        key={file.id}
                                        className={`group relative flex flex-col p-4 rounded-xl border transition-all duration-200 ${getFileColor(file.mimeType)}`}
                                    >
                                        <a
                                            href={file.webViewLink}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="flex-1"
                                        >
                                            <div className="flex justify-between items-start mb-3">
                                                <span className="material-symbols-outlined text-[28px]">{getIcon(file.mimeType)}</span>
                                                <span className="material-symbols-outlined text-[18px] opacity-0 group-hover:opacity-100 transition-opacity">open_in_new</span>
                                            </div>
                                            <h3 className="font-bold text-sm line-clamp-2 mb-2 leading-tight">
                                                {file.name}
                                            </h3>
                                            <div className="font-mono-geist mt-auto flex items-center gap-1 text-[10px] uppercase font-bold opacity-60">
                                                <span className="material-symbols-outlined text-[12px]">schedule</span>
                                                {new Date(file.modifiedTime).toLocaleDateString()}
                                            </div>
                                            {file.size && (
                                                <div className="font-mono-geist text-[10px] text-gray-600 mt-1">
                                                    {formatFileSize(file.size)}
                                                </div>
                                            )}
                                            {/* TWG Tags */}
                                            {file.access_control === 'specific_twgs' && file.scope && file.scope.length > 0 && (
                                                <div className="flex flex-wrap gap-1 mt-2">
                                                    {file.scope.slice(0, 3).map((twgId) => {
                                                        const twg = allTwgs.find(t => t.id === twgId);
                                                        if (!twg) return null;
                                                        return (
                                                            <span key={twgId} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider" style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }}>
                                                                <span className="material-symbols-outlined text-[10px]">group</span>
                                                                {twg.name}
                                                            </span>
                                                        );
                                                    })}
                                                    {file.scope.length > 3 && (
                                                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider font-mono-geist" style={{ background: 'var(--surface-2)', color: 'var(--ink-500)' }}>
                                                            +{file.scope.length - 3}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                            {file.access_control === 'all_twgs' && (
                                                <div className="flex flex-wrap gap-1 mt-2">
                                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider" style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }}>
                                                        <span className="material-symbols-outlined text-[10px]">public</span>
                                                        All TWGs
                                                    </span>
                                                </div>
                                            )}
                                        </a>
                                        {isAdmin && (
                                            <button
                                                onClick={(e) => handleDelete(file.id, file.name, e)}
                                                disabled={deletingId === file.id}
                                                className="clickable-scale absolute top-2 right-2 p-1.5 bg-white dark:bg-[#2d3748] rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 shadow-sm"
                                                title="Delete file"
                                            >
                                                {deletingId === file.id ? (
                                                    <span className="material-symbols-outlined text-[16px] text-red-600 animate-spin">progress_activity</span>
                                                ) : (
                                                    <span className="material-symbols-outlined text-[16px] text-red-600">delete</span>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {filteredFiles.map((file) => (
                                    <div
                                        key={file.id}
                                        className="flex items-center p-3 rounded-xl border border-[#e7ebf3] hover:border-teal-600 bg-white hover:shadow-md transition-all group"
                                    >
                                        <a
                                            href={file.webViewLink}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="flex items-center flex-1 min-w-0"
                                        >
                                            <div className={`size-10 rounded-lg flex items-center justify-center mr-4 ${getFileColor(file.mimeType).replace('hover:shadow-lg hover:-translate-y-1', '')}`}>
                                                <span className="material-symbols-outlined text-[20px]">{getIcon(file.mimeType)}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs font-bold text-[#0d121b] group-hover:text-teal-600 transition-colors truncate tracking-tight">{file.name}</p>
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <p className="font-mono-geist text-[9px] font-semibold uppercase tracking-wider" style={{ color: 'var(--ink-400)' }}>
                                                        Modified {new Date(file.modifiedTime).toLocaleDateString()}
                                                        {file.size && ` • ${formatFileSize(file.size)}`}
                                                    </p>
                                                    {/* TWG Tags for List View */}
                                                    {file.access_control === 'specific_twgs' && file.scope && file.scope.length > 0 && (
                                                        <div className="flex items-center gap-1">
                                                            {file.scope.slice(0, 2).map((twgId) => {
                                                                const twg = allTwgs.find(t => t.id === twgId);
                                                                if (!twg) return null;
                                                                return (
                                                                    <span key={twgId} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider" style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }}>
                                                                        <span className="material-symbols-outlined text-[10px]">group</span>
                                                                        {twg.name}
                                                                    </span>
                                                                );
                                                            })}
                                                            {file.scope.length > 2 && (
                                                                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider font-mono-geist" style={{ background: 'var(--surface-2)', color: 'var(--ink-500)' }}>
                                                                    +{file.scope.length - 2}
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}
                                                    {file.access_control === 'all_twgs' && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider" style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }}>
                                                            <span className="material-symbols-outlined text-[10px]">public</span>
                                                            All TWGs
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                            <span className="material-symbols-outlined text-[#8a9dbd] group-hover:text-teal-600 opacity-0 group-hover:opacity-100 transition-all ml-4">open_in_new</span>
                                        </a>
                                        {isAdmin && (
                                            <button
                                                onClick={(e) => handleDelete(file.id, file.name, e)}
                                                disabled={deletingId === file.id}
                                                className="clickable-scale ml-2 p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all disabled:opacity-50"
                                                title="Delete file"
                                            >
                                                {deletingId === file.id ? (
                                                    <span className="material-symbols-outlined text-red-600 animate-spin">progress_activity</span>
                                                ) : (
                                                    <span className="material-symbols-outlined text-red-600">delete</span>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CoreWorkspace;
