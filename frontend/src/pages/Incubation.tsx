import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import api from '../services/api';
import { Project, ProjectStatus, IncubationChecklist } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { UserRole } from '../types/auth';

const INCUBATION_TTL_DAYS = 90;

function fmtMoney(n: number) {
    if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
    if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
    if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
    return `$${n.toLocaleString()}`;
}

function daysSince(iso?: string | null): number | null {
    if (!iso) return null;
    const ms = Date.now() - new Date(iso).getTime();
    if (isNaN(ms)) return null;
    return Math.floor(ms / (24 * 60 * 60 * 1000));
}

const Incubation: React.FC = () => {
    const navigate = useNavigate();
    const user = useAppSelector(s => s.auth.user);

    const allowed = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR].includes(user.role as any);

    const [projects, setProjects] = useState<Project[]>([]);
    const [checklists, setChecklists] = useState<Record<string, IncubationChecklist>>({});
    const [threshold, setThreshold] = useState<number>(40);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Role-gate redirect
    useEffect(() => {
        if (user && !allowed) {
            // small delay so any layout is mounted; immediate navigate is fine too
            navigate('/dashboard', { replace: true });
        }
    }, [user, allowed, navigate]);

    useEffect(() => {
        if (!allowed) return;
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                const [list, settings] = await Promise.all([
                    pipelineService.listProjects(ProjectStatus.INCUBATION),
                    api.get('/pipeline/settings').then(r => r.data).catch(() => null),
                ]);
                if (cancelled) return;
                setProjects(list);
                if (settings?.incubation_graduation_threshold) {
                    const t = Number(settings.incubation_graduation_threshold);
                    if (!isNaN(t) && t > 0) setThreshold(t);
                }
                // Fetch checklists in parallel with a modest concurrency cap.
                const cap = 6;
                const out: Record<string, IncubationChecklist> = {};
                for (let i = 0; i < list.length; i += cap) {
                    const slice = list.slice(i, i + cap);
                    const results = await Promise.allSettled(
                        slice.map(p => pipelineService.getIncubationChecklist(p.id))
                    );
                    results.forEach((r, idx) => {
                        if (r.status === 'fulfilled') out[slice[idx].id] = r.value;
                    });
                }
                if (!cancelled) setChecklists(out);
            } catch (e: any) {
                if (!cancelled) setError(e?.response?.data?.detail ?? 'Failed to load incubation projects.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [allowed]);

    const handleDownloadTemplate = async () => {
        try {
            const blob = await pipelineService.downloadFinancialModelTemplate();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'waiis_financial_model_template.xlsx';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('template download failed', e);
        }
    };

    const sorted = useMemo(
        () => [...projects].sort((a, b) => {
            const da = daysSince((a as any).created_at ?? (a as any).updated_at);
            const db = daysSince((b as any).created_at ?? (b as any).updated_at);
            return (db ?? 0) - (da ?? 0);
        }),
        [projects],
    );

    if (!allowed) {
        return (
            <div style={{ padding: 32, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                Not authorised. Redirecting…
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", padding: '24px 0' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: 16, marginBottom: 24 }}>
                <div>
                    <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#7c3aed', fontWeight: 600 }}>R5 · Pre-pipeline</div>
                    <h1 style={{ fontFamily: "'Source Serif 4', serif", fontSize: 28, fontWeight: 400, color: 'var(--ink-900)', margin: '4px 0 0', letterSpacing: '-0.01em' }}>
                        ⚗ Incubation Track
                    </h1>
                    <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: '6px 0 0', maxWidth: 640 }}>
                        Projects being shaped into investment-ready proposals. 90-day window; graduates to DRAFT once AfCEN ≥ {threshold}.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                    <button
                        onClick={handleDownloadTemplate}
                        style={{
                            display: 'inline-flex', alignItems: 'center', gap: 6,
                            background: 'transparent', border: '1px solid var(--border)',
                            color: 'var(--ink-700)', padding: '8px 14px', fontSize: 12,
                            cursor: 'pointer', fontFamily: 'inherit',
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>download</span>
                        Financial model template
                    </button>
                    <button
                        onClick={() => navigate('/deal-pipeline/new')}
                        style={{
                            background: '#7c3aed', color: '#fff', border: 'none',
                            padding: '8px 14px', fontSize: 12, fontWeight: 500,
                            cursor: 'pointer', fontFamily: 'inherit',
                        }}
                    >
                        + New project
                    </button>
                </div>
            </div>

            {/* Count summary */}
            <div style={{ display: 'flex', gap: 24, marginBottom: 24, padding: '16px 0', borderBottom: '1px solid var(--border)' }}>
                <Stat label="In incubation" value={sorted.length.toString()} sub="active projects" />
                <Stat
                    label="Avg checklist"
                    value={sorted.length === 0 ? '—' : `${Math.round(
                        sorted.reduce((s, p) => s + (checklists[p.id]?.completed_count ?? 0), 0) / Math.max(sorted.length, 1)
                    )} / 6`}
                    sub="documents per project"
                />
                <Stat
                    label="At risk"
                    value={sorted.filter(p => {
                        const d = daysSince((p as any).created_at ?? (p as any).updated_at);
                        return d != null && (INCUBATION_TTL_DAYS - d) <= 30;
                    }).length.toString()}
                    sub="< 30 days left"
                />
            </div>

            {error && (
                <div style={{ padding: 16, border: '1px solid var(--terra)', color: 'var(--terra)', fontSize: 13, marginBottom: 16 }}>
                    {error}
                </div>
            )}

            {loading ? (
                <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>
                    Loading incubation projects…
                </div>
            ) : sorted.length === 0 ? (
                <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)', border: '1px dashed var(--border)' }}>
                    No projects currently in incubation.
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 16 }}>
                    {sorted.map(p => (
                        <ProjectCard
                            key={p.id}
                            project={p}
                            checklist={checklists[p.id]}
                            threshold={threshold}
                            onOpen={() => navigate(`/deal-pipeline/${encodeURIComponent(p.id)}`)}
                            onOpenReadiness={() => navigate(`/deal-pipeline/${encodeURIComponent(p.id)}#readiness`)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
    return (
        <div style={{ paddingRight: 24, borderRight: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{label}</div>
            <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 22, color: '#7c3aed', marginTop: 4, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 4 }}>{sub}</div>
        </div>
    );
}

function ProjectCard({
    project, checklist, threshold, onOpen, onOpenReadiness,
}: {
    project: Project;
    checklist?: IncubationChecklist;
    threshold: number;
    onOpen: () => void;
    onOpenReadiness: () => void;
}) {
    const days = daysSince((project as any).created_at ?? project.updated_at);
    const remaining = days == null ? null : INCUBATION_TTL_DAYS - days;
    const score = Number(project.afcen_score ?? 0);
    const delta = Math.max(0, threshold - score);
    const completed = checklist?.completed_count ?? 0;
    const total = checklist?.total_count ?? 6;

    // Theme-aware countdown badge — translucent rgba tints work on dark + light surfaces.
    let countdownColor = 'var(--ink-500)';
    let countdownBg = 'rgba(255, 255, 255, 0.04)';
    if (remaining != null) {
        if (remaining <= 7) {
            // Red — imminent expiry. Use bright red on translucent red tint.
            countdownColor = '#f87171';
            countdownBg = 'rgba(239, 68, 68, 0.12)';
        } else if (remaining <= 30) {
            // Amber — approaching expiry.
            countdownColor = '#fbbf24';
            countdownBg = 'rgba(245, 158, 11, 0.12)';
        }
    }

    return (
        <div
            onClick={onOpen}
            style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                padding: 20, cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 14,
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#7c3aed')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 10, color: '#7c3aed', fontWeight: 600, letterSpacing: '0.06em' }}>⚗ INCUBATION</div>
                    <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 17, color: 'var(--ink-900)', marginTop: 2, letterSpacing: '-0.005em' }}>
                        {project.name}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
                        {project.lead_country ?? '—'} · {fmtMoney(Number(project.investment_size ?? 0))}
                    </div>
                </div>
                {remaining != null && (
                    <div style={{
                        fontSize: 10, padding: '4px 8px', fontWeight: 600, alignSelf: 'flex-start',
                        background: countdownBg, color: countdownColor, letterSpacing: '0.04em',
                        fontFamily: "'Geist Mono', monospace",
                        whiteSpace: 'nowrap',
                    }}>
                        {remaining > 0 ? `${remaining}d LEFT` : 'OVERDUE'}
                    </div>
                )}
            </div>

            {/* Checklist progress */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: 'var(--ink-600)', fontWeight: 500 }}>Document checklist</span>
                    <span style={{ fontSize: 11, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace" }}>
                        {completed} / {total}
                    </span>
                </div>
                <div style={{ display: 'flex', gap: 4 }}>
                    {Array.from({ length: total }).map((_, i) => (
                        <div key={i} style={{ flex: 1, height: 4, background: i < completed ? '#7c3aed' : 'var(--ink-100)' }} />
                    ))}
                </div>
            </div>

            {/* AfCEN delta */}
            <div style={{
                display: 'flex', alignItems: 'baseline', gap: 12,
                padding: '10px 12px', background: 'var(--ink-50)',
            }}>
                <div>
                    <div style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)' }}>AfCEN</div>
                    <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 22, color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums' }}>
                        {score.toFixed(0)}
                    </div>
                </div>
                <div style={{ flex: 1, fontSize: 11, color: 'var(--ink-600)' }}>
                    {delta > 0 ? `Need +${delta.toFixed(0)} to graduate (threshold ${threshold})` : `Above graduation threshold (${threshold})`}
                </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                    onClick={e => { e.stopPropagation(); onOpenReadiness(); }}
                    style={{
                        background: 'none', border: 'none',
                        color: '#7c3aed', fontSize: 12, fontWeight: 500,
                        cursor: 'pointer', fontFamily: 'inherit', padding: 0,
                    }}
                >
                    View readiness gap report →
                </button>
            </div>
        </div>
    );
};

export default Incubation;
