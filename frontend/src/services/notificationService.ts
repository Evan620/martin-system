import api from './api';

export enum NotificationType {
    INFO = "info",
    SUCCESS = "success",
    WARNING = "warning",
    ALERT = "alert",
    MESSAGE = "message",
    DOCUMENT = "document",
    TASK = "task"
}

export interface Notification {
    id: string;
    user_id: string;
    type: NotificationType;
    title: string;
    content: string;
    link?: string;
    is_read: boolean;
    created_at: string;
}

export const getNotifications = async (skip: number = 0, limit: number = 50): Promise<Notification[]> => {
    const response = await api.get(`/notifications/?skip=${skip}&limit=${limit}`);
    return response.data;
};

export const markAsRead = async (notificationId: string): Promise<Notification> => {
    const response = await api.patch(`/notifications/${notificationId}/read`);
    return response.data;
};

export const markAllAsRead = async (): Promise<{ status: string; message: string }> => {
    const response = await api.post('/notifications/read-all');
    return response.data;
};

export const deleteNotification = async (notificationId: string): Promise<void> => {
    await api.delete(`/notifications/${notificationId}`);
};
