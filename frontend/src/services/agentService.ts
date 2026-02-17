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
    // LangGraph HITL interrupt fields (optional)
    interrupted?: boolean;
    interrupt_payload?: {
        type: string;
        request_id: string;
        draft: any;
        message: string;
    };
    thread_id?: string;
    suggestions?: string[];
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
        console.log('[AGENT_SERVICE] Raw response.data:', response.data);
        console.log('[AGENT_SERVICE] interrupted?', response.data.interrupted, 'payload?', !!response.data.interrupt_payload);
        return response.data;
    },

    // Streaming chat
    chatStream: async (
        chatRequest: AgentChatRequest,
        callbacks: {
            onStep?: (step: any) => void;
            onThinking?: (status: string) => void;
            onResponse?: (response: any) => void;
            onInterrupt?: (payload: any) => void;
            onError?: (error: any) => void;
            onDone?: () => void;
        }
    ): Promise<void> => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${api.defaults.baseURL}/agents/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(chatRequest)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            if (!response.body) throw new Error('ReadableStream not supported in this browser.');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            console.log('[STREAM]', data);

                            // Map events to structured steps
                            if (callbacks.onStep) {
                                let stepType = 'thinking';
                                let icon = 'smart_toy';
                                let label = data.status;

                                if (data.type === 'agent_routing') {
                                    stepType = 'routing';
                                    icon = 'alt_route';
                                    label = data.status;
                                } else if (data.type === 'tool_start') {
                                    stepType = 'tool';
                                    icon = data.tool === 'knowledge_search' ? 'search'
                                        : data.tool === 'email_send' ? 'mail'
                                            : data.tool === 'scheduler' ? 'calendar_month'
                                                : 'build';
                                    label = data.status;
                                } else if (data.type === 'thinking') {
                                    // Detect specific thinking phases from backend
                                    if (data.status.includes('Routing')) icon = 'alt_route';
                                    else if (data.status.includes('Synthesizing')) icon = 'auto_awesome';
                                    else if (data.status.includes('Supervisor')) icon = 'admin_panel_settings';
                                }

                                if (data.type !== 'response' && data.type !== 'done' && data.type !== 'error' && data.type !== 'interrupt') {
                                    callbacks.onStep({
                                        type: stepType,
                                        label: label,
                                        icon: data.icon || icon, // specific icon from backend wins
                                        image: data.image,
                                        status: 'active',
                                        id: data.step_id || Date.now().toString()
                                    });
                                }
                            }

                            if (data.type === 'thinking' || data.type === 'agent_routing' || data.type === 'tool_start') {
                                callbacks.onThinking?.(data.status);
                            } else if (data.type === 'response') {
                                callbacks.onResponse?.(data.message);
                            } else if (data.type === 'interrupt') {
                                callbacks.onInterrupt?.(data.payload);
                            } else if (data.type === 'done') {
                                callbacks.onDone?.();
                            } else if (data.type === 'error') {
                                callbacks.onError?.(data.error);
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e, line);
                        }
                    }
                }
            }
        } catch (err) {
            console.error('[STREAM] Connection error:', err);
            callbacks.onError?.(err);
        }
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

    // Document approval
    approveDocument: async (requestId: string, approvalData: any): Promise<any> => {
        const response = await api.post(`/agents/document/approval/${requestId}/approve`, approvalData);
        return response.data;
    },
};
