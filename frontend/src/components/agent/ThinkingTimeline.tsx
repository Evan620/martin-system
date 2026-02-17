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
    agentName = 'AI Assistant',
    error
}: ThinkingTimelineProps) {
    const [isExpanded, setIsExpanded] = useState(!isComplete);
    const [elapsedMs, setElapsedMs] = useState(0);

    // Live elapsed timer
    useEffect(() => {
        const interval = setInterval(() => {
            setElapsedMs(Date.now() - startTime);
        }, 100);

        return () => clearInterval(interval);
    }, [startTime]);

    // Format duration helper (e.g. "3.2s")
    const formatDuration = (ms: number) => {
        return (ms / 1000).toFixed(1) + 's';
    };

    // Auto-collapse on completion
    useEffect(() => {
        if (isComplete) {
            const timeout = setTimeout(() => setIsExpanded(false), 2000);
            return () => clearTimeout(timeout);
        }
    }, [isComplete]);

    // If complete and collapsed, show the minimal chip
    if (isComplete && !isExpanded) {
        return (
            <div className="flex mb-4 animate-in fade-in slide-in-from-bottom-1 duration-300">
                <button
                    onClick={() => setIsExpanded(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700/50 rounded-full transition-colors group border border-transparent hover:border-slate-300 dark:hover:border-slate-600"
                >
                    <span className="material-symbols-outlined text-[16px] text-blue-500">bolt</span>
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                        Thought for {formatDuration(elapsedMs)}
                    </span>
                    <span className="material-symbols-outlined text-[16px] text-slate-400 group-hover:text-slate-600 transition-colors">expand_more</span>
                </button>
            </div>
        );
    }

    // Otherwise show the full timeline with agent icon
    return (
        <div className="flex gap-3 justify-start mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* Agent Icon */}
            <div className="size-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white shrink-0 shadow-sm mt-1">
                <span className="material-symbols-outlined text-[18px] animate-pulse">smart_toy</span>
            </div>

            <div className="flex-1 max-w-md">
                <div className="bg-white dark:bg-[#1a202c] border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden transition-all">
                    {/* Header */}
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50/50 dark:bg-slate-800/20 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-800/40 transition-colors"
                    >
                        <div className="flex items-center gap-2">
                            {isComplete ? (
                                <span className="flex size-2 bg-green-500 rounded-full"></span>
                            ) : (
                                <span className="relative flex size-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                                </span>
                            )}
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                {isComplete ? `Completed in ${formatDuration(elapsedMs)}` : `Thinking · ${formatDuration(elapsedMs)}`}
                            </span>
                        </div>
                        <span className={`material-symbols-outlined text-[16px] text-slate-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
                            expand_more
                        </span>
                    </button>

                    {/* Timeline Body */}
                    {isExpanded && (
                        <div className="p-2 space-y-1">
                            {steps.map((step, idx) => (
                                <div
                                    key={step.id || idx}
                                    className={`flex items-start gap-3 p-2 rounded-lg text-sm transition-all duration-300 ${step.status === 'active'
                                            ? 'bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30'
                                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/30'
                                        }`}
                                >
                                    <div className="mt-0.5 shrink-0 flex items-center justify-center size-5">
                                        {step.status === 'complete' ? (
                                            <span className="material-symbols-outlined text-[18px] text-green-500 animate-in zoom-in duration-200">check_circle</span>
                                        ) : step.status === 'error' ? (
                                            <span className="material-symbols-outlined text-[18px] text-red-500">error</span>
                                        ) : (
                                            <span className="material-symbols-outlined text-[18px] text-blue-500 animate-spin">progress_activity</span>
                                        )}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className={`font-medium truncate ${step.status === 'active' ? 'text-blue-700 dark:text-blue-300' : 'text-slate-700 dark:text-slate-200'
                                            }`}>
                                            {step.label}
                                        </div>
                                        {step.tool && (
                                            <div className="text-[10px] text-slate-400 font-mono mt-0.5 flex items-center gap-1">
                                                <span className="material-symbols-outlined text-[10px]">{step.icon || 'build'}</span>
                                                {step.tool}
                                            </div>
                                        )}
                                    </div>

                                    {step.durationMs && (
                                        <div className="text-[10px] text-slate-400 font-mono mt-1 whitespace-nowrap">
                                            {formatDuration(step.durationMs)}
                                        </div>
                                    )}
                                </div>
                            ))}

                            {/* Error State */}
                            {error && (
                                <div className="flex items-start gap-3 p-2 rounded-lg text-sm bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30">
                                    <span className="material-symbols-outlined text-[18px] text-red-600 dark:text-red-400 mt-0.5">error_outline</span>
                                    <div className="text-red-700 dark:text-red-300 font-medium">{error}</div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
