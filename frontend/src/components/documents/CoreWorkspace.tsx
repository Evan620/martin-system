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

    return (
        <div className="rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] bg-white dark:bg-[#1a202c] overflow-hidden">
            <div className="px-6 py-4 border-b border-[#e7ebf3] dark:border-[#2d3748] flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/30">
                <div>
                    <h3 className="text-lg font-black text-[#0d121b] dark:text-white flex items-center gap-2">
                        <span className="material-symbols-outlined text-[#1152d4]">cloud_circle</span>
                        Core Workspace
                    </h3>
                    <p className="text-xs text-[#8a9dbd] font-bold uppercase tracking-wider mt-1">
                        Shared Drive Documents
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {canUpload && (
                        <button
                            onClick={() => setShowUpload(!showUpload)}
                            className={`p-2 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all ${showUpload ? 'bg-red-50 text-red-600' : 'bg-[#1152d4] text-white hover:bg-[#0d3ea8]'}`}
                        >
                            <span className="material-symbols-outlined text-[18px]">{showUpload ? 'close' : 'add'}</span>
                            {showUpload ? 'Close' : 'Add Document'}
                        </button>
                    )}
                    <button
                        onClick={() => setViewMode('grid')}
                        className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white dark:bg-[#4a5568] shadow-sm text-[#1152d4]' : 'text-[#8a9dbd] hover:text-[#4c669a]'}`}
                    >
                        <span className="material-symbols-outlined text-[20px]">grid_view</span>
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white dark:bg-[#4a5568] shadow-sm text-[#1152d4]' : 'text-[#8a9dbd] hover:text-[#4c669a]'}`}
                    >
                        <span className="material-symbols-outlined text-[20px]">view_list</span>
                    </button>
                    <button
                        onClick={loadFiles}
                        disabled={loading}
                        className="p-2 rounded-lg bg-gray-100 dark:bg-[#2d3748] text-[#8a9dbd] hover:text-[#1152d4] transition-all disabled:opacity-50"
                    >
                        <span className={`material-symbols-outlined text-[20px] ${loading ? 'animate-spin' : ''}`}>sync</span>
                    </button>
                </div>
            </div>

            {/* Admin Upload Section - Conditional */}
            {showUpload && canUpload && (
                <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748] bg-blue-50/20 dark:bg-blue-900/10 animate-in slide-in-from-top-2">
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

                {loading && files.length === 0 ? (
                    <div className="flex justify-center py-12">
                        <span className="material-symbols-outlined text-4xl text-[#1152d4] animate-spin">progress_activity</span>
                    </div>
                ) : files.length === 0 ? (
                    <div className="text-center py-12 border-2 border-dashed border-[#cfd7e7] rounded-xl bg-gray-50/50">
                        <span className="material-symbols-outlined text-4xl text-[#8a9dbd] mb-2">folder_off</span>
                        <p className="text-[#8a9dbd] font-bold">No core documents found.</p>
                        {canUpload && !showUpload && (
                            <button onClick={() => setShowUpload(true)} className="mt-4 text-xs font-bold text-[#1152d4] hover:underline uppercase">
                                Upload First Document
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                        {viewMode === 'grid' ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {files.map((file) => (
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
                                            <div className="mt-auto flex items-center gap-1 text-[10px] uppercase font-black opacity-60">
                                                <span className="material-symbols-outlined text-[12px]">schedule</span>
                                                {new Date(file.modifiedTime).toLocaleDateString()}
                                            </div>
                                            {file.size && (
                                                <div className="text-[10px] text-gray-600 mt-1">
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
                                                            <span key={twgId} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[9px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
                                                                <span className="material-symbols-outlined text-[10px]">group</span>
                                                                {twg.name}
                                                            </span>
                                                        );
                                                    })}
                                                    {file.scope.length > 3 && (
                                                        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-[9px] font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                                                            +{file.scope.length - 3}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                            {file.access_control === 'all_twgs' && (
                                                <div className="flex flex-wrap gap-1 mt-2">
                                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-[9px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
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
                                                className="absolute top-2 right-2 p-1.5 bg-white dark:bg-[#2d3748] rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 shadow-sm"
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
                                {files.map((file) => (
                                    <div
                                        key={file.id}
                                        className="flex items-center p-3 rounded-xl border border-[#e7ebf3] hover:border-[#1152d4] bg-white hover:shadow-md transition-all group"
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
                                                <p className="text-sm font-bold text-[#0d121b] group-hover:text-[#1152d4] transition-colors truncate">{file.name}</p>
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <p className="text-[10px] font-bold text-[#8a9dbd] uppercase tracking-wider">
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
                                                                    <span key={twgId} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[9px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
                                                                        <span className="material-symbols-outlined text-[10px]">group</span>
                                                                        {twg.name}
                                                                    </span>
                                                                );
                                                            })}
                                                            {file.scope.length > 2 && (
                                                                <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-[9px] font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                                                                    +{file.scope.length - 2}
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}
                                                    {file.access_control === 'all_twgs' && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-[9px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                                                            <span className="material-symbols-outlined text-[10px]">public</span>
                                                            All TWGs
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                            <span className="material-symbols-outlined text-[#8a9dbd] group-hover:text-[#1152d4] opacity-0 group-hover:opacity-100 transition-all ml-4">open_in_new</span>
                                        </a>
                                        {isAdmin && (
                                            <button
                                                onClick={(e) => handleDelete(file.id, file.name, e)}
                                                disabled={deletingId === file.id}
                                                className="ml-2 p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all disabled:opacity-50"
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
