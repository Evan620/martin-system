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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />

            <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg overflow-hidden border border-slate-200 dark:border-slate-700">
                {/* Header */}
                <div className="bg-red-50 dark:bg-red-900/20 px-6 py-4 border-b border-red-100 dark:border-red-900/30 flex justify-between items-center">
                    <div>
                        <h2 className="text-lg font-display font-bold text-red-700 dark:text-red-400 flex items-center gap-2">
                            <span className="material-symbols-outlined">gavel</span>
                            Manual Intervention Required
                        </h2>
                        <p className="text-xs text-red-600/70 dark:text-red-400/70">Override AI Escalation for Conflict: {conflict.description}</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 clickable-scale">
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {/* 1. Select Meeting to Act Upon */}
                    <div>
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">1. Select Target Meeting</label>
                        <div className="grid grid-cols-2 gap-3">
                            {meetingMap.map((m) => (
                                <div
                                    key={m.id}
                                    onClick={() => setSelectedMeetingId(m.id)}
                                    className={`p-3 rounded-xl border-2 cursor-pointer transition-all clickable-scale ${selectedMeetingId === m.id
                                            ? 'border-teal-500 bg-teal-50 dark:bg-teal-900/20'
                                            : 'border-slate-100 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                                        }`}
                                >
                                    <div className="font-bold text-sm text-slate-900 dark:text-white">{m.label}</div>
                                    <div className="text-xs text-slate-500 truncate">{m.name}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 2. Select Action */}
                    <div>
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">2. Choose Action</label>
                        <div className="flex gap-4">
                            <button
                                onClick={() => setAction('reschedule')}
                                className={`flex-1 py-2 rounded-lg text-sm font-bold border transition-all clickable-scale ${action === 'reschedule'
                                        ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900'
                                        : 'border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400'
                                    }`}
                            >
                                Reschedule
                            </button>
                            <button
                                onClick={() => setAction('cancel')}
                                className={`flex-1 py-2 rounded-lg text-sm font-bold border transition-all clickable-scale ${action === 'cancel'
                                        ? 'bg-red-600 text-white border-red-600'
                                        : 'border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400'
                                    }`}
                            >
                                Cancel Meeting
                            </button>
                        </div>
                    </div>

                    {/* 3. Action Details */}
                    {action === 'reschedule' && (
                        <div>
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">3. New Time</label>
                            <input
                                type="datetime-local"
                                value={newTime}
                                onChange={(e) => setNewTime(e.target.value)}
                                className="w-full px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:ring-2 focus:ring-teal-500 outline-none"
                            />
                        </div>
                    )}

                    <div>
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">Reason (Log)</label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Reason for decision..."
                            className="w-full px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm h-20 resize-none outline-none focus:ring-2 focus:ring-teal-500"
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="bg-slate-50 dark:bg-slate-800/50 px-6 py-4 flex justify-end gap-3 border-t border-slate-100 dark:border-slate-700">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors clickable-scale"
                    >
                        Close
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !selectedMeetingId || (action === 'reschedule' && !newTime)}
                        className={`px-6 py-2 rounded-xl text-sm font-bold text-white shadow-lg transition-all active:scale-95 ${loading ? 'opacity-50 cursor-not-allowed' :
                                action === 'cancel' ? 'bg-red-600 hover:bg-red-700 shadow-red-500/20' : 'bg-teal-600 hover:bg-teal-700 shadow-teal-500/20'
                            }`}
                    >
                        {loading ? 'Processing...' : 'Confirm Resolution'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ManualResolutionModal;
