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
                className="absolute inset-0 backdrop-blur-sm"
                style={{ background: 'color-mix(in srgb, var(--ink-900) 55%, transparent)' }}
                onClick={onCancel}
            />

            {/* Modal */}
            <div
                className="relative max-w-lg w-full mx-4 overflow-hidden animate-blur-slide"
                style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-card)',
                }}
            >
                {/* Header */}
                <div
                    className="px-6 py-4"
                    style={{
                        background: 'color-mix(in srgb, var(--amber) 12%, var(--surface))',
                        borderBottom: '1px solid var(--border)',
                    }}
                >
                    <div className="flex items-center gap-3">
                        <span className="text-3xl">⚠️</span>
                        <div>
                            <h2 className="text-xl font-bold" style={{ color: 'var(--amber)' }}>Scheduling Conflicts Detected</h2>
                            <p className="text-sm" style={{ color: 'var(--ink-500)' }}>
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
                                className="p-4"
                                style={{
                                    borderRadius: 'var(--radius-ctl)',
                                    background: conflict.severity === 'high'
                                        ? 'color-mix(in srgb, var(--terra) 10%, var(--surface))'
                                        : 'color-mix(in srgb, var(--amber) 10%, var(--surface))',
                                    border: `1px solid ${conflict.severity === 'high'
                                        ? 'color-mix(in srgb, var(--terra) 30%, var(--border))'
                                        : 'color-mix(in srgb, var(--amber) 30%, var(--border))'}`,
                                }}
                            >
                                <div className="flex items-start gap-3">
                                    <span className="text-xl mt-0.5">
                                        {conflict.type === 'venue_conflict' ? '🏢' : '👤'}
                                    </span>
                                    <div className="flex-1">
                                        <p
                                            className="font-medium"
                                            style={{ color: conflict.severity === 'high' ? 'var(--terra)' : 'var(--amber)' }}
                                        >
                                            {conflict.message}
                                        </p>
                                        {conflict.conflicting_meeting && (
                                            <div className="mt-2 text-sm" style={{ color: 'var(--ink-500)' }}>
                                                <p className="flex items-center gap-2">
                                                    <span>📅</span>
                                                    <span className="font-medium" style={{ color: 'var(--ink-700)' }}>
                                                        {conflict.conflicting_meeting.title}
                                                    </span>
                                                </p>
                                                {conflict.conflicting_meeting.twg && (
                                                    <p className="mt-1 text-xs" style={{ color: 'var(--ink-400)' }}>
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
                <div
                    className="px-6 py-4 flex gap-3 justify-end"
                    style={{
                        background: 'var(--surface-2)',
                        borderTop: '1px solid var(--border)',
                    }}
                >
                    <button
                        onClick={onCancel}
                        className="px-4 py-2 font-medium qp-transition clickable-scale"
                        style={{
                            borderRadius: 'var(--radius-ctl)',
                            background: 'var(--surface)',
                            border: '1px solid var(--border)',
                            color: 'var(--ink-700)',
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onProceed}
                        className="px-4 py-2 font-medium qp-transition flex items-center gap-2 clickable-scale"
                        style={{
                            borderRadius: 'var(--radius-ctl)',
                            background: 'var(--accent)',
                            color: 'var(--accent-ink)',
                        }}
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
