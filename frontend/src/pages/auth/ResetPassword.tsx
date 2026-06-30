import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { Button, Input } from '../../components/ui'
import { authService } from '../../services/auth'

export default function ResetPassword() {
    const [searchParams] = useSearchParams()
    const token = searchParams.get('token')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [errors, setErrors] = useState<Record<string, string>>({})
    const [isLoading, setIsLoading] = useState(false)
    const [isSuccess, setIsSuccess] = useState(false)
    const navigate = useNavigate()

    const validateForm = () => {
        const newErrors: Record<string, string> = {}

        if (!password) {
            newErrors.password = 'Password is required'
        } else if (password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters'
        }

        if (password !== confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match'
        }

        setErrors(newErrors)
        return Object.keys(newErrors).length === 0
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!validateForm() || !token) {
            return
        }

        setIsLoading(true)
        setErrors({})

        try {
            await authService.resetPassword(token, password)
            setIsSuccess(true)

            // Redirect to login after 2 seconds
            setTimeout(() => {
                navigate('/login')
            }, 2000)
        } catch (err: any) {
            setErrors({
                general: err.response?.data?.detail || 'Failed to reset password. Please try again or request a new reset link.'
            })
        } finally {
            setIsLoading(false)
        }
    }

    if (!token) {
        return (
            <div className="flex h-screen bg-slate-50 text-slate-900 items-center justify-center p-8">
                <div className="w-full max-w-md space-y-8 text-center animate-blur-slide">
                    <div className="flex justify-center">
                        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold text-slate-900">Invalid Reset Link</h2>
                        <p className="text-slate-500">This password reset link is invalid or has expired.</p>
                    </div>
                    <Link
                        to="/forgot-password"
                        className="clickable-scale inline-block px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-lg"
                    >
                        Request New Link
                    </Link>
                </div>
            </div>
        )
    }

    if (isSuccess) {
        return (
            <div className="flex h-screen bg-slate-50 text-slate-900 items-center justify-center p-8">
                <div className="w-full max-w-md space-y-8 text-center animate-blur-slide">
                    <div className="flex justify-center">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold text-slate-900">Password Reset Successful!</h2>
                        <p className="text-slate-500">Your password has been updated. Redirecting to login...</p>
                    </div>
                    <div className="flex justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex h-screen bg-slate-50 text-slate-900">
            {/* Left side - Visuals */}
            <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-primary">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent"></div>

                {/* Abstract visualization */}
                <div className="absolute inset-0 flex items-center justify-center opacity-30">
                    <svg className="w-full h-full p-20" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <radialGradient id="grad4" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                                <stop offset="0%" style={{ stopColor: '#ffffff', stopOpacity: 0.6 }} />
                                <stop offset="100%" style={{ stopColor: '#ffffff', stopOpacity: 0 }} />
                            </radialGradient>
                        </defs>
                        <circle cx="100" cy="100" r="80" fill="url(#grad4)" />
                        <path d="M60 100 L90 130 L140 70" stroke="#ffffff" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </div>

                <div className="relative z-10 flex flex-col justify-end p-16 space-y-6 text-white">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center border border-white/20">
                            <span className="font-bold text-lg">W</span>
                        </div>
                        <span className="text-xl font-display font-semibold">WAIIS TWG</span>
                    </div>
                    <h1 className="text-5xl font-display font-bold leading-tight">
                        Create a New Password
                    </h1>
                    <p className="text-teal-100 text-lg max-w-lg">
                        Choose a strong password to secure your account. Make sure it's at least 8 characters long.
                    </p>
                </div>
            </div>

            {/* Right side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white">
                <div className="w-full max-w-md space-y-8 animate-blur-slide">
                    <div className="flex justify-end">
                        <div className="flex items-center gap-2 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full text-xs text-slate-500 font-medium">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            RESET PASSWORD
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold text-slate-900">Reset Password</h2>
                        <p className="text-slate-500">Enter your new password below.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-4">
                            <div>
                                <Input
                                    label="New Password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => {
                                        setPassword(e.target.value)
                                        if (errors.password) setErrors(prev => ({ ...prev, password: '' }))
                                    }}
                                    required
                                    className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:ring-primary focus:border-primary"
                                />
                                {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
                            </div>

                            <div>
                                <Input
                                    label="Confirm New Password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={confirmPassword}
                                    onChange={(e) => {
                                        setConfirmPassword(e.target.value)
                                        if (errors.confirmPassword) setErrors(prev => ({ ...prev, confirmPassword: '' }))
                                    }}
                                    required
                                    className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:ring-primary focus:border-primary"
                                />
                                {errors.confirmPassword && <p className="text-red-500 text-xs mt-1">{errors.confirmPassword}</p>}
                            </div>
                        </div>

                        {errors.general && (
                            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded text-sm">
                                {errors.general}
                            </div>
                        )}

                        <div className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-xs text-slate-500 space-y-1">
                            <p className="font-medium text-slate-700">Password requirements:</p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>At least 8 characters long</li>
                                <li>Mix of uppercase and lowercase letters (recommended)</li>
                                <li>Include numbers and special characters (recommended)</li>
                            </ul>
                        </div>

                        <Button
                            type="submit"
                            isLoading={isLoading}
                            className="clickable-scale w-full py-3 bg-primary hover:bg-teal-800 text-white font-semibold rounded-lg shadow-lg shadow-teal-200 flex items-center justify-center gap-2"
                        >
                            Reset Password
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        </Button>
                    </form>

                    <div className="text-center">
                        <Link
                            to="/login"
                            className="inline-flex items-center gap-2 text-slate-500 hover:text-teal-600 transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Login
                        </Link>
                    </div>

                    <div className="pt-8 border-t border-slate-100 text-center">
                        <p className="text-xs text-slate-400">
                            WAIIS © 2026. Authorized Personnel Only.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
