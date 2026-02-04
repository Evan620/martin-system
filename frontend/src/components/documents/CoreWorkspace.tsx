import React, { useEffect, useState } from 'react';
import documentService from '../../services/documentService';

interface CoreFile {
    id: string;
    name: string;
    mimeType: string;
    webViewLink: string;
    iconLink: string;
    thumbnailLink?: string;
    modifiedTime: string;
}

const CoreWorkspace = () => {
    const [files, setFiles] = useState<CoreFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [error, setError] = useState<string | null>(null);

    const loadFiles = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await documentService.fetchCoreWorkspaceFiles();
            setFiles(data);
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

    const getIcon = (mimeType: string) => {
        if (mimeType.includes('spreadsheet')) return 'table_view';
        if (mimeType.includes('document')) return 'description';
        if (mimeType.includes('presentation')) return 'slideshow';
        if (mimeType.includes('pdf')) return 'picture_as_pdf';
        if (mimeType.includes('folder')) return 'folder';
        return 'article';
    };

    const getFileColor = (mimeType: string) => {
        if (mimeType.includes('spreadsheet')) return 'bg-green-50 hover:bg-green-100 border-green-200 text-green-700';
        if (mimeType.includes('document')) return 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700';
        if (mimeType.includes('presentation')) return 'bg-orange-50 hover:bg-orange-100 border-orange-200 text-orange-700';
        if (mimeType.includes('pdf')) return 'bg-red-50 hover:bg-red-100 border-red-200 text-red-700';
        return 'bg-gray-50 hover:bg-gray-100 border-gray-200 text-gray-700';
    };

    return (
        <div className="rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] bg-white dark:bg-[#1a202c] overflow-hidden">
            <div className="px-6 py-4 border-b border-[#e7ebf3] dark:border-[#2d3748] flex justify-between items-center">
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
                    <div className="flex bg-gray-100 dark:bg-[#2d3748] rounded-lg p-1">
                        <button
                            onClick={() => setViewMode('grid')}
                            className={`p-1.5 rounded-md transition-all ${viewMode === 'grid' ? 'bg-white dark:bg-[#4a5568] shadow-sm text-[#1152d4]' : 'text-[#8a9dbd] hover:text-[#4c669a]'}`}
                        >
                            <span className="material-symbols-outlined text-[20px]">grid_view</span>
                        </button>
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-1.5 rounded-md transition-all ${viewMode === 'list' ? 'bg-white dark:bg-[#4a5568] shadow-sm text-[#1152d4]' : 'text-[#8a9dbd] hover:text-[#4c669a]'}`}
                        >
                            <span className="material-symbols-outlined text-[20px]">view_list</span>
                        </button>
                    </div>
                    <button
                        onClick={loadFiles}
                        disabled={loading}
                        className="p-2 rounded-lg bg-gray-100 dark:bg-[#2d3748] text-[#8a9dbd] hover:text-[#1152d4] transition-all disabled:opacity-50"
                    >
                        <span className={`material-symbols-outlined text-[20px] ${loading ? 'animate-spin' : ''}`}>sync</span>
                    </button>
                </div>
            </div>

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
                    </div>
                ) : (
                    <div className="max-h-[350px] overflow-y-auto pr-2 custom-scrollbar">
                        {viewMode === 'grid' ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {files.map((file, i) => (
                                    <a
                                        key={file.id}
                                        href={file.webViewLink}
                                        target="_blank"
                                        rel="noreferrer"
                                        className={`group flex flex-col p-4 rounded-xl border transition-all duration-200 hover:shadow-lg hover:-translate-y-1 ${getFileColor(file.mimeType)}`}
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
                                    </a>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {files.map((file, i) => (
                                    <a
                                        key={file.id}
                                        href={file.webViewLink}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center p-3 rounded-xl border border-[#e7ebf3] hover:border-[#1152d4] bg-white hover:shadow-md transition-all group"
                                    >
                                        <div className={`size-10 rounded-lg flex items-center justify-center mr-4 ${getFileColor(file.mimeType).replace('hover:shadow-lg hover:-translate-y-1', '')}`}>
                                            <span className="material-symbols-outlined text-[20px]">{getIcon(file.mimeType)}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-bold text-[#0d121b] group-hover:text-[#1152d4] transition-colors truncate">{file.name}</p>
                                            <p className="text-[10px] font-bold text-[#8a9dbd] uppercase tracking-wider">
                                                Modified {new Date(file.modifiedTime).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <span className="material-symbols-outlined text-[#8a9dbd] group-hover:text-[#1152d4] opacity-0 group-hover:opacity-100 transition-all">open_in_new</span>
                                    </a>
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
