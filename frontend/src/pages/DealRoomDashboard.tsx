import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { Project } from '../types/pipeline';

function fmtMoney(n: number) {
    if (!n) return '—';
    if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
    if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
    return `$${n.toLocaleString()}`;
}

function LedgerStat({ label, value, sub, accent = false, last = false }: {
    label: string; value: string | number; sub: string; accent?: boolean; last?: boolean;
}) {
    return (
        <div style={{ paddingRight: 24, borderRight: last ? 'none' : '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>
                {label}
            </div>
            <div style={{
                fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 28,
                color: accent ? 'var(--accent)' : 'var(--ink-900)', letterSpacing: '-0.02em',
                marginTop: 4, lineHeight: 1, fontVariantNumeric: 'tabular-nums',
            }}>{value}</div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6 }}>{sub}</div>
        </div>
    );
}

type ViewMode = 'pipeline' | 'deal_room' | 'investors' | 'buyers';

interface DealRoomDashboardProps {
    viewMode?: ViewMode;
    onViewModeChange?: (v: ViewMode) => void;
    canAccessInvestorDB?: boolean;
}

const DealRoomDashboard: React.FC<DealRoomDashboardProps> = ({ viewMode = 'deal_room', onViewModeChange, canAccessInvestorDB }) => {
    const navigate = useNavigate();
    const [flagshipProjects, setFlagshipProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchFlagship = async () => {
            try {
                const allProjects = await pipelineService.listProjects();
                const flagged = allProjects.filter(p => p.is_flagship);
                setFlagshipProjects(flagged);
            } catch (e) {
                console.error('Failed to load flagship projects', e);
            } finally {
                setLoading(false);
            }
        };
        fetchFlagship();
    }, []);

    const totalFlagshipValue = flagshipProjects.reduce((s, p) => s + (Number(p.investment_size) || 0), 0);
    const avgReadiness = flagshipProjects.length
        ? flagshipProjects.reduce((s, p) => s + Number(p.afcen_score ?? p.readiness_score ?? 0), 0) / flagshipProjects.length
        : 0;

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>

            {/* ── Page header ─────────────────────────────────────── */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)' }}>
                        Deal room
                    </div>
                    <div style={{ width: 16, height: 1, background: 'var(--border)' }} />
                    <span style={{ fontSize: 10, color: 'var(--ink-400)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                        Curated · Updated {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} GMT
                    </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
                    <h1 style={{
                        fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                        fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)',
                        margin: 0, lineHeight: 1.1, maxWidth: 720,
                    }}>
                        Flagship opportunities, prepared for engagement.
                    </h1>
                    <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                        {onViewModeChange && (
                            <div style={{ display: 'flex', border: '1px solid var(--border)', overflow: 'hidden' }}>
                                {[
                                    { key: 'pipeline' as const, label: 'All projects' },
                                    { key: 'deal_room' as const, label: 'Deal room' },
                                    ...(canAccessInvestorDB ? [{ key: 'investors' as const, label: 'Investors' }] : []),
                                ].map(({ key, label }, idx, arr) => (
                                    <button key={key} onClick={() => onViewModeChange(key)} style={{
                                        padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer',
                                        background: viewMode === key ? 'var(--accent)' : 'transparent',
                                        border: 'none', color: viewMode === key ? 'var(--accent-ink)' : 'var(--ink-700)',
                                        fontFamily: 'inherit',
                                        borderRight: idx !== arr.length - 1 ? '1px solid var(--border)' : 'none',
                                    }}>{label}</button>
                                ))}
                            </div>
                        )}
                        <button onClick={() => navigate('/schedule')} style={{
                            display: 'inline-flex', alignItems: 'center', gap: 6,
                            background: 'var(--accent)', border: '1px solid var(--accent)',
                            color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500,
                            cursor: 'pointer', fontFamily: 'inherit',
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>event</span>
                            Schedule meeting
                        </button>
                    </div>
                </div>
            </div>

            {/* ── KPI strip ───────────────────────────────────────── */}
            <div
                className="kpi-strip"
                style={{
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    marginBottom: 24,
                }}
            >
                <LedgerStat label="Flagship opportunities" value={loading ? '—' : flagshipProjects.length} sub="curated by secretariat" accent />
                <LedgerStat label="Combined investment" value={loading ? '—' : fmtMoney(totalFlagshipValue)} sub="across flagship deals" />
                <LedgerStat label="Avg. AfCEN score" value={loading ? '—' : flagshipProjects.length ? avgReadiness.toFixed(1) : '—'} sub="featured projects" />
                <LedgerStat label="Upcoming meetings" value={5} sub="next 14 days" last />
            </div>

            {/* ── Featured projects ───────────────────────────────── */}
            <div style={{ marginBottom: 32 }}>
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    marginBottom: 14, paddingBottom: 12, borderBottom: '1px solid var(--border)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{
                            fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
                            fontWeight: 600, color: 'var(--accent)',
                        }}>★ Featured</span>
                        <span style={{ fontSize: 13, color: 'var(--ink-700)' }}>Flagship investment opportunities</span>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace" }}>
                        {loading ? '—' : `${flagshipProjects.length} project${flagshipProjects.length === 1 ? '' : 's'}`}
                    </span>
                </div>

                {loading ? (
                    <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
                        Loading flagship projects…
                    </div>
                ) : flagshipProjects.length === 0 ? (
                    <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
                        No flagship projects marked yet. Mark a project as flagship from Deal Pipeline to feature it here.
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 0, border: '1px solid var(--border)', background: 'var(--surface)' }}>
                        {flagshipProjects.map((project, i) => {
                            const score = Number(project.afcen_score ?? project.readiness_score ?? 0);
                            const isAIScored = project.afcen_score != null;
                            return (
                                <div
                                    key={project.id}
                                    onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(project.id)}`)}
                                    style={{
                                        padding: '20px 22px',
                                        borderRight: '1px solid var(--border)',
                                        borderBottom: '1px solid var(--border)',
                                        cursor: 'pointer',
                                        background: 'var(--surface)',
                                        transition: 'background 120ms',
                                    }}
                                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--ink-50)')}
                                    onMouseLeave={e => (e.currentTarget.style.background = 'var(--surface)')}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                                        <span style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600 }}>
                                            ★ Flagship · #{String(i + 1).padStart(2, '0')}
                                        </span>
                                        {isAIScored && (
                                            <span style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600, opacity: 0.7 }}>
                                                AI scored
                                            </span>
                                        )}
                                    </div>
                                    <h3 style={{
                                        fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                                        fontSize: 19, color: 'var(--ink-900)', letterSpacing: '-0.01em',
                                        margin: 0, lineHeight: 1.25,
                                    }}>{project.name}</h3>
                                    {project.description && (
                                        <p style={{
                                            fontSize: 13, color: 'var(--ink-500)', lineHeight: 1.5,
                                            margin: '8px 0 16px', display: '-webkit-box',
                                            WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                                            overflow: 'hidden',
                                        }}>{project.description}</p>
                                    )}
                                    <div style={{ display: 'flex', gap: 16, marginBottom: 14 }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 4 }}>
                                                Investment
                                            </div>
                                            <div style={{
                                                fontFamily: "'Geist Mono', monospace", fontSize: 14,
                                                color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums',
                                            }}>{fmtMoney(Number(project.investment_size))}</div>
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 4 }}>
                                                Lead country
                                            </div>
                                            <div style={{ fontSize: 13, color: 'var(--ink-900)' }}>{project.lead_country || 'Regional'}</div>
                                        </div>
                                    </div>
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <span style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>
                                                AfCEN score
                                            </span>
                                            <span style={{ fontSize: 12, fontFamily: "'Geist Mono', monospace", color: 'var(--ink-900)', fontWeight: 500 }}>
                                                {score.toFixed(0)} <span style={{ color: 'var(--ink-400)' }}>/ 100</span>
                                            </span>
                                        </div>
                                        <div style={{ height: 2, background: 'var(--ink-100)', position: 'relative' }}>
                                            <div style={{
                                                position: 'absolute', inset: 0, width: `${Math.min(100, score)}%`,
                                                background: score >= 75 ? 'var(--accent)' : score >= 60 ? 'var(--amber)' : 'var(--terra)',
                                            }} />
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* ── Upcoming schedule ───────────────────────────────── */}
            <div style={{ marginBottom: 32 }}>
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    marginBottom: 14, paddingBottom: 12, borderBottom: '1px solid var(--border)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, color: 'var(--ink-700)' }}>
                            Upcoming
                        </span>
                        <span style={{ fontSize: 13, color: 'var(--ink-700)' }}>Investor engagements</span>
                    </div>
                    <button onClick={() => navigate('/schedule')} style={{
                        background: 'transparent', border: 'none', cursor: 'pointer',
                        fontSize: 11, color: 'var(--accent)', fontFamily: 'inherit',
                        letterSpacing: '0.05em', textTransform: 'uppercase', fontWeight: 500,
                    }}>View calendar →</button>
                </div>

                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    {[
                        { mon: 'OCT', day: 15, title: 'Investment review · Grid expansion', time: '10:00 GMT · Zoom' },
                        { mon: 'OCT', day: 17, title: 'Diligence call · AgriTech corridor', time: '14:30 GMT · In person' },
                    ].map((m, i, arr) => (
                        <div key={i} style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '14px 22px',
                            borderBottom: i === arr.length - 1 ? 'none' : '1px solid var(--border)',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                <div style={{
                                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                                    border: '1px solid var(--border)', padding: '6px 10px', minWidth: 48,
                                }}>
                                    <span style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--ink-500)', fontWeight: 500 }}>{m.mon}</span>
                                    <span style={{
                                        fontFamily: "'Source Serif 4', serif", fontSize: 18,
                                        color: 'var(--ink-900)', lineHeight: 1, marginTop: 2,
                                        fontVariantNumeric: 'tabular-nums',
                                    }}>{m.day}</span>
                                </div>
                                <div>
                                    <div style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500 }}>{m.title}</div>
                                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>{m.time}</div>
                                </div>
                            </div>
                            <button style={{
                                background: 'transparent', border: '1px solid var(--border)',
                                color: 'var(--ink-700)', padding: '6px 14px', fontSize: 11, fontWeight: 500,
                                cursor: 'pointer', fontFamily: 'inherit',
                            }}>Join</button>
                        </div>
                    ))}
                </div>
            </div>

            <div style={{ height: 32 }} />
        </div>
    );
};

export default DealRoomDashboard;
