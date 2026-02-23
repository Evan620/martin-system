import api from './api';

export type OrganizationInvitationStatus = 'pending' | 'accepted' | 'declined' | 'expired';

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

export const organizationInvitationService = {
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

    async createInvitation(data: OrganizationInvitationCreate) {
        const response = await api.post<OrganizationInvitation>('/organization-invitations/', {
            ...data,
            send_email: data.send_email ?? true
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

    async respondToInvitation(invitationId: string, response: 'accept' | 'decline') {
        const res = await api.post<InvitationRespondResponse>(
            `/organization-invitations/${invitationId}/respond`,
            { response }
        );
        return res.data;
    }
};
