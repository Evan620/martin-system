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
                            <h2 className="text-xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>Admin Control Tower</h2>
                            <Badge variant="warning" className="uppercase tracking-widest text-[10px]">Secretariat Eyes Only</Badge>
                        </div>
                        <p className="text-sm" style={{ color: 'var(--ink-500)' }}>Synthesis & Conflict Resolution Center</p>
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
                            className="clickable-scale bg-slate-900 px-4 py-2 rounded-xl text-xs font-bold transition-all active:scale-95"
                            style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
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
                            className="clickable-scale px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 active:scale-95"
                            style={{ background: 'color-mix(in srgb, var(--terra) 12%, transparent)', color: 'var(--terra)', border: '1px solid color-mix(in srgb, var(--terra) 30%, transparent)' }}
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
                        <Card className="p-5 border-l-4" style={{ borderLeftColor: 'var(--accent)' }}>
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h3 className="font-bold" style={{ color: 'var(--ink-900)' }}>Weekly Packet</h3>
                                    <p className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--ink-500)' }}>Target: Friday 17:00</p>
                                </div>
                                <div className="text-right">
                                    <span className="text-2xl font-bold" style={{ color: 'var(--accent)' }}>{packetCompletion}%</span>
                                </div>
                            </div>
                            <div className="w-full h-2 rounded-full overflow-hidden mb-4" style={{ background: 'var(--surface-2)' }}>
                                <div className="h-full rounded-full" style={{ width: `${packetCompletion}%`, background: 'var(--accent)' }}></div>
                            </div>
                            <div className="space-y-2">
                                {weeklyPacketData ? (
                                    weeklyPacketData.twg_activity.length > 0 ? (
                                        weeklyPacketData.twg_activity.slice(0, 5).map((item: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between text-xs pb-2 last:border-0 last:pb-0" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                                                <div className="flex flex-col">
                                                    <span className="font-bold" style={{ color: 'var(--ink-700)' }}>{item.name}</span>
                                                    <span className="text-[9px]" style={{ color: 'var(--ink-400)' }}>{item.accomplishments_count} wins, {item.risks_count} risks</span>
                                                </div>
                                                <Badge variant={item.status === 'Ready' ? 'success' : 'warning'} className="text-[10px]">
                                                    {item.status}
                                                </Badge>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center text-xs italic py-2" style={{ color: 'var(--ink-400)' }}>No active TWG packets generated yet.</div>
                                    )
                                ) : (
                                    <div className="text-center py-4">
                                        <p className="text-xs mb-2" style={{ color: 'var(--ink-400)' }}>Detailed packets not generated</p>
                                        <button
                                            onClick={() => document.querySelector<HTMLElement>('button[class*="bg-slate-900"]')?.click()}
                                            className="text-[10px] font-bold uppercase tracking-wider"
                                            style={{ color: 'var(--accent)' }}
                                        >
                                            Generate Now
                                        </button>
                                    </div>
                                )}
                            </div>
                        </Card>

                        {/* System Health / Reconciliation */}
                        <Card className="p-5 border-l-4" style={{ borderLeftColor: reconciliationResult && reconciliationResult.conflicts_detected > 0 ? 'var(--amber)' : 'var(--sage)' }}>
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <h3 className="font-bold" style={{ color: 'var(--ink-900)' }}>Reconciliation State</h3>
                                    <p className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--ink-500)' }}>
                                        {reconciliationResult ? `Last scan: ${new Date(reconciliationResult.scan_time).toLocaleTimeString()}` : 'Auto-Debate Engine'}
                                    </p>
                                </div>
                                {reconciliationResult && reconciliationResult.conflicts_detected > 0 ? (
                                    <span className="material-symbols-outlined animate-pulse" style={{ color: 'var(--amber)' }}>warning</span>
                                ) : (
                                    <span className="material-symbols-outlined animate-pulse" style={{ color: 'var(--sage)' }}>check_circle</span>
                                )}
                            </div>

                            {reconciliationResult ? (
                                <div className="space-y-3 mt-4">
                                    <div className="flex items-center gap-4">
                                        <div className="flex-1 text-center p-3 rounded-lg" style={{ background: 'color-mix(in srgb, var(--terra) 10%, transparent)' }}>
                                            <div className="text-lg font-bold" style={{ color: 'var(--terra)' }}>
                                                {reconciliationResult.conflicts_detected}
                                            </div>
                                            <div className="text-[9px] font-black uppercase" style={{ color: 'var(--ink-400)' }}>Detected</div>
                                        </div>
                                        <div className="flex-1 text-center p-3 rounded-lg" style={{ background: 'color-mix(in srgb, var(--sage) 10%, transparent)' }}>
                                            <div className="text-lg font-bold" style={{ color: 'var(--sage)' }}>
                                                {reconciliationResult.auto_resolved}
                                            </div>
                                            <div className="text-[9px] font-black uppercase" style={{ color: 'var(--ink-400)' }}>Auto-Resolved</div>
                                        </div>
                                    </div>

                                    {reconciliationResult.breakdown && (
                                        <div className="text-xs space-y-1 pt-2" style={{ borderTop: '1px solid var(--border)', color: 'var(--ink-700)' }}>
                                            {reconciliationResult.breakdown.same_slot > 0 && (
                                                <div className="flex justify-between"><span>⏰ Same-slot</span><span className="font-bold" style={{ color: 'var(--terra)' }}>{reconciliationResult.breakdown.same_slot}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.venue > 0 && (
                                                <div className="flex justify-between"><span>🏛️ Venue</span><span className="font-bold" style={{ color: 'var(--terra)' }}>{reconciliationResult.breakdown.venue}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.vip_double_booking > 0 && (
                                                <div className="flex justify-between"><span>👤 VIP Double-booking</span><span className="font-bold" style={{ color: 'var(--terra)' }}>{reconciliationResult.breakdown.vip_double_booking}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.crowding > 0 && (
                                                <div className="flex justify-between"><span>⚠️ Crowding</span><span className="font-bold" style={{ color: 'var(--amber)' }}>{reconciliationResult.breakdown.crowding}</span></div>
                                            )}
                                            {reconciliationResult.breakdown.overdue_action > 0 && (
                                                <div className="flex justify-between"><span>📋 Overdue</span><span className="font-bold" style={{ color: 'var(--amber)' }}>{reconciliationResult.breakdown.overdue_action}</span></div>
                                            )}
                                            {reconciliationResult.conflicts_detected === 0 && (
                                                <div className="text-center font-bold" style={{ color: 'var(--sage)' }}>✅ All clear!</div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="flex items-center gap-4 mt-4">
                                    <div
                                        onClick={handleShowHistory}
                                        className="flex-1 text-center p-3 rounded-lg cursor-pointer transition-colors"
                                        style={{ background: 'color-mix(in srgb, var(--sage) 10%, transparent)' }}
                                    >
                                        <div className="text-lg font-bold" style={{ color: 'var(--sage)' }}>
                                            {conflicts.filter(c => c.status === 'resolved' || c.status === 'dismissed').length}
                                        </div>
                                        <div className="text-[9px] font-black uppercase" style={{ color: 'var(--ink-400)' }}>Resolved • View History</div>
                                    </div>
                                    <div className="flex-1 text-center p-3 rounded-lg" style={{ background: 'color-mix(in srgb, var(--amber) 10%, transparent)' }}>
                                        <div className="text-lg font-bold" style={{ color: 'var(--amber)' }}>
                                            {conflicts.filter(c => c.status === 'detected' || c.status === 'negotiating' || c.status === 'escalated').length}
                                        </div>
                                        <div className="text-[9px] font-black uppercase" style={{ color: 'var(--ink-400)' }}>Pending</div>
                                    </div>
                                </div>
                            )}
                        </Card>
                    </div>

                    {/* 2. Conflict Radar / Alerts */}
                    <div className="col-span-12 lg:col-span-8">
                        <Card className="h-full p-0 overflow-hidden border-t-4 relative group/card"
                            style={{ borderTopColor: 'var(--terra)' }}
                            onMouseEnter={() => setIsPaused(true)}
                            onMouseLeave={() => setIsPaused(false)}
                        >
                            <div className="p-5 flex justify-between items-center" style={{ borderBottom: '1px solid var(--border)', background: 'color-mix(in srgb, var(--terra) 6%, transparent)' }}>
                                <h3 className="font-bold flex items-center gap-2" style={{ color: 'var(--ink-900)' }}>
                                    <span className="material-symbols-outlined" style={{ color: 'var(--terra)' }}>radar</span>
                                    Detected Conflicts & Inconsistencies
                                </h3>
                                {/* Pagination Dots */}
                                <div className="flex gap-1">
                                    {conflicts.map((_, idx) => (
                                        <div
                                            key={idx}
                                            className={`h-1.5 rounded-full transition-all ${idx === currentIndex ? 'w-3' : 'w-1.5'}`}
                                            style={{ background: idx === currentIndex ? 'var(--terra)' : 'var(--ink-300)' }}
                                        />
                                    ))}
                                </div>
                            </div>

                            <div className="relative min-h-[300px]">
                                {loading && (
                                    <div className="absolute inset-0 flex items-center justify-center italic z-10" style={{ color: 'var(--ink-500)', background: 'color-mix(in srgb, var(--surface) 50%, transparent)' }}>
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
                                                <span className="text-xs font-bold" style={{ color: 'var(--ink-500)' }}>
                                                    {activeConflict.agents_involved.join(' vs ')}
                                                </span>
                                            </div>
                                        </div>

                                        <h4 className="text-xl font-bold mb-4 leading-tight" style={{ color: 'var(--ink-900)' }}>{activeConflict.description}</h4>

                                        <div className="p-5 rounded-xl mb-6 relative" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                                            <span className="absolute -top-3 left-4 px-2 text-[10px] font-bold uppercase tracking-widest" style={{ background: 'var(--surface-2)', color: 'var(--ink-400)' }}>Conflict Details</span>
                                            <p className="text-sm leading-relaxed italic" style={{ color: 'var(--ink-600)' }}>
                                                "{Object.entries(activeConflict.conflicting_positions || {}).map(([k, v]) => `${k}: ${v}`).join(' | ')}"
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-3">
                                            {activeConflict.status === 'escalated' ? (
                                                <button
                                                    onClick={() => setShowResolutionModal(true)}
                                                    className="clickable-scale px-4 py-2 rounded-xl text-sm font-bold transition-colors active:scale-95 flex items-center gap-2"
                                                    style={{ background: 'var(--terra)', color: '#ffffff' }}
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
                                                    className="clickable-scale px-4 py-2 rounded-xl text-sm font-bold transition-colors active:scale-95"
                                                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
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
                                                className="clickable-scale px-4 py-2 rounded-xl text-sm font-bold transition-colors"
                                                style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)' }}
                                            >
                                                Dismiss Issue
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* Empty State */}
                                {!loading && conflicts.length === 0 && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ color: 'var(--ink-400)' }}>
                                        <span className="material-symbols-outlined text-5xl mb-4 p-4 rounded-full" style={{ color: 'var(--sage)', background: 'color-mix(in srgb, var(--sage) 10%, transparent)' }}>check_circle</span>
                                        <p className="font-bold">No active conflicts detected.</p>
                                        <p className="text-xs opacity-70 mt-1">System is running optimally</p>
                                    </div>
                                )}

                                {/* Navigation Controls (Visible on Hover) */}
                                {conflicts.length > 1 && (
                                    <>
                                        <button
                                            onClick={prevConflict}
                                            className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full shadow-md flex items-center justify-center hover:scale-110 transition-all opacity-0 group-hover/card:opacity-100 z-20"
                                            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-500)' }}
                                        >
                                            <span className="material-symbols-outlined text-lg">chevron_left</span>
                                        </button>
                                        <button
                                            onClick={nextConflict}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full shadow-md flex items-center justify-center hover:scale-110 transition-all opacity-0 group-hover/card:opacity-100 z-20"
                                            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-500)' }}
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
                <div className="fixed inset-0 flex items-center justify-center z-50 p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
                    <div className="w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                        <div className="p-6 flex justify-between items-center" style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                            <div>
                                <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--ink-900)' }}>
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
                                <p className="text-sm mt-1" style={{ color: 'var(--ink-500)' }}>
                                    {negotiationLog.negotiation_result === 'pending_approval'
                                        ? 'Review the outcome below. Approve to apply, or provide feedback to renegotiate.'
                                        : negotiationLog.negotiation_result === 'auto_resolved'
                                            ? 'The AI agents have reached consensus and resolved the issue.'
                                            : 'The AI agents could not reach consensus.'}
                                </p>
                            </div>
                            <button onClick={() => setShowNegotiationModal(false)} className="hover:opacity-70" style={{ color: 'var(--ink-400)' }}>
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto flex-1 space-y-6">
                            {/* Negotiation Rounds */}
                            {negotiationLog.overview?.history && (
                                <div className="space-y-4">
                                    <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--ink-500)' }}>Negotiation Process</h3>
                                    {negotiationLog.overview.history.map((round: any, idx: number) => (
                                        <div key={idx} className="rounded-xl p-4" style={{ border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className="px-2 py-1 text-xs font-bold rounded" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                                    Round {round.round}
                                                </span>
                                            </div>
                                            <div className="grid grid-cols-1 gap-2">
                                                {Object.entries(round.proposals || {}).map(([agent, proposal]: [string, any]) => (
                                                    <div key={agent} className="p-3 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                                                        <p className="font-bold text-sm mb-1" style={{ color: 'var(--ink-700)' }}>{agent}</p>
                                                        <p className="text-xs italic" style={{ color: 'var(--ink-600)' }}>"{proposal}"</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Final Agreement */}
                            {negotiationLog.overview?.agreement_text && (
                                <div className="rounded-xl p-6 shadow-sm" style={{ background: 'color-mix(in srgb, var(--sage) 10%, transparent)', border: '2px solid color-mix(in srgb, var(--sage) 30%, transparent)' }}>
                                    <h3 className="text-sm font-bold uppercase tracking-wider mb-2 flex items-center gap-2" style={{ color: 'var(--sage)' }}>
                                        <span className="material-symbols-outlined text-[18px]">handshake</span>
                                        Proposed Agreement
                                    </h3>
                                    <p className="font-medium text-lg leading-relaxed" style={{ color: 'var(--ink-800)' }}>
                                        "{negotiationLog.overview.agreement_text}"
                                    </p>
                                </div>
                            )}

                            {/* Summary */}
                            {negotiationLog.overview?.summary && (
                                <div className="rounded-xl p-4" style={{ background: 'var(--accent-soft)' }}>
                                    <h3 className="text-sm font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--accent)' }}>Summary</h3>
                                    <p style={{ color: 'var(--ink-700)' }}>
                                        {negotiationLog.overview.summary}
                                    </p>
                                </div>
                            )}

                            {/* Fallback for Legacy/Escalation */}
                            {!negotiationLog.overview && (negotiationLog.winning_proposal || negotiationLog.proposal) && (
                                <div className="rounded-xl p-4" style={{ background: 'var(--accent-soft)' }}>
                                    <h3 className="text-sm font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--accent)' }}>Resolved Resolution (Legacy)</h3>
                                    <p className="font-medium" style={{ color: 'var(--ink-700)' }}>
                                        {(negotiationLog.winning_proposal || negotiationLog.proposal).action}
                                    </p>
                                </div>
                            )}

                            {/* Unresolved Options if Escalated */}
                            {negotiationLog.negotiation_result === 'escalated_to_human' && negotiationLog.proposals_considered && (
                                <div className="space-y-3">
                                    <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--amber)' }}>Unresolved Options (Escalated)</h3>
                                    {negotiationLog.proposals_considered.map((opt: any) => (
                                        <div key={opt.id} className="p-3 rounded-lg text-xs" style={{ border: '1px solid var(--border)', color: 'var(--ink-700)' }}>
                                            <span className="font-bold">{opt.action}</span>
                                            <p className="mt-1" style={{ color: 'var(--ink-500)' }}>{opt.rationale}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer Actions for Approval */}
                        {negotiationLog.negotiation_result === 'pending_approval' ? (
                            <div className="p-6" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
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
                                            className={`clickable-scale flex-1 py-3 disabled:opacity-60 disabled:cursor-wait rounded-xl text-sm font-bold active:scale-95 flex items-center justify-center gap-2 transition-all`}
                                            style={{ background: 'var(--sage)', color: '#ffffff' }}
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
                                            <div className="w-full" style={{ borderTop: '1px solid var(--border)' }}></div>
                                        </div>
                                        <div className="relative flex justify-center">
                                            <span className="px-2 text-xs uppercase tracking-widest font-semibold" style={{ background: 'var(--surface-2)', color: 'var(--ink-400)' }}>Or Request Changes</span>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <div className="flex-1 relative">
                                            <input
                                                type="text"
                                                placeholder="Example: 'Do not move the workshop to 9am, find another venue instead.'"
                                                className="w-full rounded-xl pl-4 pr-10 py-2.5 text-sm focus:ring-2 focus:border-transparent outline-none transition-all"
                                                style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-800)' }}
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
                                                    className="absolute right-2 top-1/2 -translate-y-1/2 hover:opacity-70"
                                                    style={{ color: 'var(--ink-400)' }}
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
                                            className={`clickable-scale px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-sm font-bold active:scale-95 transition-all flex items-center gap-2`}
                                            style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
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
                            <div className="p-4 flex justify-end" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
                                <button onClick={() => setShowNegotiationModal(false)} className="clickable-scale px-4 py-2 rounded-xl text-sm font-bold transition-all" style={{ background: 'var(--surface-2)', color: 'var(--ink-700)', border: '1px solid var(--border)' }}>Close</button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* History Modal */}
            {showHistoryModal && (
                <div className="fixed inset-0 flex items-center justify-center z-50 p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
                    <div className="w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col shadow-2xl" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                        <div className="p-6 flex justify-between items-center" style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                            <div>
                                <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--ink-900)' }}>
                                    <span className="material-symbols-outlined" style={{ color: 'var(--sage)' }}>history</span>
                                    Resolved Conflicts History
                                </h2>
                                <p className="text-sm" style={{ color: 'var(--ink-500)' }}>Archive of resolved and dismissed issues</p>
                            </div>
                            <button
                                onClick={() => setShowHistoryModal(false)}
                                className="hover:opacity-70"
                                style={{ color: 'var(--ink-400)' }}
                            >
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto flex-1 space-y-4">
                            {historyConflicts.length === 0 ? (
                                <div className="text-center py-10" style={{ color: 'var(--ink-500)' }}>
                                    <span className="material-symbols-outlined text-4xl mb-2">inbox</span>
                                    <p>No resolved conflicts found</p>
                                </div>
                            ) : (
                                historyConflicts.map((conflict) => (
                                    <div key={conflict.id} className="p-4 rounded-xl" style={{ border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                                        <div className="flex justify-between items-start mb-2">
                                            <Badge variant={conflict.status === 'resolved' ? 'success' : 'neutral'}>
                                                {conflict.status.toUpperCase()}
                                            </Badge>
                                            <span className="text-xs" style={{ color: 'var(--ink-400)' }}>
                                                {new Date(conflict.detected_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <p className="font-bold text-sm mb-1" style={{ color: 'var(--ink-800)' }}>
                                            {conflict.description}
                                        </p>
                                        <div className="flex items-center gap-2 mt-2 text-xs" style={{ color: 'var(--ink-500)' }}>
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

                        <div className="p-4 flex justify-end" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
                            <button
                                onClick={() => setShowHistoryModal(false)}
                                className="clickable-scale px-4 py-2 rounded-xl text-sm font-bold transition-all"
                                style={{ background: 'var(--surface-2)', color: 'var(--ink-700)', border: '1px solid var(--border)' }}
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
