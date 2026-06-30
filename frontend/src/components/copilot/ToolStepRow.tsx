import { useState } from 'react';
import {
    RoutingEvent,
    AgentEvent,
    ToolCallEvent,
    ToolResultEvent,
} from '../../hooks/useAgentStream';

type StepEvent = RoutingEvent | AgentEvent | ToolCallEvent | ToolResultEvent;

interface ToolStepRowProps {
    event: StepEvent;
    startedAt: number;
}

const ICON_MAP: Record<string, string> = {
    routing: '🔍',
    agent: '⚡',
    tool_call: '🗄️',
    tool_result: '✅',
};

function getLabel(event: StepEvent): string {
    switch (event.type) {
        case 'routing': return event.content;
        case 'agent': return event.label;
        case 'tool_call': return event.name;
        case 'tool_result': return event.name;
    }
}

function getDetail(event: StepEvent): string {
    switch (event.type) {
        case 'routing': return event.content;
        case 'agent': return `Agent: ${event.content}`;
        case 'tool_call': return JSON.stringify(event.args, null, 2).slice(0, 300);
        case 'tool_result': return event.content.slice(0, 300);
    }
}

function isTerminal(event: StepEvent): boolean {
    return event.type === 'tool_result' || event.type === 'routing' || event.type === 'agent';
}

export default function ToolStepRow({ event, startedAt }: ToolStepRowProps) {
    const [expanded, setExpanded] = useState(false);
    const elapsed = Date.now() - startedAt;
    const icon = ICON_MAP[event.type] ?? '•';
    const label = getLabel(event);
    const detail = getDetail(event);
    const done = isTerminal(event);

    return (
        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 overflow-hidden">
            <button
                onClick={() => setExpanded(prev => !prev)}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
            >
                <span className="text-sm leading-none flex-shrink-0">{icon}</span>
                <span className="flex-1 truncate text-xs text-slate-700 dark:text-slate-300 font-medium">{label}</span>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 flex-shrink-0">{elapsed}ms</span>
                <span className={`text-[10px] transition-transform flex-shrink-0 ${expanded ? 'rotate-180' : ''}`}>▾</span>
                {done ? (
                    <span className="text-green-500 flex-shrink-0 text-xs">✓</span>
                ) : (
                    <span className="w-3 h-3 border-2 border-teal-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                )}
            </button>

            {expanded && (
                <div className="px-3 pb-2">
                    <pre className="text-[10px] font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-900/50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                        {detail}
                        {detail.length >= 300 && <span className="opacity-50">… (truncated)</span>}
                    </pre>
                </div>
            )}
        </div>
    );
}
