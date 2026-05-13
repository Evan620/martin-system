import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { Project, ProjectStatus } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { UserRole } from '../types/auth';

// ── dropdown option lists ────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { value: ProjectStatus.CONCEPT,         label: 'Concept' },
  { value: ProjectStatus.PRE_FEASIBILITY, label: 'Pre-Feasibility' },
  { value: ProjectStatus.FEASIBILITY,     label: 'Feasibility' },
  { value: ProjectStatus.BANKABLE,        label: 'Bankable' },
  { value: ProjectStatus.SUMMIT_FEATURED, label: 'Summit Featured' },
  { value: ProjectStatus.IN_NEGOTIATION,  label: 'In Negotiation' },
  { value: ProjectStatus.COMMITTED,       label: 'Committed' },
  { value: ProjectStatus.ON_HOLD,         label: 'On Hold' },
  { value: ProjectStatus.DECLINED,        label: 'Declined' },
];

const PERMITS_OPTIONS = ['Obtained', 'Pending', 'Not Required', 'TBC'];
const LAND_OPTIONS    = ['Secured', 'Pending', 'Not Secured', 'Not Applicable', 'TBC'];
const FINANCE_OPTIONS = [
  'PPP / Private investment',
  'PPP / Blended Finance',
  'Private Equity',
  'Debt Financing',
  'Public Sector / Government',
  'Blended Finance',
  'Grant / Concessional',
  'TBC',
];
const INV_STAGE_OPTIONS = ['Investment-ready', 'Bankable', 'Emerging', 'Early stage', 'Pre-commercial', 'TBC'];
const ESG_OPTIONS       = ['Aligned', 'Partially Aligned', 'Not Assessed', 'TBC'];

// ── status badge colour ──────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  CONCEPT:         'bg-blue-100 text-blue-800 border-blue-200',
  PRE_FEASIBILITY: 'bg-purple-100 text-purple-800 border-purple-200',
  FEASIBILITY:     'bg-yellow-100 text-yellow-800 border-yellow-200',
  BANKABLE:        'bg-green-100 text-green-800 border-green-200',
  SUMMIT_FEATURED: 'bg-orange-100 text-orange-800 border-orange-200',
  IN_NEGOTIATION:  'bg-pink-100 text-pink-800 border-pink-200',
  COMMITTED:       'bg-emerald-100 text-emerald-800 border-emerald-200',
  ON_HOLD:         'bg-slate-100 text-slate-600 border-slate-200',
  DECLINED:        'bg-red-100 text-red-800 border-red-200',
};

// ── component ────────────────────────────────────────────────────────────────

const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAppSelector((s) => s.auth);

  const canEdit = !!user?.role && [
    UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR,
  ].includes(user.role);

  const [project, setProject]   = useState<Project | null>(null);
  const [loading, setLoading]   = useState(true);
  const [draft, setDraft]       = useState<Partial<Project>>({});
  const [dirty, setDirty]       = useState(false);
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);

  // ── data load ──────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    pipelineService.getProject(projectId)
      .then(p => { setProject(p); setDraft({ ...p }); })
      .catch(e => console.error('Failed to load project', e))
      .finally(() => setLoading(false));
  }, [projectId]);

  // ── draft helpers ──────────────────────────────────────────────────────────

  const set = useCallback((key: keyof Project, val: string | boolean) => {
    setDraft(d => ({ ...d, [key]: val }));
    setDirty(true);
    setSaved(false);
  }, []);

  const handleSave = async () => {
    if (!project || !dirty) return;
    setSaving(true);
    try {
      const updated = await pipelineService.updateProject(project.id, draft);
      setProject(updated);
      setDraft({ ...updated });
      setDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error('Save failed', e);
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => {
    if (!project) return;
    setDraft({ ...project });
    setDirty(false);
  };

  // ── render helpers ─────────────────────────────────────────────────────────

  /** One label | value row */
  const Row = ({
    label,
    fkey,
    type = 'text',
    options,
    wide = false,
  }: {
    label: string;
    fkey: keyof Project;
    type?: 'text' | 'email' | 'number' | 'textarea' | 'select' | 'bool';
    options?: string[];
    wide?: boolean;
  }) => {
    const val = draft[fkey] as string ?? '';

    const inputClass =
      'w-full bg-transparent border-0 border-b border-transparent focus:border-blue-400 ' +
      'focus:bg-blue-50/30 dark:focus:bg-blue-900/20 rounded-none px-0 py-1 text-sm ' +
      'text-slate-800 dark:text-slate-100 focus:outline-none transition-colors ' +
      'placeholder:text-slate-300 dark:placeholder:text-slate-600';

    const selectClass =
      'w-full bg-transparent border-0 border-b border-transparent focus:border-blue-400 ' +
      'focus:bg-blue-50/30 dark:focus:bg-blue-900/20 rounded-none px-0 py-1 text-sm ' +
      'text-slate-800 dark:text-slate-100 focus:outline-none transition-colors cursor-pointer';

    let input: React.ReactNode;

    if (!canEdit) {
      // View-only
      const display = type === 'bool'
        ? ((draft[fkey] as boolean) ? 'Cross-border' : 'National')
        : (val || <span className="text-slate-300 dark:text-slate-600 italic">—</span>);
      input = <span className="text-sm text-slate-800 dark:text-slate-200 py-1 block">{display}</span>;
    } else if (type === 'bool') {
      input = (
        <select
          value={(draft[fkey] as boolean) ? 'cross-border' : 'national'}
          onChange={e => set(fkey, e.target.value === 'cross-border')}
          className={selectClass}
        >
          <option value="national">National</option>
          <option value="cross-border">Cross-border</option>
        </select>
      );
    } else if (type === 'select' && options) {
      input = (
        <select
          value={val}
          onChange={e => set(fkey, e.target.value)}
          className={selectClass}
        >
          <option value="">— select —</option>
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      );
    } else if (type === 'textarea') {
      input = (
        <textarea
          value={val}
          onChange={e => set(fkey, e.target.value)}
          rows={2}
          placeholder="—"
          className={inputClass + ' resize-none leading-snug'}
        />
      );
    } else {
      input = (
        <input
          type={type}
          value={val}
          onChange={e => set(fkey, e.target.value)}
          placeholder="—"
          className={inputClass}
        />
      );
    }

    return (
      <tr className={`border-b border-slate-100 dark:border-slate-700/60 last:border-0 ${wide ? 'col-span-2' : ''}`}>
        <td className="py-2.5 pr-6 pl-0 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 w-[36%] align-middle whitespace-nowrap select-none">
          {label}
        </td>
        <td className="py-1 pr-0 align-middle">
          {input}
        </td>
      </tr>
    );
  };

  /** Section card */
  const Section = ({
    sec, color, label, children,
  }: {
    sec: string; color: string; label: string; children: React.ReactNode;
  }) => (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
      <div className={`px-6 py-2.5 border-b border-slate-100 dark:border-slate-700 flex items-center gap-2.5 ${color}`}>
        <span className="text-[10px] font-black uppercase tracking-widest opacity-70">{sec}</span>
        <span className="text-xs font-bold">{label}</span>
      </div>
      <table className="w-full px-6">
        <tbody className="divide-y-0">
          <tr><td colSpan={2} className="h-1" /></tr>
          {children}
          <tr><td colSpan={2} className="h-2" /></tr>
        </tbody>
      </table>
    </div>
  );

  // ── loading ────────────────────────────────────────────────────────────────

  if (loading || !project) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        Loading project…
      </div>
    );
  }

  // ── render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-3xl mx-auto pb-16 space-y-5">

      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-slate-400 pt-1">
        <button onClick={() => navigate('/deal-pipeline')} className="hover:text-primary transition-colors">
          Deal Pipeline
        </button>
        <span className="material-symbols-outlined text-[14px]">chevron_right</span>
        <span className="text-slate-600 dark:text-slate-300">{project.name}</span>
      </div>

      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Project name — editable for facilitators */}
          {canEdit ? (
            <input
              value={draft.name ?? ''}
              onChange={e => set('name', e.target.value)}
              className="text-2xl font-black text-slate-900 dark:text-white bg-transparent border-0 border-b-2 border-transparent focus:border-blue-400 focus:outline-none w-full pb-0.5 transition-colors"
            />
          ) : (
            <h1 className="text-2xl font-black text-slate-900 dark:text-white">{project.name}</h1>
          )}

          <div className="flex items-center flex-wrap gap-2 mt-2">
            {/* Status — select for facilitators */}
            {canEdit ? (
              <select
                value={draft.status ?? project.status}
                onChange={e => set('status', e.target.value)}
                className={`text-xs font-bold px-2 py-1 rounded border cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-400/40 ${STATUS_COLORS[draft.status as string ?? project.status] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}
              >
                {PIPELINE_STAGES.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            ) : (
              <span className={`text-xs font-bold px-2 py-1 rounded border ${STATUS_COLORS[project.status] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                {project.status.replace(/_/g, ' ')}
              </span>
            )}

            {project.pillar && (
              <span className="text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded">
                {project.pillar.replace(/_/g, ' ')}
              </span>
            )}

            {project.lead_country && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {project.lead_country}
              </span>
            )}
          </div>
        </div>

        {/* Save / discard controls */}
        {canEdit && (
          <div className="flex items-center gap-2 pt-1 shrink-0">
            {dirty && (
              <button
                onClick={handleDiscard}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Discard
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!dirty || saving}
              className={`flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
                dirty
                  ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                  : saved
                  ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                  : 'bg-slate-100 text-slate-400 cursor-not-allowed'
              }`}
            >
              {saving && <span className="material-symbols-outlined text-[14px] animate-spin">progress_activity</span>}
              <span className="material-symbols-outlined text-[14px]">
                {saved ? 'check_circle' : 'save'}
              </span>
              {saving ? 'Saving…' : saved ? 'Saved' : 'Save Changes'}
            </button>
          </div>
        )}
      </div>

      {/* ── Section A ── */}
      <Section sec="Section A" label="Basic Project Information" color="bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
        <Row label="Country / Host State"  fkey="lead_country" />
        <Row label="Regional Dimension"    fkey="is_cross_border" type="bool" />
        <Row label="Subsector"             fkey="subsector" />
        <Row label="Project Sponsor"       fkey="project_sponsor" />
        <Row label="Key Contact Name"      fkey="key_contact_name" />
        <Row label="Key Contact Email"     fkey="key_contact_email" type="email" />
        <Row label="Submitted By"          fkey="submitted_by" />
      </Section>

      {/* ── Section B ── */}
      <Section sec="Section B" label="Project Development Status" color="bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300">
        <Row label="Technical Studies"  fkey="technical_studies"  type="textarea" />
        <Row label="Permits & Licences" fkey="permits_licences"   type="select" options={PERMITS_OPTIONS} />
        <Row label="Land Status"        fkey="land_status"        type="select" options={LAND_OPTIONS} />
      </Section>

      {/* ── Section C ── */}
      <Section sec="Section C" label="Investment Profile" color="bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300">
        {/* Investment size: stored as raw USD, displayed as $XM */}
        <tr className="border-b border-slate-100 dark:border-slate-700/60 last:border-0">
          <td className="py-2.5 pr-6 pl-0 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 w-[36%] align-middle whitespace-nowrap select-none">
            Investment Size
          </td>
          <td className="py-1 pr-0 align-middle">
            {canEdit ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">$</span>
                <input
                  type="number"
                  value={draft.investment_size ? Number(draft.investment_size) / 1_000_000 : ''}
                  onChange={e => set('investment_size', String(Number(e.target.value) * 1_000_000))}
                  placeholder="e.g. 250"
                  className="w-32 bg-transparent border-0 border-b border-transparent focus:border-blue-400 focus:bg-blue-50/30 dark:focus:bg-blue-900/20 rounded-none px-0 py-1 text-sm text-slate-800 dark:text-slate-100 focus:outline-none transition-colors"
                />
                <span className="text-sm text-slate-400">M USD</span>
              </div>
            ) : (
              <span className="text-sm text-slate-800 dark:text-slate-200 py-1 block">
                ${project.investment_size ? (Number(project.investment_size) / 1_000_000).toFixed(1) : '—'} M USD
              </span>
            )}
          </td>
        </tr>
        <Row label="Financing Structure"     fkey="financing_structure"   type="select" options={FINANCE_OPTIONS} />
        <Row label="Investment Stage"        fkey="investment_stage_label" type="select" options={INV_STAGE_OPTIONS} />
        <Row label="Revenue Model"           fkey="revenue_model"         type="textarea" />
        <Row label="Macroeconomic ROI"       fkey="macroeconomic_roi"     type="textarea" />
      </Section>

      {/* ── Section D ── */}
      <Section sec="Section D" label="Climate & Social Impact" color="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300">
        <Row label="Climate & ESG Notes"        fkey="climate_impact"             type="textarea" />
        <Row label="ESG Compliance"             fkey="esg_compliance"             type="select" options={ESG_OPTIONS} />
        <Row label="GHG Avoided (tCO₂e/yr)"    fkey="ghg_avoided_target" />
        <Row label="Jobs — Construction"        fkey="jobs_construction" />
        <Row label="Jobs — O&M (ongoing)"       fkey="jobs_om" />
        <Row label="Smallholder Farmers Reached" fkey="smallholder_farmers_reached" />
        <Row label="New Electricity Connections" fkey="electricity_connections" />
        <Row label="Digital Connections / SMEs"  fkey="digital_connections" />
      </Section>

    </div>
  );
};

export default ProjectDetails;
