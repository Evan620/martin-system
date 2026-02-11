import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import { UserRole } from '../../types/auth'
import { meetings } from '../../services/api'
import CreateMeetingModal from '../../components/schedule/CreateMeetingModal'
import CalendarGrid, { CalendarEvent } from '../../components/common/CalendarGrid'



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
            const meetingData: CalendarEvent[] = response.data.map((m: any) => ({
                id: m.id,
                title: m.title,
                scheduled_at: new Date(m.scheduled_at),
                type: m.meeting_type === 'virtual' ? 'virtual' : 'in_person',
                status: m.status,
                twg_name: m.twg?.name,
                has_conflicts: false // Individual schedule doesn't explicitly track conflicts yet in same way
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

    return (
        <div className="max-w-7xl mx-auto space-y-6 h-[calc(100vh-100px)] flex flex-col">


            {/* Calendar Grid Reused */}
            <div className="flex-1 overflow-hidden">
                <CalendarGrid
                    events={events}
                    currentDate={currentDate}
                    onMonthChange={setCurrentDate}
                    onDateClick={handleDayClick}
                    onEventClick={handleEventClick}
                    isLoading={loading}
                />
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

