import React from 'react'

interface StatusModalProps {
    isOpen: boolean
    type: 'success' | 'error' | 'info'
    title: string
    message: string
    onClose: () => void
    actionText?: string
    onAction?: () => void
}

const StatusModal: React.FC<StatusModalProps> = ({
    isOpen,
    type,
    title,
    message,
    onClose,
    actionText,
    onAction
}) => {
    if (!isOpen) return null

    const getIcon = () => {
        switch (type) {
            case 'success': return '✅'
            case 'error': return '❌'
            case 'info': return 'ℹ️'
        }
    }

    const getAccentColor = () => {
        switch (type) {
            case 'success': return 'var(--sage)'
            case 'error': return 'var(--terra)'
            case 'info': return 'var(--accent)'
        }
    }

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 backdrop-blur-[2px] transition-opacity"
                style={{ background: 'color-mix(in srgb, var(--ink-900) 40%, transparent)' }}
                onClick={onClose}
            />

            {/* Modal */}
            <div
                className="relative max-w-md w-full mx-4 overflow-hidden transform transition-all scale-100 opacity-100 animate-blur-slide"
                style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderLeft: `4px solid ${getAccentColor()}`,
                    borderRadius: 'var(--radius-card)'
                }}
            >
                <div className="p-6">
                    <div className="flex items-start gap-4">
                        <span
                            className="text-3xl rounded-full p-2"
                            style={{ background: 'var(--surface-2)' }}
                        >{getIcon()}</span>
                        <div className="flex-1">
                            <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--ink-900)' }}>{title}</h3>
                            <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-600)' }}>{message}</p>
                        </div>
                    </div>

                    <div className="mt-6 flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 font-medium hover:opacity-90 transition-opacity clickable-scale"
                            style={
                                onAction
                                    ? { background: 'var(--surface-2)', color: 'var(--ink-700)', borderRadius: 'var(--radius-ctl)' }
                                    : { background: 'var(--ink-900)', color: 'var(--surface)', borderRadius: 'var(--radius-ctl)' }
                            }
                        >
                            {onAction ? 'Dismiss' : 'Close'}
                        </button>
                        {onAction && actionText && (
                            <button
                                onClick={onAction}
                                className="px-4 py-2 font-medium hover:opacity-90 transition-opacity clickable-scale"
                                style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                            >
                                {actionText}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default StatusModal
