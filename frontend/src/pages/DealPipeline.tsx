import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import api from '../services/api';
import { Project, PipelineStats, ProjectStatus } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { UserRole } from '../types/auth';
import DealRoomDashboard from './DealRoomDashboard';
import InvestorDatabase from './InvestorDatabase';

// ─── status helpers ───────────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  INCUBATION: '⚗ Incubation',
  DRAFT: 'Draft', PIPELINE: 'Pipeline', UNDER_REVIEW: 'Under review',
  SUMMIT_READY: 'Summit ready', DEAL_ROOM_FEATURED: 'Deal room',
  IN_NEGOTIATION: 'In negotiation', COMMITTED: 'Committed',
  IMPLEMENTED: 'Implemented', DECLINED: 'Declined',
  NEEDS_REVISION: 'Needs revision', ON_HOLD: 'On hold',
};

const STATUS_DOT: Record<string, string> = {
  INCUBATION: '#7c3aed',
  UNDER_REVIEW: 'var(--amber)', PIPELINE: 'var(--ink-400)',
  DEAL_ROOM_FEATURED: 'var(--accent)', IN_NEGOTIATION: 'var(--navy)',
  SUMMIT_READY: 'var(--sage)', COMMITTED: 'var(--sage)',
  IMPLEMENTED: 'var(--sage)', NEEDS_REVISION: 'var(--terra)',
  DECLINED: 'var(--terra)', ON_HOLD: 'var(--ink-400)', DRAFT: 'var(--ink-400)',
};

function fmtMoney(n: number) {
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

// ─── sub-components ───────────────────────────────────────────

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

// ─── main component ───────────────────────────────────────────

const DealPipeline: React.FC = () => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'pipeline' | 'deal_room' | 'investors'>('pipeline');
  const [activeTab, setActiveTab] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showAIInsight, setShowAIInsight] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importToast, setImportToast] = useState<string | null>(null);
  const [showWeightsModal, setShowWeightsModal] = useState(false);
  const [criteria, setCriteria] = useState<any[]>([]);
  const [weightEdits, setWeightEdits] = useState<Record<string, string>>({});
  const [weightsSaving, setWeightsSaving] = useState(false);
  const [weightsToast, setWeightsToast] = useState<string | null>(null);
  const [valueChainFilter, setValueChainFilter] = useState('');
  const [genderYouthFilter, setGenderYouthFilter] = useState<'all' | 'gender' | 'youth' | 'both'>('all');
  const [showIncubation, setShowIncubation] = useState(true);
  const [threshold, setThreshold] = useState<number>(40);

  const { user } = useAppSelector((state) => state.auth);
  const canEdit = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR].includes(user.role);
  const canAccessInvestorDB = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD].includes(user.role);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [projectsData, statsData] = await Promise.all([
          pipelineService.listProjects(
            statusFilter !== '' ? (statusFilter as ProjectStatus) : undefined,
            activeTab !== 'all' ? activeTab : undefined,
            valueChainFilter || undefined
          ),
          pipelineService.getStats()
        ]);
        setProjects(projectsData);
        setStats(statsData);
      } catch (err) {
        console.error('Failed to fetch pipeline data', err);
        setError('Unable to load pipeline data. Please check your connection and try again.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [activeTab, statusFilter, valueChainFilter]);

  useEffect(() => {
    api.get('/pipeline/settings').then((r: any) => {
      const t = Number(r.data?.incubation_graduation_threshold);
      if (!isNaN(t) && t > 0) setThreshold(t);
    }).catch(() => {});
  }, []);

  const totalPipelineValue = projects.reduce((sum, p) => sum + (Number(p.investment_size) || 0), 0);
  const pendingAIReview = projects.filter(p => p.afcen_score == null).length;

  const handleExport = () => {
    const headers = ['ID', 'Name', 'Pillar', 'Lead Country', 'Investment', 'Readiness Score', 'Status'];
    const csvContent = [
      headers.join(','),
      ...projects.map(p =>
        [p.id, p.name, p.pillar, p.lead_country, p.investment_size, p.afcen_score ?? p.readiness_score, p.status].join(',')
      )
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deal-pipeline-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const handleImportExcel = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx';
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const twgId = (user as any)?.twg_ids?.[0] ?? (user as any)?.assigned_twg_id ?? '';
      try {
        const result = await pipelineService.importFromExcel(file, twgId);
        const count = result?.imported ?? result?.count ?? result?.projects?.length ?? '?';
        setImportToast(`Imported ${count} projects successfully`);
        setTimeout(() => setImportToast(null), 5000);
        const refreshed = await pipelineService.listProjects();
        setProjects(refreshed);
      } catch (err: any) {
        const msg = err?.response?.data?.detail ?? err?.message ?? 'Import failed';
        setImportToast(`Error: ${msg}`);
        setTimeout(() => setImportToast(null), 5000);
      }
    };
    input.click();
  };

  const handleOpenWeights = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const data = await pipelineService.getScoringCriteria();
      setCriteria(data);
      const edits: Record<string, string> = {};
      data.forEach((c: any) => { edits[c.id] = String(c.weight); });
      setWeightEdits(edits);
      setShowWeightsModal(true);
    } catch (err: any) {
      setWeightsToast(`Error loading criteria: ${err?.response?.data?.detail ?? err?.message}`);
      setTimeout(() => setWeightsToast(null), 5000);
    }
  };

  const handleSaveWeights = async () => {
    setWeightsSaving(true);
    try {
      await Promise.all(
        criteria.map((c: any) =>
          pipelineService.updateCriterionWeight(c.id, parseFloat(weightEdits[c.id] ?? c.weight))
        )
      );
      // Save graduation threshold alongside weights
      await api.patch('/pipeline/settings', { incubation_graduation_threshold: threshold });
      setShowWeightsModal(false);
      setWeightsToast('Weights saved. Rescore projects to apply.');
      setTimeout(() => setWeightsToast(null), 5000);
    } catch (e: any) {
      setWeightsToast(`Error: ${e?.response?.data?.detail ?? e?.message}`);
      setTimeout(() => setWeightsToast(null), 5000);
    } finally {
      setWeightsSaving(false);
    }
  };

  const totalWeight = criteria.reduce((s, c) => s + parseFloat(weightEdits[c.id] ?? c.weight), 0);

  const itemsPerPage = 10;
  const filteredProjects = projects.filter(p => {
    if (!showIncubation && p.status === ProjectStatus.INCUBATION) return false;
    if (genderYouthFilter === 'gender') return p.gender_intentional === true;
    if (genderYouthFilter === 'youth') return p.youth_focused === true;
    if (genderYouthFilter === 'both') return p.gender_intentional === true && p.youth_focused === true;
    return true;
  });
  const totalPages = Math.ceil(filteredProjects.length / itemsPerPage);
  const paginatedProjects = filteredProjects.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const vm = viewMode as string;
  if (vm === 'deal_room') return <DealRoomDashboard />;
  if (vm === 'investors' && canAccessInvestorDB) return <InvestorDatabase />;

  const toastStyle = (isError: boolean): React.CSSProperties => ({
    position: 'fixed', bottom: 24, right: 24, zIndex: 50,
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '12px 16px', fontSize: 13, fontWeight: 500,
    background: isError ? '#dc2626' : '#16a34a', color: '#fff',
    borderRadius: 6, boxShadow: '0 4px 20px rgba(0,0,0,.2)',
    fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
  });

  const PILLAR_TABS = [
    { key: 'all', label: 'All projects' },
    { key: 'infrastructure', label: 'Infrastructure' },
    { key: 'energy', label: 'Energy' },
    { key: 'agriculture', label: 'Agriculture' },
  ];

  return (
    <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>

      {/* Toasts */}
      {importToast && (
        <div style={toastStyle(importToast.startsWith('Error'))}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
            {importToast.startsWith('Error') ? 'error' : 'check_circle'}
          </span>
          {importToast}
          <button onClick={() => setImportToast(null)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', marginLeft: 8, opacity: 0.7 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>close</span>
          </button>
        </div>
      )}
      {weightsToast && (
        <div style={toastStyle(weightsToast.startsWith('Error'))}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
            {weightsToast.startsWith('Error') ? 'error' : 'check_circle'}
          </span>
          {weightsToast}
          <button onClick={() => setWeightsToast(null)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', marginLeft: 8, opacity: 0.7 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>close</span>
          </button>
        </div>
      )}

      {/* Weights Modal */}
      {showWeightsModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 50,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.5)',
        }}>
          <div style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            width: '100%', maxWidth: 520, margin: 16, overflow: 'hidden',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '20px 24px', borderBottom: '1px solid var(--border)',
            }}>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink-900)', margin: 0 }}>WAIIS Scoring Weights</h3>
                <p style={{ fontSize: 11, color: 'var(--ink-500)', margin: '4px 0 0' }}>
                  Adjust how each criterion contributes to the AfCEN score.
                </p>
              </div>
              <button onClick={() => setShowWeightsModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div style={{ padding: '16px 24px', maxHeight: '60vh', overflowY: 'auto' }}>
              {criteria.map((c: any) => {
                const w = parseFloat(weightEdits[c.id] ?? c.weight);
                const pct = totalWeight > 0 ? ((w / totalWeight) * 100).toFixed(1) : '0';
                return (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-900)' }}>{c.criterion_name}</div>
                      <div style={{ fontSize: 11, color: 'var(--ink-500)', margin: '2px 0 6px' }}>{pct}% of AfCEN score</div>
                      <div style={{ height: 2, background: 'var(--ink-100)', position: 'relative' }}>
                        <div style={{ position: 'absolute', inset: 0, width: `${pct}%`, background: 'var(--accent)' }} />
                      </div>
                    </div>
                    <input
                      type="number" min="0" max="9.99" step="0.1"
                      value={weightEdits[c.id] ?? c.weight}
                      onChange={e => setWeightEdits(prev => ({ ...prev, [c.id]: e.target.value }))}
                      style={{
                        width: 72, textAlign: 'center',
                        border: '1px solid var(--border)', padding: '6px 8px',
                        fontSize: 13, fontWeight: 600, color: 'var(--ink-900)',
                        background: 'var(--surface)', outline: 'none',
                        fontFamily: "'Geist Mono', monospace",
                      }}
                    />
                  </div>
                );
              })}
            </div>
            {/* Graduation threshold */}
            <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border)', background: '#faf5ff' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#7c3aed', marginBottom: 4 }}>⚗ Incubation Graduation Threshold</div>
              <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 8 }}>Minimum AfCEN score (0–100) required to graduate a project from Incubation to Draft.</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input
                  type="number" min={0} max={100}
                  value={threshold}
                  onChange={e => setThreshold(Number(e.target.value))}
                  style={{ width: 72, padding: '6px 8px', border: '1px solid #e9d5ff', fontSize: 13, fontWeight: 700, color: '#7c3aed', background: 'white', outline: 'none', textAlign: 'center', fontFamily: "'Geist Mono', monospace" }}
                />
                <span style={{ fontSize: 11, color: '#6b7280' }}>/ 100</span>
              </div>
            </div>
            <div style={{
              padding: '16px 24px', borderTop: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 11, color: 'var(--ink-500)' }}>
                Total weight: <strong style={{ color: 'var(--ink-900)' }}>{totalWeight.toFixed(2)}</strong>
              </span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => setShowWeightsModal(false)} style={{
                  padding: '8px 16px', fontSize: 12, fontWeight: 500, cursor: 'pointer',
                  background: 'transparent', border: '1px solid var(--border)',
                  color: 'var(--ink-700)', fontFamily: 'inherit',
                }}>
                  Cancel
                </button>
                <button onClick={handleSaveWeights} disabled={weightsSaving} style={{
                  padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: weightsSaving ? 'default' : 'pointer',
                  background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                  fontFamily: 'inherit', opacity: weightsSaving ? 0.6 : 1,
                }}>
                  {weightsSaving ? 'Saving…' : 'Save weights'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Page header ─────────────────────────────────────── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)' }}>
            Deal pipeline
          </div>
          <div style={{ width: 16, height: 1, background: 'var(--border)' }} />
          <span style={{ fontSize: 10, color: 'var(--ink-400)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            Q2 2026 · Updated {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} GMT
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
          <h1 style={{
            fontFamily: "'Source Serif 4', serif", fontWeight: 400,
            fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)',
            margin: 0, lineHeight: 1.1, maxWidth: 720,
          }}>
            Regional investment opportunities, ranked and tracked.
          </h1>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            {/* View mode switcher */}
            <div style={{ display: 'flex', border: '1px solid var(--border)', overflow: 'hidden' }}>
              {[
                { key: 'pipeline', label: 'All projects' },
                { key: 'deal_room', label: 'Deal room' },
                ...(canAccessInvestorDB ? [{ key: 'investors', label: 'Investors' }] : []),
              ].map(({ key, label }) => (
                <button key={key} onClick={() => setViewMode(key as any)} style={{
                  padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer',
                  background: viewMode === key ? 'var(--accent)' : 'transparent',
                  border: 'none', color: viewMode === key ? 'var(--accent-ink)' : 'var(--ink-700)',
                  fontFamily: 'inherit', borderRight: key !== 'investors' ? '1px solid var(--border)' : 'none',
                }}>{label}</button>
              ))}
            </div>
            <button onClick={handleExport} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'transparent', border: '1px solid var(--border)',
              color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500,
              cursor: 'pointer', fontFamily: 'inherit',
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>download</span>
              Export
            </button>
            {canEdit && (
              <button onClick={handleImportExcel} style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: 'transparent', border: '1px solid var(--border)',
                color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>upload_file</span>
                Import
              </button>
            )}
            {canEdit && (
              <button
                onClick={() => navigate('/deal-pipeline/incubation')}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  background: 'transparent', border: '1px solid #7c3aed',
                  color: '#7c3aed', padding: '7px 14px', fontSize: 12, fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit',
                }}
                title="Open the Incubation Track workspace — pre-pipeline projects"
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>science</span>
                Incubation Track
              </button>
            )}
            {canEdit && (
              <button onClick={() => navigate('/deal-pipeline/new')} style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: 'var(--accent)', border: '1px solid var(--accent)',
                color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
                New project
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── KPI strip ───────────────────────────────────────── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        background: 'var(--surface)', border: '1px solid var(--border)',
        padding: '22px 32px', marginBottom: 24,
      }}>
        <LedgerStat label="Total pipeline value" value={loading ? '—' : fmtMoney(totalPipelineValue)} sub={`across ${stats?.total_projects ?? projects.length} projects`} />
        <LedgerStat label="High readiness" value={loading ? '—' : (stats?.healthy_projects ?? 0)} sub="score ≥ 75" />
        <LedgerStat label="Pending AI review" value={loading ? '—' : pendingAIReview} sub="awaiting agent analysis" accent />
        <LedgerStat label="Avg. AfCEN score" value={
          loading ? '—' : projects.length > 0
            ? `${(projects.filter(p => p.afcen_score != null).reduce((s, p) => s + Number(p.afcen_score), 0) / Math.max(projects.filter(p => p.afcen_score != null).length, 1)).toFixed(1)}`
            : '—'
        } sub="scored projects" last />
      </div>

      {/* ── Martin notes strip ──────────────────────────────── */}
      {showAIInsight && (
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderLeft: '2px solid var(--accent)',
          padding: '16px 24px', marginBottom: 20,
          display: 'flex', alignItems: 'flex-start', gap: 16,
        }}>
          <span style={{
            fontFamily: "'Source Serif 4', serif", fontStyle: 'italic',
            fontSize: 13, color: 'var(--accent)', paddingTop: 2, flexShrink: 0,
          }}>Martin notes</span>
          <p style={{
            margin: 0, fontFamily: "'Source Serif 4', serif", fontSize: 15,
            color: 'var(--ink-700)', lineHeight: 1.5, flex: 1,
          }}>
            {pendingAIReview > 0
              ? `${pendingAIReview} project${pendingAIReview > 1 ? 's' : ''} ${pendingAIReview > 1 ? 'are' : 'is'} awaiting AfCEN algorithm scoring. Completing financial data submissions could significantly improve overall readiness.`
              : 'All projects have been scored by the AfCEN algorithm. Review individual projects for detailed investment insights.'}
          </p>
          <button onClick={() => setShowAIInsight(false)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--ink-400)', padding: 0, flexShrink: 0,
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>close</span>
          </button>
        </div>
      )}

      {/* ── Filters bar ─────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
        paddingBottom: 14, borderBottom: '1px solid var(--border)',
      }}>
        {/* Pillar tabs */}
        <div style={{ display: 'flex', gap: 0 }}>
          {PILLAR_TABS.map(({ key, label }) => {
            const on = activeTab === key;
            return (
              <button key={key} onClick={() => { setActiveTab(key); setCurrentPage(1); }} style={{
                background: 'transparent', border: 'none', cursor: 'pointer',
                padding: '6px 12px', fontSize: 12, fontWeight: on ? 500 : 400,
                color: on ? 'var(--ink-900)' : 'var(--ink-500)',
                borderBottom: on ? '2px solid var(--accent)' : '2px solid transparent',
                fontFamily: 'inherit', marginBottom: -15,
              }}>{label}</button>
            );
          })}
        </div>
        <div style={{ flex: 1 }} />
        {/* Value chain filter */}
        <select
          value={valueChainFilter}
          onChange={(e) => { setValueChainFilter(e.target.value); setCurrentPage(1); }}
          style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            color: 'var(--ink-700)', padding: '6px 10px', fontSize: 12,
            fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
          }}
        >
          <option value="">All value chains</option>
          <option value="INPUTS">Inputs</option>
          <option value="PRODUCTION">Production</option>
          <option value="PROCESSING">Processing</option>
          <option value="LOGISTICS">Logistics</option>
          <option value="RETAIL">Retail / Market</option>
        </select>
        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
          style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            color: 'var(--ink-700)', padding: '6px 10px', fontSize: 12,
            fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
          }}
        >
          <option value="">Any status</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        {/* Incubation visibility filter */}
        <select
          value={showIncubation ? 'show' : 'hide'}
          onChange={e => { setShowIncubation(e.target.value === 'show'); setCurrentPage(1); }}
          style={{
            background: 'var(--surface)',
            border: `1px solid ${showIncubation ? '#7c3aed' : 'var(--border)'}`,
            color: 'var(--ink-700)',
            padding: '6px 10px', fontSize: 12,
            fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
            fontWeight: 400,
          }}
        >
          <option value="show">⚗ Show Incubation</option>
          <option value="hide">Hide Incubation</option>
        </select>
        {/* Gender & Youth filter */}
        <select
          value={genderYouthFilter}
          onChange={e => { setGenderYouthFilter(e.target.value as typeof genderYouthFilter); setCurrentPage(1); }}
          style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            color: 'var(--ink-700)', padding: '6px 10px', fontSize: 12,
            fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
          }}
        >
          <option value="all">All Projects</option>
          <option value="gender">Gender-Intentional</option>
          <option value="youth">Youth-Focused</option>
          <option value="both">Gender &amp; Youth</option>
        </select>
        {canAccessInvestorDB && (
          <button onClick={handleOpenWeights} style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            background: 'transparent', border: '1px solid var(--border)',
            color: 'var(--ink-600)', padding: '6px 8px', fontSize: 12,
            cursor: 'pointer', fontFamily: 'inherit',
          }} title="Configure WAIIS scoring weights">
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>tune</span>
          </button>
        )}
      </div>

      {/* ── Table ───────────────────────────────────────────── */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        {/* Column headers */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2.4fr) 0.8fr 1.2fr 0.9fr 1.1fr 0.9fr',
          padding: '12px 24px', borderBottom: '1px solid var(--border)',
          background: 'var(--ink-50)',
        }}>
          {['Project', 'Pillar', 'Lead / Co.', 'Investment', 'AfCEN score', 'Status'].map(h => (
            <div key={h} style={{
              fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase',
              color: 'var(--ink-500)', fontWeight: 500,
            }}>{h}</div>
          ))}
        </div>

        {error ? (
          <div style={{ padding: '48px 24px', textAlign: 'center' }}>
            <div style={{ fontSize: 13, color: 'var(--terra)', marginBottom: 12 }}>{error}</div>
            <button onClick={() => window.location.reload()} style={{
              background: 'var(--accent)', color: 'var(--accent-ink)', border: 'none',
              padding: '8px 18px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
            }}>Retry</button>
          </div>
        ) : loading ? (
          <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>
            Loading projects…
          </div>
        ) : paginatedProjects.length === 0 ? (
          <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)' }}>
            No projects found.
          </div>
        ) : paginatedProjects.map((project, i) => {
          const score = Number(project.afcen_score ?? project.readiness_score ?? 0);
          const isAIScored = project.afcen_score != null;
          const last = i === paginatedProjects.length - 1;
          const statusColor = STATUS_DOT[project.status] ?? 'var(--ink-400)';
          const isIncubation = project.status === ProjectStatus.INCUBATION;

          return (
            <div
              key={project.id}
              onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(project.id)}`)}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 2.4fr) 0.8fr 1.2fr 0.9fr 1.1fr 0.9fr',
                padding: '16px 24px',
                borderBottom: last ? 'none' : `1px solid ${isIncubation ? '#f3e8ff' : 'var(--border)'}`,
                background: isIncubation ? '#faf5ff' : 'var(--surface)',
                alignItems: 'center',
                cursor: 'pointer',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--ink-50)')}
              onMouseLeave={e => (e.currentTarget.style.background = isIncubation ? '#faf5ff' : 'transparent')}
            >
              {/* Project */}
              <div style={{ minWidth: 0, paddingRight: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  {(project as any).flagship && (
                    <span style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600 }}>
                      ★ Flagship
                    </span>
                  )}
                  {isIncubation ? (
                    <div style={{ fontSize: 9, color: '#7c3aed', fontWeight: 700, marginBottom: 2, letterSpacing: '0.05em' }}>⚗ INCUBATION</div>
                  ) : (
                    <span style={{ fontSize: 10, color: 'var(--ink-400)', fontFamily: "'Geist Mono', monospace" }}>
                      #{project.id.slice(0, 8)}
                    </span>
                  )}
                  {isAIScored && (
                    <span style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600, opacity: 0.7 }}>
                      AI scored
                    </span>
                  )}
                </div>
                <div style={{
                  fontSize: 14, color: 'var(--ink-900)', fontWeight: 500,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{project.name}</div>
                {project.value_chain_stages && project.value_chain_stages.length > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>
                    {project.value_chain_stages.map(s => s.charAt(0) + s.slice(1).toLowerCase()).join(' · ')}
                  </div>
                )}
                {/* Gender & Youth intentional design badges */}
                {(project.gender_intentional || project.youth_focused) && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {project.gender_intentional && (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 2,
                        padding: '1px 6px', borderRadius: 4, fontSize: 9,
                        fontWeight: 600, letterSpacing: '0.06em',
                        background: 'var(--green-50, #f0fdf4)', color: 'var(--green-700, #15803d)',
                        border: '1px solid var(--green-200, #bbf7d0)',
                      }}>
                        &#9792; Gender &#10003;
                      </span>
                    )}
                    {project.youth_focused && (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 2,
                        padding: '1px 6px', borderRadius: 4, fontSize: 9,
                        fontWeight: 600, letterSpacing: '0.06em',
                        background: 'var(--blue-50, #eff6ff)', color: 'var(--blue-700, #1d4ed8)',
                        border: '1px solid var(--blue-200, #bfdbfe)',
                      }}>
                        &#9675; Youth &#10003;
                      </span>
                    )}
                    {project.gender_intentional && project.youth_focused && (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 2,
                        padding: '1px 6px', borderRadius: 4, fontSize: 9,
                        fontWeight: 600, letterSpacing: '0.06em',
                        background: 'var(--amber-50, #fffbeb)', color: 'var(--amber-700, #b45309)',
                        border: '1px solid var(--amber-200, #fde68a)',
                      }}>
                        &#9733; Gender &amp; Youth
                      </span>
                    )}
                  </div>
                )}
                {isIncubation && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                    <div style={{ width: 70, height: 3, background: '#e9d5ff', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{
                        width: `${Math.min(100, (score / threshold) * 100)}%`,
                        height: '100%',
                        background: score >= threshold ? '#16a34a' : '#7c3aed',
                        borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontSize: 9, color: score >= threshold ? '#059669' : '#7c3aed', fontWeight: 600 }}>
                      {score >= threshold ? '✓ Ready to graduate' : `${score.toFixed(0)}/${threshold} needed`}
                    </span>
                  </div>
                )}
              </div>

              {/* Pillar */}
              <div style={{ fontSize: 12, color: 'var(--ink-700)' }}>{project.pillar || '—'}</div>

              {/* Lead */}
              <div>
                <div style={{ fontSize: 12, color: 'var(--ink-900)' }}>{project.lead_country || '—'}</div>
                <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>{project.project_sponsor || ''}</div>
              </div>

              {/* Investment */}
              <div style={{
                fontSize: 14, fontFamily: "'Geist Mono', monospace",
                color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums',
              }}>
                {project.investment_size ? fmtMoney(Number(project.investment_size)) : '—'}
              </div>

              {/* Score */}
              <div style={{ paddingRight: 16 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{
                    fontSize: 13, fontFamily: "'Geist Mono', monospace",
                    color: 'var(--ink-900)', fontWeight: 500,
                  }}>{score.toFixed(0)}</span>
                  <span style={{ fontSize: 10, color: 'var(--ink-400)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    {score >= 75 ? 'Strong' : score >= 60 ? 'Moderate' : 'Weak'}
                  </span>
                </div>
                <div style={{ height: 2, background: 'var(--ink-100)', position: 'relative' }}>
                  <div style={{
                    position: 'absolute', inset: 0, width: `${score}%`,
                    background: score >= 75 ? 'var(--accent)' : score >= 60 ? 'var(--amber)' : 'var(--terra)',
                  }} />
                </div>
              </div>

              {/* Status */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ width: 6, height: 6, borderRadius: 6, background: statusColor, display: 'inline-block', flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: 'var(--ink-700)' }}>{STATUS_LABEL[project.status] ?? project.status}</span>
                {isIncubation && score >= threshold && (
                  <span
                    onClick={e => { e.stopPropagation(); navigate(`/deal-pipeline/${project.id}`); }}
                    style={{
                      fontSize: 9, background: '#dcfce7', color: '#16a34a',
                      padding: '1px 6px', borderRadius: 10, fontWeight: 700, cursor: 'pointer',
                      marginLeft: 4, whiteSpace: 'nowrap',
                    }}
                  >↑ Graduate</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Footer / pagination ─────────────────────────────── */}
      {!loading && !error && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 4px', fontSize: 11, color: 'var(--ink-500)',
        }}>
          <span style={{ fontFamily: "'Geist Mono', monospace" }}>
            Showing {Math.min((currentPage - 1) * itemsPerPage + 1, filteredProjects.length)}–
            {Math.min(currentPage * itemsPerPage, filteredProjects.length)} of {filteredProjects.length} · {fmtMoney(totalPipelineValue)} total
          </span>
          <div style={{ display: 'flex', gap: 4 }}>
            {[{ label: '‹ Prev', enabled: currentPage > 1, action: () => setCurrentPage(p => Math.max(1, p - 1)) },
              { label: 'Next ›', enabled: currentPage < totalPages, action: () => setCurrentPage(p => Math.min(totalPages, p + 1)) }
            ].map(({ label, enabled, action }) => (
              <button key={label} onClick={action} disabled={!enabled} style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                color: enabled ? 'var(--ink-700)' : 'var(--ink-400)',
                padding: '5px 10px', fontSize: 11, fontFamily: 'inherit',
                cursor: enabled ? 'pointer' : 'default',
              }}>{label}</button>
            ))}
          </div>
        </div>
      )}

      <div style={{ height: 32 }} />
    </div>
  );
};

export default DealPipeline;
