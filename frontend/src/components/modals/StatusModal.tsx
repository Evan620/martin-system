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

    const getColorClass = () => {
        switch (type) {
            case 'success': return 'border-l-4 border-green-500'
            case 'error': return 'border-l-4 border-red-500'
            case 'info': return 'border-l-4 border-teal-500'
        }
    }

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/40 backdrop-blur-[2px] transition-opacity"
                onClick={onClose}
            />

            {/* Modal */}
            <div className={`relative bg-white dark:bg-slate-900 shadow-2xl rounded-lg max-w-md w-full mx-4 overflow-hidden transform transition-all scale-100 opacity-100 ${getColorClass()}`}>
                <div className="p-6">
                    <div className="flex items-start gap-4">
                        <span className="text-3xl bg-slate-100 dark:bg-slate-800 rounded-full p-2">{getIcon()}</span>
                        <div className="flex-1">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">{title}</h3>
                            <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">{message}</p>
                        </div>
                    </div>

                    <div className="mt-6 flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className={`${onAction ? 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300' : 'bg-slate-900 dark:bg-white text-white dark:text-slate-900'} px-4 py-2 rounded font-medium hover:opacity-90 transition-opacity clickable-scale`}
                        >
                            {onAction ? 'Dismiss' : 'Close'}
                        </button>
                        {onAction && actionText && (
                            <button
                                onClick={onAction}
                                className="bg-teal-600 text-white px-4 py-2 rounded font-medium hover:bg-teal-700 transition-colors clickable-scale"
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
