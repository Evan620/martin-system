import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { Project, ProjectScoreDetail } from '../../types/pipeline';

interface GapItem {
  criterion: string;
  weight: string;
  issue: string;
  action: string;
}

interface ReadinessGapResponse {
  gaps: GapItem[];
  current_score: number;
  threshold: number;
  cached: boolean;
}

interface Props {
  project: Project;
  scoreDetails: ProjectScoreDetail[];
  onGraduate: () => void;
  canEdit: boolean;
}

function getCriterionColorKey(score: number): 'green' | 'amber' | 'red' {
  if (score >= 50) return 'green';
  if (score >= 20) return 'amber';
  return 'red';
}

const COLOR_MAP = {
  green: { bg: '#f0fdf4', border: '#bbf7d0', text: '#15803d', dotBg: '#16a34a', icon: '✓' },
  amber: { bg: '#fffbeb', border: '#fde68a', text: '#b45309', dotBg: '#d97706', icon: '!' },
  red:   { bg: '#fef2f2', border: '#fecaca', text: '#b91c1c', dotBg: '#dc2626', icon: '✕' },
};

const ReadinessTab: React.FC<Props> = ({ project, scoreDetails, onGraduate, canEdit }) => {
  const [gapReport, setGapReport] = useState<ReadinessGapResponse | null>(null);
  const [loadingGap, setLoadingGap] = useState(false);
  const [gapError, setGapError] = useState<string | null>(null);
  const [graduating, setGraduating] = useState(false);
  const [threshold, setThreshold] = useState(40);

  useEffect(() => {
    api.get('/pipeline/settings').then((r: any) => {
      const t = Number(r.data?.incubation_graduation_threshold);
      if (!isNaN(t) && t > 0) setThreshold(t);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!project.id) return;
    setLoadingGap(true);
    setGapError(null);
    api.get(`/pipeline/${project.id}/readiness-gap`)
      .then((r: any) => setGapReport(r.data))
      .catch((e: any) => setGapError(e?.response?.data?.detail || 'Failed to load gap report'))
      .finally(() => setLoadingGap(false));
  }, [project.id]);

  const currentScore = Number(project.afcen_score ?? 0);
  const scorePercent = Math.min(100, (currentScore / threshold) * 100);
  const canGraduate = currentScore >= threshold;

  const handleGraduate = async () => {
    if (!canGraduate || !canEdit) return;
    setGraduating(true);
    try {
      await api.post(`/pipeline/${project.id}/advance`, { new_stage: 'DRAFT' });
      onGraduate();
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to graduate project');
    } finally {
      setGraduating(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24 }}>
      {/* Left: WAIIS checklist */}
      <div>
        {/* Score progress bar */}
        <div style={{ background: '#f5f3ff', border: '1px solid #e9d5ff', borderRadius: 8, padding: 16, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'center', minWidth: 52 }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#7c3aed', lineHeight: 1 }}>{currentScore.toFixed(0)}</div>
            <div style={{ fontSize: 9, color: '#7c3aed', fontWeight: 600 }}>/100</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#6b7280', marginBottom: 4 }}>
              <span>AfCEN Readiness Score</span>
              <span style={{ color: '#7c3aed', fontWeight: 600 }}>Need {threshold} to graduate</span>
            </div>
            <div style={{ height: 8, background: '#e9d5ff', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${scorePercent}%`, height: '100%', background: 'linear-gradient(90deg,#7c3aed,#a855f7)', borderRadius: 4, transition: 'width 0.4s' }} />
            </div>
            <div style={{ fontSize: 10, color: '#6b7280', marginTop: 4 }}>
              {canGraduate
                ? 'Score meets graduation threshold — ready to graduate.'
                : `${(threshold - currentScore).toFixed(1)} points needed to unlock graduation`}
            </div>
          </div>
        </div>

        {/* WAIIS criteria checklist */}
        <div style={{ fontSize: 11, fontWeight: 700, color: '#374151', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          WAIIS Criteria Checklist
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {scoreDetails.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--ink-400)', padding: 12 }}>
              No scores yet — upload documents or fill in project fields, then click Rescore.
            </div>
          ) : scoreDetails.map((detail: any) => {
            const ck = getCriterionColorKey(Number(detail.score));
            const c = COLOR_MAP[ck];
            const criterionName = detail.criterion?.criterion_name ?? 'Unknown';
            const weightRaw = Number(detail.criterion?.weight ?? 0);
            const weightPct = (weightRaw * 10).toFixed(0);
            return (
              <div key={detail.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: c.bg, border: `1px solid ${c.border}`, borderRadius: 8 }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: c.dotBg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <span style={{ color: 'white', fontSize: 11 }}>{c.icon}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: c.text }}>{criterionName} · {weightPct}%</div>
                  <div style={{ fontSize: 10, color: '#6b7280' }}>{detail.notes || 'No scoring notes'}</div>
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: c.text }}>{Number(detail.score).toFixed(0)}</div>
              </div>
            );
          })}
        </div>

        {/* Graduation button */}
        <div style={{ marginTop: 16, padding: 12, background: canGraduate ? '#f0fdf4' : '#f3f4f6', border: `1px dashed ${canGraduate ? '#86efac' : '#d1d5db'}`, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          {canGraduate ? (
            <div style={{ fontSize: 11, color: '#15803d' }}>
              Score <strong>{currentScore.toFixed(0)}</strong> meets graduation threshold of <strong>{threshold}</strong>.
            </div>
          ) : (
            <div style={{ fontSize: 11, color: '#6b7280' }}>
              Score must reach <strong>{threshold}</strong> to graduate. Currently <strong style={{ color: '#7c3aed' }}>{currentScore.toFixed(0)}</strong>.
            </div>
          )}
          <button
            onClick={handleGraduate}
            disabled={!canGraduate || !canEdit || graduating}
            style={{
              background: canGraduate && canEdit ? '#16a34a' : '#e5e7eb',
              color: canGraduate && canEdit ? 'white' : '#9ca3af',
              border: 'none', padding: '7px 16px', borderRadius: 6, fontSize: 11,
              fontWeight: 600, cursor: canGraduate && canEdit ? 'pointer' : 'not-allowed',
              fontFamily: 'inherit', flexShrink: 0,
            }}
          >
            {graduating ? 'Graduating…' : 'Graduate to Draft ↑'}
          </button>
        </div>
      </div>

      {/* Right: AI Gap Report */}
      <div>
        <div style={{ background: '#1e1b4b', borderRadius: 10, padding: 16, minHeight: 200 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'white', fontSize: 11, fontWeight: 700 }}>✦</span>
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'white' }}>Martin's Gap Report</div>
            {gapReport?.cached && <span style={{ fontSize: 9, color: '#818cf8' }}>(cached)</span>}
          </div>

          {loadingGap ? (
            <div style={{ fontSize: 10, color: '#c4b5fd' }}>Analysing project gaps…</div>
          ) : gapError ? (
            <div style={{ fontSize: 10, color: '#f87171' }}>{gapError}</div>
          ) : gapReport && gapReport.gaps.length > 0 ? (
            <div style={{ fontSize: 10, color: '#c4b5fd', lineHeight: 1.7 }}>
              {gapReport.gaps.map((gap, i) => (
                <div key={i} style={{ marginBottom: 10, paddingLeft: 8, borderLeft: '2px solid #7c3aed' }}>
                  <div style={{ fontWeight: 700, color: '#a78bfa', marginBottom: 2 }}>
                    {gap.criterion} <span style={{ color: '#818cf8', fontWeight: 400 }}>· {gap.weight}</span>
                  </div>
                  <div style={{ marginBottom: 2 }}>{gap.issue}</div>
                  <div style={{ color: 'white', fontWeight: 600 }}>→ {gap.action}</div>
                </div>
              ))}
              <div style={{ marginTop: 10, fontSize: 9, color: '#818cf8' }}>
                Addressing the gaps above should push your score past {gapReport.threshold}.
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 10, color: '#818cf8' }}>No gap data available.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReadinessTab;
