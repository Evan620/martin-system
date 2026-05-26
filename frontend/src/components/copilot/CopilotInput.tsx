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
        <div style={{
            padding: 12, borderTop: '1px solid var(--border)', background: 'var(--surface)',
            position: 'relative', fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
        }}>
            {showMentions && filteredTwgs.length > 0 && (
                <div style={{
                    position: 'absolute', bottom: '100%', left: 16, marginBottom: 8, width: 240,
                    background: 'var(--surface)', border: '1px solid var(--border)', overflow: 'hidden', zIndex: 50,
                }}>
                    <div style={{
                        padding: '8px 12px', background: 'var(--ink-50)', borderBottom: '1px solid var(--border)',
                        fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500,
                    }}>Mention TWG agent</div>
                    <ul style={{ margin: 0, padding: '4px 0', maxHeight: 200, overflowY: 'auto', listStyle: 'none' }}>
                        {filteredTwgs.map((twg, idx) => (
                            <li
                                key={twg.id}
                                style={{
                                    padding: '8px 12px', fontSize: 12, cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', gap: 8,
                                    background: idx === mentionIndex ? 'var(--accent-soft)' : 'transparent',
                                    color: idx === mentionIndex ? 'var(--accent)' : 'var(--ink-700)',
                                    fontWeight: idx === mentionIndex ? 500 : 400,
                                }}
                                onMouseDown={e => { e.preventDefault(); insertMention(twg); }}
                            >
                                <span style={{
                                    width: 6, height: 6, borderRadius: 6,
                                    background: idx === mentionIndex ? 'var(--accent)' : 'var(--ink-400)',
                                    flexShrink: 0, display: 'inline-block',
                                }} />
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{twg.name}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            <div style={{ position: 'relative' }}>
                <SlashCommandPalette
                    visible={paletteVisible}
                    query={slashQuery}
                    onSelect={handleSlashSelect}
                    onDismiss={() => setPaletteVisible(false)}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                        ref={inputRef}
                        type="text"
                        value={value}
                        onChange={handleChange}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Copilot to analyze, draft, or schedule… (@ TWG, / commands)"
                        autoComplete="off"
                        style={{
                            flex: 1, background: 'var(--ink-50)', border: '1px solid var(--border)',
                            padding: '10px 14px', fontSize: 12, fontFamily: 'inherit',
                            color: 'var(--ink-900)', outline: 'none', boxSizing: 'border-box',
                        }}
                    />
                    {isStreaming && (
                        <button
                            onClick={onCancel}
                            title="Cancel"
                            style={{
                                padding: 9, flexShrink: 0, background: 'transparent', border: '1px solid var(--terra)',
                                color: 'var(--terra)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
                            }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>stop</span>
                        </button>
                    )}
                    <button
                        onClick={onSend}
                        disabled={isStreaming || !value.trim()}
                        title="Send"
                        style={{
                            padding: 9, flexShrink: 0, background: 'var(--accent)', border: '1px solid var(--accent)',
                            color: 'var(--accent-ink)',
                            cursor: (isStreaming || !value.trim()) ? 'default' : 'pointer',
                            opacity: (isStreaming || !value.trim()) ? 0.4 : 1,
                            display: 'inline-flex', alignItems: 'center',
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>arrow_forward</span>
                    </button>
                </div>
            </div>
        </div>
    );
}
