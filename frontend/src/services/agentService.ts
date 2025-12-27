import api from './api';
import {
    EnhancedChatRequest,
    EnhancedChatResponse,
    AgentSuggestion
} from '../types/agent';

export interface AgentChatRequest {
    message: string;
    conversation_id?: string;
    twg_id?: string;
}

export interface Citation {
    source: string;
    page: number;
    relevance: number;
}

export interface AgentChatResponse {
    response: string;
    conversation_id: string;
    citations: Citation[];
    agent_id: string;
}

export interface AgentTaskRequest {
    task_type: string;
    twg_id: string;
    details: Record<string, any>;
    title: string;
}

export interface AgentStatus {
    status: string;
    swarm_ready: boolean;
    active_agents: string[];
    version: string;
}

export const agentService = {
    // Chat with the agent
    chat: async (chatRequest: AgentChatRequest): Promise<AgentChatResponse> => {
        const response = await api.post<AgentChatResponse>('/agents/chat', chatRequest);
        return response.data;
    },

    // Assign a task to the agent
    assignTask: async (taskRequest: AgentTaskRequest): Promise<{ task_id: string; status: string; message: string }> => {
        const response = await api.post('/agents/task', taskRequest);
        return response.data;
    },

    // Get agent swarm status
    getStatus: async (): Promise<AgentStatus> => {
        const response = await api.get<AgentStatus>('/agents/status');
        return response.data;
    },

    // Enhanced chat methods (Phase 1)

    // Enhanced chat with rich message support
    chatEnhanced: async (chatRequest: EnhancedChatRequest): Promise<EnhancedChatResponse> => {
        const response = await api.post<EnhancedChatResponse>('/agents/chat/enhanced', chatRequest);
        return response.data;
    },

    // Get proactive suggestions (Phase 3 - placeholder for now)
    getSuggestions: async (_conversationId?: string): Promise<{ suggestions: AgentSuggestion[] }> => {
        // TODO: Implement in Phase 3
        // const params = conversationId ? { conversation_id: conversationId } : {};
        // const response = await api.get('/agents/suggestions', { params });
        // return response.data;
        return { suggestions: [] };
    },

    // Accept a suggestion (Phase 3 - placeholder for now)
    acceptSuggestion: async (_suggestionId: string): Promise<{ status: string; result_message: any }> => {
        // TODO: Implement in Phase 3
        // const response = await api.post(`/agents/suggestions/${suggestionId}/accept`);
        // return response.data;
        return { status: 'accepted', result_message: null };
    },

    // Dismiss a suggestion (Phase 3 - placeholder for now)
    dismissSuggestion: async (_suggestionId: string): Promise<{ status: string }> => {
        // TODO: Implement in Phase 3
        // const response = await api.post(`/agents/suggestions/${suggestionId}/dismiss`);
        // return response.data;
        return { status: 'dismissed' };
    },

    // Email approval methods (Human-in-the-Loop)

    // Get pending email approvals
    getPendingApprovals: async (): Promise<any> => {
        const response = await api.get('/agents/email/pending-approvals');
        return response.data;
    },

    // Get a specific email approval request
    getEmailApproval: async (requestId: string): Promise<any> => {
        const response = await api.get(`/agents/email/approval/${requestId}`);
        return response.data;
    },

    // Approve an email
    approveEmail: async (requestId: string, approvalData: any): Promise<any> => {
        const response = await api.post(`/agents/email/approval/${requestId}/approve`, approvalData);
        return response.data;
    },

    // Decline an email
    declineEmail: async (requestId: string, reason?: string): Promise<any> => {
        const response = await api.post(`/agents/email/approval/${requestId}/decline`, { reason });
        return response.data;
    },
};
