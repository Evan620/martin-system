import { useState, useEffect } from 'react';

export interface ThinkingStep {
    id: string;
    label: string;
    status: 'pending' | 'active' | 'complete' | 'error';
    icon?: string;
    tool?: string;
    durationMs?: number;
    timestamp: number;
}

interface ThinkingTimelineProps {
    steps: ThinkingStep[];
    isComplete: boolean;
    startTime: number;
    agentName?: string;
    error?: string | null;
}

export default function ThinkingTimeline({
    steps,
    isComplete,
    startTime,
    agentName: _agentName = 'AI Assistant', // Prefixed with underscore to suppress unused variable error
    error
}: ThinkingTimelineProps) {
    const [isExpanded, setIsExpanded] = useState(!isComplete);
    const [elapsedMs, setElapsedMs] = useState(0);

    // Live elapsed timer
    useEffect(() => {
        if (isComplete) return;
        const interval = setInterval(() => {
            setElapsedMs(Date.now() - startTime);
        }, 100);
        return () => clearInterval(interval);
    }, [startTime, isComplete]);

    // Format duration helper (e.g. "3.2s")
    const formatDuration = (ms: number) => {
        return (ms / 1000).toFixed(1) + 's';
    };

    // Auto-collapse on completion
    useEffect(() => {
        if (isComplete) {
            const timeout = setTimeout(() => setIsExpanded(false), 2000); // Auto-collapse after 2s
            return () => clearTimeout(timeout);
        }
    }, [isComplete]);

    // Icon helper
    const getStatusIcon = (status: ThinkingStep['status']) => {
        switch (status) {
            case 'complete': return <span className="material-symbols-outlined text-[14px] text-green-500">check</span>;
            case 'error': return <span className="material-symbols-outlined text-[14px] text-red-500">error</span>;
            case 'active': return <span className="material-symbols-outlined text-[14px] text-blue-500 animate-spin">progress_activity</span>;
            default: return <span className="material-symbols-outlined text-[14px] text-slate-300">radio_button_unchecked</span>;
        }
    };

    if (steps.length === 0 && !isComplete) return null;

    return (
        <div className="w-full max-w-2xl animate-in fade-in slide-in-from-bottom-2 duration-300 my-2">

            {/* Minimal Header Toggle */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="group flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors px-1 py-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800/50"
            >
                <div className={`flex items-center justify-center p-0.5 rounded transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                    <span className="material-symbols-outlined text-[14px]">chevron_right</span>
                </div>

                {isComplete ? (
                    <span className="flex items-center gap-2 text-green-600 dark:text-green-500">
                        <span>Finished thought process</span>
                        <span className="text-slate-400">•</span>
                        <span>{formatDuration(elapsedMs)}</span>
                    </span>
                ) : (
                    <span className="flex items-center gap-2">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                        </span>
                        <span className="animate-pulse">Reasoning...</span>
                        <span className="text-slate-400 font-mono text-[10px]">{formatDuration(elapsedMs)}</span>
                    </span>
                )}
            </button>

            {/* Expanded Timeline Body */}
            {isExpanded && (
                <div className="relative ml-2.5 pl-4 mt-1 space-y-2 border-l-2 border-slate-100 dark:border-slate-800/50">
                    {steps.map((step, idx) => (
                        <div
                            key={step.id || idx}
                            className={`flex items-start gap-2 text-xs transition-all duration-300 ${step.status === 'active' ? 'opacity-100' : 'opacity-70 hover:opacity-100'
                                }`}
                        >
                            <div className="mt-0.5 shrink-0 select-none">
                                {getStatusIcon(step.status)}
                            </div>

                            <div className="flex-1 min-w-0 grid gap-0.5">
                                <div className={`truncate font-medium ${step.status === 'active' ? 'text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-300'
                                    }`}>
                                    {step.label}
                                </div>

                                {step.tool && (
                                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                                        <span className="material-symbols-outlined text-[10px]">terminal</span>
                                        <span className="truncate opacity-80">{step.tool}</span>
                                    </div>
                                )}
                            </div>

                            {step.durationMs && (
                                <span className="text-[10px] text-slate-300 font-mono whitespace-nowrap pt-0.5">
                                    {formatDuration(step.durationMs)}
                                </span>
                            )}
                        </div>
                    ))}

                    {error && (
                        <div className="flex items-start gap-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/10 p-2 rounded-md mt-2">
                            <span className="material-symbols-outlined text-[16px]">error</span>
                            <span>{error}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
