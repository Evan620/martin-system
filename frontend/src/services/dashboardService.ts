import api from './api';

export interface DashboardStats {
    metrics: {
        active_twgs: number;
        deals_in_pipeline: number;
        pending_approvals: number;
        next_plenary: {
            date: string | null;
            title: string;
            twg?: string;
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

export interface ConflictAlert {
    id: string;
    conflict_type: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    agents_involved: string[];
    description: string;
    conflicting_positions: Record<string, string>;
    status: 'detected' | 'negotiating' | 'escalated' | 'resolved' | 'dismissed';
    resolution_log?: Array<{ action: string; user?: string; resolution: string; timestamp: string }>;
    human_action_required: boolean;
    detected_at: string;
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
    const response = await api.get('/dashboard/stats');
    return response.data;
};

export const getTimeline = async (): Promise<TimelineItem[]> => {
    const response = await api.get('/dashboard/timeline');
    return response.data;
};

export const getConflicts = async (includeHistory: boolean = false): Promise<ConflictAlert[]> => {
    const response = await api.get('/dashboard/conflicts', {
        params: { include_history: includeHistory }
    });
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

export interface ReconciliationResult {
    status: string;
    scan_time: string;
    conflicts_detected: number;
    auto_resolved: number;
    breakdown: {
        same_slot: number;
        venue: number;
        vip_double_booking: number;
        crowding: number;
        overdue_action: number;
    };
    details: Array<{
        type: string;
        severity: string;
        description: string;
        affected_meetings?: string[];
    }>;
}

export const forceReconciliation = async (): Promise<ReconciliationResult> => {
    const response = await api.post('/dashboard/force-reconciliation');
    return response.data;
};

export const generateWeeklyPacket = async (): Promise<any> => {
    const response = await api.post('/dashboard/weekly-packet');
    return response.data;
};

export const autoNegotiateConflict = async (conflictId: string, prompt?: string): Promise<any> => {
    const body = prompt ? { prompt } : undefined;
    const response = await api.post(`/dashboard/conflicts/${conflictId}/auto-negotiate`, body);
    return response.data;
};

export const approveResolution = async (conflictId: string): Promise<any> => {
    const response = await api.post(`/dashboard/conflicts/${conflictId}/approve-resolution`);
    return response.data;
};

export const dismissConflict = async (conflictId: string, resolution: string = 'Dismissed by user'): Promise<any> => {
    const response = await api.post(`/dashboard/conflicts/${conflictId}/resolve?resolution=${encodeURIComponent(resolution)}`);
    return response.data;
};

export const resolveConflictManually = async (conflictId: string, resolutionType: string, meetingId: string, newTime?: string, reason?: string): Promise<any> => {
    const response = await api.post(`/dashboard/conflicts/${conflictId}/manual-resolve`, {
        resolution_type: resolutionType,
        meeting_id: meetingId,
        new_time: newTime,
        reason: reason
    });
    return response.data;
};

export interface AutonomousLogStats {
    total_detected: number;
    auto_resolved: number;
    escalated: number;
    resolution_rate: number;
}

export interface AutonomousLogResponse {
    stats: AutonomousLogStats;
    conflicts: ConflictAlert[];
}

export const getAutonomousLog = async (days: number = 7): Promise<AutonomousLogResponse> => {
    const response = await api.get('/dashboard/conflicts/autonomous-log', {
        params: { days }
    });
    return response.data;
};
