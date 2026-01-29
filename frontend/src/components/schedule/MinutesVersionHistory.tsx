import { useState, useEffect } from 'react'
import { meetings } from '../../services/api'
import { Card } from '../ui'

interface MinutesVersion {
    id: string
    version_number: number
    content: string
    key_decisions?: string
    change_summary?: string
    created_by: string
    created_at: string
    author?: {
        id: string
        full_name: string
        email: string
    }
}

interface MinutesVersionHistoryProps {
    meetingId: string
    isOpen: boolean
    onClose: () => void
    onRestore: () => void
}

export default function MinutesVersionHistory({ meetingId, isOpen, onClose, onRestore }: MinutesVersionHistoryProps) {
    const [versions, setVersions] = useState<MinutesVersion[]>([])
    const [selectedVersion, setSelectedVersion] = useState<MinutesVersion | null>(null)
    const [loading, setLoading] = useState(false)
    const [restoring, setRestoring] = useState(false)

    useEffect(() => {
        if (isOpen) {
            loadVersions()
        }
    }, [isOpen, meetingId])

    const loadVersions = async () => {
        try {
            setLoading(true)
            const response = await meetings.listMinutesVersions(meetingId)
            setVersions(response.data)
        } catch (error) {
            console.error('Failed to load versions', error)
        } finally {
            setLoading(false)
        }
    }

    const handleRestore = async (version: MinutesVersion) => {
        if (!confirm(`Are you sure you want to restore to version ${version.version_number}? This will create a new version with the content from v${version.version_number}.`)) {
            return
        }

        try {
            setRestoring(true)
            await meetings.restoreMinutesVersion(meetingId, version.version_number)
            alert(`✅ Successfully restored to version ${version.version_number}`)
            onRestore() // Refresh parent component
            onClose()
        } catch (error) {
            console.error('Failed to restore version', error)
            alert('Failed to restore version')
        } finally {
            setRestoring(false)
        }
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString([], {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-dark-card rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
                    <div>
                        <h2 className="text-2xl font-display font-bold text-slate-900 dark:text-white">Version History</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">View and restore previous versions of minutes</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    >
                        <svg className="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden flex">
                    {/* Version List */}
                    <div className="w-80 border-r border-slate-200 dark:border-slate-700 overflow-y-auto">
                        {loading ? (
                            <div className="p-8 text-center text-slate-500">Loading versions...</div>
                        ) : versions.length === 0 ? (
                            <div className="p-8 text-center text-slate-500">No version history yet</div>
                        ) : (
                            <div className="p-4 space-y-2">
                                {versions.map((version) => (
                                    <button
                                        key={version.id}
                                        onClick={() => setSelectedVersion(version)}
                                        className={`w-full text-left p-4 rounded-xl transition-all ${selectedVersion?.id === version.id
                                                ? 'bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-500'
                                                : 'bg-slate-50 dark:bg-slate-800 border-2 border-transparent hover:border-slate-300 dark:hover:border-slate-600'
                                            }`}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-bold text-sm text-blue-600 dark:text-blue-400">
                                                Version {version.version_number}
                                            </span>
                                            <span className="text-xs text-slate-500">
                                                {formatDate(version.created_at)}
                                            </span>
                                        </div>
                                        {version.change_summary && (
                                            <p className="text-xs text-slate-600 dark:text-slate-400 mb-2 line-clamp-2">
                                                {version.change_summary}
                                            </p>
                                        )}
                                        <div className="text-xs text-slate-500">
                                            by {version.author?.full_name || 'Unknown'}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Version Preview */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {selectedVersion ? (
                            <div>
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                                            Version {selectedVersion.version_number}
                                        </h3>
                                        <p className="text-sm text-slate-500 mt-1">
                                            {formatDate(selectedVersion.created_at)} • {selectedVersion.author?.full_name}
                                        </p>
                                        {selectedVersion.change_summary && (
                                            <p className="text-sm text-slate-600 dark:text-slate-400 mt-2 italic">
                                                "{selectedVersion.change_summary}"
                                            </p>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => handleRestore(selectedVersion)}
                                        disabled={restoring}
                                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-400 text-white rounded-lg font-bold transition-all flex items-center gap-2"
                                    >
                                        {restoring ? (
                                            <>
                                                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                                </svg>
                                                Restoring...
                                            </>
                                        ) : (
                                            <>
                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                </svg>
                                                Restore This Version
                                            </>
                                        )}
                                    </button>
                                </div>

                                {/* Content Preview */}
                                <Card className="p-6">
                                    <div
                                        className="prose dark:prose-invert max-w-none"
                                        dangerouslySetInnerHTML={{ __html: selectedVersion.content }}
                                    />
                                </Card>
                            </div>
                        ) : (
                            <div className="h-full flex items-center justify-center text-slate-400">
                                <div className="text-center">
                                    <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <p>Select a version to view its content</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
