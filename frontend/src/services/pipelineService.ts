
import api from './api';
import {
    Project, ProjectStatus, PipelineStats,
    ProjectIngestDTO, InvestorMatch, UpdateMatchStatusDTO
} from '../types/pipeline';

export const pipelineService = {
    // Pipeline Views
    listProjects: async (stage?: ProjectStatus, pillar?: string): Promise<Project[]> => {
        const params = new URLSearchParams();
        if (stage) params.append('stage', stage);
        if (pillar) params.append('pillar', pillar);

        const response = await api.get(`/pipeline/?${params.toString()}`);
        return response.data;
    },

    getProject: async (id: string): Promise<Project> => {
        const response = await api.get(`/pipeline/${id}`);
        return response.data;
    },

    getScoreDetails: async (id: string): Promise<any[]> => {
        const response = await api.get(`/pipeline/${id}/score-details`);
        return response.data;
    },

    toggleFlagship: async (id: string, isFlagship: boolean): Promise<any> => {
        const response = await api.post(`/pipeline/${id}/feature?is_flagship=${isFlagship}`);
        return response.data;
    },

    getStats: async (): Promise<PipelineStats> => {
        const response = await api.get('/pipeline/dashboard/stats');
        return response.data;
    },

    // Actions
    ingestProject: async (data: ProjectIngestDTO): Promise<Project> => {
        const response = await api.post('/pipeline/ingest', data);
        return response.data;
    },

    updateProject: async (id: string, data: any): Promise<Project> => {
        const response = await api.patch(`/pipeline/${id}`, data);
        return response.data;
    },

    advanceStage: async (id: string, newStage: ProjectStatus, notes?: string): Promise<Project> => {
        const response = await api.post(`/pipeline/${id}/advance`, { new_stage: newStage, notes });
        return response.data;
    },

    // Investor Matching
    getMatches: async (projectId: string): Promise<InvestorMatch[]> => {
        const response = await api.get(`/pipeline/${projectId}/matches`);
        return response.data;
    },

    triggerMatching: async (projectId: string): Promise<any> => {
        const response = await api.post(`/pipeline/${projectId}/match`);
        return response.data;
    },

    updateMatchStatus: async (matchId: string, data: UpdateMatchStatusDTO): Promise<any> => {
        const response = await api.patch(`/pipeline/matches/${matchId}`, data);
        return response.data;
    },

    importFromExcel: async (file: File, twgId: string): Promise<any> => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('twg_id', twgId);
        const response = await api.post('/pipeline/import-excel', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    getScoringCriteria: async (): Promise<any[]> => {
        const response = await api.get('/pipeline/scoring-criteria');
        return response.data;
    },

    updateCriterionWeight: async (criterionId: string, weight: number): Promise<any> => {
        const response = await api.patch(`/pipeline/scoring-criteria/${criterionId}`, { weight });
        return response.data;
    },
};
