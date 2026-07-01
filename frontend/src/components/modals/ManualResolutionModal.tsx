import React, { useState, useEffect } from 'react';

interface ManualResolutionModalProps {
    isOpen: boolean;
    conflict: any;
    onClose: () => void;
    onResolve: (resolutionType: string, meetingId: string, newTime?: string, reason?: string) => Promise<void>;
}

const ManualResolutionModal: React.FC<ManualResolutionModalProps> = ({ isOpen, conflict, onClose, onResolve }) => {
    const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
    const [action, setAction] = useState<'reschedule' | 'cancel'>('reschedule');
    const [newTime, setNewTime] = useState<string>('');
    const [reason, setReason] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [meetingMap, setMeetingMap] = useState<any[]>([]);

    useEffect(() => {
        if (conflict && conflict.conflicting_positions) {
            // Parse conflicting positions to extract meeting IDs
            // Structure expected: { "meeting_1": "uuid", "meeting_2": "uuid", ... }
            const meetings = [];
            if (conflict.conflicting_positions.meeting_1) {
                meetings.push({
                    id: conflict.conflicting_positions.meeting_1,
                    label: "Meeting A",
                    name: conflict.agents_involved && conflict.agents_involved[0] ? conflict.agents_involved[0] : "Agent 1 Meeting"
                });
            }
            if (conflict.conflicting_positions.meeting_2) {
                meetings.push({
                    id: conflict.conflicting_positions.meeting_2,
                    label: "Meeting B",
                    name: conflict.agents_involved && conflict.agents_involved[1] ? conflict.agents_involved[1] : "Agent 2 Meeting"
                });
            }
            setMeetingMap(meetings);
            if (meetings.length > 0) setSelectedMeetingId(meetings[0].id);
        }
    }, [conflict]);

    if (!isOpen || !conflict) return null;

    const handleSubmit = async () => {
        if (!selectedMeetingId) return;
        if (action === 'reschedule' && !newTime) return;

        setLoading(true);
        try {
            await onResolve(action, selectedMeetingId, newTime, reason);
            onClose();
        } catch (error) {
            console.error("Resolution failed", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            <div className="absolute inset-0 backdrop-blur-sm" style={{ background: 'color-mix(in srgb, var(--ink-900) 55%, transparent)' }} onClick={onClose} />

            <div className="relative w-full max-w-lg overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                {/* Header */}
                <div className="px-6 py-4 flex justify-between items-center" style={{ background: 'color-mix(in srgb, var(--terra) 8%, var(--surface))', borderBottom: '1px solid color-mix(in srgb, var(--terra) 20%, var(--border))' }}>
                    <div>
                        <h2 className="text-lg font-display font-bold flex items-center gap-2" style={{ color: 'var(--terra)' }}>
                            <span className="material-symbols-outlined">gavel</span>
                            Manual Intervention Required
                        </h2>
                        <p className="text-xs" style={{ color: 'color-mix(in srgb, var(--terra) 75%, var(--ink-500))' }}>Override AI Escalation for Conflict: {conflict.description}</p>
                    </div>
                    <button onClick={onClose} className="clickable-scale qp-transition" style={{ color: 'var(--ink-400)' }}>
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {/* 1. Select Meeting to Act Upon */}
                    <div>
                        <label className="qp-eyebrow mb-2 block">1. Select Target Meeting</label>
                        <div className="grid grid-cols-2 gap-3">
                            {meetingMap.map((m) => (
                                <div
                                    key={m.id}
                                    onClick={() => setSelectedMeetingId(m.id)}
                                    className="p-3 cursor-pointer transition-all clickable-scale"
                                    style={{
                                        borderRadius: 'var(--radius-ctl)',
                                        border: `2px solid ${selectedMeetingId === m.id ? 'var(--accent)' : 'var(--border)'}`,
                                        background: selectedMeetingId === m.id ? 'var(--accent-soft)' : 'var(--surface)',
                                    }}
                                >
                                    <div className="font-bold text-sm" style={{ color: 'var(--ink-900)' }}>{m.label}</div>
                                    <div className="text-xs truncate" style={{ color: 'var(--ink-500)' }}>{m.name}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 2. Select Action */}
                    <div>
                        <label className="qp-eyebrow mb-2 block">2. Choose Action</label>
                        <div className="flex gap-4">
                            <button
                                onClick={() => setAction('reschedule')}
                                className="flex-1 py-2 text-sm font-bold transition-all clickable-scale"
                                style={{
                                    borderRadius: 'var(--radius-ctl)',
                                    border: `1px solid ${action === 'reschedule' ? 'var(--ink-900)' : 'var(--border)'}`,
                                    background: action === 'reschedule' ? 'var(--ink-900)' : 'var(--surface)',
                                    color: action === 'reschedule' ? 'var(--surface)' : 'var(--ink-600)',
                                }}
                            >
                                Reschedule
                            </button>
                            <button
                                onClick={() => setAction('cancel')}
                                className="flex-1 py-2 text-sm font-bold transition-all clickable-scale"
                                style={{
                                    borderRadius: 'var(--radius-ctl)',
                                    border: `1px solid ${action === 'cancel' ? 'var(--terra)' : 'var(--border)'}`,
                                    background: action === 'cancel' ? 'var(--terra)' : 'var(--surface)',
                                    color: action === 'cancel' ? 'var(--accent-ink)' : 'var(--ink-600)',
                                }}
                            >
                                Cancel Meeting
                            </button>
                        </div>
                    </div>

                    {/* 3. Action Details */}
                    {action === 'reschedule' && (
                        <div>
                            <label className="qp-eyebrow mb-2 block">3. New Time</label>
                            <input
                                type="datetime-local"
                                value={newTime}
                                onChange={(e) => setNewTime(e.target.value)}
                                className="w-full px-4 py-2 text-sm outline-none focus:ring-2"
                                style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--ink-900)' }}
                            />
                        </div>
                    )}

                    <div>
                        <label className="qp-eyebrow mb-2 block">Reason (Log)</label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Reason for decision..."
                            className="w-full px-4 py-2 text-sm h-20 resize-none outline-none focus:ring-2"
                            style={{ borderRadius: 'var(--radius-ctl)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--ink-900)' }}
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 flex justify-end gap-3" style={{ background: 'var(--surface-2)', borderTop: '1px solid var(--border)' }}>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-bold qp-transition clickable-scale"
                        style={{ color: 'var(--ink-500)' }}
                    >
                        Close
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !selectedMeetingId || (action === 'reschedule' && !newTime)}
                        className="px-6 py-2 text-sm font-bold transition-all active:scale-95"
                        style={{
                            borderRadius: 'var(--radius-ctl)',
                            color: 'var(--accent-ink)',
                            background: action === 'cancel' ? 'var(--terra)' : 'var(--accent)',
                            opacity: loading ? 0.5 : 1,
                            cursor: loading ? 'not-allowed' : 'pointer',
                        }}
                    >
                        {loading ? 'Processing...' : 'Confirm Resolution'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ManualResolutionModal;
