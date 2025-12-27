import api from './api';

export interface TWG {
    id: string;
    name: string;
    description: string;
    status: string;
    facilitator_id?: string;
}

export const twgService = {
    listTWGs: async (): Promise<TWG[]> => {
        const response = await api.get<TWG[]>('/twgs/');
        return response.data;
    },

    getTWG: async (id: string): Promise<TWG> => {
        const response = await api.get<TWG>(`/twgs/${id}`);
        return response.data;
    }
};

export default twgService;
