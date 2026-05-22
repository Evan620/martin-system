import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import { UserRole } from '../../types/auth'
import { meetings } from '../../services/api'
import CreateMeetingModal from '../../components/schedule/CreateMeetingModal'
import CalendarGrid, { CalendarEvent } from '../../components/common/CalendarGrid'
import { parseUTCDate } from '../../utils/dates'



export default function SummitSchedule() {
    const navigate = useNavigate()
    const user = useSelector((state: RootState) => state.auth.user)
    const canCreateMeetings = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD || user?.role === UserRole.FACILITATOR
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [loading, setLoading] = useState(true)
    const [currentDate, setCurrentDate] = useState(new Date())
    const [isCreatingMeeting, setIsCreatingMeeting] = useState(false)
    const [selectedDate, setSelectedDate] = useState<Date | null>(null)

    useEffect(() => {
        loadMeetings()
    }, [])

    const loadMeetings = async () => {
        try {
            const response = await meetings.list()
            const meetingData: CalendarEvent[] = response.data.filter((m: any) => m.status !== 'CANCELLED').map((m: any) => ({
                id: m.id,
                title: m.title,
                scheduled_at: parseUTCDate(m.scheduled_at),
                type: m.meeting_type === 'virtual' ? 'virtual' : 'in_person',
                status: m.status,
                twg_name: m.twg?.name,
                has_conflicts: false
            }))
            setEvents(meetingData)
        } catch (error) {
            console.error("Failed to load meetings", error)
        } finally {
            setLoading(false)
        }
    }

    const handleDayClick = (day: Date) => {
        if (!canCreateMeetings) return
        setSelectedDate(day)
        setIsCreatingMeeting(true)
    }

    const handleEventClick = (event: CalendarEvent) => {
        navigate(`/meetings/${event.id}`, { state: { from: 'schedule' } })
    }

    const monthLabel = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            {/* Page header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)', marginBottom: 6 }}>
                    Meetings · {monthLabel}
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <h1 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        Schedule
                    </h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        {canCreateMeetings && (
                            <button
                                onClick={() => setIsCreatingMeeting(true)}
                                style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                            >
                                + New meeting
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Calendar */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 320 }}>
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--accent)' }}></div>
                    </div>
                ) : (
                    <CalendarGrid
                        events={events}
                        currentDate={currentDate}
                        onMonthChange={setCurrentDate}
                        onDateClick={handleDayClick}
                        onEventClick={handleEventClick}
                        isLoading={loading}
                    />
                )}
            </div>

            {/* Create Meeting Modal */}
            {canCreateMeetings && (
                <CreateMeetingModal
                    isOpen={isCreatingMeeting}
                    onClose={() => {
                        setIsCreatingMeeting(false)
                        setSelectedDate(null)
                    }}
                    onSuccess={loadMeetings}
                    prefilledDate={selectedDate}
                />
            )}
        </div>
    )
}
