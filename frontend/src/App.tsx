import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from './hooks/useRedux'
import { UserRole } from './types/auth'
import { hydrateUser, setError, setInitialCheckDone } from './store/slices/authSlice'
import { authService } from './services/auth'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import Dashboard from './pages/dashboard/Dashboard'
import CommandCenter from './pages/dashboard/CommandCenter'
import TwgWorkspace from './pages/workspace/TwgWorkspace'
import MyWorkspaces from './pages/workspace/MyWorkspaces'
import TwgAgent from './pages/workspace/TwgAgent'
import Settings from './pages/settings/Settings'
import ActionTracker from './pages/actions/ActionTracker'
import KnowledgeBase from './pages/knowledge/KnowledgeBase'
import DealPipeline from './pages/workspace/DealPipeline'
import ProjectDetails from './pages/workspace/ProjectDetails'
import ProjectMemo from './pages/workspace/ProjectMemo'
import UserProfile from './pages/profile/UserProfile'
import AgentAssistant from './pages/assistant/AgentAssistant'
import SummitSchedule from './pages/schedule/SummitSchedule'
import DocumentLibrary from './pages/documents/DocumentLibrary'
import NotificationCenter from './pages/notifications/NotificationCenter'
import TeamManagement from './pages/admin/TeamManagement'
import PendingApproval from './pages/auth/PendingApproval'
import DashboardLayout from './layouts/DashboardLayout'
import ProtectedRoute from './components/ProtectedRoute'

function HomeRedirect() {
    const user = useAppSelector((state) => state.auth.user)

    if (!user?.is_active) {
        return <Navigate to="/pending-approval" replace />
    }

    if (user?.role === UserRole.FACILITATOR || user?.role === UserRole.MEMBER) {
        return <Navigate to="/workspace/energy-twg" replace />
    }

    return <Navigate to="/dashboard" replace />
}

function App() {
    const theme = useAppSelector((state) => state.theme.mode)
    const { token, user, initialCheckDone } = useAppSelector((state) => state.auth)
    const dispatch = useAppDispatch()

    useEffect(() => {
        const initializeAuth = async () => {
            if (token && !user) {
                try {
                    const userData = await authService.getCurrentUser()
                    dispatch(hydrateUser(userData))
                } catch (err) {
                    console.error('Failed to hydrate user session', err)
                    dispatch(setError('Session expired. Please log in again.'))
                }
            } else {
                dispatch(setInitialCheckDone(true))
            }
        }

        initializeAuth()
    }, [dispatch, token, user])

    useEffect(() => {
        // Apply theme class to html element
        if (theme === 'dark') {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    }, [theme])

    if (!initialCheckDone && token && !user) {
        return (
            <div className="h-screen w-screen flex items-center justify-center bg-[#020617]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-blue-200 font-medium">Restoring session...</p>
                </div>
            </div>
        )
    }

    return (
        <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/pending-approval" element={<PendingApproval />} />

            {/* Protected routes */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={
                <ProtectedRoute>
                    <Dashboard />
                </ProtectedRoute>
            } />
            <Route path="/twgs" element={
                <ProtectedRoute>
                    <TwgAgent />
                </ProtectedRoute>
            } />
            <Route path="/documents" element={
                <ProtectedRoute>
                    <DocumentLibrary />
                </ProtectedRoute>
            } />
            <Route path="/notifications" element={
                <ProtectedRoute>
                    <NotificationCenter />
                </ProtectedRoute>
            } />
            <Route path="/integrations" element={
                <ProtectedRoute allowedRoles={[UserRole.ADMIN]}>
                    <Settings />
                </ProtectedRoute>
            } />
            <Route path="/deal-pipeline" element={
                <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.FACILITATOR, UserRole.SECRETARIAT_LEAD]}>
                    <DealPipeline />
                </ProtectedRoute>
            } />
            <Route path="/deal-pipeline/:id" element={
                <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.FACILITATOR, UserRole.SECRETARIAT_LEAD]}>
                    <ProjectDetails />
                </ProtectedRoute>
            } />
            <Route path="/deal-pipeline/:id/memo" element={
                <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.FACILITATOR, UserRole.SECRETARIAT_LEAD]}>
                    <ProjectMemo />
                </ProtectedRoute>
            } />
            <Route path="/" element={
                <ProtectedRoute>
                    <DashboardLayout />
                </ProtectedRoute>
            }>
                <Route index element={<HomeRedirect />} />
                <Route path="dashboard" element={<CommandCenter />} />
                <Route path="my-twgs" element={<MyWorkspaces />} />
                <Route path="workspace/:id" element={<TwgWorkspace />} />
                <Route path="schedule" element={<SummitSchedule />} />
                <Route path="knowledge-base" element={<KnowledgeBase />} />
                <Route path="actions" element={<ActionTracker />} />
                <Route path="profile" element={<UserProfile />} />
                <Route path="assistant" element={<AgentAssistant />} />
                <Route path="notifications" element={<NotificationCenter />} />
                <Route path="admin/team" element={
                    <ProtectedRoute allowedRoles={[UserRole.ADMIN]}>
                        <TeamManagement />
                    </ProtectedRoute>
                } />
            </Route>
        </Routes>
    )
}

export default App

