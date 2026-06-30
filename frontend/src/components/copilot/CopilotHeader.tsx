import { useState, useRef, useEffect } from 'react';

interface TWGOption {
    id: string;
    name: string;
}

interface CopilotHeaderProps {
    twgName: string | null;
    twgId: string | null;
    onTwgChange: (id: string | null) => void;
    onClearHistory: () => void;
    onClose: () => void;
    userTwgs: TWGOption[];
    isAdmin: boolean;
}

export default function CopilotHeader({
    twgName, twgId, onTwgChange, onClearHistory, onClose, userTwgs, isAdmin,
}: CopilotHeaderProps) {
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const showSelector = isAdmin || userTwgs.length > 1;

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setDropdownOpen(false);
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const contextLabel = twgName ?? (isAdmin ? 'Supervisor mode' : 'All TWGs');

    return (
        <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderBottom: '1px solid var(--border)',
            background: 'var(--surface)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                <div style={{
                    width: 24, height: 24, border: '1px solid var(--border)', background: 'var(--ink-50)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: "'Geist', serif", fontSize: 13, color: 'var(--accent)', flexShrink: 0,
                }}>M</div>
                <span style={{ fontFamily: "'Geist', serif", fontSize: 15, color: 'var(--ink-900)', letterSpacing: '-0.01em' }}>Martin</span>
                <div style={{ position: 'relative' }} ref={dropdownRef}>
                    <button
                        onClick={() => showSelector && setDropdownOpen(prev => !prev)}
                        style={{
                            display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px',
                            fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 500,
                            fontFamily: 'inherit', color: showSelector ? 'var(--accent)' : 'var(--ink-500)',
                            background: 'transparent', border: '1px solid var(--border)',
                            cursor: showSelector ? 'pointer' : 'default', maxWidth: 160,
                        }}
                    >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{contextLabel}</span>
                        {showSelector && <span style={{ opacity: 0.6, fontSize: 9 }}>▾</span>}
                    </button>
                    {dropdownOpen && (
                        <div style={{
                            position: 'absolute', top: '100%', left: 0, marginTop: 4, width: 240,
                            background: 'var(--surface)', border: '1px solid var(--border)', zIndex: 50, overflow: 'hidden',
                        }}>
                            <div style={{
                                padding: '8px 12px', background: 'var(--ink-50)', borderBottom: '1px solid var(--border)',
                                fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500,
                            }}>Select context</div>
                            <ul style={{ margin: 0, padding: '4px 0', maxHeight: 200, overflowY: 'auto', listStyle: 'none' }}>
                                {isAdmin && (
                                    <li>
                                        <button
                                            onClick={() => { onTwgChange(null); setDropdownOpen(false); }}
                                            style={{
                                                width: '100%', textAlign: 'left', padding: '8px 12px', fontSize: 12, fontFamily: 'inherit',
                                                background: twgId === null ? 'var(--accent-soft)' : 'transparent',
                                                color: twgId === null ? 'var(--accent)' : 'var(--ink-700)',
                                                fontWeight: twgId === null ? 500 : 400,
                                                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                                            }}
                                        >
                                            <span style={{ width: 6, height: 6, borderRadius: 6, background: 'var(--accent)', flexShrink: 0 }} />
                                            All TWGs (Supervisor)
                                        </button>
                                    </li>
                                )}
                                {userTwgs.map(twg => (
                                    <li key={twg.id}>
                                        <button
                                            onClick={() => { onTwgChange(twg.id); setDropdownOpen(false); }}
                                            style={{
                                                width: '100%', textAlign: 'left', padding: '8px 12px', fontSize: 12, fontFamily: 'inherit',
                                                background: twgId === twg.id ? 'var(--accent-soft)' : 'transparent',
                                                color: twgId === twg.id ? 'var(--accent)' : 'var(--ink-700)',
                                                fontWeight: twgId === twg.id ? 500 : 400,
                                                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                                            }}
                                        >
                                            <span style={{ width: 6, height: 6, borderRadius: 6, background: 'var(--ink-400)', flexShrink: 0 }} />
                                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{twg.name}</span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--sage)', fontWeight: 600,
                }}>
                    <span style={{ width: 5, height: 5, borderRadius: 5, background: 'var(--sage)', display: 'inline-block' }} className="animate-pulse" />
                    Live
                </span>
                <button onClick={onClearHistory} title="Clear history" style={{
                    padding: 6, background: 'transparent', border: '1px solid var(--border)',
                    color: 'var(--ink-500)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
                }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 14 }}>delete</span>
                </button>
                <button onClick={onClose} title="Close copilot" style={{
                    padding: 6, background: 'transparent', border: '1px solid var(--border)',
                    color: 'var(--ink-500)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
                }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 14 }}>close</span>
                </button>
            </div>
        </div>
    );
}
