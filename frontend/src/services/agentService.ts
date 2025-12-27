import api from './api';

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
};
