import { useState, useEffect } from 'react';

// ActionRequiredEvent — defined here in case useAgentStream doesn't yet export it.
// When the other agent adds it to useAgentStream.ts, import from there instead.
export interface ActionRequiredEvent {
    type: 'action_required';
    action_id: string;
    action_type: 'schedule_meeting' | 'create_action_item' | 'draft_document';
    payload: Record<string, unknown>;
    confirm_endpoint: string;
}

type CardState = 'pending' | 'editing' | 'success' | 'cancelled' | 'expired';

interface ActionConfirmCardProps {
    event: ActionRequiredEvent;
    onExecute: (actionId: string, confirmed: boolean, edits?: Record<string, unknown>) => void;
}

const TTL_MS = 10 * 60 * 1000; // 10 minutes

const ACTION_LABELS: Record<string, string> = {
    schedule_meeting: '📅 SCHEDULE MEETING',
    create_action_item: '✅ CREATE ACTION ITEM',
    draft_document: '📄 DRAFT DOCUMENT',
};

function FieldRow({ label, value }: { label: string; value: string }) {
    if (!value) return null;
    return (
        <div className="flex items-start gap-2 text-xs">
            <span className="text-slate-500 dark:text-slate-400 w-20 flex-shrink-0">{label}:</span>
            <span className="text-slate-800 dark:text-slate-200 font-medium">{value}</span>
        </div>
    );
}

function EditInput({
    label, fieldKey, value, onChange,
}: {
    label: string;
    fieldKey: string;
    value: string;
    onChange: (key: string, value: string) => void;
}) {
    return (
        <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 dark:text-slate-400 w-20 flex-shrink-0">{label}:</span>
            <input
                type="text"
                value={value}
                onChange={e => onChange(fieldKey, e.target.value)}
                className="flex-1 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-md px-2 py-1 text-xs text-slate-800 dark:text-slate-200 outline-none focus:ring-2 focus:ring-teal-500"
            />
        </div>
    );
}

function getMeetingFields(payload: Record<string, unknown>) {
    return [
        { label: 'Title', key: 'title' },
        { label: 'Date', key: 'date' },
        { label: 'Duration', key: 'duration' },
        { label: 'TWG', key: 'twg' },
        { label: 'Invitees', key: 'invitees' },
    ].filter(f => payload[f.key] !== undefined);
}

function getActionItemFields(payload: Record<string, unknown>) {
    return [
        { label: 'Title', key: 'title' },
        { label: 'Assignee', key: 'assignee' },
        { label: 'Due date', key: 'due_date' },
        { label: 'TWG', key: 'twg' },
        { label: 'Priority', key: 'priority' },
    ].filter(f => payload[f.key] !== undefined);
}

function getDocumentFields(payload: Record<string, unknown>) {
    return [
        { label: 'Title', key: 'title' },
        { label: 'Type', key: 'type' },
        { label: 'TWG', key: 'twg' },
    ].filter(f => payload[f.key] !== undefined);
}

function getFields(actionType: string, payload: Record<string, unknown>) {
    if (actionType === 'schedule_meeting') return getMeetingFields(payload);
    if (actionType === 'create_action_item') return getActionItemFields(payload);
    return getDocumentFields(payload);
}

export default function ActionConfirmCard({ event, onExecute }: ActionConfirmCardProps) {
    const [cardState, setCardState] = useState<CardState>('pending');
    const [edits, setEdits] = useState<Record<string, string>>({});
    const [successMessage, setSuccessMessage] = useState('');
    // Expire after TTL
    useEffect(() => {
        const timer = setTimeout(() => {
            setCardState(prev => (prev === 'pending' || prev === 'editing') ? 'expired' : prev);
        }, TTL_MS);
        return () => clearTimeout(timer);
    }, []);

    const fields = getFields(event.action_type, event.payload);

    const handleEditChange = (key: string, value: string) => {
        setEdits(prev => ({ ...prev, [key]: value }));
    };

    const handleConfirm = () => {
        const finalEdits = Object.keys(edits).length > 0 ? edits : undefined;
        onExecute(event.action_id, true, finalEdits);
        setSuccessMessage(
            event.action_type === 'schedule_meeting' ? 'Meeting scheduled.' :
            event.action_type === 'create_action_item' ? 'Action item created.' :
            'Document saved to library.'
        );
        setCardState('success');
    };

    const handleCancel = () => {
        onExecute(event.action_id, false);
        setCardState('cancelled');
    };

    const headerLabel = ACTION_LABELS[event.action_type] ?? event.action_type.toUpperCase();

    if (cardState === 'success') {
        return (
            <div className="bg-[var(--surface)] rounded-2xl border border-green-200/60 dark:border-green-800/40 px-4 py-3">
                <p className="text-xs font-bold text-green-600 dark:text-green-400">Done — {successMessage}</p>
            </div>
        );
    }

    if (cardState === 'cancelled') {
        return (
            <div className="bg-[var(--surface)] rounded-2xl border border-[var(--border)] px-4 py-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Cancelled</p>
            </div>
        );
    }

    if (cardState === 'expired') {
        return (
            <div className="bg-[var(--surface)] rounded-2xl border border-[var(--border)] px-4 py-3">
                <p className="text-xs text-slate-400 dark:text-slate-500 italic">This action has expired.</p>
            </div>
        );
    }

    return (
        <div className="bg-[var(--surface)] rounded-2xl border border-teal-100/40 dark:border-teal-800/30 overflow-hidden">
            {/* Card header */}
            <div className="px-4 pt-3 pb-2 border-b border-slate-100/80 dark:border-slate-700/50">
                <span className="text-[11px] font-bold text-teal-700 dark:text-teal-300 uppercase tracking-wide">{headerLabel}</span>
            </div>

            {/* Fields */}
            <div className="px-4 py-3 space-y-1.5">
                {fields.map(f => (
                    cardState === 'editing' ? (
                        <EditInput
                            key={f.key}
                            label={f.label}
                            fieldKey={f.key}
                            value={edits[f.key] ?? String(event.payload[f.key] ?? '')}
                            onChange={handleEditChange}
                        />
                    ) : (
                        <FieldRow key={f.key} label={f.label} value={String(event.payload[f.key] ?? '')} />
                    )
                ))}

                {/* Draft preview for draft_document */}
                {event.action_type === 'draft_document' && Boolean(event.payload.draft_text) && (
                    <div className="mt-2">
                        <p className="text-[10px] font-bold uppercase text-slate-400 mb-1">Draft preview</p>
                        <p className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 rounded-lg p-2 line-clamp-4">
                            {String(event.payload.draft_text ?? '').slice(0, 300)}
                        </p>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="px-4 pb-3 flex items-center gap-2 border-t border-slate-100/80 dark:border-slate-700/50 pt-3">
                <button
                    onClick={handleConfirm}
                    className="clickable-scale px-3 py-1.5 bg-teal-600 text-white text-xs font-semibold rounded-lg hover:bg-teal-700 transition-colors"
                >
                    {event.action_type === 'draft_document' ? 'Save to Library' : '✓ Confirm'}
                </button>
                {event.action_type !== 'draft_document' && (
                    <button
                        onClick={() => setCardState(cardState === 'editing' ? 'pending' : 'editing')}
                        className="clickable-scale px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-semibold rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    >
                        {cardState === 'editing' ? 'Back' : '✎ Edit'}
                    </button>
                )}
                <button
                    onClick={handleCancel}
                    className="clickable-scale px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-semibold rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors ml-auto"
                >
                    ✕ Cancel
                </button>
            </div>
        </div>
    );
}
