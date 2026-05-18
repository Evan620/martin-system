import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { Project, ProjectStatus } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { UserRole } from '../types/auth';

// ─── option lists ────────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { value: ProjectStatus.DRAFT,              label: 'Draft' },
  { value: ProjectStatus.PIPELINE,           label: 'Pipeline' },
  { value: ProjectStatus.UNDER_REVIEW,       label: 'Under Review' },
  { value: ProjectStatus.SUMMIT_READY,       label: 'Summit Ready' },
  { value: ProjectStatus.DEAL_ROOM_FEATURED, label: 'Deal Room Featured' },
  { value: ProjectStatus.IN_NEGOTIATION,     label: 'In Negotiation' },
  { value: ProjectStatus.COMMITTED,          label: 'Committed' },
  { value: ProjectStatus.IMPLEMENTED,        label: 'Implemented' },
  { value: ProjectStatus.ON_HOLD,            label: 'On Hold' },
  { value: ProjectStatus.DECLINED,           label: 'Declined' },
];

const STATUS_COLORS: Record<string, string> = {
  DRAFT:              'bg-slate-100 text-slate-600 border-slate-300',
  PIPELINE:           'bg-blue-100 text-blue-800 border-blue-300',
  UNDER_REVIEW:       'bg-violet-100 text-violet-800 border-violet-300',
  SUMMIT_READY:       'bg-green-100 text-green-800 border-green-300',
  DEAL_ROOM_FEATURED: 'bg-orange-100 text-orange-800 border-orange-300',
  IN_NEGOTIATION:     'bg-pink-100 text-pink-800 border-pink-300',
  COMMITTED:          'bg-emerald-100 text-emerald-800 border-emerald-300',
  IMPLEMENTED:        'bg-teal-100 text-teal-800 border-teal-300',
  ON_HOLD:            'bg-amber-100 text-amber-700 border-amber-300',
  DECLINED:           'bg-red-100 text-red-800 border-red-300',
};

const PERMITS_OPTIONS   = ['Obtained', 'Pending', 'Not Required', 'TBC'];
const LAND_OPTIONS      = ['Secured', 'Pending', 'Not Secured', 'Not Applicable', 'TBC'];
const FINANCE_OPTIONS   = [
  'PPP / Private investment', 'PPP / Blended Finance', 'Private Equity',
  'Debt Financing', 'Public Sector / Government', 'Blended Finance',
  'Grant / Concessional', 'TBC',
];
const INV_STAGE_OPTIONS = ['Investment-ready', 'Bankable', 'Emerging', 'Early stage', 'Pre-commercial', 'TBC'];
const ESG_OPTIONS       = ['Aligned', 'Partially Aligned', 'Not Assessed', 'TBC'];

// ─── section tab definitions ─────────────────────────────────────────────────

type SectionKey = 'A' | 'B' | 'C' | 'D';

const SECTION_TABS: { key: SectionKey; label: string; sub: string }[] = [
  { key: 'A', label: 'A',  sub: 'Basic Information' },
  { key: 'B', label: 'B',  sub: 'Development Status' },
  { key: 'C', label: 'C',  sub: 'Investment Profile' },
  { key: 'D', label: 'D',  sub: 'Climate & Impact' },
];

// ─── field row component ─────────────────────────────────────────────────────

type FieldType = 'text' | 'email' | 'textarea' | 'select' | 'bool';

interface FieldRowProps {
  label: string;
  value: string | boolean;
  type?: FieldType;
  options?: string[];
  canEdit: boolean;
  onChange: (v: string | boolean) => void;
}

const FieldRow: React.FC<FieldRowProps> = ({ label, value, type = 'text', options, canEdit, onChange }) => {
  const strVal = (value as string) ?? '';
  const boolVal = value as boolean;

  const baseInput = 'w-full bg-transparent text-sm text-slate-900 dark:text-slate-100 focus:outline-none';
  const editableInput = canEdit
    ? 'border-b border-slate-200 dark:border-slate-600 focus:border-blue-500 dark:focus:border-blue-400 py-1.5 px-0 transition-colors'
    : 'py-1.5 cursor-default';

  let valueNode: React.ReactNode;

  if (!canEdit) {
    const display = type === 'bool'
      ? (boolVal ? 'Cross-border' : 'National')
      : strVal || <span className="text-slate-300 dark:text-slate-600">—</span>;
    valueNode = <span className={`${baseInput} ${editableInput} block`}>{display}</span>;
  } else if (type === 'bool') {
    valueNode = (
      <select
        value={boolVal ? 'cross' : 'national'}
        onChange={e => onChange(e.target.value === 'cross')}
        className={`${baseInput} ${editableInput} cursor-pointer`}
      >
        <option value="national">National</option>
        <option value="cross">Cross-border</option>
      </select>
    );
  } else if (type === 'select' && options) {
    valueNode = (
      <select
        value={strVal}
        onChange={e => onChange(e.target.value)}
        className={`${baseInput} ${editableInput} cursor-pointer`}
      >
        <option value="">—</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  } else if (type === 'textarea') {
    valueNode = (
      <textarea
        value={strVal}
        onChange={e => onChange(e.target.value)}
        placeholder="—"
        rows={2}
        className={`${baseInput} ${editableInput} resize-none leading-snug`}
      />
    );
  } else {
    valueNode = (
      <input
        type={type}
        value={strVal}
        onChange={e => onChange(e.target.value)}
        placeholder="—"
        className={`${baseInput} ${editableInput}`}
      />
    );
  }

  return (
    <div className="grid grid-cols-[180px_1fr] gap-4 items-start py-3 border-b border-slate-100 dark:border-slate-700/50 last:border-0">
      <span className="text-sm font-medium text-slate-500 dark:text-slate-400 pt-1.5 leading-tight">
        {label}
      </span>
      <div className="min-w-0">{valueNode}</div>
    </div>
  );
};

// ─── main component ──────────────────────────────────────────────────────────

const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAppSelector(s => s.auth);

  const canEdit = !!user?.role && [
    UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR,
  ].includes(user.role);

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft]     = useState<Partial<Project>>({});
  const [dirty, setDirty]     = useState(false);
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);
  const [activeSection, setActiveSection] = useState<SectionKey>('A');

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    pipelineService.getProject(projectId)
      .then(p => { setProject(p); setDraft({ ...p }); })
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, [projectId]);

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

  // helper: bind a field row to the draft
  const F = (
    label: string,
    fkey: keyof Project,
    type: FieldType = 'text',
    options?: string[],
  ) => (
    <FieldRow
      key={fkey}
      label={label}
      value={(draft[fkey] as string | boolean) ?? (type === 'bool' ? false : '')}
      type={type}
      options={options}
      canEdit={canEdit}
      onChange={v => set(fkey, v)}
    />
  );

  if (loading || !project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-slate-400">Loading…</div>
      </div>
    );
  }

  const statusColor = STATUS_COLORS[String(draft.status ?? project.status)] ?? 'bg-slate-100 text-slate-600 border-slate-300';

  return (
    <div className="max-w-2xl mx-auto pb-20 space-y-6">

      {/* ── breadcrumb ── */}
      <div className="flex items-center gap-1.5 text-xs text-slate-400 pt-2">
        <button onClick={() => navigate('/deal-pipeline')} className="hover:text-primary transition-colors">
          Deal Pipeline
        </button>
        <span className="material-symbols-outlined text-[14px]">chevron_right</span>
        <span className="text-slate-500 dark:text-slate-300 truncate max-w-xs">{project.name}</span>
      </div>

      {/* ── page header card ── */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0 space-y-3">
            {/* Name */}
            {canEdit ? (
              <input
                value={draft.name ?? ''}
                onChange={e => set('name', e.target.value)}
                className="text-xl font-bold text-slate-900 dark:text-white bg-transparent w-full border-b border-transparent focus:border-blue-400 focus:outline-none pb-0.5 transition-colors leading-tight"
              />
            ) : (
              <h1 className="text-xl font-bold text-slate-900 dark:text-white leading-tight">{project.name}</h1>
            )}

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-2">
              {canEdit ? (
                <select
                  value={String(draft.status ?? project.status)}
                  onChange={e => set('status', e.target.value)}
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full border cursor-pointer focus:outline-none ${statusColor}`}
                >
                  {PIPELINE_STAGES.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              ) : (
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${statusColor}`}>
                  {String(project.status).replace(/_/g, ' ')}
                </span>
              )}

              {project.pillar && (
                <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-700 dark:text-slate-300 px-2.5 py-1 rounded-full">
                  {project.pillar.replace(/_/g, ' ')}
                </span>
              )}
              {project.lead_country && (
                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">location_on</span>
                  {project.lead_country}
                </span>
              )}
              {project.investment_size && (
                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">payments</span>
                  ${(Number(project.investment_size) / 1_000_000).toFixed(0)}M USD
                </span>
              )}
            </div>
          </div>

          {/* Save controls */}
          {canEdit && (
            <div className="flex items-center gap-2 shrink-0">
              {dirty && (
                <button
                  onClick={handleDiscard}
                  className="text-xs font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  Discard
                </button>
              )}
              <button
                onClick={handleSave}
                disabled={!dirty || saving}
                className={`flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  dirty
                    ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                    : saved
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                }`}
              >
                {saving
                  ? <><span className="material-symbols-outlined text-[14px] animate-spin">progress_activity</span> Saving…</>
                  : saved
                  ? <><span className="material-symbols-outlined text-[14px]">check_circle</span> Saved</>
                  : <><span className="material-symbols-outlined text-[14px]">save</span> Save changes</>
                }
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── section tabs + content ── */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">

        {/* Tab bar */}
        <div className="flex border-b border-slate-200 dark:border-slate-700">
          {SECTION_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveSection(tab.key)}
              className={`flex-1 flex flex-col items-center py-3.5 px-2 text-center transition-colors border-b-2 ${
                activeSection === tab.key
                  ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-900/20'
                  : 'border-transparent hover:bg-slate-50 dark:hover:bg-slate-700/50'
              }`}
            >
              <span className={`text-sm font-bold leading-none ${
                activeSection === tab.key
                  ? 'text-blue-700 dark:text-blue-400'
                  : 'text-slate-400 dark:text-slate-500'
              }`}>
                {tab.label}
              </span>
              <span className={`text-[11px] mt-0.5 leading-none ${
                activeSection === tab.key
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-slate-400 dark:text-slate-500'
              }`}>
                {tab.sub}
              </span>
            </button>
          ))}
        </div>

        {/* Section content */}
        <div className="px-6 py-2">

          {activeSection === 'A' && (
            <>
              {F('Country / Host State',  'lead_country')}
              {F('Regional Dimension',    'is_cross_border', 'bool')}
              {F('Subsector',             'subsector')}
              {F('Project Sponsor',       'project_sponsor')}
              {F('Key Contact Name',      'key_contact_name')}
              {F('Key Contact Email',     'key_contact_email', 'email')}
              {F('Submitted By',          'submitted_by')}
            </>
          )}

          {activeSection === 'B' && (
            <>
              {F('Technical Studies',  'technical_studies',  'textarea')}
              {F('Permits & Licences', 'permits_licences',   'select', PERMITS_OPTIONS)}
              {F('Land Status',        'land_status',        'select', LAND_OPTIONS)}
            </>
          )}

          {activeSection === 'C' && (
            <>
              {/* Investment size special row */}
              <div className="grid grid-cols-[180px_1fr] gap-4 items-start py-3 border-b border-slate-100 dark:border-slate-700/50">
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400 pt-1.5">Investment Size</span>
                <div className="flex items-baseline gap-2">
                  {canEdit ? (
                    <>
                      <span className="text-sm text-slate-400">$</span>
                      <input
                        type="number"
                        value={draft.investment_size ? Number(draft.investment_size) / 1_000_000 : ''}
                        onChange={e => set('investment_size', String(Number(e.target.value) * 1_000_000))}
                        placeholder="e.g. 250"
                        className="w-28 bg-transparent text-sm text-slate-900 dark:text-slate-100 border-b border-slate-200 dark:border-slate-600 focus:border-blue-500 focus:outline-none py-1.5 px-0 transition-colors"
                      />
                      <span className="text-sm text-slate-400">M USD</span>
                    </>
                  ) : (
                    <span className="text-sm text-slate-900 dark:text-slate-100 py-1.5">
                      {project.investment_size
                        ? `$${(Number(project.investment_size) / 1_000_000).toFixed(0)}M USD`
                        : <span className="text-slate-300">—</span>}
                    </span>
                  )}
                </div>
              </div>
              {F('Financing Structure',  'financing_structure',    'select', FINANCE_OPTIONS)}
              {F('Investment Stage',     'investment_stage_label', 'select', INV_STAGE_OPTIONS)}
              {F('Revenue Model',        'revenue_model',          'textarea')}
              {F('Macroeconomic ROI',    'macroeconomic_roi',      'textarea')}
            </>
          )}

          {activeSection === 'D' && (
            <>
              {F('Climate & ESG Notes',         'climate_impact',             'textarea')}
              {F('ESG Compliance',              'esg_compliance',             'select', ESG_OPTIONS)}
              {F('GHG Avoided (tCO₂e/yr)',      'ghg_avoided_target')}
              {F('Jobs — Construction',          'jobs_construction')}
              {F('Jobs — O&M (ongoing)',          'jobs_om')}
              {F('Smallholder Farmers Reached',  'smallholder_farmers_reached')}
              {F('New Electricity Connections',  'electricity_connections')}
              {F('Digital Connections / SMEs',   'digital_connections')}
            </>
          )}

        </div>

        {/* Section footer with prev/next */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
          <button
            onClick={() => {
              const keys: SectionKey[] = ['A', 'B', 'C', 'D'];
              const idx = keys.indexOf(activeSection);
              if (idx > 0) setActiveSection(keys[idx - 1]);
            }}
            disabled={activeSection === 'A'}
            className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            Previous
          </button>
          <span className="text-xs text-slate-400 dark:text-slate-500">
            Section {activeSection} of 4
          </span>
          <button
            onClick={() => {
              const keys: SectionKey[] = ['A', 'B', 'C', 'D'];
              const idx = keys.indexOf(activeSection);
              if (idx < keys.length - 1) setActiveSection(keys[idx + 1]);
            }}
            disabled={activeSection === 'D'}
            className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next
            <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
          </button>
        </div>

      </div>
    </div>
  );
};

export default ProjectDetails;
