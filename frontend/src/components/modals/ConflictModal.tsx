import React from 'react'

interface ConflictModalProps {
    isOpen: boolean
    conflicts: Array<{
        type: string
        severity: string
        message: string
        conflicting_meeting?: {
            id: string
            title: string
            time: string
            twg: string
        }
    }>
    onProceed: () => void
    onCancel: () => void
}

const ConflictModal: React.FC<ConflictModalProps> = ({ isOpen, conflicts, onProceed, onCancel }) => {
    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onCancel}
            />

            {/* Modal */}
            <div className="relative bg-gray-800 border border-yellow-500/50 rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
                {/* Header */}
                <div className="bg-yellow-500/20 border-b border-yellow-500/30 px-6 py-4">
                    <div className="flex items-center gap-3">
                        <span className="text-3xl">⚠️</span>
                        <div>
                            <h2 className="text-xl font-bold text-yellow-400">Scheduling Conflicts Detected</h2>
                            <p className="text-sm text-yellow-300/70">
                                {conflicts.length} potential conflict{conflicts.length !== 1 ? 's' : ''} found
                            </p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="px-6 py-4 max-h-80 overflow-y-auto">
                    <div className="space-y-3">
                        {conflicts.map((conflict, index) => (
                            <div
                                key={index}
                                className={`p-4 rounded-lg border ${conflict.severity === 'high'
                                        ? 'bg-red-500/10 border-red-500/30'
                                        : 'bg-yellow-500/10 border-yellow-500/30'
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    <span className="text-xl mt-0.5">
                                        {conflict.type === 'venue_conflict' ? '🏢' : '👤'}
                                    </span>
                                    <div className="flex-1">
                                        <p className={`font-medium ${conflict.severity === 'high'
                                                ? 'text-red-300'
                                                : 'text-yellow-300'
                                            }`}>
                                            {conflict.message}
                                        </p>
                                        {conflict.conflicting_meeting && (
                                            <div className="mt-2 text-sm text-gray-400">
                                                <p className="flex items-center gap-2">
                                                    <span>📅</span>
                                                    <span className="font-medium text-gray-300">
                                                        {conflict.conflicting_meeting.title}
                                                    </span>
                                                </p>
                                                {conflict.conflicting_meeting.twg && (
                                                    <p className="mt-1 text-xs text-gray-500">
                                                        TWG: {conflict.conflicting_meeting.twg}
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div className="bg-gray-900/50 border-t border-gray-700 px-6 py-4 flex gap-3 justify-end">
                    <button
                        onClick={onCancel}
                        className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium transition-colors clickable-scale"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onProceed}
                        className="px-4 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white font-medium transition-colors flex items-center gap-2 clickable-scale"
                    >
                        <span>⚡</span>
                        Proceed Anyway
                    </button>
                </div>
            </div>
        </div>
    )
}

export default ConflictModal
