import api from './api';

export type OrganizationInvitationStatus = 'pending' | 'accepted' | 'declined' | 'expired';
export type InvitationMessageSender = 'admin' | 'invitee';

export interface OrganizationInvitation {
    id: string;
    organization_name: string;
    contact_email: string;
    twg_id: string;
    twg_name: string | null;
    custom_message: string | null;
    status: OrganizationInvitationStatus;
    expires_at: string;
    sent_at: string | null;
    responded_at: string | null;
    created_by_id: string;
    created_by_name: string | null;
    resend_count: number;
    last_resend_at: string | null;
    created_at: string;
    unread_message_count: number;
    has_messages: boolean;
}

export interface OrganizationInvitationCreate {
    organization_name: string;
    contact_email: string;
    twg_id: string;
    custom_message?: string;
    send_email?: boolean;
}

export interface OrganizationInvitationUpdate {
    organization_name?: string;
    contact_email?: string;
    twg_id?: string;
    custom_message?: string;
}

export interface OrganizationInvitationListResponse {
    items: OrganizationInvitation[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
}

export interface ResendInvitationResponse {
    id: string;
    organization_name: string;
    contact_email: string;
    invite_sent: boolean;
    message: string;
}

export interface InvitationRespondResponse {
    id: string;
    organization_name: string;
    twg_name: string;
    status: OrganizationInvitationStatus;
    message: string;
}

export interface InvitationMessage {
    id: string;
    invitation_id: string;
    sender_type: InvitationMessageSender;
    sender_user_id: string | null;
    sender_name: string;
    content: string;
    is_read_by_admin: boolean;
    is_read_by_invitee: boolean;
    created_at: string;
    is_read: boolean;
}

export interface InvitationMessageCreate {
    content: string;
}

export interface InvitationMessageListResponse {
    items: InvitationMessage[];
    total: number;
    unread_count: number;
}

export interface PublicInvitation {
    id: string;
    organization_name: string;
    twg_name: string;
    status: OrganizationInvitationStatus;
    expires_at: string;
    custom_message: string | null;
    has_messages: boolean;
}

export const organizationInvitationService = {
    // Authenticated endpoints
    async getInvitations(params?: {
        page?: number;
        page_size?: number;
        status?: OrganizationInvitationStatus;
        twg_id?: string;
    }) {
        const response = await api.get<OrganizationInvitationListResponse>('/organization-invitations/', { params });
        return response.data;
    },

    async getInvitation(invitationId: string) {
        const response = await api.get<OrganizationInvitation>(`/organization-invitations/${invitationId}`);
        return response.data;
    },

    async createInvitation(data: OrganizationInvitationCreate, attachments: File[] = []) {
        // If no attachments, use regular JSON
        if (attachments.length === 0) {
            const response = await api.post<OrganizationInvitation>('/organization-invitations/', {
                ...data,
                send_email: data.send_email ?? true
            });
            return response.data;
        }

        // With attachments, use FormData
        const formData = new FormData();
        formData.append('organization_name', data.organization_name);
        formData.append('contact_email', data.contact_email);
        formData.append('twg_id', data.twg_id);
        if (data.custom_message) {
            formData.append('custom_message', data.custom_message);
        }
        formData.append('send_email', String(data.send_email ?? true));

        attachments.forEach((file) => {
            formData.append('attachments', file);
        });

        const response = await api.post<OrganizationInvitation>('/organization-invitations/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        return response.data;
    },

    async updateInvitation(invitationId: string, data: OrganizationInvitationUpdate) {
        const response = await api.patch<OrganizationInvitation>(
            `/organization-invitations/${invitationId}`,
            data
        );
        return response.data;
    },

    async deleteInvitation(invitationId: string) {
        await api.delete(`/organization-invitations/${invitationId}`);
    },

    async resendInvitation(invitationId: string) {
        const response = await api.post<ResendInvitationResponse>(
            `/organization-invitations/${invitationId}/resend`
        );
        return response.data;
    },

    // Authenticated message endpoints
    async getMessages(invitationId: string) {
        const response = await api.get<InvitationMessageListResponse>(
            `/organization-invitations/${invitationId}/messages`
        );
        return response.data;
    },

    async sendMessage(invitationId: string, data: InvitationMessageCreate) {
        const response = await api.post<InvitationMessage>(
            `/organization-invitations/${invitationId}/messages`,
            data
        );
        return response.data;
    },

    // Public endpoints (no auth required)
    async getPublicInvitation(invitationId: string) {
        const response = await api.get<PublicInvitation>(
            `/public/invitations/${invitationId}`
        );
        return response.data;
    },

    async getPublicMessages(invitationId: string) {
        const response = await api.get<InvitationMessageListResponse>(
            `/public/invitations/${invitationId}/messages`
        );
        return response.data;
    },

    async sendPublicMessage(invitationId: string, data: InvitationMessageCreate) {
        const response = await api.post<InvitationMessage>(
            `/public/invitations/${invitationId}/messages`,
            data
        );
        return response.data;
    },

    async respondToInvitation(invitationId: string, response: 'accept' | 'decline') {
        const res = await api.post<InvitationRespondResponse>(
            `/public/invitations/${invitationId}/respond`,
            { response }
        );
        return res.data;
    }
};
