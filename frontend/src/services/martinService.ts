import api from './api';

export interface UpcomingMeeting {
    title: string;
    twg_name: string;
    starts_at: string;
    minutes_until: number;
}

export interface ThresholdAlert {
    project_name: string;
    gap_type: 'gender' | 'youth';
    current_pct: number | null;
    required_pct: number;
}

export interface OverdueItem {
    title: string;
    days_overdue: number;
}

export interface BriefingData {
    greeting: string;
    upcoming_meetings: UpcomingMeeting[];
    threshold_alerts: ThresholdAlert[];
    overdue_items: OverdueItem[];
}

export const getBriefing = async (): Promise<BriefingData> => {
    const response = await api.get<BriefingData>('/martin/briefing');
    return response.data;
};
