import { useState, useEffect } from 'react'
import { meetings } from '../../services/api'

interface InvitePreviewModalProps {
    isOpen: boolean
    meetingId: string
    onClose: () => void
    onApprove: () => void
    isApproving: boolean
}

export default function InvitePreviewModal({
    isOpen,
    meetingId,
    onClose,
    onApprove,
    isApproving
}: InvitePreviewModalProps) {
    const [loading, setLoading] = useState(true)
    const [preview, setPreview] = useState<{
        subject: string
        html_content: string
        participants: string[]
        status: string
    } | null>(null)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (isOpen && meetingId) {
            loadPreview()
        }
    }, [isOpen, meetingId])

    const loadPreview = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await meetings.getInvitePreview(meetingId)
            setPreview(res.data)
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Failed to load preview')
        } finally {
            setLoading(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
            <div className="w-full max-w-3xl max-h-[90vh] flex flex-col" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                {/* Header */}
                <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 flex items-center justify-center" style={{ background: 'var(--accent-soft)', borderRadius: 'var(--radius-ctl)' }}>
                            <span className="text-xl">📧</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>Review Invitation</h2>
                            <p className="text-sm" style={{ color: 'var(--ink-500)' }}>HITL Gate: Approve before sending</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 qp-transition rounded-lg clickable-scale"
                        style={{ color: 'var(--ink-500)' }}
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="flex justify-center py-20">
                            <div className="animate-spin rounded-full h-8 w-8" style={{ borderBottom: '2px solid var(--accent)' }}></div>
                        </div>
                    ) : error ? (
                        <div className="text-center py-10">
                            <div className="text-4xl mb-3" style={{ color: 'var(--terra)' }}>⚠️</div>
                            <p style={{ color: 'var(--terra)' }}>{error}</p>
                        </div>
                    ) : preview ? (
                        <div className="space-y-6">
                            {/* Recipients */}
                            <div>
                                <h3 className="text-sm font-bold mb-2" style={{ color: 'var(--ink-700)' }}>Recipients ({preview.participants.length})</h3>
                                <div className="flex flex-wrap gap-2">
                                    {preview.participants.map((email, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1 rounded-full text-sm"
                                            style={{ background: 'var(--surface-2)', color: 'var(--ink-600)' }}
                                        >
                                            {email}
                                        </span>
                                    ))}
                                    {preview.participants.length === 0 && (
                                        <span className="italic" style={{ color: 'var(--ink-400)' }}>No participants added</span>
                                    )}
                                </div>
                            </div>

                            {/* Subject */}
                            <div>
                                <h3 className="text-sm font-bold mb-2" style={{ color: 'var(--ink-700)' }}>Subject</h3>
                                <p style={{ color: 'var(--ink-600)' }}>{preview.subject}</p>
                            </div>

                            {/* Email Preview */}
                            <div>
                                <h3 className="text-sm font-bold mb-2" style={{ color: 'var(--ink-700)' }}>Email Preview</h3>
                                <div
                                    className="p-4 max-h-80 overflow-y-auto"
                                    style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', background: 'var(--surface)' }}
                                    dangerouslySetInnerHTML={{ __html: preview.html_content }}
                                />
                            </div>

                            {/* Calendar Note */}
                            <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--ink-500)' }}>
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                <span>Google Calendar invite will be sent to all participants</span>
                            </div>
                        </div>
                    ) : null}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 flex items-center justify-end gap-3" style={{ borderTop: '1px solid var(--border)' }}>
                    <button
                        onClick={onClose}
                        disabled={isApproving}
                        className="px-4 py-2 text-sm font-medium qp-transition rounded-lg disabled:opacity-50 clickable-scale"
                        style={{ color: 'var(--ink-700)' }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onApprove}
                        disabled={isApproving || loading || !!error || !preview?.participants.length}
                        className="px-6 py-2 text-sm font-bold qp-transition flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed clickable-scale"
                        style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                    >
                        {isApproving ? (
                            <>
                                <span className="animate-spin">⏳</span>
                                Sending...
                            </>
                        ) : (
                            <>
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Approve & Send
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
