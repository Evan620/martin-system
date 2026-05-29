
import React, { useState, useEffect } from 'react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import Input from '../../components/ui/Input';
import api from '../../services/api';
import ComingSoonOverlay from '../../components/common/ComingSoonOverlay';

// Feature is gated behind the COMING SOON overlay. While gated, skip the
// data fetch/poll so we don't hit the conflicts endpoints (which require a
// live conflicts dataset) and spam the console with errors every 30s.
const FEATURE_ENABLED = false;


interface Conflict {
    id: string;
    conflict_type: string;
    severity: string; // critical, high, medium, low
    description: string;
    agents_involved: string[];
    conflicting_positions: any;
    metadata_json: any;
    status: string;
    detected_at: string;
}

const ProjectConflicts: React.FC = () => {
    const [dependencies, setDependencies] = useState<Conflict[]>([]);
    const [duplicates, setDuplicates] = useState<Conflict[]>([]);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [selectedConflict, setSelectedConflict] = useState<Conflict | null>(null);
    const [resolutionAction, setResolutionAction] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);

    // Form state
    const [formData, setFormData] = useState<any>({});

    const fetchConflicts = async () => {
        try {
            const deps = await api.get('/conflicts/project-dependencies');
            setDependencies(deps.data);
            const dups = await api.get('/conflicts/duplicates');
            setDuplicates(dups.data);
        } catch (error) {
            console.error("Failed to fetch conflicts", error);
        }
    };

    useEffect(() => {
        if (!FEATURE_ENABLED) return; // Don't poll while feature is gated (COMING SOON)
        fetchConflicts();
        const interval = setInterval(fetchConflicts, 30000); // Poll every 30s
        return () => clearInterval(interval);
    }, []);

    const handleResolveClick = (conflict: Conflict) => {
        setSelectedConflict(conflict);
        setFormData({});
        setIsModalVisible(true);
        // Set default action based on type
        if (conflict.conflict_type === 'project_dependency_conflict') {
            setResolutionAction('ADJUST_TIMELINE');
            setFormData({ project_id: conflict.metadata_json?.dependent_project_id || '' });
        } else {
            setResolutionAction('MERGE_PROJECTS');
            // Pre-fill if we have IDs
            if (conflict.metadata_json?.project_a_id && conflict.metadata_json?.project_b_id) {
                setFormData({
                    keep_project_id: conflict.metadata_json.project_a_id,
                    merge_project_id: conflict.metadata_json.project_b_id
                });
            }
        }
    };

    const handleResolutionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedConflict) return;

        setIsLoading(true);
        try {
            await api.post(`/conflicts/${selectedConflict.id}/resolve`, {
                action: resolutionAction,
                ...formData
            });
            setIsModalVisible(false);
            fetchConflicts();
            // Show success notification (could use toast if available, or just console for now)
            console.log("Resolution successful");
        } catch (error) {
            console.error("Failed to resolve", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleInputChange = (field: string, value: any) => {
        setFormData((prev: any) => ({ ...prev, [field]: value }));
    };

    const mapSeverityToVariant = (severity: string): 'danger' | 'warning' | 'info' | 'neutral' => {
        switch (severity.toLowerCase()) {
            case 'critical': return 'danger';
            case 'high': return 'warning';
            case 'medium': return 'info';
            default: return 'neutral';
        }
    };

    return (
        <div className="p-6 space-y-6 relative">
            <ComingSoonOverlay />
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-amber-500">warning</span>
                    Project Conflict Dashboard
                </h1>
                <p className="text-slate-500 dark:text-slate-400">Detecting dependencies and duplicates across TWGs</p>
            </div>

            <div className="space-y-4">
                <h2 className="text-lg font-bold text-slate-800 dark:text-slate-200">Dependency Conflicts</h2>
                {dependencies.length === 0 ? (
                    <div className="bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 p-4 rounded-lg flex items-center gap-2">
                        <span className="material-symbols-outlined">check_circle</span>
                        No dependency conflicts detected
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {dependencies.map(conflict => (
                            <Card key={conflict.id} className="relative border-l-4 border-l-amber-500">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-2">
                                        <Badge variant={mapSeverityToVariant(conflict.severity)} className="uppercase text-xs font-bold">
                                            {conflict.severity}
                                        </Badge>
                                        <h3 className="font-bold text-slate-900 dark:text-white">{conflict.description}</h3>
                                    </div>
                                    <Button size="sm" onClick={() => handleResolveClick(conflict)}>Resolve</Button>
                                </div>

                                <div className="space-y-2 mt-3 text-sm text-slate-600 dark:text-slate-300">
                                    <p><strong className="text-slate-900 dark:text-slate-100">Impact:</strong> {conflict.metadata_json?.estimated_delay_days} days delay estimated.</p>
                                    <p><strong className="text-slate-900 dark:text-slate-100">Reason:</strong> {conflict.metadata_json?.reason}</p>
                                    <div className="flex items-center gap-2 mt-2">
                                        <Badge variant="info">Dependent: {conflict.conflicting_positions.dependent}</Badge>
                                        <span className="material-symbols-outlined text-slate-400">arrow_right_alt</span>
                                        <Badge variant="neutral">Prerequisite: {conflict.conflicting_positions.prerequisite}</Badge>
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}
            </div>

            <div className="space-y-4 pt-6 border-t border-slate-200 dark:border-slate-700">
                <h2 className="text-lg font-bold text-slate-800 dark:text-slate-200">Potential Duplicates</h2>
                {duplicates.length === 0 ? (
                    <div className="bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 p-4 rounded-lg flex items-center gap-2">
                        <span className="material-symbols-outlined">check_circle</span>
                        No duplicate projects detected
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {duplicates.map(conflict => (
                            <Card key={conflict.id} className="relative border-l-4 border-l-red-500">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-2">
                                        <Badge variant={mapSeverityToVariant(conflict.severity)} className="uppercase text-xs font-bold">
                                            {conflict.severity}
                                        </Badge>
                                        <h3 className="font-bold text-slate-900 dark:text-white">{conflict.description}</h3>
                                    </div>
                                    <Button size="sm" onClick={() => handleResolveClick(conflict)}>Resolve</Button>
                                </div>

                                <div className="space-y-2 mt-3">
                                    <p className="text-sm text-slate-600 dark:text-slate-400">
                                        <strong>Similarity Score:</strong> {(conflict.metadata_json?.similarity_score * 100).toFixed(1)}%
                                    </p>
                                    <div className="grid md:grid-cols-2 gap-4">
                                        <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
                                            <strong className="block mb-1 text-slate-700 dark:text-slate-300">Project A</strong>
                                            {conflict.conflicting_positions.project_a}
                                        </div>
                                        <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
                                            <strong className="block mb-1 text-slate-700 dark:text-slate-300">Project B</strong>
                                            {conflict.conflicting_positions.project_b}
                                        </div>
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal */}
            {isModalVisible && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Resolve Conflict</h3>
                            <button onClick={() => setIsModalVisible(false)} className="text-slate-400 hover:text-slate-600">
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>

                        <form onSubmit={handleResolutionSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Action</label>
                                <select
                                    className="input-field w-full rounded-lg border-slate-300 dark:bg-slate-800 dark:border-slate-600"
                                    value={resolutionAction}
                                    onChange={(e) => setResolutionAction(e.target.value)}
                                >
                                    <option value="MERGE_PROJECTS">Merge Projects</option>
                                    <option value="ADJUST_TIMELINE">Adjust Timeline</option>
                                    <option value="DISMISS">Dismiss As False Positive</option>
                                </select>
                            </div>

                            {resolutionAction === 'MERGE_PROJECTS' && (
                                <>
                                    <Input
                                        label="Project to Keep (ID)"
                                        value={formData.keep_project_id || ''}
                                        onChange={(e) => handleInputChange('keep_project_id', e.target.value)}
                                        placeholder="UUID of project to keep"
                                        required
                                    />
                                    <Input
                                        label="Project to Merge/Cancel (ID)"
                                        value={formData.merge_project_id || ''}
                                        onChange={(e) => handleInputChange('merge_project_id', e.target.value)}
                                        placeholder="UUID of project to merge"
                                        required
                                    />
                                </>
                            )}

                            {resolutionAction === 'ADJUST_TIMELINE' && (
                                <>
                                    <Input
                                        label="Project to Update (ID)"
                                        value={formData.project_id || ''}
                                        onChange={(e) => handleInputChange('project_id', e.target.value)}
                                        placeholder="UUID of project"
                                        required
                                    />
                                    <Input
                                        label="New Start Date"
                                        type="date"
                                        value={formData.new_start_date || ''}
                                        onChange={(e) => handleInputChange('new_start_date', e.target.value)}
                                        required
                                    />
                                    <div className="w-full">
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Reason</label>
                                        <textarea
                                            className="input-field w-full rounded-lg border-slate-300 dark:bg-slate-800 dark:border-slate-600 min-h-[80px]"
                                            value={formData.reason || ''}
                                            onChange={(e) => handleInputChange('reason', e.target.value)}
                                        />
                                    </div>
                                </>
                            )}

                            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-700 mt-4">
                                <Button type="button" variant="ghost" onClick={() => setIsModalVisible(false)}>Cancel</Button>
                                <Button type="submit" isLoading={isLoading}>Submit Resolution</Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProjectConflicts;
