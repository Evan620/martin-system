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
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
                try {
                    // Attempt silent token refresh
                    const res = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refreshToken });
                    const newAccessToken: string = res.data.access_token;

                    localStorage.setItem('token', newAccessToken);
                    store.dispatch({ type: 'auth/setToken', payload: newAccessToken });

                    // Retry original request with new token
                    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                    return api(originalRequest);
                } catch {
                    // Refresh failed — force logout
                }
            }

            store.dispatch(logout());
        }

        return Promise.reject(error);
    }
);

export default api;

// Chair-approved, public-safe summary authored alongside the minutes.
// This block — never the raw minutes/transcript — is what is shared to
// WAIIS channels after the minutes are approved.
export interface PublicSummary {
    highlights: string[];              // 3-5 chair-approved bullets
    decisions_milestones: string[];    // only items cleared for public release
    institutions_public: string[];     // only orgs that consented to being named
    next_milestone: string;
}

export const meetings = {
    getActive: () => api.get('/meetings/active'),
    list: (skip = 0, limit = 100) => api.get(`/meetings/?skip=${skip}&limit=${limit}`),
    get: (id: string) => api.get(`/meetings/${id}`),
    create: (data: any) => api.post('/meetings/', data),
    update: (id: string, data: any) => api.patch(`/meetings/${id}`, data),
    schedule: (id: string) => api.post(`/meetings/${id}/schedule`),
    getInvitePreview: (id: string) => api.get(`/meetings/${id}/invite-preview`),
    approveInvite: (id: string) => api.post(`/meetings/${id}/approve-invite`),
    syncCalendar: (id: string) => api.post(`/meetings/${id}/sync-calendar`),
    conflictCheck: (id: string) => api.post(`/meetings/${id}/conflict-check`),
    cancel: (id: string, reason?: string) => api.post(`/meetings/${id}/cancel`, { reason, notify_participants: true }),
    notifyUpdate: (id: string, changes: string[]) => api.post(`/meetings/${id}/notify-update`, { changes, notify_participants: true }),

    // Operational Tools
    getAgenda: (id: string) => api.get(`/meetings/${id}/agenda`),
    updateAgenda: (id: string, data: { content: string }) => api.post(`/meetings/${id}/agenda`, data),
    generateAgenda: (id: string) => api.post(`/meetings/${id}/agenda/generate`),

    addParticipants: (id: string, participants: Array<{ user_id?: string, email?: string, name?: string }>, applyToSeries: boolean = false) =>
        api.post(`/meetings/${id}/participants${applyToSeries ? '?apply_to_series=true' : ''}`, participants),

    updateRsvp: (meetingId: string, participantId: string, status: string) =>
        api.put(`/meetings/${meetingId}/participants/${participantId}/rsvp`, { rsvp_status: status }),

    removeParticipant: (meetingId: string, participantId: string, applyToSeries: boolean = false) =>
        api.delete(`/meetings/${meetingId}/participants/${participantId}${applyToSeries ? '?apply_to_series=true' : ''}`),

    getMinutes: (id: string) => api.get(`/meetings/${id}/minutes`),
    updateMinutes: (id: string, data: { content: string, status?: string, public_summary?: PublicSummary }) => api.post(`/meetings/${id}/minutes`, data),
    generateMinutes: (id: string) => api.post(`/meetings/${id}/generate-minutes`),
    submitMinutesForApproval: (id: string) => api.post(`/meetings/${id}/minutes/submit-for-approval`),
    approveMinutes: (id: string) => api.post(`/meetings/${id}/minutes/approve`),
    rejectMinutes: (id: string, reason: string, suggestedChanges?: string) =>
        api.post(`/meetings/${id}/minutes/reject`, { reason, suggested_changes: suggestedChanges }),
    downloadMinutesPdf: (id: string, language?: string) => api.get(`/meetings/${id}/minutes/pdf${language ? `?language=${language}` : ''}`, { responseType: 'blob' }),
    translateMinutes: (id: string, targetLanguage: string) => api.post(`/meetings/${id}/minutes/translate`, { target_language: targetLanguage }),

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
    detachFromSeries: (id: string) => api.patch(`/meetings/${id}/detach-from-series`),
};

export const actionItems = {
    list: (params?: { twg_id?: string; mine_only?: boolean; status?: string }) =>
        api.get('/action-items/', { params }),
    summary: (params?: { twg_id?: string }) =>
        api.get('/action-items/summary', { params }),
    create: (data: any) => api.post('/action-items/', data),
    update: (id: string, data: any) => api.patch(`/action-items/${id}`, data),
    delete: (id: string) => api.delete(`/action-items/${id}`),
};


export const twgs = {
    list: (skip = 0, limit = 100) => api.get(`/twgs/?skip=${skip}&limit=${limit}`),
    dropdown: () => api.get(`/twgs/dropdown`),
    get: (id: string) => api.get(`/twgs/${id}`),
    update: (id: string, data: any) => api.patch(`/twgs/${id}`, data),
    listMembers: (twgId: string) => api.get(`/twgs/${twgId}/members`),
    addMember: (twgId: string, email: string, fullName?: string) => api.post(`/twgs/${twgId}/members`, { email, full_name: fullName || '' }),
    bulkAddMembers: (twgId: string, members: { email: string; full_name: string }[]) => api.post(`/twgs/${twgId}/members/bulk`, { members }),
    removeMember: (twgId: string, userId: string) => api.delete(`/twgs/${twgId}/members/${userId}`),
    exportMembers: (twgId: string) => api.get(`/twgs/${twgId}/members/export`, { responseType: 'blob' }),
    exportAllMembers: () => api.get(`/twgs/members/export`, { responseType: 'blob' }),
};

export const subgroups = {
    list: (twgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/`),
    create: (twgId: string, data: { name: string; description?: string; lead_id?: string }) =>
        api.post(`/twgs/${twgId}/subgroups/`, data),
    get: (twgId: string, sgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/${sgId}`),
    update: (twgId: string, sgId: string, data: { name?: string; description?: string; lead_id?: string; status?: string }) =>
        api.patch(`/twgs/${twgId}/subgroups/${sgId}`, data),
    delete: (twgId: string, sgId: string) =>
        api.delete(`/twgs/${twgId}/subgroups/${sgId}`),
    listMembers: (twgId: string, sgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/${sgId}/members`),
    addMember: (twgId: string, sgId: string, userId: string) =>
        api.post(`/twgs/${twgId}/subgroups/${sgId}/members`, { user_id: userId }),
    removeMember: (twgId: string, sgId: string, userId: string) =>
        api.delete(`/twgs/${twgId}/subgroups/${sgId}/members/${userId}`),
    listDocuments: (twgId: string, sgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/${sgId}/documents`),
};

export const auditLogs = {
    list: (skip = 0, limit = 100) => api.get(`/audit-logs/?skip=${skip}&limit=${limit}`),
};

export const sharedDocuments = {
    list: () => api.get('/shared-documents/'),
    upload: (file: File, accessControl: string = 'all_twgs', sharedWithTwgIds?: string[]) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('access_control', accessControl);
        if (sharedWithTwgIds && sharedWithTwgIds.length > 0) {
            formData.append('shared_with_twg_ids', sharedWithTwgIds.join(','));
        }
        return api.post('/shared-documents/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
    addLink: (driveUrl: string, accessControl: string = 'all_twgs', sharedWithTwgIds?: string[]) => {
        const formData = new FormData();
        formData.append('drive_url', driveUrl);
        formData.append('access_control', accessControl);
        if (sharedWithTwgIds && sharedWithTwgIds.length > 0) {
            formData.append('shared_with_twg_ids', sharedWithTwgIds.join(','));
        }
        return api.post('/shared-documents/add-link', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
    setPermissions: (fileId: string, emails: string, permissionRole: string = 'viewer') => {
        const formData = new FormData();
        formData.append('file_id', fileId);
        formData.append('emails', emails);
        formData.append('permission_role', permissionRole);
        return api.post('/shared-documents/set-permissions', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
    delete: (fileId: string) => api.delete(`/shared-documents/${fileId}`),
    cleanupOrphans: () => api.delete('/shared-documents/cleanup-orphans'),
};

export const recurringMeetings = {
    list: (params?: { twg_id?: string; status?: string; skip?: number; limit?: number }) => {
        const queryParams = new URLSearchParams();
        if (params?.twg_id) queryParams.append('twg_id', params.twg_id);
        if (params?.status) queryParams.append('status', params.status);
        if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
        if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
        const query = queryParams.toString();
        return api.get(`/recurring-meetings/${query ? `?${query}` : ''}`);
    },

    get: (id: string) => api.get(`/recurring-meetings/${id}`),

    create: (data: {
        twg_id: string;
        title_template: string;
        duration_minutes?: number;
        location?: string;
        meeting_type?: string;
        recurrence_rule: {
            frequency: 'weekly' | 'biweekly' | 'monthly';
            interval_weeks?: number;
            day_of_week?: number | null;
        };
        recurrence_end: {
            end_type: 'after_date' | 'after_occurrences' | 'never';
            end_date?: string | null;
            max_occurrences?: number | null;
        };
        start_date: string;
        start_time: string;
    }) => api.post('/recurring-meetings/', data),

    update: (id: string, data: {
        title_template?: string;
        duration_minutes?: number;
        location?: string;
        meeting_type?: string;
        recurrence_rule?: {
            frequency: 'weekly' | 'biweekly' | 'monthly';
            interval_weeks?: number;
            day_of_week?: number | null;
        };
        recurrence_end?: {
            end_type: 'after_date' | 'after_occurrences' | 'never';
            end_date?: string | null;
            max_occurrences?: number | null;
        };
        start_time?: string;
        status?: 'active' | 'paused' | 'ended' | 'cancelled';
        update_scope?: 'future' | 'all';
    }) => api.patch(`/recurring-meetings/${id}`, data),

    delete: (id: string, cancelFuture: boolean = true) =>
        api.delete(`/recurring-meetings/${id}?cancel_future=${cancelFuture}`),

    preview: (data: {
        twg_id: string;
        title_template: string;
        duration_minutes?: number;
        location?: string;
        meeting_type?: string;
        recurrence_rule: {
            frequency: 'weekly' | 'biweekly' | 'monthly';
            interval_weeks?: number;
            day_of_week?: number | null;
        };
        recurrence_end: {
            end_type: 'after_date' | 'after_occurrences' | 'never';
            end_date?: string | null;
            max_occurrences?: number | null;
        };
        start_date: string;
        start_time: string;
    }) => api.post('/recurring-meetings/preview', data),

    pause: (id: string) => api.post(`/recurring-meetings/${id}/pause`),

    resume: (id: string) => api.post(`/recurring-meetings/${id}/resume`),
};

