import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAppSelector } from '../hooks/useRedux'
import { UserRole } from '../types/auth'

interface ProtectedRouteProps {
    children: ReactNode
    allowedRoles?: UserRole[]
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
    const { user, token } = useAppSelector((state) => state.auth)
    const location = useLocation()

    if (!token) {
        // Redirect to login page but save the attempted location
        return <Navigate to="/login" state={{ from: location }} replace />
    }

    if (allowedRoles && user) {
        // Check if user has any of the allowed roles
        // We cast user.role to UserRole because the string from backend should match
        if (!allowedRoles.includes(user.role as UserRole)) {
            // User authorized but not for this role -> 403 or Dashboard
            // Ideally a 403 page, but for now redirect to dashboard
            return <Navigate to="/dashboard" replace />
        }
    }

    return <>{children}</>
}
