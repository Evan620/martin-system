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

function formatCountdown(dateString: string | null) {
    if (!dateString) return 'TBD';
    const diff = new Date(dateString).getTime() - Date.now();
    const days = Math.ceil(diff / 86_400_000);
    if (days < 0) return 'Past';
    if (days === 0) return 'Today';
    return `${days}`;
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

// ─── sub-components ───────────────────────────────────────────

function LedgerStat({
    label, value, sub, accent = false, last = false,
}: { label: string; value: string | number; sub: string; accent?: boolean; last?: boolean }) {
    return (
        <div style={{
            paddingRight: 24,
            borderRight: last ? 'none' : '1px solid var(--border)',
        }}>
            <div style={{
                fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase',
                color: 'var(--ink-500)', fontWeight: 500, fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
            }}>{label}</div>
            <div style={{
                fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                fontSize: 28, color: accent ? 'var(--accent)' : 'var(--ink-900)',
                letterSpacing: '-0.02em', marginTop: 4, lineHeight: 1,
                fontVariantNumeric: 'tabular-nums',
            }}>{value}</div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{sub}</div>
        </div>
    );
}

// ─── component ────────────────────────────────────────────────

export default function Dashboard() {
    const navigate = useNavigate();
    const { user } = useAppSelector((s) => s.auth);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [timeline, setTimeline] = useState<TimelineItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [hoveredTwgId, setHoveredTwgId] = useState<string | null>(null);

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
        .slice(0, 8);

    const atRiskCount =
        stats?.twg_health.filter((t) => t.status === 'stalled' || t.completion < 50).length ?? 0;

    const firstName = user?.full_name?.split(' ')[0] || 'there';

    const today = new Date().toLocaleDateString('en-GB', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });

    // Pipeline bar data from stats.pipeline
    const pipelineBuckets = stats ? [
        { label: 'Drafting',     n: stats.pipeline.drafting,     color: 'var(--ink-400)' },
        { label: 'Negotiation',  n: stats.pipeline.negotiation,  color: 'var(--accent)' },
        { label: 'Final review', n: stats.pipeline.final_review, color: 'var(--amber)' },
        { label: 'Signed',       n: stats.pipeline.signed,       color: 'var(--sage)' },
    ].filter(b => b.n > 0) : [];
    const pipelineTotal = pipelineBuckets.reduce((s, b) => s + b.n, 0) || 1;

    const summitReadyCount = stats?.twg_health.filter(t => t.completion >= 75).length ?? 0;

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                    <div className="size-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
                    <p style={{ fontSize: 12, color: 'var(--ink-500)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                        Loading dashboard…
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>

            {/* ── Greeting header ───────────────────────────────── */}
            <div style={{ marginBottom: 24 }}>
                <div style={{
                    fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase',
                    fontWeight: 500, color: 'var(--ink-500)', marginBottom: 6,
                }}>
                    Daily briefing · {today}
                </div>
                <h1 style={{
                    fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                    fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)',
                    margin: 0, lineHeight: 1.1,
                }}>
                    {getGreeting()}, {firstName}.
                </h1>
            </div>

            {/* ── Hero: Martin's Briefing ───────────────────────── */}
            <div style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                padding: '28px 36px 24px', marginBottom: 28,
            }}>
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    marginBottom: 16,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{
                            fontFamily: "'Source Serif 4', serif", fontStyle: 'italic',
                            fontSize: 13, color: 'var(--accent)',
                        }}>Martin</span>
                        <div style={{ width: 24, height: 1, background: 'var(--border)' }} />
                        <div style={{
                            fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase',
                            fontWeight: 500, color: 'var(--ink-500)',
                        }}>Today's briefing</div>
                    </div>
                    <span style={{
                        fontSize: 11, color: 'var(--ink-400)',
                        fontFamily: "'Geist Mono', monospace",
                    }}>
                        {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} GMT
                    </span>
                </div>

                <p style={{
                    fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                    fontSize: 20, lineHeight: 1.45, color: 'var(--ink-900)',
                    letterSpacing: '-0.01em', margin: '0 0 24px', maxWidth: 880,
                }}>
                    {generateBriefing(stats, todayItems.length, atRiskCount)}
                </p>

                {/* 4 KPI stats */}
                <div style={{
                    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                    borderTop: '1px solid var(--border)', paddingTop: 20,
                }}>
                    <LedgerStat
                        label="Deals in pipeline"
                        value={stats?.metrics.deals_in_pipeline ?? 0}
                        sub="active projects"
                    />
                    <LedgerStat
                        label="Summit-ready TWGs"
                        value={summitReadyCount}
                        sub={`of ${stats?.twg_health.length ?? 0}`}
                    />
                    <LedgerStat
                        label="Pending decisions"
                        value={stats?.metrics.pending_approvals ?? 0}
                        sub="needs your sign-off"
                        accent
                    />
                    <LedgerStat
                        label="Days to Summit"
                        value={formatCountdown(stats?.metrics.next_plenary.date ?? null)}
                        sub={stats?.metrics.next_plenary.date
                            ? new Date(stats.metrics.next_plenary.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                            : stats?.metrics.next_plenary.title ?? 'TBD'}
                        last
                    />
                </div>
            </div>

            {/* ── Two-column ────────────────────────────────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 32 }}>

                {/* Left: TWG Readiness + Pipeline */}
                <section>
                    {/* Section head */}
                    <div style={{
                        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
                        paddingBottom: 12,
                    }}>
                        <h2 style={{
                            fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                            fontSize: 18, letterSpacing: '-0.01em', color: 'var(--ink-900)', margin: 0,
                        }}>TWG readiness</h2>
                        <button
                            onClick={() => navigate('/twgs')}
                            style={{
                                fontSize: 11, color: 'var(--accent)', background: 'none',
                                border: 'none', cursor: 'pointer', letterSpacing: '0.02em', padding: 0,
                            }}
                        >
                            View all TWGs ↗
                        </button>
                    </div>

                    {/* TWG Readiness table */}
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                        {stats?.twg_health.length ? stats.twg_health.map((twg, i) => {
                            const atRisk = twg.status === 'stalled' || twg.completion < 50;
                            const last = i === (stats.twg_health.length - 1);
                            const isHovered = hoveredTwgId === twg.id;
                            return (
                                <div
                                    key={twg.id}
                                    onClick={() => navigate(`/workspace/${twg.id}`)}
                                    onMouseEnter={() => setHoveredTwgId(twg.id)}
                                    onMouseLeave={() => setHoveredTwgId(null)}
                                    style={{
                                        padding: '14px 24px',
                                        borderBottom: last ? 'none' : '1px solid var(--border)',
                                        display: 'grid',
                                        gridTemplateColumns: '1fr 180px 110px 28px',
                                        alignItems: 'center',
                                        gap: 20,
                                        cursor: 'pointer',
                                        background: isHovered ? 'var(--accent-soft)' : 'transparent',
                                        transition: 'background 0.15s ease',
                                    }}
                                >
                                    <div>
                                        <div style={{ fontSize: 14, color: isHovered ? 'var(--accent)' : 'var(--ink-900)', fontWeight: 500, transition: 'color 0.15s' }}>
                                            {twg.name}
                                        </div>
                                        <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>
                                            Lead · {twg.lead}
                                        </div>
                                    </div>
                                    <div>
                                        <div style={{
                                            display: 'flex', alignItems: 'center',
                                            justifyContent: 'space-between', marginBottom: 6,
                                        }}>
                                            <span style={{
                                                fontSize: 10, color: 'var(--ink-500)',
                                                letterSpacing: '0.08em', textTransform: 'uppercase',
                                            }}>Readiness</span>
                                            <span style={{
                                                fontSize: 12, fontFamily: "'Geist Mono', monospace",
                                                color: atRisk ? 'var(--terra)' : 'var(--ink-900)',
                                                fontWeight: 500,
                                            }}>{twg.completion}%</span>
                                        </div>
                                        <div style={{ height: 3, background: 'var(--ink-100)', position: 'relative' }}>
                                            <div style={{
                                                position: 'absolute', inset: 0,
                                                width: `${twg.completion}%`,
                                                background: atRisk ? 'var(--terra)' : 'var(--accent)',
                                                transition: 'width 0.6s ease',
                                            }} />
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span style={{
                                            width: 6, height: 6, borderRadius: 6,
                                            background: atRisk ? 'var(--terra)' : 'var(--sage)',
                                            display: 'inline-block', flexShrink: 0,
                                        }} />
                                        <span style={{ fontSize: 12, color: atRisk ? 'var(--terra)' : 'var(--ink-700)' }}>
                                            {twg.status === 'stalled' ? 'At risk' : 'On track'}
                                        </span>
                                    </div>
                                    <div style={{
                                        fontSize: 16,
                                        color: isHovered ? 'var(--accent)' : 'var(--ink-300)',
                                        transition: 'color 0.15s, transform 0.15s',
                                        transform: isHovered ? 'translateX(2px)' : 'translateX(0)',
                                        lineHeight: 1,
                                    }}>›</div>
                                </div>
                            );
                        }) : (
                            <div style={{ padding: '32px 24px', textAlign: 'center', color: 'var(--ink-400)', fontSize: 13 }}>
                                No TWG data available
                            </div>
                        )}
                    </div>

                    {/* Pipeline at a glance */}
                    <div style={{
                        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
                        padding: '28px 0 12px',
                    }}>
                        <h2 style={{
                            fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                            fontSize: 18, letterSpacing: '-0.01em', color: 'var(--ink-900)', margin: 0,
                        }}>Pipeline at a glance</h2>
                        <button
                            onClick={() => navigate('/pipeline')}
                            style={{
                                fontSize: 11, color: 'var(--accent)', background: 'none',
                                border: 'none', cursor: 'pointer', letterSpacing: '0.02em', padding: 0,
                            }}
                        >
                            Open Deal Pipeline ↗
                        </button>
                    </div>

                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '24px 28px' }}>
                        <div style={{
                            display: 'flex', alignItems: 'baseline',
                            justifyContent: 'space-between', marginBottom: 20,
                        }}>
                            <div>
                                <div style={{
                                    fontFamily: "'Source Serif 4', serif", fontSize: 28,
                                    color: 'var(--ink-900)', letterSpacing: '-0.02em',
                                    lineHeight: 1, fontVariantNumeric: 'tabular-nums',
                                }}>
                                    {stats?.metrics.deals_in_pipeline ?? 0} projects
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6 }}>
                                    Total across all stages · {summitReadyCount} summit-ready
                                </div>
                            </div>
                        </div>

                        {pipelineBuckets.length > 0 && (
                            <>
                                <div style={{
                                    height: 8, display: 'flex', overflow: 'hidden',
                                    border: '1px solid var(--border)',
                                    marginBottom: 16,
                                }}>
                                    {pipelineBuckets.map((b, i) => (
                                        <div key={b.label} style={{
                                            width: `${(b.n / pipelineTotal) * 100}%`,
                                            background: b.color,
                                            borderRight: i === pipelineBuckets.length - 1 ? 'none' : '1px solid var(--surface)',
                                        }} />
                                    ))}
                                </div>
                                <div style={{
                                    display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)',
                                    gap: '8px 24px',
                                }}>
                                    {pipelineBuckets.map(b => (
                                        <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <span style={{ width: 6, height: 6, borderRadius: 6, background: b.color, display: 'inline-block' }} />
                                            <span style={{ fontSize: 12, color: 'var(--ink-700)' }}>{b.label}</span>
                                            <span style={{
                                                marginLeft: 'auto', fontSize: 11,
                                                color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace",
                                            }}>{b.n}</span>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </section>

                {/* Right: Schedule */}
                <section>
                    <div style={{
                        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
                        paddingBottom: 12,
                    }}>
                        <h2 style={{
                            fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                            fontSize: 18, letterSpacing: '-0.01em', color: 'var(--ink-900)', margin: 0,
                        }}>Schedule</h2>
                        <span style={{
                            fontSize: 11, color: 'var(--ink-500)',
                            fontFamily: "'Geist Mono', monospace", letterSpacing: '0.04em',
                        }}>NEXT 14 DAYS</span>
                    </div>

                    <div style={{
                        background: 'var(--surface)', border: '1px solid var(--border)',
                        padding: '8px 0',
                    }}>
                        {upcomingItems.length > 0 ? upcomingItems.map((item, i) => {
                            const d = new Date(item.date);
                            const isToday = d.toDateString() === new Date().toDateString();
                            return (
                                <div key={i} style={{
                                    padding: '12px 24px',
                                    display: 'grid', gridTemplateColumns: '48px 1fr',
                                    gap: 16, alignItems: 'flex-start',
                                    borderBottom: i < upcomingItems.length - 1 ? '1px solid var(--border)' : 'none',
                                }}>
                                    <div style={{ textAlign: 'left', paddingTop: 2 }}>
                                        <div style={{
                                            fontFamily: "'Geist Mono', monospace", fontSize: 10,
                                            color: isToday ? 'var(--accent)' : 'var(--ink-500)',
                                            letterSpacing: '0.04em',
                                        }}>
                                            {d.toLocaleString('en-GB', { month: 'short' }).toUpperCase()}
                                        </div>
                                        <div style={{
                                            fontFamily: "'Source Serif 4', serif", fontSize: 22,
                                            color: isToday ? 'var(--accent)' : 'var(--ink-900)',
                                            lineHeight: 1, letterSpacing: '-0.02em',
                                        }}>{d.getDate()}</div>
                                        <div style={{
                                            fontFamily: "'Geist Mono', monospace", fontSize: 10,
                                            color: 'var(--ink-400)', marginTop: 3,
                                        }}>
                                            {d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    <div style={{ paddingTop: 2 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            {item.status === 'critical' && (
                                                <span style={{ width: 5, height: 5, borderRadius: 5, background: 'var(--terra)', display: 'inline-block' }} />
                                            )}
                                            <span style={{
                                                fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase',
                                                color: 'var(--ink-500)',
                                            }}>{item.twg}</span>
                                        </div>
                                        <div style={{ fontSize: 13, color: 'var(--ink-900)', marginTop: 4, lineHeight: 1.4 }}>
                                            {item.title}
                                        </div>
                                    </div>
                                </div>
                            );
                        }) : (
                            <div style={{ padding: '32px 24px', textAlign: 'center', color: 'var(--ink-400)', fontSize: 13 }}>
                                No upcoming events
                            </div>
                        )}

                        <div style={{
                            padding: '12px 24px 8px',
                            borderTop: '1px solid var(--border)',
                            marginTop: 4,
                        }}>
                            <button
                                onClick={() => navigate('/schedule')}
                                style={{
                                    width: '100%', padding: '8px 10px', justifyContent: 'center',
                                    display: 'flex', alignItems: 'center',
                                    background: 'transparent', border: '1px solid var(--border)',
                                    color: 'var(--ink-700)', fontSize: 12, fontWeight: 500,
                                    cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                                    borderRadius: 4,
                                }}
                            >
                                + Schedule a meeting
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
