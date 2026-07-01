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

            <div
                className="relative max-w-md w-full overflow-hidden"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}
            >
                <div
                    className="px-6 py-5 flex items-center justify-between"
                    style={{ borderBottom: '1px solid var(--border)' }}
                >
                    <h2 className="text-xl font-bold" style={{ color: 'var(--ink-900)' }}>Change Password</h2>
                    <button
                        onClick={onClose}
                        className="clickable-scale p-1 rounded-lg transition-colors"
                        style={{ color: 'var(--ink-500)' }}
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                <div className="p-6">
                    {success ? (
                        <div className="flex flex-col items-center py-6 text-center">
                            <div
                                className="size-16 rounded-full flex items-center justify-center mb-4"
                                style={{ background: 'var(--accent-soft)', color: 'var(--sage)' }}
                            >
                                <span className="material-symbols-outlined text-[32px]">check_circle</span>
                            </div>
                            <h3 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>Password Changed!</h3>
                            <p className="text-sm mt-1" style={{ color: 'var(--ink-500)' }}>
                                Your password has been updated successfully. Closing...
                            </p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {error && (
                                <div
                                    className="p-3 rounded-lg text-sm"
                                    style={{ background: 'var(--surface-2)', border: '1px solid color-mix(in srgb, var(--terra) 30%, var(--border))', color: 'var(--terra)' }}
                                >
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
                                    className="clickable-scale flex-1 px-4 py-2 text-sm font-bold rounded-lg transition-colors"
                                    style={{ border: '1px solid var(--border)', color: 'var(--ink-700)', background: 'transparent' }}
                                >
                                    Cancel
                                </button>
                                <Button
                                    type="submit"
                                    isLoading={isLoading}
                                    className="clickable-scale flex-1 py-2 text-sm font-bold rounded-lg"
                                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
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
