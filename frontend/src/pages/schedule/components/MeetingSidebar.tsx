interface MeetingSidebarProps {
    meeting: any
}

import { formatMeetingDate, formatMeetingTime } from '../../../utils/dates'

const fmtDate = (date: string) => formatMeetingDate(date)
const fmtTime = (date: string) => formatMeetingTime(date)

const eyebrow: React.CSSProperties = {
    fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
    color: 'var(--ink-500)', fontWeight: 500, marginBottom: 4,
}

const sectionLabel: React.CSSProperties = {
    fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase',
    color: 'var(--ink-500)', fontWeight: 500, marginBottom: 14,
}

const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div style={{ paddingBottom: 14, marginBottom: 14, borderBottom: '1px solid var(--border)' }}>
        <div style={eyebrow}>{label}</div>
        <div style={{ fontSize: 13, color: 'var(--ink-900)' }}>{children}</div>
    </div>
)

export default function MeetingSidebar({ meeting }: MeetingSidebarProps) {
    if (!meeting) {
        return (
            <aside
                style={{
                    width: 320, flexShrink: 0,
                    borderLeft: '1px solid var(--border)',
                    padding: '28px 28px',
                    background: 'var(--surface)',
                    fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                }}
                className="hidden lg:block"
            >
                <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>Loading meeting…</div>
            </aside>
        )
    }

    const participants = meeting.participants || []
    const visibleParticipants = participants.slice(0, 4)
    const remaining = Math.max(0, participants.length - 4)

    const rsvpColor = (s: string) =>
        s === 'accepted' ? 'var(--sage)' :
            s === 'declined' ? 'var(--terra)' :
                'var(--amber)'

    return (
        <aside
            className="hidden lg:block"
            style={{
                width: 320, flexShrink: 0,
                borderLeft: '1px solid var(--border)',
                padding: '28px 28px',
                background: 'var(--surface)',
                fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                overflowY: 'auto',
            }}
        >
            {/* Meeting details section */}
            <div style={{ marginBottom: 28 }}>
                <div style={sectionLabel}>Meeting details</div>

                <Row label="Date &amp; time">
                    <div style={{
                        fontFamily: "'Geist', serif", fontSize: 18,
                        color: 'var(--ink-900)', letterSpacing: '-0.01em', lineHeight: 1.2,
                    }}>{fmtDate(meeting.scheduled_at)}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 4, fontFamily: "'Geist Mono', monospace" }}>
                        {fmtTime(meeting.scheduled_at)} · {meeting.duration_minutes}m
                    </div>
                </Row>

                <Row label="Venue">
                    <div style={{ fontSize: 13, color: 'var(--ink-900)' }}>{meeting.location || 'Virtual'}</div>
                    {meeting.video_link ? (
                        meeting.video_link.startsWith('meet.google.com/') && !meeting.video_link.startsWith('https://') ? (
                            <div style={{ fontSize: 11, color: 'var(--amber)', marginTop: 6, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>warning</span>
                                Invalid meeting link — please update
                            </div>
                        ) : (
                            <a
                                href={meeting.video_link.startsWith('http') ? meeting.video_link : `https://${meeting.video_link}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                style={{
                                    display: 'inline-flex', alignItems: 'center', gap: 6,
                                    marginTop: 8, padding: 0,
                                    fontSize: 11, fontWeight: 500, letterSpacing: '0.06em',
                                    textTransform: 'uppercase', color: 'var(--accent)',
                                    textDecoration: 'none',
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>videocam</span>
                                Join video call →
                            </a>
                        )
                    ) : (
                        meeting.location === 'Virtual' && (
                            <div style={{ fontSize: 11, color: 'var(--ink-400)', fontStyle: 'italic', marginTop: 4 }}>
                                No video link yet
                            </div>
                        )
                    )}
                </Row>

                <Row label="TWG">
                    <div style={{ fontSize: 13, color: 'var(--ink-900)' }}>
                        {meeting.twg?.name || 'Infrastructure Development'}
                    </div>
                </Row>
            </div>

            {/* Participants */}
            <div style={{ marginBottom: 28 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 14 }}>
                    <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>
                        Participants
                    </div>
                    <span style={{ fontSize: 12, fontFamily: "'Geist Mono', monospace", color: 'var(--ink-700)', fontVariantNumeric: 'tabular-nums' }}>
                        {participants.length}
                    </span>
                </div>

                <div>
                    {visibleParticipants.map((p: any) => {
                        const name = p.name || p.user?.full_name || p.email || 'Guest'
                        const initial = name[0]?.toUpperCase() || '?'
                        return (
                            <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                                <div style={{
                                    width: 28, height: 28,
                                    border: '1px solid var(--border)',
                                    background: 'var(--ink-50)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontFamily: "'Geist', serif",
                                    fontSize: 13, color: 'var(--ink-700)',
                                    flexShrink: 0,
                                }}>{initial}</div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: 12, color: 'var(--ink-900)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {p.name || p.user?.full_name || 'Guest'}
                                    </div>
                                    <div style={{ fontSize: 10, color: 'var(--ink-500)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 2 }}>
                                        {p.user?.role || 'Member'}
                                    </div>
                                </div>
                                <span style={{
                                    width: 6, height: 6, borderRadius: 6,
                                    background: rsvpColor(p.rsvp_status),
                                    flexShrink: 0,
                                }} />
                            </div>
                        )
                    })}

                    {remaining > 0 && (
                        <button style={{
                            background: 'transparent', border: 'none', cursor: 'pointer',
                            color: 'var(--accent)', fontSize: 11, fontWeight: 500,
                            letterSpacing: '0.06em', textTransform: 'uppercase',
                            padding: '10px 0 0', textAlign: 'left',
                        }}>
                            View full list ({remaining} more) →
                        </button>
                    )}
                </div>
            </div>

            <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>
                        Attachments
                    </div>
                    <button style={{
                        background: 'transparent', border: '1px solid var(--border)',
                        color: 'var(--ink-500)', padding: '2px 6px', cursor: 'pointer',
                        display: 'inline-flex', alignItems: 'center',
                    }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>add</span>
                    </button>
                </div>

                <div>
                    {meeting.documents && meeting.documents.length > 0 ? (
                        meeting.documents.map((doc: any) => (
                            <a
                                key={doc.id}
                                href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/documents/${doc.id}/download`}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 10,
                                    padding: '10px 12px',
                                    border: '1px solid var(--border)',
                                    marginBottom: 6, textDecoration: 'none',
                                    background: 'var(--surface)',
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--ink-400)', flexShrink: 0 }}>
                                    {doc.file_name?.endsWith?.('.pdf') ? 'picture_as_pdf' : 'description'}
                                </span>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: 12, color: 'var(--ink-900)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {doc.file_name}
                                    </div>
                                    <div style={{ fontSize: 10, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace", marginTop: 2 }}>
                                        {new Date(doc.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                            </a>
                        ))
                    ) : (
                        <div style={{ fontSize: 12, color: 'var(--ink-400)', fontStyle: 'italic' }}>No attachments</div>
                    )}
                </div>
            </div>
        </aside>
    )
}
