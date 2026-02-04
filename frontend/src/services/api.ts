import axios from 'axios';
import { store } from '../store';
import { logout } from '../store/slices/authSlice';

// Create axios instance with base URL
// In VITE, we use import.meta.env for environment variables
// FORCE IPv4: Convert 'localhost' to '127.0.0.1' to avoid IPv6 connection refusals
let envUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1').trim();
let apiUrl = envUrl.replace('localhost', '127.0.0.1');

// Fix Mixed Content: Force HTTPS for Railway production URLs
// This handles both http:// URLs and ensures railway.app always uses https://
if (apiUrl.toLowerCase().includes('railway.app')) {
    // Remove any existing protocol
    apiUrl = apiUrl.replace(/^https?:\/\//i, '');
    // Add https://
    apiUrl = 'https://' + apiUrl;
}

// Debug logging (will be visible in browser console)

export const API_URL = apiUrl;

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for adding the auth token
api.interceptors.request.use(
    (config) => {

        // Try to get token from Redux store first, then fall back to localStorage
        let token = store.getState().auth.token;
        if (!token) {
            token = localStorage.getItem('token');
        }
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        // Inject User Timezone
        try {
            const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            if (userTimezone) {
                config.headers['X-User-Timezone'] = userTimezone;
            }
        } catch (e) {
            console.warn('[API] Failed to detect user timezone', e);
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor for handling 401 (Unauthorized)
api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        const originalRequest = error.config;

        // If error is 401 and we haven't tried to refresh already
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            // Dispatch logout action to clear state and redirect to login
            // Ideally implementation would try to refresh token here
            store.dispatch(logout());
            return Promise.reject(error);
        }

        return Promise.reject(error);
    }
);

export default api;

export const meetings = {
    getActive: () => api.get('/meetings/active'),
    list: (skip = 0, limit = 100) => api.get(`/meetings/?skip=${skip}&limit=${limit}`),
    get: (id: string) => api.get(`/meetings/${id}`),
    create: (data: any) => api.post('/meetings/', data),
    update: (id: string, data: any) => api.patch(`/meetings/${id}`, data),
    schedule: (id: string) => api.post(`/meetings/${id}/schedule`),
    getInvitePreview: (id: string) => api.get(`/meetings/${id}/invite-preview`),
    approveInvite: (id: string) => api.post(`/meetings/${id}/approve-invite`),
    conflictCheck: (id: string) => api.post(`/meetings/${id}/conflict-check`),
    cancel: (id: string, reason?: string) => api.post(`/meetings/${id}/cancel`, { reason, notify_participants: true }),
    notifyUpdate: (id: string, changes: string[]) => api.post(`/meetings/${id}/notify-update`, { changes, notify_participants: true }),

    // Operational Tools
    getAgenda: (id: string) => api.get(`/meetings/${id}/agenda`),
    updateAgenda: (id: string, data: { content: string }) => api.post(`/meetings/${id}/agenda`, data),
    generateAgenda: (id: string) => api.post(`/meetings/${id}/agenda/generate`),

    addParticipants: (id: string, participants: Array<{ user_id?: string, email?: string, name?: string }>) =>
        api.post(`/meetings/${id}/participants`, participants),

    updateRsvp: (meetingId: string, participantId: string, status: string) =>
        api.put(`/meetings/${meetingId}/participants/${participantId}/rsvp`, { rsvp_status: status }),

    getMinutes: (id: string) => api.get(`/meetings/${id}/minutes`),
    updateMinutes: (id: string, data: { content: string, status?: string }) => api.post(`/meetings/${id}/minutes`, data),
    generateMinutes: (id: string) => api.post(`/meetings/${id}/generate-minutes`),
    submitMinutesForApproval: (id: string) => api.post(`/meetings/${id}/minutes/submit-for-approval`),
    approveMinutes: (id: string) => api.post(`/meetings/${id}/minutes/approve`),
    rejectMinutes: (id: string, reason: string, suggestedChanges?: string) =>
        api.post(`/meetings/${id}/minutes/reject`, { reason, suggested_changes: suggestedChanges }),
    downloadMinutesPdf: (id: string) => api.get(`/meetings/${id}/minutes/pdf`, { responseType: 'blob' }),

    // Version control
    listMinutesVersions: (id: string) => api.get(`/meetings/${id}/minutes/versions`),
    getMinutesVersion: (id: string, version: number) => api.get(`/meetings/${id}/minutes/versions/${version}`),
    restoreMinutesVersion: (id: string, version: number) => api.post(`/meetings/${id}/minutes/versions/${version}/restore`),

    getActionItems: (id: string) => api.get(`/meetings/${id}/action-items`),
    createActionItem: (id: string, data: any) => api.post(`/meetings/${id}/action-items`, data),
    extractActionItems: (id: string) => api.post(`/meetings/${id}/extract-actions`),

    getDocuments: (id: string) => api.get(`/meetings/${id}/documents`),
    uploadDocument: (id: string, formData: FormData) => api.post(`/meetings/${id}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    uploadRecording: (id: string, formData: FormData) => api.post(`/meetings/${id}/upload-recording`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    compileMeetingPack: (id: string) => api.post(`/meetings/${id}/meeting-pack`),
    proposeNextMeeting: (id: string) => api.post(`/meetings/${id}/propose-next`),
};

export const actionItems = {
    update: (id: string, data: any) => api.patch(`/action-items/${id}`, data),
    delete: (id: string) => api.delete(`/action-items/${id}`),
};


export const twgs = {
    list: (skip = 0, limit = 100) => api.get(`/twgs/?skip=${skip}&limit=${limit}`),
    get: (id: string) => api.get(`/twgs/${id}`),
    update: (id: string, data: any) => api.patch(`/twgs/${id}`, data),
};

export const auditLogs = {
    list: (skip = 0, limit = 100) => api.get(`/audit-logs/?skip=${skip}&limit=${limit}`),
};

export const sharedDocuments = {
    list: () => api.get('/shared-documents/'),
    upload: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/shared-documents/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
    delete: (fileId: string) => api.delete(`/shared-documents/${fileId}`),
};

