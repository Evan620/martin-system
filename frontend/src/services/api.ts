import axios from 'axios';
import { store } from '../store';
import { logout } from '../store/slices/authSlice';

// Create axios instance with base URL
// In VITE, we use import.meta.env for environment variables
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for adding the auth token
api.interceptors.request.use(
    (config) => {
        const token = store.getState().auth.token;
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor for handling 401 (Unauthorized)
api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        const originalRequest = error.config;

        // If error is 401 and we haven't tried to refresh already
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            // Dispatch logout action to clear state and redirect to login
            // Ideally implementation would try to refresh token here
            store.dispatch(logout());
            return Promise.reject(error);
        }

        return Promise.reject(error);
    }
);

export default api;
