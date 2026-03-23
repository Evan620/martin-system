import { Badge } from '../../../components/ui'

interface MeetingSidebarProps {
    meeting: any
}

export default function MeetingSidebar({ meeting }: MeetingSidebarProps) {
    // Early return if meeting data hasn't loaded yet
    if (!meeting) {
        return (
            <div className="hidden lg:block w-80 bg-slate-50 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 p-6">
                <div className="flex justify-center py-10">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            </div>
        )
    }

    const formatDate = (date: string) => {
        // Ensure date is treated as UTC if it doesn't have timezone info
        const dateStr = date.endsWith('Z') ? date : `${date}Z`
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric'
        })
    }

    const formatTime = (date: string) => {
        // Ensure date is treated as UTC if it doesn't have timezone info
        const dateStr = date.endsWith('Z') ? date : `${date}Z`
        return new Date(dateStr).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    return (
        <div className="hidden lg:block w-80 bg-slate-50 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 p-6 space-y-6 overflow-y-auto">
            {/* Meeting Details */}
            <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Meeting Details</h3>

                {/* Date & Time */}
                <div className="space-y-3">
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                            <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Date & Time</div>
                            <div className="text-sm font-bold text-slate-900 dark:text-white">{formatDate(meeting.scheduled_at)}</div>
                            <div className="text-sm text-slate-600 dark:text-slate-400">{formatTime(meeting.scheduled_at)} - {meeting.duration_minutes}m</div>
                        </div>
                    </div>

                    {/* Venue */}
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center shrink-0">
                            <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">Venue</div>
                            <div className="text-sm font-bold text-slate-900 dark:text-white">{meeting.location || 'Virtual'}</div>
                            {meeting.video_link ? (
                                // Check if link looks like a fake generated link (no https://)
                                meeting.video_link.startsWith('meet.google.com/') && !meeting.video_link.startsWith('https://') ? (
                                    <div className="text-xs text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                        Invalid meeting link - please update
                                    </div>
                                ) : (
                                    <a
                                        href={meeting.video_link.startsWith('http') ? meeting.video_link : `https://${meeting.video_link}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 mt-1"
                                        onClick={(e) => {
                                            // Prevent any duplicate handlers
                                            e.stopPropagation();
                                        }}
                                    >
                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                        </svg>
                                        Join Video Call
                                    </a>
                                )
                            ) : (
                                meeting.location === 'Virtual' && <span className="text-xs text-slate-400 italic">No video link yet</span>
                            )}
                        </div>
                    </div>

                    {/* TWG */}
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center shrink-0">
                            <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">TWG</div>
                            <div className="text-sm font-bold text-slate-900 dark:text-white">{meeting.twg?.name || 'Infrastructure Development'}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Participants */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">Participants</h3>
                    <Badge variant="info" className="text-xs">{meeting.participants?.length || 0}</Badge>
                </div>

                <div className="space-y-2">
                    {meeting.participants?.slice(0, 4).map((p: any) => (
                        <div key={p.id} className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                                {(p.name || p.user?.full_name || p.email || '?')[0].toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                    {p.name || p.user?.full_name || 'Guest'}
                                </div>
                                <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                                    {p.user?.role || 'Member'}
                                </div>
                            </div>
                            <div className={`w-2 h-2 rounded-full shrink-0 ${p.rsvp_status === 'accepted' ? 'bg-green-500' :
                                p.rsvp_status === 'declined' ? 'bg-red-500' :
                                    'bg-yellow-500'
                                }`} />
                        </div>
                    ))}

                    {meeting.participants?.length > 4 && (
                        <button className="text-sm text-blue-600 dark:text-blue-400 font-bold hover:underline w-full text-left">
                            View Full List ({meeting.participants.length - 4} more)
                        </button>
                    )}
                </div>
            </div>

            {/* Attachments */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">Attachments</h3>
                    <button className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors">
                        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                    </button>
                </div>

                <div className="space-y-2">
                    {meeting.documents && meeting.documents.length > 0 ? (
                        meeting.documents.map((doc: any) => (
                            <a
                                key={doc.id}
                                href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/documents/${doc.id}/download`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer group"
                            >
                                <div className="w-8 h-8 rounded bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
                                    <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm font-bold text-slate-900 dark:text-white truncate">{doc.file_name}</div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400">
                                        {new Date(doc.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                            </a>
                        ))
                    ) : (
                        <div className="text-sm text-slate-500 italic p-2">No attachments</div>
                    )}
                </div>
            </div>
        </div>
    )
}
