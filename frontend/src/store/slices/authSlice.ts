import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { AuthState, User } from '../../types/auth'

const initialState: AuthState = {
    user: null,
    isAuthenticated: false,
    token: localStorage.getItem('token'),
    loading: false,
    error: null,
    initialCheckDone: false
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
        setToken: (state, action: PayloadAction<string>) => {
            state.token = action.payload
            localStorage.setItem('token', action.payload)
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
            state.initialCheckDone = true
        },
        hydrateUser: (state, action: PayloadAction<User>) => {
            state.user = action.payload
            state.isAuthenticated = true
            state.initialCheckDone = true
            state.loading = false
        },
        setInitialCheckDone: (state, action: PayloadAction<boolean>) => {
            state.initialCheckDone = action.payload
        }
    },
})

export const { setCredentials, setToken, logout, setLoading, setError, hydrateUser, setInitialCheckDone } = authSlice.actions
export default authSlice.reducer
