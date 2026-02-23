export enum UserRole {
    ADMIN = 'ADMIN',
    FACILITATOR = 'TWG_FACILITATOR',
    MEMBER = 'TWG_MEMBER',
    SECRETARIAT_LEAD = 'SECRETARIAT_LEAD'
}

export interface User {
    id: string;
    email: string;
    full_name: string;
    role: UserRole;
    organization?: string;
    is_active: boolean;
    assigned_twg_id?: string;
    twg_ids: string[];
    twgs?: Array<{
        id: string;
        name: string;
    }>;
    avatar?: string;
    invite_sent_at?: string;
    invite_accepted_at?: string;
    password_reset_at?: string;
    last_login?: string;
    created_at?: string;
}

export interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    loading: boolean;
    error: string | null;
    initialCheckDone: boolean;
}

export interface UserRegister {
    email: string;
    password: string;
    full_name: string;
    role?: UserRole;
    organization?: string;
}

export interface UserLogin {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface UserWithToken extends LoginResponse {
    user: User;
}
