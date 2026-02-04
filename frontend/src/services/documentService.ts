import api from './api';


export interface Document {
    id: string;
    twg_id: string | null;
    file_name: string;
    file_path: string;
    file_type: string;
    uploaded_by_id: string;
    is_confidential: boolean;
    metadata_json: Record<string, any> | null;
    created_at: string;
    ingested_at?: string;
    uploaded_by?: { full_name: string; email: string };
    twg?: { id: string; name: string; pillar: string };
}

export interface IngestionResponse {
    status: string;
    chunks_ingested: number;
    namespace: string;
}

export interface SearchResult {
    id: string;
    score: number;
    metadata: {
        text: string;
        twg_id: string;
        doc_id: string;
        file_name: string;
        [key: string]: any;
    };
}

export const documentService = {
    uploadDocument: async (file: File, twgId?: string, isConfidential: boolean = false): Promise<Document> => {
        const formData = new FormData();
        formData.append('file', file);
        if (twgId) formData.append('twg_id', twgId);
        formData.append('is_confidential', String(isConfidential));

        const response = await api.post<Document>('/documents/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    listDocuments: async (twgId?: string, page: number = 1, limit: number = 10, projectId?: string): Promise<{ data: Document[]; total: number }> => {
        const params = {
            ...(twgId ? { twg_id: twgId } : {}),
            ...(projectId ? { project_id: projectId } : {}),
            skip: (page - 1) * limit,
            limit
        };
        const response = await api.get<Document[]>('/documents/', { params });
        const total = parseInt(response.headers['x-total-count'] || '0', 10);
        return { data: response.data, total };
    },

    downloadDocument: async (docId: string): Promise<void> => {
        const response = await api.get(`/documents/${docId}/download`, {
            responseType: 'blob',
        });

        const contentType = response.headers['content-type'];
        const url = window.URL.createObjectURL(new Blob([response.data], { type: contentType }));
        const link = document.createElement('a');
        link.href = url;

        // Get filename from Content-Disposition if available
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'document';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
            if (filenameMatch && filenameMatch.length > 1) {
                filename = filenameMatch[1];
            }
        }

        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    },

    ingestDocument: async (docId: string): Promise<IngestionResponse> => {
        const response = await api.post<IngestionResponse>(`/documents/${docId}/ingest`);
        return response.data;
    },

    deleteDocument: async (docId: string): Promise<void> => {
        await api.delete(`/documents/${docId}`);
    },

    bulkDeleteDocuments: async (docIds: string[]): Promise<void> => {
        await api.post('/documents/bulk-delete', docIds);
    },

    searchDocuments: async (query: string, twgId?: string, limit: number = 5): Promise<SearchResult[]> => {
        const params = {
            query,
            limit,
            ...(twgId && { twg_id: twgId }),
        };
        const response = await api.get<SearchResult[]>('/documents/search', { params });
        return response.data;
    },

    fetchCoreWorkspaceFiles: async (): Promise<any[]> => {
        const response = await api.get<any[]>('/documents/core-workspace');
        return response.data;
    }
};

export default documentService;
