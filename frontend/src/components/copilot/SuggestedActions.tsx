import { useLocation } from 'react-router-dom';
import { BriefingData } from '../../services/martinService';

interface ActionChip {
    emoji: string;
    label: string;
    template: string;
    color?: 'red' | 'blue' | 'amber' | 'default';
}

interface SuggestedActionsProps {
    onFillInput: (text: string) => void;
    onSubmit: (text: string) => void;
    briefing?: BriefingData | null;
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

const FALLBACK_CHIPS: ActionChip[] = [
    { emoji: '📅', label: "What's on today?", template: "What's on my schedule today?" },
    { emoji: '📁', label: 'Show my projects', template: 'Show me the projects in the pipeline' },
    { emoji: '❓', label: 'Help me navigate', template: 'How do I use the Deal Pipeline?' },
];

function hasPlaceholder(template: string): boolean {
    return /\[.+?\]/.test(template);
}

function getPageChips(pathname: string): ActionChip[] | null {
    for (const [pattern, chips] of Object.entries(SUGGESTED_ACTIONS)) {
        if (pathname.startsWith(pattern)) return chips;
    }
    return null;
}

function getBriefingChips(briefing: BriefingData): ActionChip[] {
    const chips: ActionChip[] = [];

    if (briefing.threshold_alerts.length > 0) {
        const count = briefing.threshold_alerts.length;
        chips.push({
            emoji: '⚠️',
            label: `Fix ${count} gap${count > 1 ? 's' : ''}`,
            template: 'Show me the projects below the gender and youth employment threshold',
            color: 'red',
        });
    }

    if (briefing.upcoming_meetings.length > 0) {
        const m = briefing.upcoming_meetings[0];
        chips.push({
            emoji: '📅',
            label: 'Prep for meeting',
            template: `Help me prepare for the ${m.title} meeting`,
            color: 'blue',
        });
    }

    if (briefing.overdue_items.length > 0) {
        chips.push({
            emoji: '📋',
            label: 'Review notifications',
            template: 'Show me my unread notifications',
            color: 'amber',
        });
    }

    return chips.length > 0 ? chips : FALLBACK_CHIPS;
}

const COLOR_CLASSES: Record<string, string> = {
    red: 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300',
    blue: 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    amber: 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    default: 'bg-slate-100 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-700 dark:hover:text-blue-300',
};

export default function SuggestedActions({ onFillInput, onSubmit, briefing }: SuggestedActionsProps) {
    const { pathname } = useLocation();

    // Priority: page-specific > briefing-driven > fallback
    const pageChips = getPageChips(pathname);
    const chips: ActionChip[] = pageChips
        ? pageChips
        : briefing
        ? getBriefingChips(briefing)
        : FALLBACK_CHIPS;

    const handleChip = (chip: ActionChip) => {
        if (hasPlaceholder(chip.template)) {
            onFillInput(chip.template);
        } else {
            onSubmit(chip.template);
        }
    };

    return (
        <div className="px-3 py-2 flex gap-1.5 flex-wrap border-b border-slate-100 dark:border-slate-700/60">
            {chips.map(chip => {
                const colorClass = COLOR_CLASSES[chip.color ?? 'default'];
                return (
                    <button
                        key={chip.label}
                        onClick={() => handleChip(chip)}
                        className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${colorClass}`}
                    >
                        <span>{chip.emoji}</span>
                        <span>{chip.label}</span>
                    </button>
                );
            })}
        </div>
    );
}
