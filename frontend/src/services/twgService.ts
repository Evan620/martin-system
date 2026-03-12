import api from './api';

export interface TWG {
    id: string;
    name: string;
    description: string;
    status: string;
    group_type: string;
    facilitator_id?: string;
}

export const twgService = {
    listTWGs: async (): Promise<TWG[]> => {
        const response = await api.get<TWG[]>('/twgs/');
        return response.data;
    },

    listDropdown: async (): Promise<TWG[]> => {
        const response = await api.get<TWG[]>('/twgs/dropdown');
        return response.data;
    },

    getTWG: async (id: string): Promise<TWG> => {
        const response = await api.get<TWG>(`/twgs/${id}`);
        return response.data;
    }
};

export default twgService;
