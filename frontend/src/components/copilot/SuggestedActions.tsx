import { useLocation } from 'react-router-dom';

interface ActionChip {
    emoji: string;
    label: string;
    template: string;
}

interface SuggestedActionsProps {
    onFillInput: (text: string) => void;
    onSubmit: (text: string) => void;
}

const SUGGESTED_ACTIONS: Record<string, ActionChip[]> = {
    '/workspace': [
        { emoji: '📅', label: 'Draft agenda', template: 'Draft an agenda for the next [TWG] meeting on [date]' },
        { emoji: '🗓', label: 'Schedule', template: 'Schedule a meeting for [topic] on [date] at [time]' },
        { emoji: '📋', label: 'Summarize docs', template: 'Summarize the latest documents in this workspace' },
        { emoji: '✅', label: 'Add action', template: 'Create an action item: [task] assigned to [person] due [date]' },
    ],
    '/meetings': [
        { emoji: '🗓', label: 'Schedule meeting', template: 'Schedule a meeting for [topic] on [date] at [time]' },
        { emoji: '📝', label: 'Draft minutes', template: 'Draft minutes for the [TWG] meeting on [date]' },
        { emoji: '⚠️', label: 'Check conflicts', template: 'Check for scheduling conflicts in the next 2 weeks' },
        { emoji: '📅', label: 'View agenda', template: 'Show the agenda for the upcoming [TWG] meeting' },
    ],
    '/documents': [
        { emoji: '📄', label: 'Summarize', template: 'Summarize the most recent documents' },
        { emoji: '✍️', label: 'Draft brief', template: 'Draft a brief on [topic] for [TWG]' },
        { emoji: '🔍', label: 'Search by topic', template: 'Search documents for [topic]' },
        { emoji: '📋', label: 'Export list', template: 'List all documents shared with [TWG]' },
    ],
};

const DEFAULT_CHIPS: ActionChip[] = [
    { emoji: '💬', label: 'Ask a question', template: 'What is the status of [topic]?' },
    { emoji: '📝', label: 'Draft report', template: 'Draft a report on [topic] for [TWG]' },
    { emoji: '📅', label: 'Check schedule', template: 'What meetings are scheduled this week?' },
    { emoji: '✅', label: 'Add task', template: 'Create an action item: [task] assigned to [person] due [date]' },
];

function hasPlaceholder(template: string): boolean {
    return /\[.+?\]/.test(template);
}

function getChipsForPath(pathname: string): ActionChip[] {
    for (const [pattern, chips] of Object.entries(SUGGESTED_ACTIONS)) {
        if (pathname.startsWith(pattern)) return chips;
    }
    return DEFAULT_CHIPS;
}

export default function SuggestedActions({ onFillInput, onSubmit }: SuggestedActionsProps) {
    const { pathname } = useLocation();
    const chips = getChipsForPath(pathname);

    const handleChip = (chip: ActionChip) => {
        if (hasPlaceholder(chip.template)) {
            onFillInput(chip.template);
        } else {
            onSubmit(chip.template);
        }
    };

    return (
        <div className="px-3 py-2 flex gap-1.5 flex-wrap border-b border-slate-100 dark:border-slate-700/60">
            {chips.map(chip => (
                <button
                    key={chip.label}
                    onClick={() => handleChip(chip)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 text-xs font-medium hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                >
                    <span>{chip.emoji}</span>
                    <span>{chip.label}</span>
                </button>
            ))}
        </div>
    );
}
