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

    const getVariantClasses = () => {
        switch (confirmVariant) {
            case 'danger':
                return 'bg-red-600 hover:bg-red-500 text-white ring-red-500'
            case 'warning':
                return 'bg-yellow-600 hover:bg-yellow-500 text-white ring-yellow-500'
            default:
                return 'bg-teal-600 hover:bg-teal-500 text-white ring-teal-500'
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
                onClick={isLoading ? undefined : onCancel}
            />

            {/* Modal */}
            <div className="relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden transform transition-all scale-100 opacity-100">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3 bg-slate-50/50 dark:bg-slate-800/30">
                    <span className="text-2xl">{icon}</span>
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h2>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    <p className="text-slate-600 dark:text-slate-300 mb-4 text-sm">
                        {description}
                    </p>
                    <textarea
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        placeholder={placeholder}
                        disabled={isLoading}
                        className="w-full h-32 px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-opacity-50 focus:outline-none transition-shadow resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3">
                    <button
                        onClick={onCancel}
                        disabled={isLoading}
                        className="px-4 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed clickable-scale"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={isLoading}
                        className={`px-4 py-2 rounded-lg font-medium transition-all shadow-lg shadow-current/20 flex items-center gap-2 clickable-scale ${getVariantClasses()} disabled:opacity-70 disabled:cursor-not-allowed`}
                    >
                        {isLoading && (
                            <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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
