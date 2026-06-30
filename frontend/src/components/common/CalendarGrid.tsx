
import {
    format,
    startOfMonth,
    endOfMonth,
    startOfWeek,
    endOfWeek,
    eachDayOfInterval,
    isSameMonth,
    isSameDay,
    addMonths,
    subMonths,
    isToday
} from 'date-fns';


export interface CalendarEvent {
    id: string;
    title: string;
    scheduled_at: Date;
    type: 'virtual' | 'in_person';
    status?: string;
    color?: string; // Optional override
    twg_name?: string; // For global view
    has_conflicts?: boolean;
}

interface CalendarGridProps {
    events: CalendarEvent[];
    onEventClick?: (event: CalendarEvent) => void;
    onDateClick?: (date: Date) => void;
    currentDate: Date;
    onMonthChange: (date: Date) => void;
    isLoading?: boolean;
}

export default function CalendarGrid({
    events,
    onEventClick,
    onDateClick,
    currentDate,
    onMonthChange,
    isLoading = false
}: CalendarGridProps) {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);
    const calendarDays = eachDayOfInterval({ start: startDate, end: endDate });

    const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    const nextMonth = () => onMonthChange(addMonths(currentDate, 1));
    const prevMonth = () => onMonthChange(subMonths(currentDate, 1));
    const resetDate = () => onMonthChange(new Date());

    const getEventsForDay = (day: Date) => {
        return events.filter(event => isSameDay(event.scheduled_at, day))
            .sort((a, b) => a.scheduled_at.getTime() - b.scheduled_at.getTime());
    };

    if (isLoading) {
        return (
            <div className="flex h-[400px] items-center justify-center bg-[var(--surface)] border border-[var(--border)] rounded-2xl">
                <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden flex flex-col h-full">
            {/* Header / Navigation */}
            <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 rounded-lg p-1 border" style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}>
                        <button onClick={prevMonth} className="p-1 rounded-md text-[var(--ink-500)] hover:bg-[var(--surface)]">
                            <span className="material-symbols-outlined text-lg">chevron_left</span>
                        </button>
                        <button onClick={resetDate} className="px-3 text-sm font-extrabold tracking-tight text-[var(--ink-900)] min-w-[120px] text-center font-mono-geist">
                            {format(currentDate, 'MMMM yyyy')}
                        </button>
                        <button onClick={nextMonth} className="p-1 rounded-md text-[var(--ink-500)] hover:bg-[var(--surface)]">
                            <span className="material-symbols-outlined text-lg">chevron_right</span>
                        </button>
                    </div>
                </div>

                {/* Legend */}
                <div className="hidden sm:flex items-center gap-3 text-[10px] uppercase tracking-wider font-semibold text-[var(--ink-500)]">
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-teal-500"></span>
                        <span>In-Person</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                        <span>Virtual</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-amber-500 text-[14px]">warning</span>
                        <span>Conflict</span>
                    </div>
                </div>
            </div>

            {/* Scrollable calendar area for mobile */}
            <div className="flex-1 overflow-x-auto">
              <div className="min-w-[500px]">
                {/* Weekday Headers */}
                <div className="grid grid-cols-7 border-b border-[var(--border)]" style={{ background: 'var(--surface-2)' }}>
                    {weekDays.map(day => (
                        <div key={day} className="py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-[var(--ink-500)]">
                            {day}
                        </div>
                    ))}
                </div>

                {/* Days Grid */}
                <div className="grid grid-cols-7 auto-rows-[minmax(80px,1fr)]">
                {calendarDays.map((day) => {
                    const dayEvents = getEventsForDay(day);
                    const isCurrentMonth = isSameMonth(day, monthStart);
                    const isTodayDate = isToday(day);

                    return (
                        <div
                            key={day.toString()}
                            onClick={() => onDateClick?.(day)}
                            className={`
                                border-b border-r border-[var(--border)] p-3 relative group flex flex-col cursor-pointer transition-colors overflow-hidden
                                ${!isCurrentMonth ? 'text-[var(--ink-300)]' : 'bg-transparent hover:bg-[var(--surface-2)]'}
                                ${isTodayDate ? 'bg-[var(--surface-2)]' : ''}
                            `}
                        >
                            <div className="flex justify-between items-start mb-1 shrink-0">
                                <span className={`
                                    text-xs font-bold font-mono-geist w-6 h-6 flex items-center justify-center rounded-full
                                    ${isTodayDate ? 'text-white shadow-sm' : 'text-[var(--ink-700)]'}
                                    ${!isCurrentMonth ? 'opacity-30' : ''}
                                `}
                                style={isTodayDate ? { background: 'var(--accent)', color: 'var(--accent-ink)' } : undefined}>
                                    {format(day, 'd')}
                                </span>
                            </div>

                            <div className="space-y-1 flex-1 overflow-y-auto min-h-0 scrollbar-thin">
                                {dayEvents.map(event => (
                                    <div
                                        key={event.id}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onEventClick?.(event);
                                        }}
                                        className={`
                                            px-1.5 py-1 rounded text-[10px] cursor-pointer transition-all border group/event truncate flex items-center gap-1
                                            ${event.type === 'virtual'
                                                ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border-purple-100 dark:border-purple-800 hover:bg-purple-100'
                                                : 'bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-300 border-teal-100 dark:border-teal-800 hover:bg-teal-100'}
                                            ${event.has_conflicts ? 'border-amber-400 ring-1 ring-amber-400/30' : ''}
                                        `}
                                        title={`${event.title} (${event.twg_name})`}
                                    >
                                        {event.has_conflicts && <span className="material-symbols-outlined text-[10px] text-amber-500">warning</span>}
                                        {['in_progress', 'IN_PROGRESS'].includes(event.status || '') && (
                                            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse shrink-0" title="Meeting is Live" />
                                        )}
                                        <span className="font-semibold truncate flex-1">{event.title}</span>
                                        {event.twg_name && (
                                            <span className="text-[8px] opacity-70 uppercase tracking-tighter bg-white/20 px-0.5 rounded ml-1">
                                                {event.twg_name.substring(0, 3)}
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
              </div>
            </div>
        </div>
    );
}
