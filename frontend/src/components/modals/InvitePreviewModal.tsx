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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-900/30 flex items-center justify-center">
                            <span className="text-xl">📧</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Review Invitation</h2>
                            <p className="text-sm text-slate-500">HITL Gate: Approve before sending</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors clickable-scale"
                    >
                        <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="flex justify-center py-20">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                        </div>
                    ) : error ? (
                        <div className="text-center py-10">
                            <div className="text-red-500 text-4xl mb-3">⚠️</div>
                            <p className="text-red-600 dark:text-red-400">{error}</p>
                        </div>
                    ) : preview ? (
                        <div className="space-y-6">
                            {/* Recipients */}
                            <div>
                                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Recipients ({preview.participants.length})</h3>
                                <div className="flex flex-wrap gap-2">
                                    {preview.participants.map((email, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full text-sm text-slate-600 dark:text-slate-400"
                                        >
                                            {email}
                                        </span>
                                    ))}
                                    {preview.participants.length === 0 && (
                                        <span className="text-slate-400 italic">No participants added</span>
                                    )}
                                </div>
                            </div>

                            {/* Subject */}
                            <div>
                                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Subject</h3>
                                <p className="text-slate-600 dark:text-slate-400">{preview.subject}</p>
                            </div>

                            {/* Email Preview */}
                            <div>
                                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Email Preview</h3>
                                <div
                                    className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 bg-white dark:bg-slate-800 max-h-80 overflow-y-auto"
                                    dangerouslySetInnerHTML={{ __html: preview.html_content }}
                                />
                            </div>

                            {/* Calendar Note */}
                            <div className="flex items-center gap-2 text-sm text-slate-500">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                <span>Google Calendar invite will be sent to all participants</span>
                            </div>
                        </div>
                    ) : null}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-end gap-3">
                    <button
                        onClick={onClose}
                        disabled={isApproving}
                        className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50 clickable-scale"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onApprove}
                        disabled={isApproving || loading || !!error || !preview?.participants.length}
                        className="px-6 py-2 text-sm font-bold text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed clickable-scale"
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
