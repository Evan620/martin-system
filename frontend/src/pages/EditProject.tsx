import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';

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
        women_employment_pct: undefined as number | undefined,
        youth_employment_pct: undefined as number | undefined,
        gender_intentional: undefined as boolean | undefined,
        gender_justification: undefined as string | undefined,
        youth_focused: undefined as boolean | undefined,
        youth_justification: undefined as string | undefined,
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
                    women_employment_pct: project.women_employment_pct ?? undefined,
                    youth_employment_pct: project.youth_employment_pct ?? undefined,
                    gender_intentional: project.gender_intentional ?? undefined,
                    gender_justification: project.gender_justification ?? undefined,
                    youth_focused: project.youth_focused ?? undefined,
                    youth_justification: project.youth_justification ?? undefined,
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
                women_employment_pct: formData.women_employment_pct,
                youth_employment_pct: formData.youth_employment_pct,
                gender_intentional: formData.gender_intentional,
                gender_justification: formData.gender_justification,
                youth_focused: formData.youth_focused,
                youth_justification: formData.youth_justification,
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

    if (isLoading) return <div className="p-8 text-center">Loading project...</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <button onClick={() => navigate('/deal-pipeline')} className="hover:text-primary">Deal Pipeline</button>
                <span>&gt;</span>
                <button onClick={() => navigate(`/deal-pipeline/${projectId}`)} className="hover:text-primary">{formData.name || 'Project'}</button>
                <span>&gt;</span>
                <span className="text-slate-900 font-medium">Edit</span>
            </div>

            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Edit Project</h2>
                <button onClick={() => navigate(`/deal-pipeline/${projectId}`)} className="text-sm px-4 py-2 border rounded-lg hover:bg-slate-50">Cancel</button>
            </div>

            {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg">{error}</div>}

            <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 border rounded-xl p-6 space-y-6">
                <div>
                    <label className="block text-sm font-medium mb-2">Project Name</label>
                    <input
                        value={formData.name}
                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600"
                        required
                    />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">Pillar</label>
                        <select
                            value={formData.pillar}
                            onChange={e => setFormData({ ...formData, pillar: e.target.value })}
                            className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600"
                        >
                            {pillars.map(p => <option key={p.value} value={p.value}>{p.value}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-2">Lead Country</label>
                        <select
                            value={formData.leadCountry}
                            onChange={e => setFormData({ ...formData, leadCountry: e.target.value })}
                            className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600"
                        >
                            {ecowasCountries.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">Lead Company</label>
                    <input
                        value={formData.leadCompany}
                        onChange={e => setFormData({ ...formData, leadCompany: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">Investment Amount</label>
                    <input
                        value={formData.investment}
                        onChange={e => setFormData({ ...formData, investment: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600"
                        placeholder="e.g. 1.2B"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-2">Description</label>
                    <textarea
                        value={formData.description}
                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                        className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600"
                        rows={4}
                    />
                </div>

                {/* Value Chain Stages */}
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                        Value Chain Stage
                    </label>
                    <div className="flex gap-2 flex-wrap">
                        {(['INPUTS', 'PRODUCTION', 'PROCESSING', 'LOGISTICS', 'RETAIL'] as const).map(stage => {
                            const selected = formData.value_chain_stages.includes(stage);
                            return (
                                <button
                                    key={stage}
                                    type="button"
                                    onClick={() => setFormData(prev => ({
                                        ...prev,
                                        value_chain_stages: selected
                                            ? prev.value_chain_stages.filter(s => s !== stage)
                                            : [...prev.value_chain_stages, stage],
                                    }))}
                                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                                        selected
                                            ? 'bg-blue-600 text-white border-blue-600'
                                            : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600'
                                    }`}
                                >
                                    {stage.charAt(0) + stage.slice(1).toLowerCase()}
                                </button>
                            );
                        })}
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Select all stages this project operates in.</p>
                </div>

                {/* Gender & Youth Employment */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                            Women Employed (%) <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={formData.women_employment_pct ?? ''}
                            onChange={e => setFormData(prev => ({ ...prev, women_employment_pct: e.target.value ? parseFloat(e.target.value) : undefined }))}
                            placeholder="e.g. 35"
                            className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600 text-sm"
                        />
                        {formData.women_employment_pct !== undefined && formData.women_employment_pct < 30 && (
                            <p className="text-xs text-amber-600 mt-1">
                                Below 30% threshold — project cannot advance to Summit Ready until this is met.
                            </p>
                        )}
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                            Youth Employed (%) <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={formData.youth_employment_pct ?? ''}
                            onChange={e => setFormData(prev => ({ ...prev, youth_employment_pct: e.target.value ? parseFloat(e.target.value) : undefined }))}
                            placeholder="e.g. 28"
                            className="w-full px-4 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600 text-sm"
                        />
                        {formData.youth_employment_pct !== undefined && formData.youth_employment_pct < 25 && (
                            <p className="text-xs text-amber-600 mt-1">
                                Below 25% threshold — project cannot advance to Summit Ready until this is met.
                            </p>
                        )}
                    </div>
                </div>

                {/* Gender-intentional design toggle */}
                <div className="flex flex-col gap-1.5">
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                        Gender-Intentional Design
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
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                        Youth Employment Focus
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

                <div className="pt-4 border-t flex justify-end gap-3">
                    <button type="button" onClick={() => navigate(`/deal-pipeline/${projectId}`)} className="px-4 py-2 border rounded-lg hover:bg-slate-50">Cancel</button>
                    <button type="submit" disabled={isSubmitting} className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                        {isSubmitting ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default EditProject;
