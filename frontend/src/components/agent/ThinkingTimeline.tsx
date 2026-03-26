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
    steps: _steps,
    isComplete,
    startTime,
    agentName: _agentName = 'AI Assistant',
    error
}: ThinkingTimelineProps) {
    const [elapsedMs, setElapsedMs] = useState(0);
    const [visible, setVisible] = useState(true);

    // Live elapsed timer
    useEffect(() => {
        if (isComplete) return;
        const interval = setInterval(() => {
            setElapsedMs(Date.now() - startTime);
        }, 100);
        return () => clearInterval(interval);
    }, [startTime, isComplete]);

    // Fade out after completion
    useEffect(() => {
        if (isComplete) {
            const timeout = setTimeout(() => setVisible(false), 1500);
            return () => clearTimeout(timeout);
        } else {
            setVisible(true);
        }
    }, [isComplete]);

    const formatDuration = (ms: number) => {
        return (ms / 1000).toFixed(1) + 's';
    };

    if (!visible) return null;

    return (
        <div className={`flex items-center gap-3 py-2 px-1 my-1 transition-opacity duration-500 ${isComplete ? 'opacity-0' : 'opacity-100'}`}>
            {/* Pulsing dots */}
            <div className="flex items-center gap-1">
                <span
                    className="block w-1.5 h-1.5 rounded-full bg-slate-400/60 dark:bg-slate-500/50"
                    style={{ animation: 'thinkPulse 1.4s ease-in-out infinite' }}
                />
                <span
                    className="block w-1.5 h-1.5 rounded-full bg-slate-400/60 dark:bg-slate-500/50"
                    style={{ animation: 'thinkPulse 1.4s ease-in-out 0.2s infinite' }}
                />
                <span
                    className="block w-1.5 h-1.5 rounded-full bg-slate-400/60 dark:bg-slate-500/50"
                    style={{ animation: 'thinkPulse 1.4s ease-in-out 0.4s infinite' }}
                />
            </div>

            {/* Label */}
            <span className="text-xs text-slate-400/80 dark:text-slate-500/80 font-medium select-none"
                  style={{ animation: 'thinkFade 2s ease-in-out infinite' }}>
                Thinking
            </span>

            {/* Elapsed time */}
            {!isComplete && elapsedMs > 2000 && (
                <span className="text-[10px] text-slate-300/60 dark:text-slate-600/60 font-mono select-none">
                    {formatDuration(elapsedMs)}
                </span>
            )}

            {/* Error */}
            {error && (
                <span className="text-[10px] text-red-400/80 ml-1">{error}</span>
            )}

            {/* Inline keyframes */}
            <style>{`
                @keyframes thinkPulse {
                    0%, 100% { opacity: 0.3; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.3); }
                }
                @keyframes thinkFade {
                    0%, 100% { opacity: 0.5; }
                    50% { opacity: 0.9; }
                }
            `}</style>
        </div>
    );
}
