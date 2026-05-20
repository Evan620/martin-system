import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector } from '../../hooks/useRedux';
import {
    getDashboardStats,
    getTimeline,
    DashboardStats,
    TimelineItem,
} from '../../services/dashboardService';

// ─── helpers ──────────────────────────────────────────────────

function getGreeting() {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
}

function getPillarIcon(pillar: string) {
    const p = pillar.toLowerCase();
    if (p === 'minerals') return 'diamond';
    if (p === 'energy') return 'bolt';
    if (p === 'agribusiness' || p === 'agriculture') return 'agriculture';
    if (p === 'digital') return 'terminal';
    return 'groups';
}

function formatCountdown(dateString: string | null) {
    if (!dateString) return 'TBD';
    const diff = new Date(dateString).getTime() - Date.now();
    const days = Math.ceil(diff / 86_400_000);
    if (days < 0) return 'Past';
    if (days === 0) return 'Today';
    return `${days}d`;
}

function formatShortDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
    });
}

function generateBriefing(
    stats: DashboardStats | null,
    todayCount: number,
    atRiskCount: number,
): string {
    if (!stats) return 'Loading your briefing…';
    const parts: string[] = [];

    if (todayCount > 0)
        parts.push(`${todayCount} meeting${todayCount > 1 ? 's' : ''} on today's agenda.`);

    if (stats.metrics.pending_approvals > 0)
        parts.push(`${stats.metrics.pending_approvals} pending task${stats.metrics.pending_approvals > 1 ? 's' : ''} need your attention.`);

    if (atRiskCount > 0)
        parts.push(`${atRiskCount} TWG${atRiskCount > 1 ? 's' : ''} flagged at risk — review before Summit.`);

    if (stats.metrics.next_plenary.date) {
        const days = Math.ceil(
            (new Date(stats.metrics.next_plenary.date).getTime() - Date.now()) / 86_400_000,
        );
        if (days > 0 && days <= 60)
            parts.push(`Summit in ${days} day${days !== 1 ? 's' : ''}.`);
    }

    return parts.length ? parts.join(' ') : 'All systems on track. No urgent items today.';
}

// ─── component ────────────────────────────────────────────────

export default function Dashboard() {
    const navigate = useNavigate();
    const { user } = useAppSelector((s) => s.auth);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [timeline, setTimeline] = useState<TimelineItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const withTimeout = <T,>(p: Promise<T>, ms: number): Promise<T> =>
            Promise.race([p, new Promise<T>((_, r) => setTimeout(() => r(new Error('timeout')), ms))]);

        (async () => {
            const [s, t] = await Promise.allSettled([
                withTimeout(getDashboardStats(), 8000),
                withTimeout(getTimeline(), 8000),
            ]);
            if (s.status === 'fulfilled') setStats(s.value);
            if (t.status === 'fulfilled') setTimeline(t.value);
            setLoading(false);
        })();
    }, []);


    const todayStr = new Date().toISOString().split('T')[0];
    const todayItems = timeline.filter((i) => i.date.startsWith(todayStr));
    const upcomingItems = timeline
        .filter((i) => new Date(i.date) >= new Date())
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
        .slice(0, 6);

    const atRiskCount =
        stats?.twg_health.filter((t) => t.status === 'stalled' || t.completion < 50).length ?? 0;

    const firstName = user?.full_name?.split(' ')[0] || 'there';

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="flex flex-col items-center gap-3">
                    <div className="size-10 border-[3px] border-primary border-t-transparent rounded-full animate-spin" />
                    <p className="text-slate-500 text-sm font-medium">Loading dashboard…</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">

            {/* ── Page header ───────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
                        {getGreeting()}, {firstName}
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                        {new Date().toLocaleDateString('en-US', {
                            weekday: 'long', month: 'long', day: 'numeric',
                        })}
                    </p>
                </div>
            </div>

            {/* ── Martin's AI Briefing Banner ───────────────────── */}
            <div className="glass-martin rounded-2xl p-4">
                <div className="flex items-start gap-3">
                    <div className="size-9 rounded-xl bg-primary/10 dark:bg-primary/20 flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-primary text-[20px]">psychology</span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-primary/70 mb-1">
                            Martin's Briefing
                        </p>
                        <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
                            {generateBriefing(stats, todayItems.length, atRiskCount)}
                        </p>
                    </div>
                    <p className="text-[10px] text-slate-400 font-medium shrink-0">
                        {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                </div>
            </div>

            {/* ── KPI Row ───────────────────────────────────────── */}
            <div className="grid grid-cols-3 gap-3">

                {/* Active TWGs */}
                <div className="glass-card rounded-2xl p-4">
                    <div className="flex items-start justify-between mb-2">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                            Active TWGs
                        </p>
                        <div className="size-8 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary text-[18px]">groups</span>
                        </div>
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">
                        {stats?.metrics.active_twgs ?? 0}
                    </h3>
                    <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-[11px] font-semibold">
                        <span className="material-symbols-outlined text-[13px]">trending_up</span>
                        All tracking
                    </div>
                </div>

                {/* Pending Tasks */}
                <div className="glass-card rounded-2xl p-4">
                    <div className="flex items-start justify-between mb-2">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                            Pending Tasks
                        </p>
                        <div className="size-8 rounded-xl bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center">
                            <span className="material-symbols-outlined text-amber-500 text-[18px]">pending_actions</span>
                        </div>
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">
                        {stats?.metrics.pending_approvals ?? 0}
                    </h3>
                    <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400 text-[11px] font-semibold">
                        <span className="material-symbols-outlined text-[13px]">warning</span>
                        Action required
                    </div>
                </div>

                {/* Summit Countdown */}
                <div className="glass-card rounded-2xl p-4 bg-gradient-to-br from-primary/8 to-violet-500/5">
                    <div className="flex items-start justify-between mb-2">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-primary/70">
                            Summit
                        </p>
                        <div className="size-8 rounded-xl bg-primary/10 dark:bg-primary/20 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary text-[18px]">event_available</span>
                        </div>
                    </div>
                    <h3 className="text-2xl font-bold text-primary mb-1">
                        {formatCountdown(stats?.metrics.next_plenary.date ?? null)}
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium truncate">
                        {stats?.metrics.next_plenary.date
                            ? formatShortDate(stats.metrics.next_plenary.date)
                            : stats?.metrics.next_plenary.title ?? 'TBD'}
                    </p>
                </div>
            </div>

            {/* ── Two-column main area ──────────────────────────── */}
            <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">

                {/* Left col — 3/5: Schedule + TWG Readiness */}
                <div className="xl:col-span-3 flex flex-col gap-4">

                    {/* Today's schedule (only if events exist) */}
                    {todayItems.length > 0 && (
                        <div className="glass-card rounded-2xl p-4">
                            <div className="flex items-center justify-between mb-3">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                                    Today's Schedule
                                </p>
                                <span className="text-[11px] font-semibold text-primary bg-primary/8 px-2 py-0.5 rounded-full">
                                    {todayItems.length} event{todayItems.length > 1 ? 's' : ''}
                                </span>
                            </div>
                            <div className="space-y-1">
                                {todayItems.map((item, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-3 py-2 border-b border-white/50 dark:border-white/10 last:border-0"
                                    >
                                        <div
                                            className={`size-2 rounded-full shrink-0 ${item.status === 'critical' ? 'bg-red-500' : 'bg-blue-400'}`}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                                                {item.title}
                                            </p>
                                            <p className="text-[11px] text-slate-500 dark:text-slate-400">{item.twg}</p>
                                        </div>
                                        <span className="text-[11px] text-slate-400 dark:text-slate-500 shrink-0">
                                            {new Date(item.date).toLocaleTimeString('en-US', {
                                                hour: '2-digit', minute: '2-digit',
                                            })}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* TWG Readiness grid */}
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                                TWG Readiness
                            </p>
                            <button
                                onClick={() => navigate('/twgs')}
                                className="text-[11px] font-semibold text-primary hover:underline"
                            >
                                View all
                            </button>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {stats?.twg_health.map((twg) => (
                                <div
                                    key={twg.id}
                                    className="glass-card rounded-xl p-3 cursor-pointer hover:scale-[1.015] transition-transform"
                                    onClick={() => navigate(`/workspace/${twg.id}`)}
                                >
                                    <div className="flex items-start justify-between gap-2 mb-3">
                                        <div className="flex items-center gap-2">
                                            <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary shrink-0">
                                                <span className="material-symbols-outlined text-[16px]">
                                                    {getPillarIcon(twg.pillar)}
                                                </span>
                                            </div>
                                            <div>
                                                <p className="text-sm font-semibold text-slate-900 dark:text-white leading-tight">
                                                    {twg.name}
                                                </p>
                                                <p className="text-[11px] text-slate-500 dark:text-slate-400">{twg.lead}</p>
                                            </div>
                                        </div>
                                        <span
                                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                                                twg.status === 'active'
                                                    ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                                                    : 'bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                                            }`}
                                        >
                                            {twg.status.toUpperCase()}
                                        </span>
                                    </div>
                                    <div>
                                        <div className="flex justify-between text-[11px] mb-1.5">
                                            <span className="text-slate-500 dark:text-slate-400">Readiness</span>
                                            <span
                                                className={`font-bold ${
                                                    twg.completion >= 70
                                                        ? 'text-emerald-600 dark:text-emerald-400'
                                                        : twg.completion >= 50
                                                        ? 'text-amber-500'
                                                        : 'text-red-500'
                                                }`}
                                            >
                                                {twg.completion}%
                                            </span>
                                        </div>
                                        <div className="h-1.5 w-full bg-slate-100/80 dark:bg-slate-700/60 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full rounded-full transition-all duration-700 ${
                                                    twg.completion >= 70
                                                        ? 'bg-emerald-500'
                                                        : twg.completion >= 50
                                                        ? 'bg-amber-400'
                                                        : 'bg-red-400'
                                                }`}
                                                style={{ width: `${twg.completion}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right col — 2/5: Upcoming Events */}
                <div className="xl:col-span-2 glass-card rounded-2xl p-4 flex flex-col min-h-[420px]">
                    <div className="flex items-center justify-between mb-4">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                            Upcoming Events
                        </p>
                        <button
                            onClick={() => navigate('/schedule')}
                            className="text-[11px] font-semibold text-primary hover:underline"
                        >
                            All
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto no-scrollbar space-y-1">
                        {upcomingItems.length > 0 ? (
                            upcomingItems.map((item, i) => {
                                const d = new Date(item.date);
                                return (
                                    <div
                                        key={i}
                                        className="flex gap-3 items-start py-2.5 border-b border-white/50 dark:border-white/10 last:border-0"
                                    >
                                        <div className="text-center shrink-0 w-9">
                                            <p className="text-[9px] font-bold text-primary/70 uppercase">
                                                {d.toLocaleString('en-US', { month: 'short' })}
                                            </p>
                                            <p className="text-lg font-bold text-slate-800 dark:text-white leading-none">
                                                {d.getDate()}
                                            </p>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-slate-800 dark:text-slate-100 leading-snug">
                                                {item.title}
                                            </p>
                                            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                                                {item.twg}
                                            </p>
                                        </div>
                                        <div
                                            className={`size-2 mt-1.5 rounded-full shrink-0 ${
                                                item.status === 'critical' ? 'bg-red-500' : 'bg-blue-400'
                                            }`}
                                        />
                                    </div>
                                );
                            })
                        ) : (
                            <div className="flex flex-col items-center justify-center flex-1 py-12 text-slate-400">
                                <span className="material-symbols-outlined text-[32px] mb-2">
                                    event_available
                                </span>
                                <p className="text-sm">No upcoming events</p>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={() => navigate('/schedule')}
                        className="mt-3 pt-3 border-t border-white/50 dark:border-white/10 w-full py-2.5 rounded-xl bg-white/40 dark:bg-white/5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-white/60 dark:hover:bg-white/10 transition-colors"
                    >
                        Schedule a Meeting
                    </button>
                </div>
            </div>
        </div>
    );
}
