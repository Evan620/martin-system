import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { AuthState, User } from '../../types/auth'

const initialState: AuthState = {
    user: null,
    isAuthenticated: false,
    token: localStorage.getItem('token'),
    loading: false,
    error: null
}

const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        setCredentials: (state, action: PayloadAction<{ user: User; token: string }>) => {
            state.user = action.payload.user
            state.token = action.payload.token
            state.isAuthenticated = true
            state.error = null
            localStorage.setItem('token', action.payload.token)
        },
        logout: (state) => {
            state.user = null
            state.token = null
            state.isAuthenticated = false
            state.error = null
            localStorage.removeItem('token')
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.loading = action.payload
        },
        setError: (state, action: PayloadAction<string>) => {
            state.error = action.payload
            state.loading = false
        }
    },
})

export const { setCredentials, logout, setLoading, setError } = authSlice.actions
export default authSlice.reducer
