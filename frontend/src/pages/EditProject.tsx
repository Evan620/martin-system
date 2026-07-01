import React, { useState, useEffect } from 'react';
import SiteLocationPicker from '../components/geospatial/SiteLocationPicker';
import { useNavigate, useParams } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';

// R1 — Value chain controlled vocabulary. Order is intentional: upstream → downstream,
// then the three cross-cutting stages (digital, finance, policy) that span multiple
// segments. Keep in sync with backend VALID_VALUE_CHAIN_STAGES.
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

const EditProject: React.FC = () => {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        name: '',
        pillar: 'Infrastructure',
        leadCountry: '',
        leadCompany: '',
        investment: '',
        description: '',
        currency: 'USD',
        status: '',
        is_flagship: false,
        value_chain_stages: [] as string[],
        gender_intentional: undefined as boolean | undefined,
        gender_justification: undefined as string | undefined,
        youth_focused: undefined as boolean | undefined,
        youth_justification: undefined as string | undefined,
        site_lat: null as number | null,
        site_lon: null as number | null,
        site_location_name: '' as string,
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

    useEffect(() => {
        const fetchProject = async () => {
            if (!projectId) return;
            try {
                const project = await pipelineService.getProject(projectId);
                setFormData({
                    name: project.name,
                    pillar: project.pillar || 'Infrastructure',
                    leadCountry: project.lead_country || '',
                    leadCompany: (project.metadata_json as any)?.leadCompany || '',
                    investment: project.currency === 'USD' ? `$${project.investment_size}` : `${project.investment_size}`,
                    description: project.description,
                    currency: project.currency || 'USD',
                    status: project.status,
                    is_flagship: project.is_flagship || false,
                    value_chain_stages: project.value_chain_stages ?? [],
                    gender_intentional: project.gender_intentional ?? undefined,
                    gender_justification: project.gender_justification ?? undefined,
                    youth_focused: project.youth_focused ?? undefined,
                    youth_justification: project.youth_justification ?? undefined,
                    site_lat: project.site_lat ?? null,
                    site_lon: project.site_lon ?? null,
                    site_location_name: project.site_location_name ?? '',
                });

                // Improve investment formatting
                if (project.investment_size >= 1000000000) {
                    setFormData(prev => ({ ...prev, investment: `${project.investment_size / 1000000000}B` }));
                } else if (project.investment_size >= 1000000) {
                    setFormData(prev => ({ ...prev, investment: `${project.investment_size / 1000000}M` }));
                } else {
                    setFormData(prev => ({ ...prev, investment: `${project.investment_size}` }));
                }

            } catch (e) {
                console.error("Failed", e);
                setError("Failed to load project details.");
            } finally {
                setIsLoading(false);
            }
        };
        fetchProject();
    }, [projectId]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!projectId) return;

        setIsSubmitting(true);
        setError(null);

        try {
            // Parse investment amount
            const investmentStr = formData.investment.replace(/[$,]/g, '');
            let investmentAmount = 0;

            if (investmentStr.includes('B')) {
                investmentAmount = parseFloat(investmentStr.replace('B', '')) * 1000000000;
            } else if (investmentStr.includes('M')) {
                investmentAmount = parseFloat(investmentStr.replace('M', '')) * 1000000;
            } else {
                investmentAmount = parseFloat(investmentStr);
            }

            const updateData = {
                name: formData.name,
                description: formData.description,
                investment_size: investmentAmount,
                pillar: formData.pillar,
                lead_country: formData.leadCountry,
                is_flagship: formData.is_flagship,
                metadata_json: {
                    leadCompany: formData.leadCompany
                },
                value_chain_stages: formData.value_chain_stages.length > 0 ? formData.value_chain_stages : undefined,
                gender_intentional: formData.gender_intentional,
                gender_justification: formData.gender_justification,
                youth_focused: formData.youth_focused,
                youth_justification: formData.youth_justification,
                site_lat: formData.site_lat ?? undefined,
                site_lon: formData.site_lon ?? undefined,
                site_location_name: formData.site_location_name || undefined,
            };

            await pipelineService.updateProject(projectId, updateData);

            alert('Project updated successfully!');
            navigate(`/deal-pipeline/${projectId}`);
        } catch (err: any) {
            console.error('Error updating project:', err);
            setError(err.message || 'Failed to update project.');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (isLoading) return <div className="p-8 text-center" style={{ color: 'var(--ink-500)' }}>Loading project...</div>;

    const inputStyle: React.CSSProperties = {
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-ctl)',
        color: 'var(--ink-900)',
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--ink-500)' }}>
                <button onClick={() => navigate('/deal-pipeline')} className="qp-transition" style={{ color: 'var(--ink-500)' }} onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')} onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-500)')}>Deal Pipeline</button>
                <span>&gt;</span>
                <button onClick={() => navigate(`/deal-pipeline/${projectId}`)} className="qp-transition" style={{ color: 'var(--ink-500)' }} onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')} onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-500)')}>{formData.name || 'Project'}</button>
                <span>&gt;</span>
                <span className="font-medium" style={{ color: 'var(--ink-900)' }}>Edit</span>
            </div>

            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold" style={{ color: 'var(--ink-900)' }}>Edit Project</h2>
                <button onClick={() => navigate(`/deal-pipeline/${projectId}`)} className="clickable-scale qp-transition text-sm px-4 py-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-700)' }}>Cancel</button>
            </div>

            {error && <div className="p-4" style={{ background: 'color-mix(in srgb, var(--terra) 12%, transparent)', color: 'var(--terra)', borderRadius: 'var(--radius-ctl)' }}>{error}</div>}

            <form onSubmit={handleSubmit} className="p-6 space-y-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>Project Name</label>
                    <input
                        value={formData.name}
                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-4 py-2"
                        style={inputStyle}
                        required
                    />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>Pillar</label>
                        <select
                            value={formData.pillar}
                            onChange={e => setFormData({ ...formData, pillar: e.target.value })}
                            className="w-full px-4 py-2"
                            style={inputStyle}
                        >
                            {pillars.map(p => <option key={p.value} value={p.value}>{p.value}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>Lead Country</label>
                        <select
                            value={formData.leadCountry}
                            onChange={e => setFormData({ ...formData, leadCountry: e.target.value })}
                            className="w-full px-4 py-2"
                            style={inputStyle}
                        >
                            {ecowasCountries.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>Lead Company</label>
                    <input
                        value={formData.leadCompany}
                        onChange={e => setFormData({ ...formData, leadCompany: e.target.value })}
                        className="w-full px-4 py-2"
                        style={inputStyle}
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>Investment Amount</label>
                    <input
                        value={formData.investment}
                        onChange={e => setFormData({ ...formData, investment: e.target.value })}
                        className="w-full px-4 py-2"
                        style={inputStyle}
                        placeholder="e.g. 1.2B"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>Description</label>
                    <textarea
                        value={formData.description}
                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                        className="w-full px-4 py-2"
                        style={inputStyle}
                        rows={4}
                    />
                </div>

                {/* Site location — R8 */}
                <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>
                        Site location <span className="text-xs font-normal" style={{ color: 'var(--ink-500)' }}>(used for satellite analysis)</span>
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

                {/* Value Chain Stages */}
                <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'var(--ink-700)' }}>
                        Value Chain Stage
                    </label>
                    <div className="flex gap-2 flex-wrap">
                        {VALUE_CHAIN_STAGES.map(({ code, label }) => {
                            const selected = formData.value_chain_stages.includes(code);
                            return (
                                <button
                                    key={code}
                                    type="button"
                                    onClick={() => setFormData(prev => ({
                                        ...prev,
                                        value_chain_stages: selected
                                            ? prev.value_chain_stages.filter(s => s !== code)
                                            : [...prev.value_chain_stages, code],
                                    }))}
                                    className="clickable-scale qp-transition px-3 py-1.5 rounded-full text-xs font-medium"
                                    style={selected
                                        ? { background: 'var(--accent)', color: 'var(--accent-ink)', border: '1px solid var(--accent)' }
                                        : { background: 'var(--surface)', color: 'var(--ink-600)', border: '1px solid var(--border)' }}
                                >
                                    {label}
                                </button>
                            );
                        })}
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'var(--ink-500)' }}>Select all stages this project operates in. At least one is required.</p>
                </div>

                {/* Gender-intentional design toggle */}
                <div className="flex flex-col gap-1.5">
                    <label className="block text-xs font-medium" style={{ color: 'var(--ink-700)' }}>
                        Gender-Intentional Design
                    </label>
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, gender_intentional: true }))}
                            className="clickable-scale qp-transition px-3 py-1.5 rounded-lg text-xs font-medium"
                            style={formData.gender_intentional === true
                                ? { background: 'var(--sage)', color: 'var(--accent-ink)', border: '1px solid var(--sage)' }
                                : { background: 'var(--surface)', color: 'var(--ink-600)', border: '1px solid var(--border)' }}
                        >Yes</button>
                        <button
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, gender_intentional: false }))}
                            className="clickable-scale qp-transition px-3 py-1.5 rounded-lg text-xs font-medium"
                            style={formData.gender_intentional === false
                                ? { background: 'var(--ink-600)', color: 'var(--surface)', border: '1px solid var(--ink-600)' }
                                : { background: 'var(--surface)', color: 'var(--ink-600)', border: '1px solid var(--border)' }}
                        >No</button>
                    </div>
                    {formData.gender_intentional === true && (
                        <textarea
                            rows={2}
                            placeholder="Describe how this project is intentionally designed to benefit women (ownership, leadership, beneficiaries)..."
                            value={formData.gender_justification ?? ''}
                            onChange={e => setFormData(prev => ({ ...prev, gender_justification: e.target.value }))}
                            className="w-full rounded-lg px-3 py-2 text-xs focus:outline-none resize-none"
                            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-900)' }}
                        />
                    )}
                </div>

                {/* Youth-focused toggle */}
                <div className="flex flex-col gap-1.5">
                    <label className="block text-xs font-medium" style={{ color: 'var(--ink-700)' }}>
                        Youth Employment Focus
                    </label>
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, youth_focused: true }))}
                            className="clickable-scale qp-transition px-3 py-1.5 rounded-lg text-xs font-medium"
                            style={formData.youth_focused === true
                                ? { background: 'var(--accent)', color: 'var(--accent-ink)', border: '1px solid var(--accent)' }
                                : { background: 'var(--surface)', color: 'var(--ink-600)', border: '1px solid var(--border)' }}
                        >Yes</button>
                        <button
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, youth_focused: false }))}
                            className="clickable-scale qp-transition px-3 py-1.5 rounded-lg text-xs font-medium"
                            style={formData.youth_focused === false
                                ? { background: 'var(--ink-600)', color: 'var(--surface)', border: '1px solid var(--ink-600)' }
                                : { background: 'var(--surface)', color: 'var(--ink-600)', border: '1px solid var(--border)' }}
                        >No</button>
                    </div>
                    {formData.youth_focused === true && (
                        <textarea
                            rows={2}
                            placeholder="Describe the youth employment focus (target age group, jobs created for under-35s, youth ownership)..."
                            value={formData.youth_justification ?? ''}
                            onChange={e => setFormData(prev => ({ ...prev, youth_justification: e.target.value }))}
                            className="w-full rounded-lg px-3 py-2 text-xs focus:outline-none resize-none"
                            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-900)' }}
                        />
                    )}
                </div>

                <div className="pt-4 flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)' }}>
                    <button type="button" onClick={() => navigate(`/deal-pipeline/${projectId}`)} className="clickable-scale qp-transition px-4 py-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-700)' }}>Cancel</button>
                    <button type="submit" disabled={isSubmitting} className="clickable-scale qp-transition px-6 py-2 disabled:opacity-50" style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}>
                        {isSubmitting ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default EditProject;
