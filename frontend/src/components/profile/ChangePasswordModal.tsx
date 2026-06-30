import React, { useState } from 'react'
import { authService } from '../../services/auth'
import { Button, Input } from '../ui'

interface ChangePasswordModalProps {
    isOpen: boolean
    onClose: () => void
}

const ChangePasswordModal: React.FC<ChangePasswordModalProps> = ({ isOpen, onClose }) => {
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    if (!isOpen) return null

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)

        if (newPassword !== confirmPassword) {
            setError('New passwords do not match')
            return
        }

        if (newPassword.length < 8) {
            setError('New password must be at least 8 characters long')
            return
        }

        setIsLoading(true)
        try {
            await authService.changePassword(currentPassword, newPassword)
            setSuccess(true)
            setTimeout(() => {
                onClose()
                // Reset state
                setCurrentPassword('')
                setNewPassword('')
                setConfirmPassword('')
                setSuccess(false)
            }, 2000)
        } catch (err: any) {
            const detail = err.response?.data?.detail
            let errorMessage = 'Failed to change password. Please check your current password.'

            if (typeof detail === 'string') {
                errorMessage = detail
            } else if (Array.isArray(detail)) {
                // Handle Pydantic validation error array
                errorMessage = detail.map((e: any) => e.msg).join('. ')
            } else if (typeof detail === 'object' && detail !== null) {
                // Fallback for other object types
                errorMessage = JSON.stringify(detail)
            }

            setError(errorMessage)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            <div className="relative bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl shadow-2xl max-w-md w-full overflow-hidden">
                <div className="px-6 py-5 border-b border-[#e7ebf3] dark:border-[#2d3748] flex items-center justify-between">
                    <h2 className="text-xl font-bold text-[#0d121b] dark:text-white">Change Password</h2>
                    <button
                        onClick={onClose}
                        className="clickable-scale p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        <span className="material-symbols-outlined text-[#4c669a]">close</span>
                    </button>
                </div>

                <div className="p-6">
                    {success ? (
                        <div className="flex flex-col items-center py-6 text-center">
                            <div className="size-16 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 mb-4">
                                <span className="material-symbols-outlined text-[32px]">check_circle</span>
                            </div>
                            <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">Password Changed!</h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mt-1">
                                Your password has been updated successfully. Closing...
                            </p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {error && (
                                <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 p-3 rounded-lg text-sm">
                                    {error}
                                </div>
                            )}

                            <Input
                                label="Current Password"
                                type="password"
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />

                            <Input
                                label="New Password"
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />

                            <Input
                                label="Confirm New Password"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />

                            <div className="pt-2 flex gap-3">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="clickable-scale flex-1 px-4 py-2 border border-[#e7ebf3] dark:border-[#4a5568] text-sm font-bold rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                >
                                    Cancel
                                </button>
                                <Button
                                    type="submit"
                                    isLoading={isLoading}
                                    className="clickable-scale flex-1 py-2 bg-[var(--accent)] text-white text-sm font-bold rounded-lg hover:bg-teal-700 shadow-sm"
                                >
                                    Update Password
                                </Button>
                            </div>
                        </form>
                    )}
                </div>
            </div>
        </div>
    )
}

export default ChangePasswordModal
