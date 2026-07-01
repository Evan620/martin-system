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
        <div className="h-full flex flex-col" style={{ background: 'var(--bg)' }}>
            {/* Header */}
            <div className="px-4 sm:px-8 py-4 sm:py-6" style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                <div className="flex items-center justify-between">
                    <div>
                        <button onClick={() => navigate(`/meetings/${meetingId}`)} className="text-sm mb-2 flex items-center gap-1 qp-transition" style={{ color: 'var(--ink-500)' }}>
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Meeting Details
                        </button>
                        <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--ink-900)' }}>
                            {meeting?.title || 'Loading...'}
                            <Badge variant={status === 'connected' ? 'success' : 'neutral'} className={status === 'connected' ? 'animate-pulse' : ''}>
                                {status === 'connected' ? '🟢 Vexa Sync Active' : 'OFFLINE'}
                            </Badge>
                        </h1>
                    </div>

                    <div className="flex gap-3">
                        <Badge variant="neutral" className="px-4 py-2 text-xs font-bold uppercase tracking-widest" style={{ background: 'var(--surface-2)', color: 'var(--ink-500)', border: '1px solid var(--border)' }}>
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
                            <div className="p-4 mb-6" style={{ background: 'color-mix(in srgb, var(--terra) 10%, transparent)', borderLeft: '4px solid var(--terra)', borderRadius: '0 var(--radius-ctl) var(--radius-ctl) 0' }}>
                                <div className="flex">
                                    <div className="flex-shrink-0">
                                        <svg className="h-5 w-5" style={{ color: 'var(--terra)' }} viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                    <div className="ml-3">
                                        <p className="text-sm" style={{ color: 'var(--terra)' }}>{error}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        <Card className="min-h-[500px] p-8">
                            <h2 className="text-lg font-semibold mb-6 pb-2" style={{ color: 'var(--ink-800)', borderBottom: '1px solid var(--border)' }}>Live Transcript</h2>

                            <div className="space-y-4 font-mono text-sm leading-relaxed">
                                {transcript ? (
                                    <p className="whitespace-pre-wrap" style={{ color: 'var(--ink-700)' }}>{transcript}</p>
                                ) : (
                                    <p className="italic" style={{ color: 'var(--ink-400)' }}>Waiting for speech...</p>
                                )}

                                <div ref={transcriptEndRef} />
                            </div>
                        </Card>
                    </div>
                </div>

                {/* Right Sidebar - Agenda Monitor */}
                <div className="w-96 p-6 overflow-y-auto hidden xl:block qp-transition" style={{ borderLeft: '1px solid var(--border)', background: 'var(--surface)' }}>
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--ink-500)' }}>Agenda Monitor</h2>
                        <Badge variant="neutral" className="text-xs">AI Agent Active</Badge>
                    </div>

                    {!agendaAnalysis ? (
                        <div className="text-center py-10 opacity-50">
                            <div className="animate-spin w-8 h-8 rounded-full mx-auto mb-3" style={{ border: '2px solid var(--border)', borderTopColor: 'var(--accent)' }}></div>
                            <p className="text-xs italic" style={{ color: 'var(--ink-500)' }}>Listening for insights...</p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Current Focus */}
                            <div className="relative">
                                <div className="absolute -left-3 top-[-10px] text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                    Martin Insight
                                </div>
                                <div className="p-4 pt-6 relative overflow-hidden" style={{ background: 'var(--accent-soft)', border: '1px solid color-mix(in srgb, var(--accent) 30%, var(--border))', borderRadius: 'var(--radius-ctl)' }}>
                                    <div className="absolute top-0 right-0 p-2 opacity-10">
                                        <svg className="w-16 h-16" style={{ color: 'var(--accent)' }} fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6l5.25 3.15-.75 1.23-6.5-3.9V7z" /></svg>
                                    </div>
                                    <div className="flex items-start gap-3 relative z-10">
                                        <div className="mt-1.5 w-2.5 h-2.5 rounded-full animate-ping" style={{ background: 'var(--accent)' }} />
                                        <div className="w-2.5 h-2.5 rounded-full absolute left-0 top-1.5" style={{ background: 'var(--accent)' }} />
                                        <div>
                                            <h3 className="font-bold text-sm leading-tight" style={{ color: 'var(--ink-800)' }}>
                                                {agendaAnalysis.source === 'live_conflict_detector' ? '🚨 Policy Alert' : (agendaAnalysis.source === 'live_command' ? '🤖 Martin Answer' : (agendaAnalysis.source === 'agenda_monitor' ? '📋 Agenda Sync' : 'System Analysis'))}
                                            </h3>

                                            {agendaAnalysis.current_focus && (
                                                <div className="mt-2 text-[10px] font-bold px-2 py-0.5 rounded inline-block" style={{ color: 'var(--accent)', background: 'color-mix(in srgb, var(--accent) 12%, transparent)' }}>
                                                    Current Focus: {agendaAnalysis.current_focus}
                                                </div>
                                            )}

                                            <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--ink-600)' }}>
                                                {agendaAnalysis.content || "Monitoring meeting flow..."}
                                            </p>
                                            {agendaAnalysis.original_question && (
                                                <p className="text-[10px] mt-2 italic" style={{ color: 'var(--ink-400)' }}>Re: "{agendaAnalysis.original_question}"</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Decisions */}
                            {agendaAnalysis.decisions && agendaAnalysis.decisions.length > 0 && (
                                <div>
                                    <h3 className="text-xs font-bold uppercase mb-3 flex items-center gap-2" style={{ color: 'var(--ink-400)' }}>
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                        Captured Decisions
                                    </h3>
                                    <ul className="space-y-2">
                                        {agendaAnalysis.decisions.map((d: string, i: number) => (
                                            <li key={i} className="text-sm p-3 flex gap-2" style={{ background: 'color-mix(in srgb, var(--sage) 10%, transparent)', color: 'var(--ink-800)', border: '1px solid color-mix(in srgb, var(--sage) 25%, transparent)', borderRadius: 'var(--radius-ctl)' }}>
                                                <span className="font-bold" style={{ color: 'var(--sage)' }}>✓</span>
                                                {d}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Progress Tracker (Example if we had full items list, but we rely on agent output for now) */}
                            {agendaAnalysis.completed_items_indices && agendaAnalysis.completed_items_indices.length > 0 && (
                                <div>
                                    <h3 className="text-xs font-bold uppercase mb-3" style={{ color: 'var(--ink-400)' }}>Completed Items</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {agendaAnalysis.completed_items_indices.map((idx: number) => (
                                            <span key={idx} className="px-2 py-1 rounded text-xs line-through" style={{ background: 'var(--surface-2)', color: 'var(--ink-500)' }}>
                                                Item {idx + 1}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Martin Command Center */}
                    <div className="mt-8 pt-6" style={{ borderTop: '1px solid var(--border)' }}>
                        <h3 className="text-xs font-bold uppercase mb-4 flex items-center gap-2" style={{ color: 'var(--ink-400)' }}>
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
                            Martin Command Center
                        </h3>

                        <div className="space-y-3">
                            <div className="relative">
                                <textarea
                                    className="w-full p-3 text-sm focus:ring-2 focus:ring-teal-500 outline-none resize-none h-24"
                                    style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-800)' }}
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
                                    <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'color-mix(in srgb, var(--surface) 70%, transparent)', borderRadius: 'var(--radius-ctl)' }}>
                                        <div className="flex items-center gap-2 font-medium text-xs" style={{ color: 'var(--accent)' }}>
                                            <div className="animate-spin w-4 h-4 rounded-full" style={{ border: '2px solid var(--accent)', borderTopColor: 'transparent' }} />
                                            Martin is thinking...
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <button
                                    onClick={() => sendManualCommand()}
                                    disabled={!commandInput.trim() || isThinking}
                                    className="flex-1 disabled:opacity-50 text-xs font-bold py-2.5 qp-transition clickable-scale"
                                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                                >
                                    Ask Martin
                                </button>
                                <button
                                    onClick={requestQuickInsight}
                                    disabled={isThinking}
                                    className="px-4 text-xs font-bold py-2.5 qp-transition clickable-scale"
                                    style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', borderRadius: 'var(--radius-ctl)' }}
                                    title="Request an immediate AI scan of the last few minutes"
                                >
                                    Force Sync
                                </button>
                            </div>

                            <p className="text-[10px] text-center italic" style={{ color: 'var(--ink-400)' }}>
                                Use "@martin" in speech or type above to interact.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
