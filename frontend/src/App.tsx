import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAppSelector } from './hooks/useRedux'
import { UserRole } from './types/auth'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import Dashboard from './pages/dashboard/Dashboard'
import TwgWorkspace from './pages/workspace/TwgWorkspace'
import MyWorkspaces from './pages/workspace/MyWorkspaces'
import TwgAgent from './pages/workspace/TwgAgent'
import Integrations from './pages/settings/Integrations'
import ActionTracker from './pages/actions/ActionTracker'
import KnowledgeBase from './pages/knowledge/KnowledgeBase'
import DealPipeline from './pages/resource/DealPipeline'
import UserProfile from './pages/profile/UserProfile'
import AgentAssistant from './pages/assistant/AgentAssistant'
import SummitSchedule from './pages/schedule/SummitSchedule'
import DocumentLibrary from './pages/documents/DocumentLibrary'
import NotificationCenter from './pages/notifications/NotificationCenter'
import Settings from './pages/settings/Settings'
import DashboardLayout from './layouts/DashboardLayout'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
    const theme = useAppSelector((state) => state.theme.mode)

    useEffect(() => {
        // Apply theme class to html element
        if (theme === 'dark') {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    }, [theme])

    return (
        <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

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
            <Route path="/" element={
                <ProtectedRoute>
                    <DashboardLayout />
                </ProtectedRoute>
            }>
                <Route path="my-twgs" element={<MyWorkspaces />} />
                <Route path="workspace/:id" element={<TwgWorkspace />} />
                <Route path="schedule" element={<SummitSchedule />} />
                <Route path="knowledge-base" element={<KnowledgeBase />} />
                <Route path="deal-pipeline" element={
                    <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.FACILITATOR, UserRole.SECRETARIAT_LEAD]}>
                        <DealPipeline />
                    </ProtectedRoute>
                } />
                <Route path="actions" element={<ActionTracker />} />
                <Route path="profile" element={<UserProfile />} />
                <Route path="assistant" element={<AgentAssistant />} />
            </Route>
        </Routes>
    )
}

export default App

