
import api from './api';
import {
    Project, ProjectStatus, PipelineStats,
    ProjectIngestDTO, InvestorMatch, UpdateMatchStatusDTO,
    Investor,
    Buyer, BuyerMatch, UpdateBuyerMatchStatusDTO,
    DFIMatch, DFIWindow, UpdateDFIMatchStatusDTO, FinancingMemo,
    IncubationChecklist,
    ProjectGeospatial, ScoutedCoordinates, ImpactLogEntry, ImpactLogEntryCreate, ImpactSummary,
} from '../types/pipeline';

export const pipelineService = {
    // Pipeline Views
    listProjects: async (stage?: ProjectStatus, pillar?: string, value_chain_stage?: string, include_archived?: boolean): Promise<Project[]> => {
        const params = new URLSearchParams();
        if (stage) params.append('stage', stage);
        if (pillar) params.append('pillar', pillar);
        if (value_chain_stage) params.append('value_chain_stage', value_chain_stage);
        if (include_archived) params.append('include_archived', 'true');

        const response = await api.get(`/pipeline/?${params.toString()}`);
        return response.data;
    },

    // R5 — Incubation Track
    getIncubationChecklist: async (projectId: string): Promise<IncubationChecklist> => {
        const response = await api.get(`/pipeline/${projectId}/incubation-checklist`);
        return response.data;
    },

    downloadFinancialModelTemplate: async (): Promise<Blob> => {
        const response = await api.get('/pipeline/templates/financial-model', {
            responseType: 'blob',
        });
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

    // Buyer / Offtake Matching
    getBuyerMatches: async (projectId: string): Promise<BuyerMatch[]> => {
        const response = await api.get(`/pipeline/${projectId}/buyer-matches`);
        return response.data;
    },

    triggerBuyerMatching: async (projectId: string): Promise<any> => {
        const response = await api.post(`/pipeline/${projectId}/buyer-match`);
        return response.data;
    },

    updateBuyerMatchStatus: async (matchId: string, data: UpdateBuyerMatchStatusDTO): Promise<any> => {
        const response = await api.patch(`/pipeline/buyer-matches/${matchId}`, data);
        return response.data;
    },

    listBuyers: async (): Promise<Buyer[]> => {
        const response = await api.get('/pipeline/buyers/');
        return response.data;
    },

    createBuyer: async (data: Omit<Buyer, 'id'>): Promise<Buyer> => {
        const response = await api.post('/pipeline/buyers/', data);
        return response.data;
    },

    // Investor database
    listInvestors: async (): Promise<Investor[]> => {
        const response = await api.get('/pipeline/investors/');
        return response.data;
    },

    createInvestor: async (data: Omit<Investor, 'id'>): Promise<Investor> => {
        const response = await api.post('/pipeline/investors/', data);
        return response.data;
    },

    // DFI / Blended Finance
    getDFIMatches: async (projectId: string): Promise<DFIMatch[]> => {
        const response = await api.get(`/pipeline/${projectId}/dfi-matches`);
        return response.data;
    },

    triggerDFIMatching: async (projectId: string): Promise<any> => {
        const response = await api.post(`/pipeline/${projectId}/dfi-match`);
        return response.data;
    },

    updateDFIMatchStatus: async (matchId: string, data: UpdateDFIMatchStatusDTO): Promise<any> => {
        const response = await api.patch(`/pipeline/dfi-matches/${matchId}`, data);
        return response.data;
    },

    getFinancingMemo: async (projectId: string): Promise<FinancingMemo> => {
        const response = await api.post(`/pipeline/${projectId}/financing-memo`);
        return response.data;
    },

    listDFIWindows: async (): Promise<DFIWindow[]> => {
        const response = await api.get('/pipeline/dfi-windows');
        return response.data;
    },

    createDFIWindow: async (data: Omit<DFIWindow, 'id'>): Promise<DFIWindow> => {
        const response = await api.post('/pipeline/dfi-windows', data);
        return response.data;
    },

    updateDFIWindow: async (id: string, data: Partial<Omit<DFIWindow, 'id'>>): Promise<DFIWindow> => {
        const response = await api.patch(`/pipeline/dfi-windows/${id}`, data);
        return response.data;
    },

    // R8 — Geospatial site analysis
    analyseSite: async (projectId: string, force?: boolean): Promise<ProjectGeospatial> => {
        const url = force ? `/pipeline/${projectId}/analyse-site?force=true` : `/pipeline/${projectId}/analyse-site`;
        const response = await api.post(url);
        return response.data;
    },
    scoutCoordinates: async (projectId: string): Promise<ScoutedCoordinates> => {
        const response = await api.post(`/pipeline/${projectId}/scout-coordinates`);
        return response.data;
    },
    getSiteAnalysis: async (projectId: string): Promise<ProjectGeospatial | null> => {
        try {
            const response = await api.get(`/pipeline/${projectId}/site-analysis`);
            return response.data;
        } catch (e: any) {
            if (e?.response?.status === 404) return null;
            throw e;
        }
    },

    // R9 — Post-commitment impact monitoring
    listImpactLogEntries: async (projectId: string): Promise<ImpactLogEntry[]> => {
        const response = await api.get(`/pipeline/${projectId}/impact-log`);
        return response.data;
    },
    createImpactLogEntry: async (projectId: string, payload: ImpactLogEntryCreate): Promise<ImpactLogEntry> => {
        const response = await api.post(`/pipeline/${projectId}/impact-log`, payload);
        return response.data;
    },
    getImpactSummary: async (projectId: string): Promise<ImpactSummary> => {
        const response = await api.get(`/pipeline/${projectId}/impact-log/summary`);
        return response.data;
    },
    deleteImpactLogEntry: async (projectId: string, entryId: string): Promise<void> => {
        await api.delete(`/pipeline/${projectId}/impact-log/${entryId}`);
    },
};
