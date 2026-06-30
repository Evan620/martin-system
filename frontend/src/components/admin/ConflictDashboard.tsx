import { Card, Badge } from '../../components/ui';

import { useEffect, useState } from 'react';
import { getConflicts, ConflictAlert, getDashboardStats, forceReconciliation, ReconciliationResult, generateWeeklyPacket, autoNegotiateConflict, dismissConflict, resolveConflictManually, approveResolution } from '../../services/dashboardService';
import ManualResolutionModal from '../modals/ManualResolutionModal';

export default function ConflictDashboard() {
    const [stats, setStats] = useState<any>(null);
    const [conflicts, setConflicts] = useState<ConflictAlert[]>([]);
    const [loading, setLoading] = useState(true);
    const [reconciliationResult, setReconciliationResult] = useState<ReconciliationResult | null>(null);
    const [negotiationLog, setNegotiationLog] = useState<any>(null);
    const [showNegotiationModal, setShowNegotiationModal] = useState(false);
    const [showResolutionModal, setShowResolutionModal] = useState(false);
    const [showHistoryModal, setShowHistoryModal] = useState(false);
    const [historyConflicts, setHistoryConflicts] = useState<ConflictAlert[]>([]);
    const [negotiationPrompt, setNegotiationPrompt] = useState("");

    const handleShowHistory = async () => {
        try {
            const allConflicts = await getConflicts(true);
            const resolved = allConflicts.filter(c => c.status === 'resolved' || c.status === 'dismissed');
            setHistoryConflicts(resolved);
            setShowHistoryModal(true);
        } catch (error) {
            console.error("Failed to load history", error);
        }
    };

    const handleManualResolve = async (type: string, meetingId: string, newTime?: string, reason?: string) => {
        if (!activeConflict) return;
        try {
            await resolveConflictManually(activeConflict.id, type, meetingId, newTime, reason);
            // Refresh
            const updatedConflicts = await getConflicts();
            setConflicts(updatedConflicts);
            // Re-fetch stats
            const statsData = await getDashboardStats();
            setStats(statsData);
        } catch (error) {
            console.error("Manual resolution failed", error);
        }
    };

    useEffect(() => {
        const loadData = async () => {
            try {
                const [conflictsData, statsData] = await Promise.all([
                    getConflicts(),
                    getDashboardStats()
                ]);
                setConflicts(conflictsData);
                setStats(statsData);
            } catch (error) {
                console.error("Failed to load dashboard data", error);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, []);

    // State for carousel
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPaused, setIsPaused] = useState(false);

    // Auto-advance logic
    useEffect(() => {
        if (!conflicts.length || isPaused) return;

        const interval = setInterval(() => {
            setCurrentIndex((prev) => (prev + 1) % conflicts.length);
        }, 5000); // 5 seconds

        return () => clearInterval(interval);
    }, [conflicts.length, isPaused]);

    const nextConflict = () => {
        setCurrentIndex((prev) => (prev + 1) % conflicts.length);
    };

    const prevConflict = () => {
        setCurrentIndex((prev) => (prev - 1 + conflicts.length) % conflicts.length);
    };

    // Current active conflict
    const activeConflict = conflicts[currentIndex];

    const [weeklyPacketData, setWeeklyPacketData] = useState<any>(null);

    // Calculate Weekly Packet progress from pipeline stats
    const totalDeals = stats?.pipeline?.total || 1;
    const completedDeals = (stats?.pipeline?.final_review || 0) + (stats?.pipeline?.signed || 0);
    const packetCompletion = Math.round((completedDeals / totalDeals) * 100) || 0;

    return (
        <>
            <div className="space-y-6 mb-8">
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2">
                            <h2 className="text-xl font-display font-bold text-slate-900 dark:text-white">Admin Control Tower</h2>
                            <Badge variant="warning" className="uppercase tracking-widest text-[10px]">Secretariat Eyes Only</Badge>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Synthesis & Conflict Resolution Center</p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={async () => {
                                try {
                                    setLoading(true);
                                    const result = await generateWeeklyPacket();
                                    setWeeklyPacketData(result);
                                } catch (error) {
                                    console.error('Failed to generate weekly packet', error);
                                } finally {
                                    setLoading(false);
                                }
                            }}
                            className="clickable-scale px-4 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl text-xs font-bold hover:shadow-lg transition-all active:scale-95"
                        >
                            Generate Weekly Packet
                        </button>
                        <button
                            onClick={async () => {
                                setLoading(true);
                                setReconciliationResult(null);
                                try {
                                    const result = await forceReconciliation();
                                    setReconciliationResult(result);
                                    // Refresh conflicts list
                                    const newConflicts = await getConflicts();
                                    setConflicts(newConflicts);
                                } catch (error) {
                                    console.error('Force reconciliation failed', error);
                                } finally {
                                    setLoading(false);
                                }
                            }}
                            className="clickable-scale px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/30 rounded-xl text-xs font-bold hover:bg-red-100 dark:hover:bg-red-900/40 transition-all flex items-center gap-2 active:scale-95"
                        >
                            <span className="material-symbols-outlined text-[16px]">warning</span>
                            Force Reconciliation
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-12 gap-6">
                    {/* 1. Reconciliation State & Weekly Packet */}
                    <div className="col-span-12 lg:col-span-4 space-y-6">
                        {/* Weekly Packet Status */}
                        <Card className="p-5 border-l-4 border-l-teal-500">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h3 className="font-bold text-slate-900 dark:text-white">Weekly Packet</h3>
                                    <p className="text-[10px] text-slate-500 uppercase tracking-widest">Target: Friday 17:00</p>
                                </div>
                                <div className="text-right">
                                    <span className="text-2xl font-bold text-teal-600">{packetCompletion}%</span>
                                </div>
                            </div>
                            <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mb-4">
                                <div className="h-full bg-teal-500 rounded-full" style={{ width: `${packetCompletion}%` }}></div>
                            </div>
                            <div className="space-y-2">
                                {weeklyPacketData ? (
                                    weeklyPacketData.twg_activity.length > 0 ? (
                                        weeklyPacketData.twg_activity.slice(0, 5).map((item: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between text-xs border-b border-slate-50 dark:border-slate-800 pb-2 last:border-0 last:pb-0">
                                                <div className="flex flex-col">
                                                    <span className="text-slate-600 dark:text-slate-300 font-bold">{item.name}</span>
                                                    <span className="text-[9px] text-slate-400">{item.accomplishments_count} wins, {item.risks_count} risks</span>
                                                </div>
                                                <Badge variant={item.status === 'Ready' ? 'success' : 'warning'} className="text-[10px]">
                                                    {item.status}
                                                </Badge>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center text-xs text-slate-400 italic py-2">No active TWG packets generated yet.</div>
                                    )
                                ) : (
                                    <div className="text-center py-4">
                                        <p className="text-xs text-slate-400 mb-2">Detailed packets not generated</p>
                                        <button
                                            onClick={() => document.querySelector<HTMLElement>('button[class*="bg-slate-900"]')?.click()}
                                            className="text-[10px] text-teal-500 hover:text-teal-600 font-bold uppercase tracking-wider"
                                        >
                                            Generate Now
                                        </button>
                                    </div>
                                )}
                            </div>
                        </Card>

                        {/* System Health / Reconciliation */}
                        <Card className={`p-5 border-l-4 ${reconciliationResult && reconciliationResult.conflicts_detected > 0 ? 'border-l-amber-500' : 'border-l-emerald-500'}`}>
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <h3 className="font-bold text-slate-900 dark:text-white">Reconciliation State</h3>
                                    <p className="text-[10px] text-slate-500 uppercase tracking-widest">
                                        {reconciliationResult ? `Last scan: ${new Date(reconciliationResult.scan_time).toLocaleTimeString()}` : 'Auto-Debate Engine'}
                                    </p>
                                </div>
                                {reconciliationResult && reconciliationResult.conflicts_detected > 0 ? (
                                    <span className="material-symbols-outlined text-amber-500 animate-pulse">warning</span>
                                ) : (
                                    <span className="material-symbols-outlined text-emerald-500 animate-pulse">check_circle</span>
                                )}
                            </div>

                            {reconciliationResult ? (
                                <div className="space-y-3 mt-4">
                                    <div className="flex items-center gap-4">
                                        <div className="flex-1 text-center p-3 rounded-lg bg-red-50 dark:bg-red-900/20">
                                            <div className="text-lg font-bold text-red-600 dark:text-red-400">
                                                {reconciliationResult.conflicts_detected}
                                            </div>
                                            <div className="text-[9px] font-black uppercase text-slate-400">Detected</div>
                                        </div>
                                        <div className="flex-1 text-center p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                                            <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                                                {reconciliationResult.auto_resolved}
                                            </div>
                                            <div className="text-[9px] font-black uppercase text-slate-400">Auto-Resolved</div>
                                        </div>
                                    </div>

                                    {reconciliationResult.breakdown && (
                                        <div className="text-xs space-y-1 pt-2 border-t border-slate-100 dark:border-slate-700">
                                            {reconciliationResult.breakdown.same_slot > 0 && (
                                                <div className="flex justify-between"><span>⏰ Same-slot</span><span className="font-bold text-red-500">{reconciliationResult.breakdown.same_slot}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.venue > 0 && (
                                                <div className="flex justify-between"><span>🏛️ Venue</span><span className="font-bold text-red-500">{reconciliationResult.breakdown.venue}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.vip_double_booking > 0 && (
                                                <div className="flex justify-between"><span>👤 VIP Double-booking</span><span className="font-bold text-red-500">{reconciliationResult.breakdown.vip_double_booking}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.crowding > 0 && (
                                                <div className="flex justify-between"><span>⚠️ Crowding</span><span className="font-bold text-amber-500">{reconciliationResult.breakdown.crowding}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.overdue_action > 0 && (
                                                <div className="flex justify-between"><span>📋 Overdue</span><span className="font-bold text-amber-500">{reconciliationResult.breakdown.overdue_action}</span></div>
                                            )}
                                            {reconciliationResult.conflicts_detected === 0 && (
                                                <div className="text-center text-emerald-500 font-bold">✅ All clear!</div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="flex items-center gap-4 mt-4">
                                    <div
                                        onClick={handleShowHistory}
                                        className="flex-1 text-center p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 cursor-pointer hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors"
                                    >
                                        <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                                            {conflicts.filter(c => c.status === 'resolved' || c.status === 'dismissed').length}
                                        </div>
                                        <div className="text-[9px] font-black uppercase text-slate-400">Resolved • View History</div>
                                    </div>
                                    <div className="flex-1 text-center p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20">
                                        <div className="text-lg font-bold text-amber-600 dark:text-amber-400">
                                            {conflicts.filter(c => c.status === 'detected' || c.status === 'negotiating' || c.status === 'escalated').length}
                                        </div>
                                        <div className="text-[9px] font-black uppercase text-slate-400">Pending</div>
                                    </div>
                                </div>
                            )}
                        </Card>
                    </div>

                    {/* 2. Conflict Radar / Alerts */}
                    <div className="col-span-12 lg:col-span-8">
                        <Card className="h-full p-0 overflow-hidden border-t-4 border-t-red-500 relative group/card"
                            onMouseEnter={() => setIsPaused(true)}
                            onMouseLeave={() => setIsPaused(false)}
                        >
                            <div className="p-5 border-b border-slate-100 dark:border-dark-border bg-red-50/50 dark:bg-red-900/10 flex justify-between items-center">
                                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    <span className="material-symbols-outlined text-red-500">radar</span>
                                    Detected Conflicts & Inconsistencies
                                </h3>
                                {/* Pagination Dots */}
                                <div className="flex gap-1">
                                    {conflicts.map((_, idx) => (
                                        <div
                                            key={idx}
                                            className={`w-1.5 h-1.5 rounded-full transition-all ${idx === currentIndex ? 'bg-red-500 w-3' : 'bg-slate-300 dark:bg-slate-700'}`}
                                        />
                                    ))}
                                </div>
                            </div>

                            <div className="relative min-h-[300px]">
                                {loading && (
                                    <div className="absolute inset-0 flex items-center justify-center text-slate-500 italic bg-white/50 dark:bg-slate-900/50 z-10">
                                        Scanning for conflicts...
                                    </div>
                                )}

                                {!loading && conflicts.length > 0 && activeConflict && (
                                    <div className="p-8 h-full flex flex-col justify-center transition-all duration-300">
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="flex items-center gap-2">
                                                <Badge variant={activeConflict.severity === 'high' || activeConflict.severity === 'critical' ? 'danger' : 'warning'} className="uppercase text-[10px] font-black tracking-widest">
                                                    {activeConflict.conflict_type}
                                                </Badge>
                                                <span className="text-xs font-bold text-slate-500">
                                                    {activeConflict.agents_involved.join(' vs ')}
                                                </span>
                                            </div>
                                        </div>

                                        <h4 className="text-xl font-bold text-slate-900 dark:text-white mb-4 leading-tight">{activeConflict.description}</h4>

                                        <div className="bg-slate-50 dark:bg-slate-800 p-5 rounded-xl border border-slate-100 dark:border-slate-700 mb-6 relative">
                                            <span className="absolute -top-3 left-4 px-2 bg-slate-50 dark:bg-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Conflict Details</span>
                                            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed italic">
                                                "{Object.entries(activeConflict.conflicting_positions || {}).map(([k, v]) => `${k}: ${v}`).join(' | ')}"
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-3">
                                            {activeConflict.status === 'escalated' ? (
                                                <button
                                                    onClick={() => setShowResolutionModal(true)}
                                                    className="clickable-scale px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-bold transition-colors shadow-lg shadow-red-500/20 active:scale-95 flex items-center gap-2"
                                                >
                                                    <span className="material-symbols-outlined text-[16px]">gavel</span>
                                                    Resolve Manually
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={async () => {
                                                        if (!activeConflict) return;
                                                        try {
                                                            setLoading(true);
                                                            const result = await autoNegotiateConflict(activeConflict.id);
                                                            setNegotiationLog(result);
                                                            setShowNegotiationModal(true);
                                                            // Refresh conflicts list
                                                            const newConflicts = await getConflicts();
                                                            setConflicts(newConflicts);
                                                        } catch (error) {
                                                            console.error('Auto-negotiation failed', error);
                                                        } finally {
                                                            setLoading(false);
                                                        }
                                                    }}
                                                    className="clickable-scale px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-sm font-bold transition-colors shadow-lg shadow-teal-500/20 active:scale-95"
                                                >
                                                    Initiate Auto-Negotiation
                                                </button>
                                            )}
                                            <button
                                                onClick={async () => {
                                                    if (!activeConflict) return;
                                                    try {
                                                        setLoading(true);
                                                        await dismissConflict(activeConflict.id);
                                                        // Refresh conflicts list
                                                        const newConflicts = await getConflicts();
                                                        setConflicts(newConflicts);
                                                        // Reset index if needed
                                                        if (currentIndex >= newConflicts.length) {
                                                            setCurrentIndex(0);
                                                        }
                                                    } catch (error) {
                                                        console.error('Dismiss failed', error);
                                                    } finally {
                                                        setLoading(false);
                                                    }
                                                }}
                                                className="clickable-scale px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-bold hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                                            >
                                                Dismiss Issue
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* Empty State */}
                                {!loading && conflicts.length === 0 && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400">
                                        <span className="material-symbols-outlined text-5xl mb-4 text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-full">check_circle</span>
                                        <p className="font-bold">No active conflicts detected.</p>
                                        <p className="text-xs opacity-70 mt-1">System is running optimally</p>
                                    </div>
                                )}

                                {/* Navigation Controls (Visible on Hover) */}
                                {conflicts.length > 1 && (
                                    <>
                                        <button
                                            onClick={prevConflict}
                                            className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white dark:bg-slate-800 shadow-md border border-slate-100 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-teal-600 hover:scale-110 transition-all opacity-0 group-hover/card:opacity-100 z-20"
                                        >
                                            <span className="material-symbols-outlined text-lg">chevron_left</span>
                                        </button>
                                        <button
                                            onClick={nextConflict}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white dark:bg-slate-800 shadow-md border border-slate-100 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-teal-600 hover:scale-110 transition-all opacity-0 group-hover/card:opacity-100 z-20"
                                        >
                                            <span className="material-symbols-outlined text-lg">chevron_right</span>
                                        </button>
                                    </>
                                )}
                            </div>
                        </Card>
                    </div>
                </div>
            </div>

            {/* Negotiation Results Modal */}
            {showNegotiationModal && negotiationLog && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center bg-slate-50 dark:bg-slate-800/50">
                            <div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    {negotiationLog.negotiation_result === 'pending_approval' ? (
                                        <>
                                            <span className="text-2xl">🗳️</span>
                                            <span>Proposal Ready for Review</span>
                                        </>
                                    ) : negotiationLog.negotiation_result === 'auto_resolved' ? (
                                        <>
                                            <span className="text-2xl">✅</span>
                                            <span>Conflict Resolved</span>
                                        </>
                                    ) : (
                                        <>
                                            <span className="text-2xl">⚠️</span>
                                            <span>Negotiation Escalated</span>
                                        </>
                                    )}
                                </h2>
                                <p className="text-sm text-slate-500 mt-1">
                                    {negotiationLog.negotiation_result === 'pending_approval'
                                        ? 'Review the outcome below. Approve to apply, or provide feedback to renegotiate.'
                                        : negotiationLog.negotiation_result === 'auto_resolved'
                                            ? 'The AI agents have reached consensus and resolved the issue.'
                                            : 'The AI agents could not reach consensus.'}
                                </p>
                            </div>
                            <button onClick={() => setShowNegotiationModal(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto flex-1 space-y-6">
                            {/* Negotiation Rounds */}
                            {negotiationLog.overview?.history && (
                                <div className="space-y-4">
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">Negotiation Process</h3>
                                    {negotiationLog.overview.history.map((round: any, idx: number) => (
                                        <div key={idx} className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-slate-50 dark:bg-slate-800/20">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="px-2 py-1 bg-teal-100 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400 text-xs font-bold rounded">
                                                    Round {round.round}
                                                </span>
                                            </div>
                                            <div className="grid grid-cols-1 gap-2">
                                                {Object.entries(round.proposals || {}).map(([agent, proposal]: [string, any]) => (
                                                    <div key={agent} className="p-3 bg-white dark:bg-slate-900 rounded-lg border border-slate-100 dark:border-slate-700">
                                                        <p className="font-bold text-sm text-slate-700 dark:text-slate-300 mb-1">{agent}</p>
                                                        <p className="text-xs text-slate-600 dark:text-slate-400 italic">"{proposal}"</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Final Agreement */}
                            {negotiationLog.overview?.agreement_text && (
                                <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-6 border-2 border-emerald-200 dark:border-emerald-800 shadow-sm">
                                    <h3 className="text-sm font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                        <span className="material-symbols-outlined text-[18px]">handshake</span>
                                        Proposed Agreement
                                    </h3>
                                    <p className="text-slate-800 dark:text-slate-200 font-medium text-lg leading-relaxed">
                                        "{negotiationLog.overview.agreement_text}"
                                    </p>
                                </div>
                            )}

                            {/* Summary */}
                            {negotiationLog.overview?.summary && (
                                <div className="bg-teal-50 dark:bg-teal-900/20 rounded-xl p-4">
                                    <h3 className="text-sm font-bold text-teal-600 uppercase tracking-wider mb-2">Summary</h3>
                                    <p className="text-slate-700 dark:text-slate-300">
                                        {negotiationLog.overview.summary}
                                    </p>
                                </div>
                            )}

                            {/* Fallback for Legacy/Escalation */}
                            {!negotiationLog.overview && (negotiationLog.winning_proposal || negotiationLog.proposal) && (
                                <div className="bg-teal-50 dark:bg-teal-900/20 rounded-xl p-4">
                                    <h3 className="text-sm font-bold text-teal-600 uppercase tracking-wider mb-2">Resolved Resolution (Legacy)</h3>
                                    <p className="text-slate-700 dark:text-slate-300 font-medium">
                                        {(negotiationLog.winning_proposal || negotiationLog.proposal).action}
                                    </p>
                                </div>
                            )}

                            {/* Unresolved Options if Escalated */}
                            {negotiationLog.negotiation_result === 'escalated_to_human' && negotiationLog.proposals_considered && (
                                <div className="space-y-3">
                                    <h3 className="text-sm font-bold text-amber-600 uppercase tracking-wider">Unresolved Options (Escalated)</h3>
                                    {negotiationLog.proposals_considered.map((opt: any) => (
                                        <div key={opt.id} className="p-3 border border-slate-200 dark:border-slate-700 rounded-lg text-xs">
                                            <span className="font-bold">{opt.action}</span>
                                            <p className="text-slate-500 mt-1">{opt.rationale}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer Actions for Approval */}
                        {negotiationLog.negotiation_result === 'pending_approval' ? (
                            <div className="p-6 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30">
                                <div className="flex flex-col gap-4">
                                    <div className="flex items-center gap-4">
                                        <button
                                            disabled={loading}
                                            onClick={async () => {
                                                if (!activeConflict) return;
                                                setLoading(true);
                                                try {
                                                    await approveResolution(activeConflict.id);
                                                    setShowNegotiationModal(false);
                                                    const newConflicts = await getConflicts();
                                                    setConflicts(newConflicts);
                                                } catch (e) { console.error(e); }
                                                finally { setLoading(false); }
                                            }}
                                            className={`clickable-scale flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 disabled:cursor-wait text-white rounded-xl text-sm font-bold shadow-lg shadow-emerald-500/20 active:scale-95 flex items-center justify-center gap-2 transition-all`}
                                        >
                                            {loading ? (
                                                <>
                                                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                                    Processing...
                                                </>
                                            ) : (
                                                <>
                                                    <span className="material-symbols-outlined">check_circle</span>
                                                    Approve & Execute Resolution
                                                </>
                                            )}
                                        </button>
                                    </div>

                                    <div className="relative py-2">
                                        <div className="absolute inset-0 flex items-center" aria-hidden="true">
                                            <div className="w-full border-t border-slate-200 dark:border-slate-700"></div>
                                        </div>
                                        <div className="relative flex justify-center">
                                            <span className="bg-slate-50 dark:bg-slate-800/30 px-2 text-xs text-slate-400 uppercase tracking-widest font-semibold">Or Request Changes</span>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <div className="flex-1 relative">
                                            <input
                                                type="text"
                                                placeholder="Example: 'Do not move the workshop to 9am, find another venue instead.'"
                                                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl pl-4 pr-10 py-2.5 text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all"
                                                value={negotiationPrompt}
                                                onChange={(e) => setNegotiationPrompt(e.target.value)}
                                                onKeyDown={async (e) => {
                                                    if (e.key === 'Enter' && negotiationPrompt && activeConflict) {
                                                        setLoading(true);
                                                        try {
                                                            const result = await autoNegotiateConflict(activeConflict.id, negotiationPrompt);
                                                            setNegotiationLog(result);
                                                            setNegotiationPrompt("");
                                                        } catch (e) { console.error(e); }
                                                        finally { setLoading(false); }
                                                    }
                                                }}
                                            />
                                            {negotiationPrompt && (
                                                <button
                                                    onClick={() => setNegotiationPrompt("")}
                                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                                                >
                                                    <span className="material-symbols-outlined text-sm">close</span>
                                                </button>
                                            )}
                                        </div>
                                        <button
                                            disabled={!negotiationPrompt || loading}
                                            onClick={async () => {
                                                if (!activeConflict) return;
                                                setLoading(true);
                                                try {
                                                    const result = await autoNegotiateConflict(activeConflict.id, negotiationPrompt);
                                                    setNegotiationLog(result);
                                                    setNegotiationPrompt("");
                                                } catch (e) { console.error(e); }
                                                finally { setLoading(false); }
                                            }}
                                            className={`clickable-scale px-6 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-sm font-bold shadow-lg shadow-teal-500/20 active:scale-95 transition-all flex items-center gap-2`}
                                        >
                                            {loading ? (
                                                <>
                                                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                                    Renegotiating...
                                                </>
                                            ) : (
                                                <>
                                                    <span className="material-symbols-outlined">refresh</span>
                                                    Renegotiate
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end bg-white dark:bg-slate-900">
                                <button onClick={() => setShowNegotiationModal(false)} className="clickable-scale px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-bold transition-all">Close</button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* History Modal */}
            {showHistoryModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center bg-slate-50 dark:bg-slate-800/50">
                            <div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    <span className="material-symbols-outlined text-emerald-500">history</span>
                                    Resolved Conflicts History
                                </h2>
                                <p className="text-sm text-slate-500">Archive of resolved and dismissed issues</p>
                            </div>
                            <button
                                onClick={() => setShowHistoryModal(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto flex-1 space-y-4">
                            {historyConflicts.length === 0 ? (
                                <div className="text-center py-10 text-slate-500">
                                    <span className="material-symbols-outlined text-4xl mb-2">inbox</span>
                                    <p>No resolved conflicts found</p>
                                </div>
                            ) : (
                                historyConflicts.map((conflict) => (
                                    <div key={conflict.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/20">
                                        <div className="flex justify-between items-start mb-2">
                                            <Badge variant={conflict.status === 'resolved' ? 'success' : 'neutral'}>
                                                {conflict.status.toUpperCase()}
                                            </Badge>
                                            <span className="text-xs text-slate-400">
                                                {new Date(conflict.detected_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <p className="font-bold text-slate-800 dark:text-slate-200 text-sm mb-1">
                                            {conflict.description}
                                        </p>
                                        <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                                            <span className="material-symbols-outlined text-[14px]">smart_toy</span>
                                            <span>
                                                {conflict.status === 'resolved'
                                                    ? 'Resolved by Supervisor Agent'
                                                    : 'Dismissed by User'}
                                            </span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end bg-white dark:bg-slate-900">
                            <button
                                onClick={() => setShowHistoryModal(false)}
                                className="clickable-scale px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-bold transition-all"
                            >
                                Close History
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Manual Resolution Modal */}
            <ManualResolutionModal
                isOpen={showResolutionModal}
                conflict={activeConflict}
                onClose={() => setShowResolutionModal(false)}
                onResolve={handleManualResolve}
            />
        </>
    );
}
