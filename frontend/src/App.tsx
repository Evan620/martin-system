import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from './hooks/useRedux'
import { UserRole } from './types/auth'
import { hydrateUser, setError, setInitialCheckDone } from './store/slices/authSlice'
import { authService } from './services/auth'
import Login from './pages/auth/Login'

import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import ModernLayout from './layouts/ModernLayout'
import Dashboard from './pages/dashboard/Dashboard'
import TwgWorkspace from './pages/workspace/TwgWorkspace'
import TwgAgent from './pages/workspace/TwgAgent'
import ActionTracker from './pages/actions/ActionTracker'
import KnowledgeBase from './pages/knowledge/KnowledgeBase'
import DealPipeline from './pages/DealPipeline'
import Incubation from './pages/Incubation'
import NewProject from './pages/NewProject'
import EditProject from './pages/EditProject'
import ProjectDetails from './pages/ProjectDetails'
import ProjectMemo from './pages/ProjectMemo'
import UserProfile from './pages/profile/UserProfile'
import AgentAssistant from './pages/assistant/AgentAssistant'
import SummitSchedule from './pages/schedule/SummitSchedule'
import MeetingDetail from './pages/schedule/MeetingDetail'
import LiveMeeting from './pages/schedule/LiveMeeting'
import ActiveMeetingRedirect from './pages/schedule/ActiveMeetingRedirect'
import DocumentLibrary from './pages/documents/DocumentLibrary'
import NotificationCenter from './pages/notifications/NotificationCenter'
import TeamManagement from './pages/admin/TeamManagement'
import ControlTower from './pages/admin/ControlTower'
import AuditLogs from './pages/admin/AuditLogs'
import OrganizationInvitations from './pages/admin/OrganizationInvitations'
import ProjectConflicts from './pages/Conflicts/ProjectConflicts'
import ProtectedRoute from './components/ProtectedRoute'
import PublicInvitationRespond from './pages/public/PublicInvitationRespond'
import BuyerDatabase from './pages/BuyerDatabase'

function HomeRedirect() {
    const user = useAppSelector((state) => state.auth.user)

    // Admin approval disabled - all users are active

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
                    // Clear invalid token
                    localStorage.removeItem('token')
                    dispatch(setError('Session expired. Please log in again.'))
                    dispatch(setInitialCheckDone(true))
                }
            } else {
                dispatch(setInitialCheckDone(true))
            }
        }

        initializeAuth()
    }, [dispatch, token, user])

    useEffect(() => {
        document.documentElement.classList.toggle('dark', theme === 'dark')
    }, [theme])

    if (!initialCheckDone && token && !user) {
        return (
            <div className="h-screen w-screen flex items-center justify-center bg-white">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-primary font-medium">Restoring session...</p>
                </div>
            </div>
        )
    }

    return (
        <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/invitations/:invitationId/respond" element={<PublicInvitationRespond />} />

            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            {/* Pending approval route removed - admin approval disabled */}

            {/* Home Redirect */}
            <Route path="/" element={<HomeRedirect />} />

            {/* Protected routes wrapped in Layout */}
            <Route element={
                <ProtectedRoute>
                    <ModernLayout />
                </ProtectedRoute>
            }>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/twgs" element={<TwgAgent />} />
                <Route path="/twgs/:id" element={<TwgAgent />} />
                <Route path="/workspace/:id" element={<TwgWorkspace />} />
                <Route path="/documents" element={<DocumentLibrary />} />
                <Route path="/notifications" element={<NotificationCenter />} />
                <Route path="/profile" element={<UserProfile />} />
                <Route path="/schedule" element={<SummitSchedule />} />
                <Route path="/meetings/:id" element={<MeetingDetail />} />
                <Route path="/meetings/:id/live" element={<LiveMeeting />} />
                <Route path="/meetings/active/live" element={<ActiveMeetingRedirect />} />
                <Route path="/knowledge-base" element={<KnowledgeBase />} />
                <Route path="/conflicts" element={<ProjectConflicts />} />
                <Route path="/deal-pipeline" element={<DealPipeline />} />
                <Route path="/deal-pipeline/incubation" element={<Incubation />} />
                <Route path="/deal-pipeline/new" element={<NewProject />} />
                <Route path="/deal-pipeline/buyers" element={<BuyerDatabase />} />
                <Route path="/deal-pipeline/:projectId/edit" element={<EditProject />} />
                <Route path="/deal-pipeline/:projectId" element={<ProjectDetails />} />
                <Route path="/deal-pipeline/:projectId/memo" element={<ProjectMemo />} />
                <Route path="/actions" element={<ActionTracker />} />
                <Route path="/assistant" element={<AgentAssistant />} />

                {/* Admin Routes */}
                <Route path="/admin/team" element={
                    <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]}>
                        <TeamManagement />
                    </ProtectedRoute>
                } />
                <Route path="/admin/control-tower" element={
                    <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]}>
                        <ControlTower />
                    </ProtectedRoute>
                } />
                <Route path="/admin/logs" element={
                    <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]}>
                        <AuditLogs />
                    </ProtectedRoute>
                } />
                <Route path="/admin/invitations" element={
                    <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]}>
                        <OrganizationInvitations />
                    </ProtectedRoute>
                } />
            </Route>
            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
    )
}

export default App
