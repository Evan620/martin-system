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
            const el = item as HTMLElement;
            el.style.background = i === index ? 'var(--accent-soft)' : 'transparent';
            el.style.color = i === index ? 'var(--accent)' : 'var(--ink-700)';
        });
    };

    if (!visible || filtered.length === 0) return null;

    return (
        <div
            className="absolute bottom-full left-0 right-0 mb-2 overflow-hidden z-50"
            style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-card)',
            }}
        >
            <div
                className="px-3 py-2"
                style={{
                    background: 'var(--surface-2)',
                    borderBottom: '1px solid var(--border)',
                }}
            >
                <p
                    className="text-[10px] font-semibold uppercase"
                    style={{ letterSpacing: '0.14em', color: 'var(--ink-500)' }}
                >
                    Commands
                </p>
            </div>
            <ul ref={listRef} className="py-1 max-h-52 overflow-y-auto">
                {filtered.map((cmd, idx) => (
                    <li
                        key={cmd.command}
                        className="px-3 py-2 text-xs cursor-pointer flex items-center gap-3 qp-transition"
                        style={
                            idx === 0
                                ? { background: 'var(--accent-soft)', color: 'var(--accent)' }
                                : { background: 'transparent', color: 'var(--ink-700)' }
                        }
                        onMouseDown={e => {
                            e.preventDefault();
                            onSelect(cmd.template);
                        }}
                        onMouseEnter={() => {
                            activeIndexRef.current = idx;
                            highlightItem(idx);
                        }}
                    >
                        <span
                            className="font-mono font-bold w-20 flex-shrink-0 text-[11px]"
                            style={{ color: 'var(--accent)' }}
                        >
                            {cmd.command}
                        </span>
                        <span className="flex-1 truncate" style={{ color: 'var(--ink-500)' }}>{cmd.description}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
