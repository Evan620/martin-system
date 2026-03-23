import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AudioStreamer } from '../../services/audioStreamer';
import { meetings } from '../../services/api';
import { Card, Badge } from '../../components/ui';

export default function LiveMeeting() {
    const { id: meetingId } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [status, setStatus] = useState<'connected' | 'disconnected' | 'recording'>('disconnected');
    const [transcript, setTranscript] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [meeting, setMeeting] = useState<any>(null);
    const [agendaAnalysis, setAgendaAnalysis] = useState<any>(null);
    const streamerRef = useRef<AudioStreamer | null>(null);
    const transcriptEndRef = useRef<HTMLDivElement>(null);

    // Command Center State
    const [commandInput, setCommandInput] = useState('');
    const [isThinking, setIsThinking] = useState(false);

    useEffect(() => {
        loadMeeting();
        return () => {
            if (streamerRef.current) {
                streamerRef.current.stop();
            }
        };
    }, [meetingId]);

    useEffect(() => {
        // Auto-scroll to bottom of transcript
        transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [transcript]);

    const loadMeeting = async () => {
        if (!meetingId) return;
        try {
            const res = await meetings.get(meetingId);
            setMeeting(res.data);
            if (res.data.transcript) {
                setTranscript(res.data.transcript);
            }
            if (['in_progress', 'scheduled'].includes(res.data.status?.toLowerCase())) {
                handleStart(res.data);
            } else {
                setStatus('disconnected');
            }
        } catch (e) {
            console.error("Failed to load meeting", e);
            setError("Failed to load meeting details");
        }
    };

    // Check for meeting flag from props/load
    const handleStart = async (meetingData?: any) => {
        if (!meetingId) return;

        // Use provided data or current state
        const m = meetingData || meeting;
        if (m && !['in_progress', 'scheduled'].includes(m.status?.toLowerCase())) {
            return;
        }

        setError(null);

        streamerRef.current = new AudioStreamer({
            meetingId,
            onTranscript: (data) => {
                // Determine if it's final or interim
                // The backend sends { text: "...", is_final: boolean } OR { type: "agenda_update", data: ... }
                // Since AudioStreamer might just pass data.data if type is transcript, let's see implementation.
                // Assuming AudioStreamer raw message handler needs to distinguish.
                // Wait, AudioStreamer implementation only passed transcript data. 
                // Let's modify AudioStreamer to pass full event or handle it here if it's generic.
                // Looking at AudioStreamer implementation in previous memory, it checks type.

                if (data.is_final) {
                    setTranscript(prev => prev + (prev ? ' ' : '') + data.text);
                }
            },
            onAgendaUpdate: (data) => {
                console.log("Agenda Update:", data);
                if (data.source === 'agenda_monitor' && data.metadata) {
                    setAgendaAnalysis((prev: any) => {
                        // Merge decisions and completed items to avoid losing history
                        const prevDecisions = prev?.decisions || [];
                        const newDecisions = data.metadata.decisions || [];
                        const mergedDecisions = Array.from(new Set([...prevDecisions, ...newDecisions]));

                        const prevIndices = prev?.completed_items_indices || [];
                        const newIndices = data.metadata.completed_items_indices || [];
                        const mergedIndices = Array.from(new Set([...prevIndices, ...newIndices]));

                        return {
                            ...data,
                            ...data.metadata, // Flatten metadata (current_focus, insight_summary, etc)
                            decisions: mergedDecisions,
                            completed_items_indices: mergedIndices,
                            // Ensure content is the insight_summary or existing content
                            content: data.metadata.insight_summary || data.content
                        };
                    });
                } else {
                    setAgendaAnalysis(data);
                }
            },
            onError: (err) => setError(err),
            onStatusChange: (s) => setStatus(s)
        });

        await streamerRef.current.start();
    };

    const sendManualCommand = (cmd?: string) => {
        const text = cmd || commandInput;
        if (!text.trim() || !streamerRef.current) return;

        setIsThinking(true);
        streamerRef.current.sendCommand({
            type: 'live_command',
            command: text
        });
        setCommandInput('');

        // Fallback to clear thinking state if no response in 10s
        setTimeout(() => setIsThinking(false), 10000);
    };

    const requestQuickInsight = () => {
        if (!streamerRef.current) return;
        setIsThinking(true);
        streamerRef.current.sendCommand({
            type: 'request_insight',
            trigger: 'manual_button'
        });
        setTimeout(() => setIsThinking(false), 5000);
    };


    return (
        <div className="h-full flex flex-col bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <div className="px-4 sm:px-8 py-4 sm:py-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between">
                    <div>
                        <button onClick={() => navigate(`/meetings/${meetingId}`)} className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 mb-2 flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Meeting Details
                        </button>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                            {meeting?.title || 'Loading...'}
                            <Badge variant={status === 'connected' ? 'success' : 'neutral'} className={status === 'connected' ? 'animate-pulse' : ''}>
                                {status === 'connected' ? '🟢 Vexa Sync Active' : 'OFFLINE'}
                            </Badge>
                        </h1>
                    </div>

                    <div className="flex gap-3">
                        <Badge variant="neutral" className="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-slate-100 text-slate-500 border border-slate-200">
                            Automated Notetaker Active
                        </Badge>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden flex">
                {/* Transcript Area */}
                <div className="flex-1 p-4 sm:p-8 overflow-y-auto">
                    <div className="max-w-3xl mx-auto">

                        {error && (
                            <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded-r-lg">
                                <div className="flex">
                                    <div className="flex-shrink-0">
                                        <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                    <div className="ml-3">
                                        <p className="text-sm text-red-700">{error}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        <Card className="min-h-[500px] p-8 shadow-sm border border-slate-200 dark:border-slate-800">
                            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-6 border-b pb-2">Live Transcript</h2>

                            <div className="space-y-4 font-mono text-sm leading-relaxed">
                                {transcript ? (
                                    <p className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{transcript}</p>
                                ) : (
                                    <p className="text-slate-400 italic">Waiting for speech...</p>
                                )}

                                <div ref={transcriptEndRef} />
                            </div>
                        </Card>
                    </div>
                </div>

                {/* Right Sidebar - Agenda Monitor */}
                <div className="w-96 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 overflow-y-auto hidden xl:block transition-all">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">Agenda Monitor</h2>
                        <Badge variant="neutral" className="text-xs">AI Agent Active</Badge>
                    </div>

                    {!agendaAnalysis ? (
                        <div className="text-center py-10 opacity-50">
                            <div className="animate-spin w-8 h-8 border-2 border-slate-300 border-t-blue-600 rounded-full mx-auto mb-3"></div>
                            <p className="text-xs text-slate-500 italic">Listening for insights...</p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Current Focus */}
                            <div className="relative">
                                <div className="absolute -left-3 top-[-10px] bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                                    Martin Insight
                                </div>
                                <div className="p-4 pt-6 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 shadow-sm relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-2 opacity-10">
                                        <svg className="w-16 h-16 text-blue-600" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6l5.25 3.15-.75 1.23-6.5-3.9V7z" /></svg>
                                    </div>
                                    <div className="flex items-start gap-3 relative z-10">
                                        <div className="mt-1.5 w-2.5 h-2.5 rounded-full bg-blue-600 animate-ping" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-blue-600 absolute left-0 top-1.5" />
                                        <div>
                                            <h3 className="font-bold text-slate-800 text-sm leading-tight">
                                                {agendaAnalysis.source === 'live_conflict_detector' ? '🚨 Policy Alert' : (agendaAnalysis.source === 'live_command' ? '🤖 Martin Answer' : (agendaAnalysis.source === 'agenda_monitor' ? '📋 Agenda Sync' : 'System Analysis'))}
                                            </h3>

                                            {agendaAnalysis.current_focus && (
                                                <div className="mt-2 text-[10px] font-bold text-blue-600 bg-blue-100/50 px-2 py-0.5 rounded inline-block">
                                                    Current Focus: {agendaAnalysis.current_focus}
                                                </div>
                                            )}

                                            <p className="text-slate-600 text-xs mt-2 leading-relaxed">
                                                {agendaAnalysis.content || "Monitoring meeting flow..."}
                                            </p>
                                            {agendaAnalysis.original_question && (
                                                <p className="text-[10px] text-slate-400 mt-2 italic">Re: "{agendaAnalysis.original_question}"</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Decisions */}
                            {agendaAnalysis.decisions && agendaAnalysis.decisions.length > 0 && (
                                <div>
                                    <h3 className="text-xs font-bold uppercase text-slate-400 mb-3 flex items-center gap-2">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                        Captured Decisions
                                    </h3>
                                    <ul className="space-y-2">
                                        {agendaAnalysis.decisions.map((d: string, i: number) => (
                                            <li key={i} className="text-sm bg-green-50 text-green-900 border border-green-100 p-3 rounded-md flex gap-2">
                                                <span className="text-green-500 font-bold">✓</span>
                                                {d}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Progress Tracker (Example if we had full items list, but we rely on agent output for now) */}
                            {agendaAnalysis.completed_items_indices && agendaAnalysis.completed_items_indices.length > 0 && (
                                <div>
                                    <h3 className="text-xs font-bold uppercase text-slate-400 mb-3">Completed Items</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {agendaAnalysis.completed_items_indices.map((idx: number) => (
                                            <span key={idx} className="bg-slate-100 text-slate-500 px-2 py-1 rounded text-xs line-through">
                                                Item {idx + 1}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Martin Command Center */}
                    <div className="mt-8 pt-6 border-t border-slate-200 dark:border-slate-800">
                        <h3 className="text-xs font-bold uppercase text-slate-400 mb-4 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
                            Martin Command Center
                        </h3>

                        <div className="space-y-3">
                            <div className="relative">
                                <textarea
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none h-24 dark:text-white"
                                    placeholder="Ask Martin a question..."
                                    value={commandInput}
                                    onChange={(e) => setCommandInput(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            sendManualCommand();
                                        }
                                    }}
                                />
                                {isThinking && (
                                    <div className="absolute inset-0 bg-white/50 dark:bg-slate-900/50 flex items-center justify-center rounded-lg backdrop-blur-[1px]">
                                        <div className="flex items-center gap-2 text-blue-600 font-medium text-xs">
                                            <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full" />
                                            Martin is thinking...
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <button
                                    onClick={() => sendManualCommand()}
                                    disabled={!commandInput.trim() || isThinking}
                                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold py-2.5 rounded-lg transition-colors shadow-sm"
                                >
                                    Ask Martin
                                </button>
                                <button
                                    onClick={requestQuickInsight}
                                    disabled={isThinking}
                                    className="px-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold py-2.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
                                    title="Request an immediate AI scan of the last few minutes"
                                >
                                    Force Sync
                                </button>
                            </div>

                            <p className="text-[10px] text-slate-400 text-center italic">
                                Use "@martin" in speech or type above to interact.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
