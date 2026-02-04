import { useState } from 'react';
import { sharedDocuments } from '../../services/api';

interface SharedDocumentsManagerProps {
    onUploadSuccess?: () => void;
}

const SharedDocumentsManager = ({ onUploadSuccess }: SharedDocumentsManagerProps) => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            validateAndSetFile(file);
        }
    };

    const validateAndSetFile = (file: File) => {
        setError(null);
        setSuccess(null);

        // Validate file size
        if (file.size > MAX_FILE_SIZE) {
            setError('File size exceeds 50MB limit');
            return;
        }

        setSelectedFile(file);
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files?.[0];
        if (file) {
            validateAndSetFile(file);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setUploading(true);
        setError(null);
        setSuccess(null);
        setUploadProgress(0);

        try {
            // Simulate progress (since we don't have real progress tracking)
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => Math.min(prev + 10, 90));
            }, 200);

            await sharedDocuments.upload(selectedFile);

            clearInterval(progressInterval);
            setUploadProgress(100);
            setSuccess(`File "${selectedFile.name}" uploaded successfully!`);
            setSelectedFile(null);

            // Reset file input
            const fileInput = document.getElementById('file-input') as HTMLInputElement;
            if (fileInput) fileInput.value = '';

            // Call success callback
            if (onUploadSuccess) {
                onUploadSuccess();
            }

            // Clear success message after 3 seconds
            setTimeout(() => setSuccess(null), 3000);

        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload file');
        } finally {
            setUploading(false);
            setUploadProgress(0);
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    return (
        <div className="bg-white dark:bg-[#1a202c] rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] p-6">
            <div className="mb-6">
                <h3 className="text-lg font-black text-[#0d121b] dark:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-[#1152d4]">upload_file</span>
                    Upload Shared Document
                </h3>
                <p className="text-xs text-[#8a9dbd] font-bold uppercase tracking-wider mt-1">
                    Admin Only - Max 50MB
                </p>
            </div>

            {/* Drag and Drop Area */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isDragging
                        ? 'border-[#1152d4] bg-blue-50 dark:bg-blue-900/20'
                        : 'border-[#cfd7e7] dark:border-[#2d3748] hover:border-[#1152d4]'
                    }`}
            >
                <input
                    id="file-input"
                    type="file"
                    onChange={handleFileSelect}
                    className="hidden"
                    disabled={uploading}
                />

                {!selectedFile ? (
                    <div>
                        <span className="material-symbols-outlined text-6xl text-[#8a9dbd] mb-4 block">
                            cloud_upload
                        </span>
                        <p className="text-[#0d121b] dark:text-white font-bold mb-2">
                            Drag and drop your file here
                        </p>
                        <p className="text-sm text-[#8a9dbd] mb-4">or</p>
                        <button
                            onClick={() => document.getElementById('file-input')?.click()}
                            className="px-6 py-2 bg-[#1152d4] text-white rounded-lg font-bold hover:bg-[#0d3da0] transition-all"
                        >
                            Browse Files
                        </button>
                        <p className="text-xs text-[#8a9dbd] mt-4">
                            Supported: PDF, DOCX, XLSX, PPTX, Images (Max 50MB)
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="flex items-center justify-center gap-3 p-4 bg-gray-50 dark:bg-[#2d3748] rounded-lg">
                            <span className="material-symbols-outlined text-[#1152d4] text-3xl">
                                description
                            </span>
                            <div className="flex-1 text-left">
                                <p className="font-bold text-[#0d121b] dark:text-white truncate">
                                    {selectedFile.name}
                                </p>
                                <p className="text-xs text-[#8a9dbd]">
                                    {formatFileSize(selectedFile.size)}
                                </p>
                            </div>
                            {!uploading && (
                                <button
                                    onClick={() => setSelectedFile(null)}
                                    className="p-2 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-lg transition-all"
                                >
                                    <span className="material-symbols-outlined text-red-600">close</span>
                                </button>
                            )}
                        </div>

                        {uploading && (
                            <div className="space-y-2">
                                <div className="w-full bg-gray-200 dark:bg-[#2d3748] rounded-full h-2">
                                    <div
                                        className="bg-[#1152d4] h-2 rounded-full transition-all duration-300"
                                        style={{ width: `${uploadProgress}%` }}
                                    />
                                </div>
                                <p className="text-sm text-[#8a9dbd]">Uploading... {uploadProgress}%</p>
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={handleUpload}
                                disabled={uploading}
                                className="flex-1 px-6 py-3 bg-[#1152d4] text-white rounded-lg font-bold hover:bg-[#0d3da0] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {uploading ? (
                                    <>
                                        <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                        Uploading...
                                    </>
                                ) : (
                                    <>
                                        <span className="material-symbols-outlined">upload</span>
                                        Upload to Drive
                                    </>
                                )}
                            </button>
                            {!uploading && (
                                <button
                                    onClick={() => setSelectedFile(null)}
                                    className="px-6 py-3 border border-[#e7ebf3] dark:border-[#2d3748] text-[#8a9dbd] rounded-lg font-bold hover:bg-gray-50 dark:hover:bg-[#2d3748] transition-all"
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Error Message */}
            {error && (
                <div className="mt-4 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm font-bold flex items-center gap-2">
                    <span className="material-symbols-outlined">error</span>
                    {error}
                </div>
            )}

            {/* Success Message */}
            {success && (
                <div className="mt-4 p-4 rounded-xl bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-sm font-bold flex items-center gap-2">
                    <span className="material-symbols-outlined">check_circle</span>
                    {success}
                </div>
            )}
        </div>
    );
};

export default SharedDocumentsManager;
