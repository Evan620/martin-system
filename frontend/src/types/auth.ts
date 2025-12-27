export enum UserRole {
    ADMIN = 'admin',
    FACILITATOR = 'twg_facilitator',
    MEMBER = 'twg_member',
    SECRETARIAT_LEAD = 'secretariat_lead'
}

export interface User {
    id: string;
    email: string;
    full_name: string;
    role: UserRole;
    organization?: string;
    is_active: boolean;
    assigned_twg_id?: string;
    avatar?: string;
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
