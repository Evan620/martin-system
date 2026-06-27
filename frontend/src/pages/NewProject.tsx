import React, { useState } from 'react';
import SiteLocationPicker from '../components/geospatial/SiteLocationPicker';
import InfoTooltip from '../components/InfoTooltip';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { sectorByPillar, FieldDef } from '../config/sectorConfig';

// R1 — Value chain controlled vocabulary. Keep in sync with backend
// VALID_VALUE_CHAIN_STAGES in app/schemas/pipeline_schemas.py.
const VALUE_CHAIN_STAGES = [
  { code: 'INPUTS', label: 'Inputs & Seeds' },
  { code: 'PRODUCTION', label: 'Primary Production' },
  { code: 'PROCESSING', label: 'Post-Harvest & Processing' },
  { code: 'LOGISTICS', label: 'Logistics & Cold Chain' },
  { code: 'RETAIL', label: 'Retail / Markets' },
  { code: 'DIGITAL_PLATFORM', label: 'Digital Agri-Platform' },
  { code: 'FINANCIAL_SERVICES', label: 'Financial Services' },
  { code: 'POLICY_ENABLING', label: 'Policy & Enabling Env.' },
];

const NewProject: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const [startInIncubation, setStartInIncubation] = useState(true);

  const [formData, setFormData] = useState({
    name: '',
    pillar: 'Infrastructure',
    leadCountry: '',
    leadCompany: '',
    investment: '',
    description: '',
    currency: 'USD',
    icon: 'business',
    iconColor: 'blue',
    subsector: '',
    projectSponsor: '',
    isCrossBorder: false,
    landStatus: '',
    revenueModel: '',
    climateImpact: '',
    esgCompliance: '',
    value_chain_stages: [] as string[],
    sector_details: {} as Record<string, any>,
    gender_intentional: undefined as boolean | undefined,
    gender_justification: undefined as string | undefined,
    youth_focused: undefined as boolean | undefined,
    youth_justification: undefined as string | undefined,
    site_lat: null as number | null,
    site_lon: null as number | null,
    site_location_name: '' as string,
    financing_structure: '',
    technicalStudies: '',
    permitsLicences: '',
    ghgAvoidedTarget: '',
    jobsConstruction: '',
    jobsOm: '',
    smallholderFarmersReached: '',
    macroeconomicRoi: '',
  });

  const pillars = [
    { value: 'Strategic Minerals and Natural Resource Development', icon: 'train', color: 'blue' },
    { value: 'Energy Trade and Industrial Growth', icon: 'solar_power', color: 'orange' },
    { value: 'Agribusiness and Food Systems Transformation', icon: 'agriculture', color: 'green' },
    { value: 'Digital Transformation', icon: 'computer', color: 'indigo' },
  ];

  const ecowasCountries = [
    'Benin', 'Burkina Faso', 'Cape Verde', "Côte d'Ivoire", 'Gambia',
    'Ghana', 'Guinea', 'Guinea-Bissau', 'Liberia', 'Mali',
    'Niger', 'Nigeria', 'Senegal', 'Sierra Leone', 'Togo'
  ];

  const handlePillarChange = (pillar: string) => {
    const selectedPillar = pillars.find(p => p.value === pillar);
    setFormData({
      ...formData,
      pillar,
      icon: selectedPillar?.icon || 'business',
      iconColor: selectedPillar?.color || 'blue',
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      console.log('Starting project creation...');

      // Parse investment amount (remove $ and convert M/B to number)
      const investmentStr = formData.investment.replace(/[$,]/g, '');
      let investmentAmount = 0;

      if (investmentStr.includes('B')) {
        investmentAmount = parseFloat(investmentStr.replace('B', '')) * 1000000000;
      } else if (investmentStr.includes('M')) {
        investmentAmount = parseFloat(investmentStr.replace('M', '')) * 1000000;
      } else {
        investmentAmount = parseFloat(investmentStr);
      }

      console.log('Investment amount:', investmentAmount);

      // Get token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found. Please log in again.');
      }

      let investmentMemoId = null;

      // Skip document upload for now - will be added after project creation
      // Document upload requires TWG to be set up first
      if (uploadedFiles.length > 0) {
        console.log(`Note: ${uploadedFiles.length} documents selected. Documents will need to be uploaded separately after project creation.`);
        // TODO: Implement document upload after TWGs are properly set up
      }

      // First, get the TWG ID based on the pillar
      console.log('Fetching TWGs...');
      let twgId = null;

      try {
        const twgsResponse = await api.get('/twgs/dropdown');

        console.log('Available TWGs:', twgsResponse.data);

        if (twgsResponse.data && twgsResponse.data.length > 0) {
          // Map pillar to TWG pillar enum
          const pillarMap: Record<string, string> = {
            'Strategic Minerals and Natural Resource Development': 'critical_minerals_industrialization',
            'Energy Trade and Industrial Growth': 'energy_infrastructure',
            'Agribusiness and Food Systems Transformation': 'agriculture_food_systems',
            'Digital Transformation': 'digital_economy_transformation',
          };

          const targetPillar = pillarMap[formData.pillar];
          const twg = twgsResponse.data.find((t: any) => t.pillar === targetPillar);

          if (twg) {
            twgId = twg.id;
            console.log('Found TWG:', twgId);
          } else {
            // Use first available TWG as fallback
            twgId = twgsResponse.data[0].id;
            console.log('Using first available TWG as fallback:', twgId);
          }
        } else {
          console.warn('No TWGs found in the system');
        }
      } catch (twgErr: any) {
        console.error('Failed to fetch TWGs:', twgErr);
        // Continue without TWG - we'll use a placeholder
      }

      if (!twgId) {
        // Use a placeholder UUID for now
        // In production, this should create a default TWG or require admin setup
        console.warn('No TWG available - using placeholder. Projects may need TWG assignment later.');
        twgId = '00000000-0000-0000-0000-000000000001';
      }

      // Create project via API
      const projectData: any = {
        twg_id: twgId,
        name: formData.name,
        description: formData.description,
        investment_size: investmentAmount,
        currency: formData.currency,
        readiness_score: 0,
        strategic_alignment_score: 0,
        pillar: formData.pillar,
        lead_country: formData.leadCountry,
        status: 'identified',
        subsector: formData.subsector || undefined,
        project_sponsor: formData.projectSponsor || undefined,
        is_cross_border: formData.isCrossBorder,
        land_status: formData.landStatus || undefined,
        revenue_model: formData.revenueModel || undefined,
        climate_impact: formData.climateImpact || undefined,
        esg_compliance: formData.esgCompliance || undefined,
        metadata_json: {
          leadCompany: formData.leadCompany,
          icon: formData.icon,
          iconColor: formData.iconColor,
        },
        value_chain_stages: formData.value_chain_stages.length > 0 ? formData.value_chain_stages : undefined,
        sector_details: activeSector && !activeSector.legacyAgri ? formData.sector_details : undefined,
        gender_intentional: formData.gender_intentional,
        gender_justification: formData.gender_justification,
        youth_focused: formData.youth_focused,
        youth_justification: formData.youth_justification,
        site_lat: formData.site_lat ?? undefined,
        site_lon: formData.site_lon ?? undefined,
        site_location_name: formData.site_location_name || undefined,
        financing_structure: formData.financing_structure || undefined,
        technical_studies: formData.technicalStudies || undefined,
        permits_licences: formData.permitsLicences || undefined,
        ghg_avoided_target: formData.ghgAvoidedTarget || undefined,
        jobs_construction: formData.jobsConstruction || undefined,
        jobs_om: formData.jobsOm || undefined,
        smallholder_farmers_reached: formData.smallholderFarmersReached || undefined,
        macroeconomic_roi: formData.macroeconomicRoi || undefined,
        start_in_incubation: startInIncubation,
      };

      // Add investment memo ID if document was uploaded
      if (investmentMemoId) {
        projectData.investment_memo_id = investmentMemoId;
      }

      console.log('Creating project with data:', projectData);

      const response = await api.post('/pipeline/ingest', projectData, {
        timeout: 30000 // 30 second timeout
      });

      console.log('Project created successfully:', response.data);

      // Show success message
      alert('Project created successfully!');

      // Navigate to the project details page or back to pipeline
      navigate('/deal-pipeline');
    } catch (err: any) {
      console.error('Error creating project:', err);
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });

      let errorMessage = 'Failed to create project. Please try again.';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else {
          errorMessage = JSON.stringify(err.response.data.detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
      console.log('Form submission complete');
    }
  };

  const activeSector = sectorByPillar(formData.pillar);
  const setSectorField = (key: string, value: any) =>
    setFormData(prev => ({ ...prev, sector_details: { ...prev.sector_details, [key]: value } }));

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <a href="/dashboard" className="hover:text-primary transition-colors">
          Dashboard
        </a>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <a href="/deal-pipeline" className="hover:text-primary transition-colors">
          Deal Pipeline
        </a>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-slate-900 dark:text-white font-medium">New Project</span>
      </div>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Create New Investment Project
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Add a new regional investment opportunity to the pipeline.
          </p>
        </div>
        <button
          onClick={() => navigate('/deal-pipeline')}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          Back to Pipeline
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
          <span className="material-symbols-outlined text-red-600 dark:text-red-400">error</span>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 dark:text-red-200">Error</h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm">
        {/* Incubation stage toggle */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: startInIncubation ? '#faf5ff' : undefined,
          gap: 16,
        }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: startInIncubation ? '#7c3aed' : 'var(--ink-900)' }}>
              {startInIncubation ? '⚗ Start in Incubation (Stage 0)' : '✏ Start as Draft'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
              {startInIncubation
                ? 'Project will be hidden from investors until AfCEN score reaches the graduation threshold.'
                : 'Project enters the pipeline immediately as a Draft.'}
            </div>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', flexShrink: 0 }}>
            <span style={{ fontSize: 11, color: 'var(--ink-500)' }}>
              {startInIncubation ? 'On' : 'Off'}
            </span>
            <input
              type="checkbox"
              checked={startInIncubation}
              onChange={e => setStartInIncubation(e.target.checked)}
              style={{ width: 16, height: 16, cursor: 'pointer', accentColor: '#7c3aed' }}
            />
          </label>
        </div>
        <div className="p-6 space-y-6">
          {/* Project Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Project Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="e.g., West African Rail Link"
            />
          </div>

          {/* Pillar */}
          <div>
            <label htmlFor="pillar" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Investment Pillar <span className="text-red-500">*</span>
            </label>
            <select
              id="pillar"
              required
              value={formData.pillar}
              onChange={(e) => handlePillarChange(e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {pillars.map((p) => (
                <option key={p.value} value={p.value}>{p.value}</option>
              ))}
            </select>
          </div>

          {/* Lead Country & Company Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="leadCountry" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Lead Country <span className="text-red-500">*</span>
              </label>
              <select
                id="leadCountry"
                required
                value={formData.leadCountry}
                onChange={(e) => setFormData({ ...formData, leadCountry: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Select a country...</option>
                {ecowasCountries.map((country) => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="leadCompany" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Lead Company <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="leadCompany"
                required
                value={formData.leadCompany}
                onChange={(e) => setFormData({ ...formData, leadCompany: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., RailCo Ltd."
              />
            </div>
          </div>

          {/* Subsector, Project Sponsor & Cross-Border Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="subsector" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Subsector
              </label>
              <input
                type="text"
                id="subsector"
                value={formData.subsector}
                onChange={(e) => setFormData({ ...formData, subsector: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., Renewable Energy"
              />
            </div>

            <div>
              <label htmlFor="projectSponsor" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Project Sponsor
              </label>
              <input
                type="text"
                id="projectSponsor"
                value={formData.projectSponsor}
                onChange={(e) => setFormData({ ...formData, projectSponsor: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., Ministry of Energy"
              />
            </div>
          </div>

          {/* Cross-Border Toggle */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="isCrossBorder"
              checked={formData.isCrossBorder}
              onChange={(e) => setFormData({ ...formData, isCrossBorder: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary"
            />
            <label htmlFor="isCrossBorder" className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Cross-Border Project
            </label>
            <p className="text-xs text-slate-500 dark:text-slate-400">Check if this project spans multiple countries</p>
          </div>

          {/* Value Chain Stages — Agribusiness only */}
          {activeSector?.legacyAgri && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Value Chain Stage
                </label>
                <div className="flex gap-2 flex-wrap">
                  {VALUE_CHAIN_STAGES.map(({ code, label }) => {
                    const selected = formData.value_chain_stages.includes(code);
                    return (
                      <button
                        key={code}
                        type="button"
                        onClick={() => {
                          setFormData(prev => ({
                            ...prev,
                            value_chain_stages: selected
                              ? prev.value_chain_stages.filter(s => s !== code)
                              : [...prev.value_chain_stages, code],
                          }));
                        }}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                          selected
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600'
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Select all stages this project operates in. At least one is required.</p>
              </div>
            </>
          )}

          {/* Sector-specific bespoke fields — non-agri sectors */}
          {activeSector && !activeSector.legacyAgri && activeSector.fields.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 10 }}>
                {activeSector.label} details
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
                {activeSector.fields.map((f: FieldDef) => (
                  <div key={f.key}>
                    <label style={{ display: 'block', fontSize: 12, color: 'var(--ink-600)', marginBottom: 4 }}>
                      {f.label}{f.optional ? ' (optional)' : ''}
                    </label>
                    {f.type === 'text' && (
                      <input
                        value={formData.sector_details[f.key] ?? ''}
                        onChange={e => setSectorField(f.key, e.target.value)}
                        style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none', boxSizing: 'border-box' }}
                      />
                    )}
                    {f.type === 'number' && (
                      <input
                        type="number"
                        value={formData.sector_details[f.key] ?? ''}
                        onChange={e => setSectorField(f.key, e.target.value === '' ? null : Number(e.target.value))}
                        style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none', boxSizing: 'border-box' }}
                      />
                    )}
                    {f.type === 'select' && (
                      <select
                        value={formData.sector_details[f.key] ?? ''}
                        onChange={e => setSectorField(f.key, e.target.value || null)}
                        style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none', cursor: 'pointer' }}
                      >
                        <option value="">Select…</option>
                        {f.options!.map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    )}
                    {f.type === 'multiselect' && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {f.options!.map(o => {
                          const sel: string[] = formData.sector_details[f.key] ?? [];
                          const on = sel.includes(o);
                          return (
                            <button
                              type="button"
                              key={o}
                              onClick={() => setSectorField(f.key, on ? sel.filter(x => x !== o) : [...sel, o])}
                              style={{
                                padding: '5px 10px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
                                background: on ? 'var(--accent)' : 'transparent',
                                border: `1px solid ${on ? 'var(--accent)' : 'var(--border)'}`,
                                color: on ? 'var(--accent-ink)' : 'var(--ink-700)',
                              }}
                            >{o}</button>
                          );
                        })}
                      </div>
                    )}
                    {f.type === 'toggle' && (
                      <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--ink-700)', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={!!formData.sector_details[f.key]}
                          onChange={e => setSectorField(f.key, e.target.checked)}
                          style={{ accentColor: 'var(--accent)' }}
                        />
                        Yes
                      </label>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gender-intentional design toggle */}
          <div className="flex flex-col gap-1.5">
            <label className="flex items-center gap-1 text-xs font-medium text-slate-700 dark:text-slate-300">
              Gender-Intentional Design
              <InfoTooltip
                ariaLabel="What counts as gender-intentional design?"
                text={
                  <span>
                    Choose <strong>Yes</strong> if the project explicitly: targets women-led businesses
                    or women as key beneficiaries; sets a measurable women-employment or women-ownership
                    target of <strong>at least 30%</strong>; or adopts a gender action plan as part of
                    project design.<br /><br />
                    Choose <strong>No</strong> if gender outcomes are incidental rather than designed in.
                  </span>
                }
              />
            </label>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, gender_intentional: true }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  formData.gender_intentional === true
                    ? 'bg-green-600 text-white border-green-600'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-green-400'
                }`}
              >Yes</button>
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, gender_intentional: false }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  formData.gender_intentional === false
                    ? 'bg-slate-600 text-white border-slate-600'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-slate-400'
                }`}
              >No</button>
            </div>
            {formData.gender_intentional === true && (
              <textarea
                rows={2}
                placeholder="Describe how this project is intentionally designed to benefit women (ownership, leadership, beneficiaries)..."
                value={formData.gender_justification ?? ''}
                onChange={e => setFormData(prev => ({ ...prev, gender_justification: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            )}
          </div>

          {/* Youth-focused toggle */}
          <div className="flex flex-col gap-1.5">
            <label className="flex items-center gap-1 text-xs font-medium text-slate-700 dark:text-slate-300">
              Youth Employment Focus
              <InfoTooltip
                ariaLabel="What counts as youth employment focus?"
                text={
                  <span>
                    Choose <strong>Yes</strong> if the project explicitly: targets under-35s as
                    <strong> at least 30%</strong> of jobs created; includes a youth training,
                    aggregator, or kiosk programme; or has a dedicated youth entrepreneurship
                    pipeline.<br /><br />
                    Choose <strong>No</strong> if youth outcomes are incidental.
                  </span>
                }
              />
            </label>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, youth_focused: true }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  formData.youth_focused === true
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-blue-400'
                }`}
              >Yes</button>
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, youth_focused: false }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  formData.youth_focused === false
                    ? 'bg-slate-600 text-white border-slate-600'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-blue-400'
                }`}
              >No</button>
            </div>
            {formData.youth_focused === true && (
              <textarea
                rows={2}
                placeholder="Describe the youth employment focus (target age group, jobs created for under-35s, youth ownership)..."
                value={formData.youth_justification ?? ''}
                onChange={e => setFormData(prev => ({ ...prev, youth_justification: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            )}
          </div>

          {/* Investment Amount */}
          <div>
            <label htmlFor="investment" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Investment Amount <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">$</span>
              <input
                type="text"
                id="investment"
                required
                value={formData.investment}
                onChange={(e) => setFormData({ ...formData, investment: e.target.value })}
                className="w-full pl-8 pr-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., 1.2B or 450M"
              />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Use 'M' for millions or 'B' for billions (e.g., 1.2B, 450M)
            </p>
          </div>

          {/* Funding Structure (optional) */}
          <div>
            <label htmlFor="financingStructure" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Funding Structure <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <textarea
              id="financingStructure"
              rows={2}
              value={formData.financing_structure}
              onChange={(e) => setFormData({ ...formData, financing_structure: e.target.value })}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
              placeholder="e.g., 60% commercial debt + 40% concessional from DFIs; PPP with sovereign guarantee"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              If known, note the intended capital mix. You can leave this blank and add it later.
            </p>
          </div>

          {/* Land Status & Revenue Model */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="landStatus" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Land Status
              </label>
              <select
                id="landStatus"
                value={formData.landStatus}
                onChange={(e) => setFormData({ ...formData, landStatus: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Select land status...</option>
                <option value="Secured">Secured</option>
                <option value="In Progress">In Progress</option>
                <option value="Not Started">Not Started</option>
              </select>
            </div>

            <div>
              <label htmlFor="revenueModel" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Revenue Model
              </label>
              <textarea
                id="revenueModel"
                rows={2}
                value={formData.revenueModel}
                onChange={(e) => setFormData({ ...formData, revenueModel: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                placeholder="Describe the revenue model..."
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Project Description <span className="text-red-500">*</span>
            </label>
            <textarea
              id="description"
              required
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
              placeholder="Provide a detailed description of the investment project..."
            />
          </div>

          {/* Site location — R8 */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Site location <span className="text-xs text-slate-500 font-normal">(used for satellite NDVI / water / EUDR analysis — can be added later)</span>
            </label>
            <SiteLocationPicker
              value={{
                lat: formData.site_lat,
                lon: formData.site_lon,
                name: formData.site_location_name,
              }}
              onChange={(next) => setFormData(prev => ({
                ...prev,
                site_lat: next.lat,
                site_lon: next.lon,
                site_location_name: next.name,
              }))}
            />
          </div>

          {/* Readiness, Impact & Economics — drives AfCEN score */}
          <div className="border-t border-slate-200 dark:border-slate-700 pt-6">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-1">
              Readiness, Impact &amp; Economics
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              These fields directly drive your AfCEN readiness &amp; bankability score and move the project up the Deal Room continuum. Please complete what you can — leave blank only if genuinely unknown.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="technicalStudies" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Technical / Feasibility Studies
                </label>
                <textarea
                  id="technicalStudies"
                  rows={2}
                  value={formData.technicalStudies}
                  onChange={(e) => setFormData({ ...formData, technicalStudies: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                  placeholder="e.g., feasibility study complete; ESIA underway; pre-FEED done"
                />
              </div>
              <div>
                <label htmlFor="permitsLicences" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Permits &amp; Licences
                </label>
                <textarea
                  id="permitsLicences"
                  rows={2}
                  value={formData.permitsLicences}
                  onChange={(e) => setFormData({ ...formData, permitsLicences: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                  placeholder="e.g., mining licence granted; generation licence pending"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              <div>
                <label htmlFor="jobsConstruction" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Jobs — Construction
                </label>
                <input
                  id="jobsConstruction"
                  type="text"
                  value={formData.jobsConstruction}
                  onChange={(e) => setFormData({ ...formData, jobsConstruction: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="e.g., 500 (temporary)"
                />
              </div>
              <div>
                <label htmlFor="jobsOm" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Jobs — O&amp;M (ongoing)
                </label>
                <input
                  id="jobsOm"
                  type="text"
                  value={formData.jobsOm}
                  onChange={(e) => setFormData({ ...formData, jobsOm: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="e.g., 120 (permanent)"
                />
              </div>
              <div>
                <label htmlFor="smallholderFarmersReached" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Smallholder farmers reached
                </label>
                <input
                  id="smallholderFarmersReached"
                  type="text"
                  value={formData.smallholderFarmersReached}
                  onChange={(e) => setFormData({ ...formData, smallholderFarmersReached: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="e.g., 5,000 (if applicable)"
                />
              </div>
            </div>
            <div className="mt-4">
              <label htmlFor="macroeconomicRoi" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Macroeconomic ROI
              </label>
              <input
                id="macroeconomicRoi"
                type="text"
                value={formData.macroeconomicRoi}
                onChange={(e) => setFormData({ ...formData, macroeconomicRoi: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., USD 2.40 of GDP per USD 1 invested"
              />
            </div>
          </div>

          {/* Climate & ESG Section */}
          <div className="border-t border-slate-200 dark:border-slate-700 pt-6">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-4">
              Climate & ESG
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="climateImpact" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  Climate Impact
                </label>
                <textarea
                  id="climateImpact"
                  rows={3}
                  value={formData.climateImpact}
                  onChange={(e) => setFormData({ ...formData, climateImpact: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                  placeholder="Describe the project's climate impact..."
                />
              </div>

              <div>
                <label htmlFor="esgCompliance" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                  ESG Compliance
                </label>
                <textarea
                  id="esgCompliance"
                  rows={3}
                  value={formData.esgCompliance}
                  onChange={(e) => setFormData({ ...formData, esgCompliance: e.target.value })}
                  className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                  placeholder="Describe ESG compliance measures..."
                />
              </div>
            </div>
            <div className="mt-4">
              <label htmlFor="ghgAvoidedTarget" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                GHG Emissions Avoided (target)
              </label>
              <input
                id="ghgAvoidedTarget"
                type="text"
                value={formData.ghgAvoidedTarget}
                onChange={(e) => setFormData({ ...formData, ghgAvoidedTarget: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., 120,000 tCO2e/year"
              />
            </div>
          </div>

          {/* Document Upload */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Supporting Documents
            </label>
            <div className="space-y-3">
              {/* Upload Area */}
              <div className="relative">
                <input
                  type="file"
                  id="documents"
                  multiple
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg p-6 text-center hover:border-primary dark:hover:border-primary transition-colors cursor-pointer">
                  <span className="material-symbols-outlined text-4xl text-slate-400 dark:text-slate-500 mb-2">
                    upload_file
                  </span>
                  <p className="text-sm text-slate-600 dark:text-slate-300 font-medium">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    PDF, DOC, XLS, PPT files up to 10MB
                  </p>
                </div>
              </div>

              {/* Uploaded Files List */}
              {uploadedFiles.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    Uploaded Files ({uploadedFiles.length})
                  </p>
                  {uploadedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <span className="material-symbols-outlined text-primary">
                          description
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                            {file.name}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {(file.size / 1024).toFixed(2)} KB
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="ml-2 p-1 text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                      >
                        <span className="material-symbols-outlined text-[20px]">close</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Upload investment memos, feasibility studies, or other supporting documents
            </p>
          </div>
        </div>

        {/* Form Actions */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700 rounded-b-xl flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/deal-pipeline')}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => {
                // Save as draft logic
                alert('Save as draft functionality coming soon!');
              }}
              className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              Save as Draft
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-bold shadow-md shadow-primary/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Creating...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[20px]">add</span>
                  Create Project
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Bottom spacing */}
      <div className="h-10"></div>
    </div>
  );
};

export default NewProject;
