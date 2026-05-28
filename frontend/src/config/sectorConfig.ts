export type FieldType = 'text' | 'number' | 'select' | 'multiselect' | 'toggle';

export interface FieldDef {
  key: string;          // sector_details[key] for non-agri sectors
  label: string;
  type: FieldType;
  options?: string[];   // select / multiselect
  optional?: boolean;
  card?: boolean;       // include in the project-card summary line
}

export interface SectorConfig {
  pillarValue: string;   // exact value submitted as `pillar` (matches NewProject pillars[].value)
  label: string;         // display label
  filterToken: string;   // lowercase substring the backend ilike pillar filter matches
  usesOfftake: boolean;  // gates Buyer DB + offtake matching (agri only)
  legacyAgri?: boolean;  // agribusiness uses its own typed columns, not sector_details
  fields: FieldDef[];    // bespoke intake fields (empty for agri — it has its own form blocks)
}

export const SECTORS: SectorConfig[] = [
  {
    pillarValue: 'Agribusiness and Food Systems Transformation',
    label: 'Agribusiness & Food Systems',
    // Matches both 'Agribusiness and Food Systems Transformation' (human label)
    // and 'agriculture_food_systems' (enum key) — historic projects use both.
    filterToken: 'agri',
    usesOfftake: true,
    legacyAgri: true,
    fields: [],
  },
  {
    pillarValue: 'Energy Trade and Industrial Growth',
    label: 'Energy Trade & Industrial Growth',
    filterToken: 'energy',
    usesOfftake: false,
    fields: [
      { key: 'asset_type', label: 'Asset / generation type', type: 'select',
        options: ['Solar', 'Hydro', 'Wind', 'Gas', 'Transmission', 'Industrial plant'], card: true },
      { key: 'capacity_mw', label: 'Installed / planned capacity (MW)', type: 'number', card: true },
      { key: 'offtake_status', label: 'Offtake / PPA status', type: 'select',
        options: ['PPA signed', 'Under negotiation', 'None'], card: true },
      { key: 'grid_connection', label: 'Grid connection', type: 'select',
        options: ['On-grid', 'Mini-grid', 'Off-grid'] },
      { key: 'annual_output_gwh', label: 'Annual output (GWh)', type: 'number', optional: true },
    ],
  },
  {
    pillarValue: 'Strategic Minerals and Natural Resource Development',
    label: 'Strategic Minerals & Natural Resources',
    filterToken: 'mineral',
    usesOfftake: false,
    fields: [
      { key: 'mineral_types', label: 'Mineral / resource type', type: 'multiselect',
        options: ['Lithium', 'Bauxite', 'Gold', 'Iron ore', 'Manganese', 'Phosphate', 'Cobalt'], card: true },
      { key: 'project_stage', label: 'Project stage', type: 'select',
        options: ['Exploration', 'Feasibility', 'Development', 'Production'], card: true },
      { key: 'reserve_estimate', label: 'Estimated reserves / resource size', type: 'text' },
      { key: 'processing_level', label: 'Processing level', type: 'select',
        options: ['Raw export', 'Beneficiation', 'Refining'], card: true },
      { key: 'permits_esg', label: 'Key permits & ESG status (EIA, mining licence)', type: 'text' },
    ],
  },
  {
    pillarValue: 'Digital Transformation',
    label: 'Digital Transformation',
    filterToken: 'digital',
    usesOfftake: false,
    fields: [
      { key: 'solution_type', label: 'Solution type', type: 'select',
        options: ['Platform', 'Infrastructure / data centre', 'Connectivity', 'Fintech', 'E-gov'], card: true },
      { key: 'target_users', label: 'Target users / beneficiaries', type: 'number', card: true },
      { key: 'infrastructure_tier', label: 'Infrastructure tier', type: 'select',
        options: ['Software-only', 'Cloud', 'Physical infra'] },
      { key: 'data_regulatory', label: 'Data & regulatory posture (residency, licences)', type: 'text' },
      { key: 'cross_border_dpi', label: 'Cross-border digital public infrastructure', type: 'toggle' },
    ],
  },
];

/** Match a stored pillar string (human name or token) to a sector config. */
export function sectorByPillar(pillar?: string | null): SectorConfig | undefined {
  if (!pillar) return undefined;
  const p = pillar.toLowerCase();
  return SECTORS.find(s => p.includes(s.filterToken) || p === s.pillarValue.toLowerCase());
}

/** Build a one-line card summary from a project's sector + sector_details. */
export function sectorCardSummary(pillar: string | undefined, details?: Record<string, any> | null): string | null {
  const cfg = sectorByPillar(pillar);
  if (!cfg || cfg.legacyAgri || !details) return null;
  const parts = cfg.fields
    .filter(f => f.card)
    .map(f => {
      const v = details[f.key];
      if (v == null || v === '' || (Array.isArray(v) && v.length === 0)) return null;
      return Array.isArray(v) ? v.join(', ') : String(v);
    })
    .filter(Boolean);
  return parts.length ? parts.join(' · ') : null;
}
