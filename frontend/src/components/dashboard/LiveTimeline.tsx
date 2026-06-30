import { useNavigate } from 'react-router-dom';
import { TimelineItem } from '../../services/dashboardService';

interface LiveTimelineProps {
    items: TimelineItem[];
}

export default function LiveTimeline({ items }: LiveTimelineProps) {
    const navigate = useNavigate();

    // Group items by date
    // Sort items by date first just in case
    const sortedItems = [...items].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    // Grouping structure: { "2024-01-21": [item1, item2], ... }
    const groupedItems: { [key: string]: TimelineItem[] } = {};

    sortedItems.forEach(item => {
        const dateObj = new Date(item.date);
        const dateKey = dateObj.toISOString().split('T')[0]; // YYYY-MM-DD for stable keys
        if (!groupedItems[dateKey]) {
            groupedItems[dateKey] = [];
        }
        groupedItems[dateKey].push(item);
    });

    const getMonthDay = (dateStr: string) => {
        const date = new Date(dateStr);
        return {
            month: date.toLocaleString('en-US', { month: 'short' }).toUpperCase(),
            day: date.getDate()
        };
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'critical': return 'var(--terra)';
            case 'completed': return 'var(--sage)';
            case 'warning': return 'var(--amber)';
            default: return 'var(--accent)';
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'critical': return 'Critical';
            case 'completed': return 'Done';
            case 'warning': return 'Warning';
            default: return 'Scheduled';
        }
    };

    return (
        <div
            className="p-5 h-full flex flex-col"
            style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-card)',
                overflow: 'hidden',
            }}
        >
            <style>{`
                .no-scrollbar::-webkit-scrollbar {
                    display: none;
                }
                .no-scrollbar {
                    -ms-overflow-style: none;
                    scrollbar-width: none;
                }
            `}</style>

            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h3
                    className="font-display"
                    style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--ink-900)' }}
                >Live Timeline</h3>
                <span className="material-symbols-outlined text-2xl" style={{ color: 'var(--accent)' }}>schedule</span>
            </div>

            {/* Timeline Content */}
            <div className="flex-1 overflow-y-auto no-scrollbar pr-1 max-h-[420px]">
                {Object.entries(groupedItems).length > 0 ? (
                    Object.entries(groupedItems).map(([dateKey, dayItems]) => {
                        const { month, day } = getMonthDay(dateKey);
                        return (
                            <div key={dateKey} className="mb-8 last:mb-0">
                                {/* Date Header with Line */}
                                <div className="flex items-end gap-4 mb-4">
                                    <div className="flex flex-col leading-none">
                                        <span
                                            className="uppercase mb-1"
                                            style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.14em', color: 'var(--ink-500)' }}
                                        >{month}</span>
                                        <span
                                            className="font-mono-geist"
                                            style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.02em', fontFamily: "'Geist Mono', monospace", color: 'var(--ink-900)' }}
                                        >{day}</span>
                                    </div>
                                    <div className="h-px flex-1 mb-2" style={{ background: 'var(--border)' }}></div>
                                </div>

                                {/* Events List */}
                                <div className="space-y-5 pl-2">
                                    {dayItems.map((item, idx) => (
                                        <div key={`${dateKey}-${idx}`} className="flex justify-between items-start gap-3 group cursor-pointer">
                                            <div className="flex-1 pr-2">
                                                <h4
                                                    className="font-bold mb-0.5 transition-colors"
                                                    style={{ fontSize: 13, lineHeight: 1.35, color: 'var(--ink-900)' }}
                                                >{item.title}</h4>
                                                <p
                                                    className="uppercase"
                                                    style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.14em', color: 'var(--ink-500)' }}
                                                >{item.twg}</p>
                                            </div>
                                            {/* Status Pill */}
                                            <span
                                                className="uppercase shrink-0"
                                                style={{
                                                    fontSize: 8, fontWeight: 700, letterSpacing: '0.08em',
                                                    padding: '3px 7px', borderRadius: 999,
                                                    color: getStatusColor(item.status),
                                                    background: `color-mix(in srgb, ${getStatusColor(item.status)} 12%, transparent)`,
                                                }}
                                            >{getStatusLabel(item.status)}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <div className="text-center py-12">
                        <p style={{ fontSize: 12, color: 'var(--ink-400)' }}>No scheduled events.</p>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="mt-6 pt-4">
                <button
                    onClick={() => navigate('/schedule')}
                    className="w-full py-3 rounded-lg transition-colors"
                    style={{
                        fontSize: 12, fontWeight: 600,
                        background: 'var(--surface-2)', color: 'var(--ink-900)',
                        border: '1px solid var(--border)',
                    }}
                >
                    View All Events
                </button>
            </div>
        </div>
    );
}
