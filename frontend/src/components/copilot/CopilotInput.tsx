import { useState, useRef, useEffect } from 'react';
import { UserRole } from '../../types/auth';
import SlashCommandPalette from './SlashCommandPalette';

interface TWGOption {
    id: string;
    name: string;
}

interface CopilotInputProps {
    value: string;
    onChange: (v: string) => void;
    onSend: () => void;
    onCancel: () => void;
    isStreaming: boolean;
    userTwgs: TWGOption[];
    onMentionInsert: (twgName: string) => void;
    userRole?: UserRole;
}

export default function CopilotInput({
    value,
    onChange,
    onSend,
    onCancel,
    isStreaming,
    userTwgs,
    onMentionInsert,
    userRole,
}: CopilotInputProps) {
    const inputRef = useRef<HTMLInputElement>(null);

    // Slash command palette state
    const [paletteVisible, setPaletteVisible] = useState(false);
    const [slashQuery, setSlashQuery] = useState('');

    // @mention state
    const [showMentions, setShowMentions] = useState(false);
    const [mentionQuery, setMentionQuery] = useState('');
    const [mentionIndex, setMentionIndex] = useState(0);
    const [allTwgs, setAllTwgs] = useState<TWGOption[]>(userTwgs);

    const canMention = userRole === UserRole.ADMIN || userRole === UserRole.SECRETARIAT_LEAD;

    // Load all TWGs for admin/secretariat mention
    useEffect(() => {
        if (canMention && allTwgs.length === 0) {
            import('../../services/twgService').then(mod => {
                mod.default.listDropdown()
                    .then((data: { id: string; name: string }[]) => setAllTwgs(data))
                    .catch(console.error);
            });
        }
    }, [canMention]);

    const filteredTwgs = allTwgs.filter(t =>
        t.name.toLowerCase().includes(mentionQuery.toLowerCase())
    );

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        onChange(val);

        // Slash command detection
        if (val.startsWith('/')) {
            setPaletteVisible(true);
            setSlashQuery(val.slice(1));
        } else {
            setPaletteVisible(false);
            setSlashQuery('');
        }

        // @mention detection
        if (canMention) {
            const words = val.split(' ');
            const lastWord = words[words.length - 1];
            if (lastWord.startsWith('@')) {
                setShowMentions(true);
                setMentionQuery(lastWord.slice(1));
                setMentionIndex(0);
            } else {
                setShowMentions(false);
            }
        }
    };

    const insertMention = (twg: TWGOption) => {
        const words = value.split(' ');
        words.pop();
        const newValue = [...words, `@${twg.name} `].join(' ');
        onChange(newValue);
        onMentionInsert(twg.name);
        setShowMentions(false);
        inputRef.current?.focus();
    };

    const handleSlashSelect = (template: string) => {
        onChange(template);
        setPaletteVisible(false);
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        // Mention navigation
        if (showMentions && filteredTwgs.length > 0) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                setMentionIndex(prev => (prev > 0 ? prev - 1 : filteredTwgs.length - 1));
                return;
            }
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setMentionIndex(prev => (prev < filteredTwgs.length - 1 ? prev + 1 : 0));
                return;
            }
            if (e.key === 'Enter' || e.key === 'Tab') {
                e.preventDefault();
                insertMention(filteredTwgs[mentionIndex]);
                return;
            }
            if (e.key === 'Escape') {
                setShowMentions(false);
                return;
            }
        }

        // Palette dismissal (arrow/enter handled inside SlashCommandPalette via document listener)
        if (paletteVisible && e.key === 'Escape') {
            setPaletteVisible(false);
            return;
        }

        // Send on Enter
        if (e.key === 'Enter' && !paletteVisible && !showMentions) {
            e.preventDefault();
            if (!isStreaming && value.trim()) onSend();
        }
    };

    return (
        <div className="p-3 border-t border-slate-100 dark:border-dark-border bg-slate-50/50 dark:bg-slate-800/20 relative">
            {/* Mentions popup */}
            {showMentions && filteredTwgs.length > 0 && (
                <div className="absolute bottom-full left-4 mb-2 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden z-50">
                    <div className="px-3 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700">
                        <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Mention TWG Agent</p>
                    </div>
                    <ul className="max-h-48 overflow-y-auto py-1">
                        {filteredTwgs.map((twg, idx) => (
                            <li
                                key={twg.id}
                                className={`px-3 py-2 text-xs cursor-pointer flex items-center gap-2 transition-colors
                                    ${idx === mentionIndex
                                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                                    }`}
                                onMouseDown={e => {
                                    e.preventDefault();
                                    insertMention(twg);
                                }}
                            >
                                <div className={`w-3 h-3 rounded-full flex-shrink-0 ${idx === mentionIndex ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'}`} />
                                <span className="font-medium truncate">{twg.name}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Slash command palette */}
            <div className="relative">
                <SlashCommandPalette
                    visible={paletteVisible}
                    query={slashQuery}
                    onSelect={handleSlashSelect}
                    onDismiss={() => setPaletteVisible(false)}
                />

                <div className="flex items-center gap-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={value}
                        onChange={handleChange}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Copilot to analyze, draft, or schedule... (@ TWG, / commands)"
                        className="flex-1 bg-white dark:bg-slate-800 rounded-xl py-3 pl-4 pr-4 text-xs font-medium text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500 transition-all shadow-sm outline-none border border-slate-200 dark:border-slate-700"
                        autoComplete="off"
                    />

                    {/* Cancel button — only while streaming */}
                    {isStreaming && (
                        <button
                            onClick={onCancel}
                            title="Cancel"
                            className="p-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors shadow-sm flex-shrink-0"
                        >
                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                                <rect x="6" y="6" width="12" height="12" rx="1" />
                            </svg>
                        </button>
                    )}

                    {/* Send button */}
                    <button
                        onClick={onSend}
                        disabled={isStreaming || !value.trim()}
                        title="Send"
                        className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-md shadow-blue-900/20 flex-shrink-0"
                    >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
