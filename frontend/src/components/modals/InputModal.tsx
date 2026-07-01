import React, { useState, useEffect } from 'react'

interface InputModalProps {
    isOpen: boolean
    title: string
    description: string
    placeholder?: string
    confirmText?: string
    confirmVariant?: 'primary' | 'danger' | 'warning'
    icon?: string
    isLoading?: boolean
    onConfirm: (value: string) => void
    onCancel: () => void
}

const InputModal: React.FC<InputModalProps> = ({
    isOpen,
    title,
    description,
    placeholder = "Enter details...",
    confirmText = "Confirm",
    confirmVariant = 'primary',
    icon = '✏️',
    isLoading = false,
    onConfirm,
    onCancel
}) => {
    const [value, setValue] = useState('')

    // Reset value when modal opens
    useEffect(() => {
        if (isOpen) setValue('')
    }, [isOpen])

    if (!isOpen) return null

    const handleConfirm = () => {
        if (isLoading) return
        onConfirm(value)
        // Do NOT reset value immediately, wait for close or success
    }

    const getVariantColor = () => {
        switch (confirmVariant) {
            case 'danger':
                return 'var(--terra)'
            case 'warning':
                return 'var(--amber)'
            default:
                return 'var(--accent)'
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 backdrop-blur-sm transition-opacity"
                style={{ background: 'rgba(0,0,0,0.5)' }}
                onClick={isLoading ? undefined : onCancel}
            />

            {/* Modal */}
            <div
                className="relative max-w-lg w-full mx-4 overflow-hidden transform transition-all scale-100 opacity-100 animate-blur-slide"
                style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-card)',
                }}
            >
                {/* Header */}
                <div
                    className="px-6 py-4 flex items-center gap-3"
                    style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}
                >
                    <span className="text-2xl">{icon}</span>
                    <div>
                        <h2 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>{title}</h2>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    <p className="mb-4 text-sm" style={{ color: 'var(--ink-600)' }}>
                        {description}
                    </p>
                    <textarea
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        placeholder={placeholder}
                        disabled={isLoading}
                        className="w-full h-32 px-4 py-3 focus:outline-none transition-shadow resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                            borderRadius: 'var(--radius-ctl)',
                            border: '1px solid var(--border)',
                            background: 'var(--surface)',
                            color: 'var(--ink-900)',
                        }}
                    />
                </div>

                {/* Footer */}
                <div
                    className="px-6 py-4 flex justify-end gap-3"
                    style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}
                >
                    <button
                        onClick={onCancel}
                        disabled={isLoading}
                        className="px-4 py-2 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed clickable-scale"
                        style={{ borderRadius: 'var(--radius-ctl)', color: 'var(--ink-600)' }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={isLoading}
                        className="px-4 py-2 font-medium transition-all flex items-center gap-2 clickable-scale disabled:opacity-70 disabled:cursor-not-allowed"
                        style={{
                            borderRadius: 'var(--radius-ctl)',
                            background: getVariantColor(),
                            color: 'var(--accent-ink)',
                        }}
                    >
                        {isLoading && (
                            <svg className="animate-spin h-4 w-4" style={{ color: 'var(--accent-ink)' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                        {isLoading ? 'Processing...' : confirmText}
                    </button>
                </div>
            </div>
        </div>
    )
}

export default InputModal
