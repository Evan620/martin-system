import { useEffect, useRef } from 'react';

interface SlashCommand {
    command: string;
    description: string;
    template: string;
}

interface SlashCommandPaletteProps {
    visible: boolean;
    query: string;
    onSelect: (template: string) => void;
    onDismiss: () => void;
}

const SLASH_COMMANDS: SlashCommand[] = [
    {
        command: '/schedule',
        description: 'Schedule a TWG meeting',
        template: 'Schedule a meeting for [topic] on [date] at [time]',
    },
    {
        command: '/draft',
        description: 'Draft meeting minutes',
        template: 'Draft minutes for the [TWG] meeting on [date]',
    },
    {
        command: '/action',
        description: 'Create an action item',
        template: 'Create an action item: [task] assigned to [person] due [date]',
    },
    {
        command: '/summarize',
        description: 'Summarize recent activity',
        template: 'Summarize the last [N] meetings for [TWG]',
    },
    {
        command: '/search',
        description: 'Search documents',
        template: 'Search documents for [topic]',
    },
    {
        command: '/agenda',
        description: 'Generate meeting agenda',
        template: 'Generate an agenda for [TWG] meeting on [date]',
    },
];

export default function SlashCommandPalette({
    visible,
    query,
    onSelect,
    onDismiss,
}: SlashCommandPaletteProps) {
    const activeIndexRef = useRef(0);
    const listRef = useRef<HTMLUListElement>(null);

    const filtered = SLASH_COMMANDS.filter(cmd =>
        cmd.command.toLowerCase().includes(query.toLowerCase()) ||
        cmd.description.toLowerCase().includes(query.toLowerCase())
    );

    // Reset active index when filtered list changes
    useEffect(() => {
        activeIndexRef.current = 0;
    }, [query]);

    useEffect(() => {
        if (!visible) return;

        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                onDismiss();
                return;
            }
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndexRef.current = Math.min(activeIndexRef.current + 1, filtered.length - 1);
                highlightItem(activeIndexRef.current);
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndexRef.current = Math.max(activeIndexRef.current - 1, 0);
                highlightItem(activeIndexRef.current);
            }
            if (e.key === 'Enter' && filtered.length > 0) {
                e.preventDefault();
                onSelect(filtered[activeIndexRef.current].template);
            }
        };

        document.addEventListener('keydown', handleKey);
        return () => document.removeEventListener('keydown', handleKey);
    }, [visible, filtered, onSelect, onDismiss]);

    const highlightItem = (index: number) => {
        if (!listRef.current) return;
        const items = listRef.current.querySelectorAll('li');
        items.forEach((item, i) => {
            item.classList.toggle('bg-blue-50', i === index);
            item.classList.toggle('dark:bg-blue-900/30', i === index);
            item.classList.toggle('text-blue-700', i === index);
            item.classList.toggle('dark:text-blue-300', i === index);
            item.classList.toggle('text-slate-700', i !== index);
            item.classList.toggle('dark:text-slate-300', i !== index);
        });
    };

    if (!visible || filtered.length === 0) return null;

    return (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden z-50">
            <div className="px-3 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700">
                <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Commands</p>
            </div>
            <ul ref={listRef} className="py-1 max-h-52 overflow-y-auto">
                {filtered.map((cmd, idx) => (
                    <li
                        key={cmd.command}
                        className={`px-3 py-2 text-xs cursor-pointer flex items-center gap-3 transition-colors
                            ${idx === 0
                                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                            }`}
                        onMouseDown={e => {
                            e.preventDefault();
                            onSelect(cmd.template);
                        }}
                        onMouseEnter={() => {
                            activeIndexRef.current = idx;
                            highlightItem(idx);
                        }}
                    >
                        <span className="font-mono font-bold text-blue-600 dark:text-blue-400 w-20 flex-shrink-0 text-[11px]">
                            {cmd.command}
                        </span>
                        <span className="flex-1 truncate text-slate-500 dark:text-slate-400">{cmd.description}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
