
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
            <div className="flex h-[400px] items-center justify-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col h-full">
            {/* Header / Navigation */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-900 rounded-lg p-1">
                        <button onClick={prevMonth} className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md text-slate-500">
                            <span className="material-symbols-outlined text-lg">chevron_left</span>
                        </button>
                        <button onClick={resetDate} className="px-3 text-sm font-bold text-slate-700 dark:text-slate-200 min-w-[120px] text-center">
                            {format(currentDate, 'MMMM yyyy')}
                        </button>
                        <button onClick={nextMonth} className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md text-slate-500">
                            <span className="material-symbols-outlined text-lg">chevron_right</span>
                        </button>
                    </div>
                </div>

                {/* Legend */}
                <div className="flex items-center gap-3 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
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

            {/* Weekday Headers */}
            <div className="grid grid-cols-7 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                {weekDays.map(day => (
                    <div key={day} className="py-2 text-center text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        {day}
                    </div>
                ))}
            </div>

            {/* Days Grid */}
            <div className="grid grid-cols-7 flex-1 auto-rows-[minmax(100px,auto)]">
                {calendarDays.map((day) => {
                    const dayEvents = getEventsForDay(day);
                    const isCurrentMonth = isSameMonth(day, monthStart);
                    const isTodayDate = isToday(day);

                    return (
                        <div
                            key={day.toString()}
                            onClick={() => onDateClick?.(day)}
                            className={`
                                border-b border-r border-slate-100 dark:border-slate-700/50 p-2 relative group flex flex-col cursor-pointer transition-colors
                                ${!isCurrentMonth ? 'bg-slate-50/50 dark:bg-slate-900/30 text-slate-300 dark:text-slate-700' : 'bg-white dark:bg-slate-800 hover:bg-blue-50/10'}
                                ${isTodayDate ? 'bg-blue-50/30 dark:bg-blue-900/10' : ''}
                            `}
                        >
                            <div className="flex justify-between items-start mb-1 shrink-0">
                                <span className={`
                                    text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full
                                    ${isTodayDate ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-700 dark:text-slate-400'}
                                    ${!isCurrentMonth ? 'opacity-30' : ''}
                                `}>
                                    {format(day, 'd')}
                                </span>
                            </div>

                            <div className="space-y-1 flex-1">
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
                                                : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-100 dark:border-blue-800 hover:bg-blue-100'}
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
    );
}
