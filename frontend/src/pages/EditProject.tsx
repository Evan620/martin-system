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
    });

    const pillars = [
        { value: 'Infrastructure', icon: 'train', color: 'blue' },
        { value: 'Energy', icon: 'solar_power', color: 'orange' },
        { value: 'Agribusiness and Food Systems Transformation', icon: 'agriculture', color: 'green' },
        { value: 'Technology', icon: 'computer', color: 'indigo' },
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
                    leadCompany: (project.metadata_json as any)?.leadCompany || '', // Assuming metadata_json type allows this access or use 'any' cast
                    investment: project.currency === 'USD' ? `$${project.investment_size}` : `${project.investment_size}`, // formatting is tricky, better to keep raw
                    description: project.description,
                    currency: project.currency || 'USD',
                    status: project.status,
                    is_flagship: project.is_flagship || false
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
                }
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
