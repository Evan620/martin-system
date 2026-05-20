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
    twgName,
    twgId,
    onTwgChange,
    onClearHistory,
    onClose,
    userTwgs,
    isAdmin,
}: CopilotHeaderProps) {
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const showSelector = isAdmin || userTwgs.length > 1;

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const contextLabel = twgName ?? (isAdmin ? 'Supervisor Mode' : 'All TWGs');

    return (
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700/60">
            {/* Left: Avatar + Name + TWG chip */}
            <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-blue-900/20">
                    <span className="text-white text-sm font-bold leading-none">✦</span>
                </div>
                <span className="text-sm font-bold text-slate-900 dark:text-white">Martin</span>

                {/* TWG context chip */}
                <div className="relative" ref={dropdownRef}>
                    <button
                        onClick={() => showSelector && setDropdownOpen(prev => !prev)}
                        className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors
                            ${showSelector
                                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 cursor-pointer'
                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 cursor-default'
                            }`}
                    >
                        <span className="max-w-[120px] truncate">{contextLabel}</span>
                        {showSelector && <span className="opacity-60">▾</span>}
                    </button>

                    {dropdownOpen && (
                        <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden z-50">
                            <div className="px-3 py-2 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700">
                                <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Select Context</p>
                            </div>
                            <ul className="py-1 max-h-48 overflow-y-auto">
                                {isAdmin && (
                                    <li>
                                        <button
                                            onClick={() => { onTwgChange(null); setDropdownOpen(false); }}
                                            className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors
                                                ${twgId === null
                                                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                                                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                                                }`}
                                        >
                                            <span className="w-2 h-2 rounded-full bg-purple-400 flex-shrink-0" />
                                            All TWGs (Supervisor mode)
                                        </button>
                                    </li>
                                )}
                                {userTwgs.map(twg => (
                                    <li key={twg.id}>
                                        <button
                                            onClick={() => { onTwgChange(twg.id); setDropdownOpen(false); }}
                                            className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors
                                                ${twgId === twg.id
                                                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                                                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                                                }`}
                                        >
                                            <span className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                                            <span className="truncate">{twg.name}</span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>

            {/* Right: Live indicator + controls */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
                <span className="flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400 font-bold uppercase">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Live
                </span>
                <button
                    onClick={onClearHistory}
                    title="Clear history"
                    className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-all"
                >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                </button>
                <button
                    onClick={onClose}
                    title="Close copilot"
                    className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-all"
                >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
