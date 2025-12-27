import api from './api';

export interface DashboardStats {
    metrics: {
        active_twgs: number;
        deals_in_pipeline: number;
        pending_approvals: number;
        next_plenary: {
            date: string | null;
            title: string;
        };
    };
    pipeline: {
        drafting: number;
        negotiation: number;
        final_review: number;
        signed: number;
        total: number;
    };
    twg_health: Array<{
        id: string;
        name: string;
        lead: string;
        status: 'active' | 'stalled';
        completion: number;
        pillar: string;
    }>;
}

export interface TimelineItem {
    type: 'meeting' | 'deadline';
    date: string;
    title: string;
    twg: string;
    status: 'normal' | 'critical';
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
    const response = await api.get('/dashboard/stats');
    return response.data;
};

export const getTimeline = async (): Promise<TimelineItem[]> => {
    const response = await api.get('/dashboard/timeline');
    return response.data;
};

export const exportDashboardReport = async (): Promise<void> => {
    const response = await api.get('/dashboard/export', {
        responseType: 'blob'
    });

    // Create a link and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    // Get filename from header if possible, or use default
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'summit_intelligence_report.csv';
    if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/);
        if (filenameMatch.length > 1) {
            filename = filenameMatch[1];
        }
    }

    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();

    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
};
