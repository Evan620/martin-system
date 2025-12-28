import api from './api';
import { User, UserRole } from '../types/auth';

export interface UserUpdateData {
    full_name?: string;
    role?: UserRole;
    organization?: string;
    is_active?: boolean;
}

export const userService = {
    async getUsers(params?: { is_active?: boolean; role?: UserRole }) {
        const response = await api.get<User[]>('/users/', { params });
        return response.data;
    },

    async getUser(userId: string) {
        const response = await api.get<User>(`/users/${userId}`);
        return response.data;
    },

    async updateUser(userId: string, data: UserUpdateData) {
        const response = await api.patch<User>(`/users/${userId}`, data);
        return response.data;
    },

    async deleteUser(userId: string) {
        const response = await api.delete(`/users/${userId}`);
        return response.data;
    }
};
