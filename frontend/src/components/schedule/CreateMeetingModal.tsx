import { useState, useEffect } from 'react';
import { Card } from '../ui';
import { meetings, twgs, recurringMeetings } from '../../services/api';
import { useAppSelector } from '../../hooks/useRedux';
import { UserRole } from '../../types/auth';
import { eventLocalToUTCISO, EVENT_TIME_ZONE } from '../../utils/dates';

interface CreateMeetingModalProps {
    isOpen: boolean;
    onClose: () => void;
    twgId?: string;
    onSuccess: () => void;
    prefilledDate?: Date | null;
}

type RecurrenceFrequency = 'weekly' | 'biweekly' | 'monthly';
type RecurrenceEndType = 'never' | 'after_date' | 'after_occurrences';

interface RecurrenceState {
    isRecurring: boolean;
    frequency: RecurrenceFrequency;
    endType: RecurrenceEndType;
    endDate: string;
    maxOccurrences: number;
}

export default function CreateMeetingModal({ isOpen, onClose, twgId, onSuccess, prefilledDate }: CreateMeetingModalProps) {
    const [loading, setLoading] = useState(false);
    const [twgList, setTwgList] = useState<any[]>([]);

    // Get user info from Redux
    const user = useAppSelector(state => state.auth.user);
    const isAdmin = user?.role === UserRole.ADMIN;
    const userTwgIds = user?.twg_ids || [];

    // Auto-select TWG for non-admins
    const getInitialTwgId = () => {
        if (twgId) return twgId; // If passed from TWG Workspace, use it
        if (!isAdmin && userTwgIds.length > 0) return userTwgIds[0]; // Auto-select for facilitators
        return '';
    };

    const [selectedTwgId, setSelectedTwgId] = useState(getInitialTwgId());

    const [formData, setFormData] = useState({
        title: '',
        date: '',
        time: '',
        duration: '60',
        location: 'Virtual',
        description: '',
        type: 'virtual' // Default to virtual for Google Meet link generation
    });

    const [recurrence, setRecurrence] = useState<RecurrenceState>({
        isRecurring: false,
        frequency: 'weekly',
        endType: 'never',
        endDate: '',
        maxOccurrences: 10
    });

    // Update date when prefilledDate changes
    useEffect(() => {
        if (prefilledDate) {
            const year = prefilledDate.getFullYear();
            const month = String(prefilledDate.getMonth() + 1).padStart(2, '0');
            const day = String(prefilledDate.getDate()).padStart(2, '0');
            setFormData(prev => ({ ...prev, date: `${year}-${month}-${day}` }));
        }
    }, [prefilledDate]);

    // Load TWGs only if admin and no twgId provided
    useEffect(() => {
        if (isAdmin && !twgId && isOpen) {
            loadTwgs();
        }
    }, [isAdmin, twgId, isOpen]);

    const loadTwgs = async () => {
        try {
            const response = await twgs.dropdown();
            setTwgList(response.data);
        } catch (error) {
            console.error('Failed to load TWGs', error);
        }
    };

    // Get day of week from date (0 = Monday, 6 = Sunday)
    const getDayOfWeek = (dateStr: string): number => {
        if (!dateStr) return 0;
        const date = new Date(dateStr);
        // JavaScript: 0 = Sunday, 6 = Saturday
        // Our format: 0 = Monday, 6 = Sunday
        const jsDay = date.getDay();
        return jsDay === 0 ? 6 : jsDay - 1;
    };

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            // TIMEZONE HANDLING:
            // The entered date/time is always the canonical event timezone (EAT),
            // NOT the creator's browser timezone. We convert EAT -> UTC for storage
            // so the meeting shows the same time for every viewer regardless of where
            // it was scheduled from. (The display side renders stored UTC back to EAT.)
            const scheduledAtUTC = eventLocalToUTCISO(formData.date, formData.time);

            console.log('📅 Entered (EAT):', `${formData.date} ${formData.time}`);
            console.log('⏰ Stored (UTC):', scheduledAtUTC);

            if (recurrence.isRecurring) {
                // Create recurring meeting
                const dayOfWeek = getDayOfWeek(formData.date);
                const effectiveTwgId = twgId || selectedTwgId;

                if (!effectiveTwgId) {
                    alert('Please select a TWG for the recurring meeting.');
                    setLoading(false);
                    return;
                }

                const recurringData = {
                    twg_id: effectiveTwgId,
                    title_template: formData.title,
                    duration_minutes: parseInt(formData.duration),
                    location: formData.location,
                    meeting_type: formData.type,
                    recurrence_rule: {
                        frequency: recurrence.frequency,
                        interval_weeks: 1,
                        day_of_week: dayOfWeek
                    },
                    recurrence_end: {
                        end_type: recurrence.endType,
                        end_date: recurrence.endType === 'after_date' && recurrence.endDate
                            ? new Date(recurrence.endDate).toISOString()
                            : null,
                        max_occurrences: recurrence.endType === 'after_occurrences'
                            ? recurrence.maxOccurrences
                            : null
                    },
                    start_date: scheduledAtUTC,
                    start_time: formData.time,
                    // Generate recurring instances in the canonical event tz (EAT),
                    // not the creator's browser tz, so every instance lands at the
                    // intended EAT wall-clock time.
                    timezone: EVENT_TIME_ZONE,
                };

                console.log('🔄 Creating recurring meeting:', recurringData);
                await recurringMeetings.create(recurringData);
            } else {
                // Create single meeting
                await meetings.create({
                    title: formData.title,
                    twg_id: twgId || selectedTwgId || undefined,
                    scheduled_at: scheduledAtUTC,
                    duration_minutes: parseInt(formData.duration),
                    location: formData.location,
                    meeting_type: formData.type
                });
            }

            onSuccess();
            onClose();
        } catch (error) {
            console.error('Failed to create meeting', error);
            alert('Failed to schedule meeting. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
            <Card className="w-full max-w-lg max-h-[90vh] overflow-y-auto" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                <div className="p-6 flex justify-between items-center sticky top-0 z-10" style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                    <h2 className="text-xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>Schedule New Session</h2>
                    <button onClick={onClose} className="qp-transition" style={{ color: 'var(--ink-400)' }} onMouseEnter={e => (e.currentTarget.style.color = 'var(--ink-600)')} onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-400)')}>
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="qp-eyebrow block mb-1">Session Title</label>
                        <input
                            required
                            type="text"
                            className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                            placeholder="e.g. Policy Framework Review"
                            value={formData.title}
                            onChange={e => setFormData({ ...formData, title: e.target.value })}
                        />
                    </div>

                    {/* Show TWG selector only for admins when no twgId provided */}
                    {!twgId && isAdmin && (
                        <div>
                            <label className="qp-eyebrow block mb-1">Technical Working Group</label>
                            <select
                                required
                                className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                value={selectedTwgId}
                                onChange={e => setSelectedTwgId(e.target.value)}
                            >
                                <option value="">Select TWG...</option>
                                {twgList.map(twg => (
                                    <option key={twg.id} value={twg.id}>{twg.name}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="qp-eyebrow block mb-1">Date</label>
                            <input
                                required
                                type="date"
                                readOnly={!!prefilledDate}
                                className={`w-full px-4 py-2 focus:ring-2 outline-none text-sm ${prefilledDate
                                    ? 'cursor-not-allowed opacity-75'
                                    : ''
                                    }`}
                                style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: prefilledDate ? 'var(--ink-100)' : 'var(--surface-2)', color: prefilledDate ? 'var(--ink-500)' : 'var(--ink-900)' }}
                                value={formData.date}
                                onChange={e => setFormData({ ...formData, date: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="qp-eyebrow block mb-1">Time</label>
                            <div
                                onClick={(e) => {
                                    const input = e.currentTarget.querySelector('input');
                                    input?.showPicker?.();
                                }}
                                className="cursor-pointer"
                            >
                                <input
                                    required
                                    type="time"
                                    className="w-full px-4 py-2 focus:ring-2 outline-none text-sm cursor-pointer"
                                    style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                    value={formData.time}
                                    onChange={e => setFormData({ ...formData, time: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="qp-eyebrow block mb-1">Duration</label>
                            <select
                                className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                value={formData.duration}
                                onChange={e => setFormData({ ...formData, duration: e.target.value })}
                            >
                                <option value="30">30 Minutes</option>
                                <option value="60">1 Hour</option>
                                <option value="90">1.5 Hours</option>
                                <option value="120">2 Hours</option>
                            </select>
                        </div>
                        <div>
                            <label className="qp-eyebrow block mb-1">Meeting Type</label>
                            <select
                                className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                value={formData.type}
                                onChange={e => setFormData({
                                    ...formData,
                                    type: e.target.value,
                                    location: e.target.value === 'virtual' ? 'Virtual' : ''
                                })}
                            >
                                <option value="virtual">Virtual (Google Meet)</option>
                                <option value="in_person">In-Person</option>
                            </select>
                        </div>
                    </div>

                    {formData.type === 'in_person' && (
                        <div>
                            <label className="qp-eyebrow block mb-1">Location / Venue</label>
                            <input
                                required
                                type="text"
                                placeholder="e.g. Conference Room A, ECOWAS HQ"
                                className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                value={formData.location}
                                onChange={e => setFormData({ ...formData, location: e.target.value })}
                            />
                        </div>
                    )}

                    {/* Recurring Meeting Section */}
                    <div className="pt-4 mt-4" style={{ borderTop: '1px solid var(--border)' }}>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={recurrence.isRecurring}
                                onChange={e => setRecurrence({ ...recurrence, isRecurring: e.target.checked })}
                                className="w-5 h-5 rounded"
                                style={{ accentColor: 'var(--accent)' }}
                            />
                            <span className="text-sm font-medium" style={{ color: 'var(--ink-700)' }}>
                                Make this a recurring meeting
                            </span>
                        </label>

                        {recurrence.isRecurring && (
                            <div className="mt-4 space-y-4 pl-8" style={{ borderLeft: '2px solid var(--accent-soft)' }}>
                                {/* Frequency */}
                                <div>
                                    <label className="qp-eyebrow block mb-1">Repeat</label>
                                    <select
                                        className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                        value={recurrence.frequency}
                                        onChange={e => setRecurrence({ ...recurrence, frequency: e.target.value as RecurrenceFrequency })}
                                    >
                                        <option value="weekly">Weekly</option>
                                        <option value="biweekly">Bi-weekly (Every 2 weeks)</option>
                                        <option value="monthly">Monthly</option>
                                    </select>
                                </div>

                                {/* End Condition */}
                                <div>
                                    <label className="qp-eyebrow block mb-2">End Condition</label>
                                    <div className="space-y-2">
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="radio"
                                                name="endType"
                                                value="never"
                                                checked={recurrence.endType === 'never'}
                                                onChange={() => setRecurrence({ ...recurrence, endType: 'never' })}
                                                className="w-4 h-4"
                                                style={{ accentColor: 'var(--accent)' }}
                                            />
                                            <span className="text-sm" style={{ color: 'var(--ink-700)' }}>Never (keep generating)</span>
                                        </label>
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="radio"
                                                name="endType"
                                                value="after_date"
                                                checked={recurrence.endType === 'after_date'}
                                                onChange={() => setRecurrence({ ...recurrence, endType: 'after_date' })}
                                                className="w-4 h-4"
                                                style={{ accentColor: 'var(--accent)' }}
                                            />
                                            <span className="text-sm" style={{ color: 'var(--ink-700)' }}>On a specific date</span>
                                        </label>
                                        <label className="flex items-center gap-2">
                                            <input
                                                type="radio"
                                                name="endType"
                                                value="after_occurrences"
                                                checked={recurrence.endType === 'after_occurrences'}
                                                onChange={() => setRecurrence({ ...recurrence, endType: 'after_occurrences' })}
                                                className="w-4 h-4"
                                                style={{ accentColor: 'var(--accent)' }}
                                            />
                                            <span className="text-sm" style={{ color: 'var(--ink-700)' }}>After a number of meetings</span>
                                        </label>
                                    </div>
                                </div>

                                {/* Conditional End Date */}
                                {recurrence.endType === 'after_date' && (
                                    <div>
                                        <label className="qp-eyebrow block mb-1">End Date</label>
                                        <input
                                            type="date"
                                            required
                                            min={formData.date}
                                            className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                            value={recurrence.endDate}
                                            onChange={e => setRecurrence({ ...recurrence, endDate: e.target.value })}
                                        />
                                    </div>
                                )}

                                {/* Conditional Max Occurrences */}
                                {recurrence.endType === 'after_occurrences' && (
                                    <div>
                                        <label className="qp-eyebrow block mb-1">Number of Meetings</label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="100"
                                            required
                                            className="w-full px-4 py-2 focus:ring-2 outline-none text-sm"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--ink-900)' }}
                                            value={recurrence.maxOccurrences}
                                            onChange={e => setRecurrence({ ...recurrence, maxOccurrences: parseInt(e.target.value) || 10 })}
                                        />
                                        <p className="text-xs mt-1" style={{ color: 'var(--ink-500)' }}>Will generate {recurrence.maxOccurrences} meeting instances</p>
                                    </div>
                                )}

                                <p className="text-xs italic" style={{ color: 'var(--ink-500)' }}>
                                    Meetings will be automatically generated 30 days in advance.
                                </p>
                            </div>
                        )}
                    </div>

                    <div className="pt-4 flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-2.5 font-bold qp-transition clickable-scale"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', color: 'var(--ink-600)', background: 'transparent' }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="flex-1 py-2.5 font-bold qp-transition disabled:opacity-50 flex items-center justify-center gap-2 clickable-scale"
                            style={{ borderRadius: 'var(--radius-ctl)', background: 'var(--accent)', color: 'var(--accent-ink)' }}
                        >
                            {loading
                                ? 'Scheduling...'
                                : recurrence.isRecurring
                                    ? 'Create Recurring Series'
                                    : 'Schedule Session'
                            }
                        </button>
                    </div>
                </form>
            </Card>
        </div>
    );
}
