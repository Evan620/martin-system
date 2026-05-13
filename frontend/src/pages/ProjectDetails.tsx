import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { documentService, Document } from '../services/documentService';
import { Project, InvestorMatch, InvestorMatchStatus, ProjectScoreDetail, ProjectStatus } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { ProjectLifecycleTimeline } from '../components/pipeline/ProjectLifecycleTimeline';
import { ProjectHistoryTimeline } from '../components/pipeline/ProjectHistoryTimeline';
import { UserRole } from '../types/auth';
import api from '../services/api';

const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'financials' | 'documents' | 'history' | 'matches'>('overview');
  const [project, setProject] = useState<Project | null>(null);
  const [matches, setMatches] = useState<InvestorMatch[]>([]);
  const [scoreDetails, setScoreDetails] = useState<ProjectScoreDetail[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [triggeringMatch, setTriggeringMatch] = useState(false);
  const [togglingFlagship, setTogglingFlagship] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('feasibility_study');
  const [rescoring, setRescoring] = useState(false);

  // RBAC - Must be at top level before any returns
  const { user } = useAppSelector((state) => state.auth);
  const canEdit = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR].includes(user.role);

  // AI Insight State
  const [aiInsight, setAiInsight] = useState<string>('');
  const [aiRecommendation, setAiRecommendation] = useState<string>('');
  const [isLoadingInsight, setIsLoadingInsight] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!projectId) return;
      setLoading(true);
      try {
        const data = await pipelineService.getProject(projectId);
        setProject(data);

        // Fetch parallel data
        fetchMatches(projectId);
        fetchScoreDetails(projectId);
        fetchDocuments(projectId);
      } catch (error) {
        console.error("Failed to fetch project", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  const fetchMatches = async (id: string) => {
    setLoadingMatches(true);
    try {
      const matchData = await pipelineService.getMatches(id);
      setMatches(matchData);
    } catch (e) {
      console.error("Failed to load matches", e);
    } finally {
      setLoadingMatches(false);
    }
  };

  const fetchScoreDetails = async (id: string) => {
    try {
      const details = await pipelineService.getScoreDetails(id);
      setScoreDetails(details);
    } catch (e) {
      console.error("Failed to load score details", e);
    }
  };

  const fetchDocuments = async (id: string) => {
    try {
      // documentService now supports projectId filter
      const response = await documentService.listDocuments(undefined, 1, 100, id);
      setDocuments(response.data);
    } catch (e) {
      console.error("Failed to load documents", e);
    }
  };

  const handleUploadDocument = async () => {
    if (!selectedFile || !projectId) return;

    setUploadingDoc(true);
    try {
      // Upload document with project_id in metadata
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('is_confidential', 'false');
      formData.append('document_type', documentType);
      formData.append('project_id', projectId);

      await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // Refresh documents list and scores
      await fetchDocuments(projectId);
      await fetchScoreDetails(projectId);

      // Close modal and reset
      setShowUploadModal(false);
      setSelectedFile(null);
      setDocumentType('feasibility_study');

      alert('Document uploaded successfully!');
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload document. Please try again.');
    } finally {
      setUploadingDoc(false);
    }
  };

  const handleDeleteDocument = async (docId: string, fileName: string) => {
    if (!confirm(`Are you sure you want to delete "${fileName}"?`)) return;

    try {
      await documentService.deleteDocument(docId);

      // Refresh documents list and scores
      if (projectId) {
        await fetchDocuments(projectId);
        await fetchScoreDetails(projectId);
      }

      alert('Document deleted successfully!');
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete document. Please try again.');
    }
  };

  const toggleFlagship = async () => {
    if (!project) return;
    setTogglingFlagship(true);
    try {
      const newVal = !project.is_flagship;
      await pipelineService.toggleFlagship(project.id, newVal);
      setProject({ ...project, is_flagship: newVal });
    } catch (e) {
      console.error("Failed toggle", e);
    } finally {
      setTogglingFlagship(false);
    }
  };

  const handleTriggerMatching = async () => {
    if (!project) return;
    setTriggeringMatch(true);
    try {
      await pipelineService.triggerMatching(project.id);
      await fetchMatches(project.id);
      alert("Investor matching triggered successfully!");
    } catch (error: any) {
      let errorMessage = 'Failed to trigger matching. Please try again.';
      if (error.response?.data?.detail) {
        errorMessage = typeof error.response.data.detail === 'string'
          ? error.response.data.detail
          : JSON.stringify(error.response.data.detail);
      } else if (error.message) {
        errorMessage = error.message;
      }
      console.error("Failed to trigger matching", error);
      alert(errorMessage);
    } finally {
      setTriggeringMatch(false);
    }
  };

  const handleUpdateMatchStatus = async (matchId: string, newStatus: InvestorMatchStatus) => {
    try {
      await pipelineService.updateMatchStatus(matchId, { status: newStatus });
      // Optimistic update
      setMatches(prev => prev.map(m => m.match_id === matchId ? { ...m, status: newStatus } : m));
      if (newStatus === InvestorMatchStatus.INTERESTED) {
        alert("Status updated to 'Interested'. Protocol Agent has been notified to schedule a meeting.");
      }
    } catch (error) {
      console.error("Failed to update match status", error);
      alert("Failed to update status.");
    }
  };

  const handleStageTransition = async (newStage: string) => {
    if (!project) return;
    if (!confirm(`Are you sure you want to move this project to ${newStage.replace('_', ' ')}?`)) return;

    try {
      const result = await pipelineService.advanceStage(project.id, newStage as ProjectStatus);
      setProject(result);
      alert(`Project moved to ${newStage.replace('_', ' ')} successfully.`);
    } catch (e: any) {
      console.error("Transition failed", e);
      alert(`Failed to transition: ${e.response?.data?.detail || e.message}`);
    }
  };

  const fetchAIInsights = async () => {
    if (!project) return;
    setIsLoadingInsight(true);

    try {
      // Call the new AI insights API endpoint
      const response = await api.get(`/pipeline/${project.id}/insights`);
      setAiInsight(response.data.insight);
      setAiRecommendation(response.data.recommendation);
    } catch (error) {
      console.error('Failed to fetch AI insights:', error);
      // Fallback to basic insight
      setAiInsight(`Readiness Score is ${project.readiness_score >= 80 ? 'high' : 'moderate'} (${project.readiness_score}/100). AfCEN Score: ${project.afcen_score ? Number(project.afcen_score).toFixed(1) : 'N/A'}`);
      setAiRecommendation('Review pending investor matches in the Deal Room tab.');
    } finally {
      setIsLoadingInsight(false);
    }
  };

  useEffect(() => {
    if (project) fetchAIInsights();
  }, [project]);

  const handleRescore = async () => {
    if (!project) return;
    setRescoring(true);
    try {
      const response = await api.post(`/pipeline/${project.id}/rescore`);
      // Refresh project data to get new score
      const updatedProject = await pipelineService.getProject(project.id);
      setProject(updatedProject);
      await fetchScoreDetails(project.id);
      alert(response.data.message || 'Project rescored successfully!');
    } catch (error: any) {
      console.error('Rescore failed:', error);
      alert(error.response?.data?.detail || 'Failed to rescore project. Please try again.');
    } finally {
      setRescoring(false);
    }
  };


  const getStatusColor = (status: string) => {
    switch (status) {
        case 'CONCEPT':         return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200 border-blue-200 dark:border-blue-800';
        case 'PRE_FEASIBILITY': return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200 border-purple-200 dark:border-purple-800';
        case 'FEASIBILITY':     return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800';
        case 'BANKABLE':        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200 border-green-200 dark:border-green-800';
        case 'SUMMIT_FEATURED': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200 border-orange-200 dark:border-orange-800';
        case 'IN_NEGOTIATION':  return 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-200 border-pink-200 dark:border-pink-800';
        case 'COMMITTED':       return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800';
        case 'DECLINED':        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200 border-red-200 dark:border-red-800';
        case 'NEEDS_REVISION':  return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200 border-amber-200 dark:border-amber-800';
        default:                return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700';
    }
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-primary';
    return 'bg-orange-500';
  };

  const formatCurrency = (amount?: number) => {
    if (!amount) return 'N/A';
    if (amount >= 1000000000) return `$${(amount / 1000000000).toFixed(1)}B`;
    if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  if (loading || !project) {
    return <div className="p-12 text-center">Loading Project...</div>;
  }

  return (
    <div className="max-w-[1200px] mx-auto space-y-6 relative">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <button onClick={() => navigate('/dashboard')} className="hover:text-primary transition-colors">
          Home
        </button>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <button onClick={() => navigate('/deal-pipeline')} className="hover:text-primary transition-colors">
          Deal Pipeline
        </button>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-slate-900 dark:text-white font-medium">{project.name}</span>
      </div>

      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-start gap-3">
        <div className="flex flex-col gap-2 min-w-72">
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white leading-tight tracking-tight">
              {project.name}
            </h1>
            <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider border ${getStatusColor(project.status)}`}>
              {project.status.replace('_', ' ')}
            </span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Project ID: {project.id} • Lead: {project.lead_country || 'Regional'} •{' '}
            <span className="inline-flex items-center gap-1 font-medium text-primary">
              <span className="material-symbols-outlined text-[16px]">smart_toy</span>
              AI Agent
            </span>
          </p>
        </div>
        <div className="flex gap-3">
          {canEdit && (
            <>
              <button
                onClick={toggleFlagship}
                disabled={togglingFlagship}
                className={`flex items-center justify-center gap-2 px-4 py-2 border text-sm font-bold rounded-lg transition-colors ${project.is_flagship
                  ? 'bg-amber-100 border-amber-300 text-amber-800 hover:bg-amber-200'
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
              >
                <span className="material-symbols-outlined text-[18px]">
                  {project.is_flagship ? 'star' : 'star_outline'}
                </span>
                <span>{project.is_flagship ? 'Flagship Project' : 'Mark as Flagship'}</span>
              </button>

              <button
                onClick={() => navigate(`/deal-pipeline/${project.id}/edit`)}
                className="flex items-center justify-center px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                <span>Edit Project</span>
              </button>

              {/* Transition Actions */}
              {project.allowed_transitions && project.allowed_transitions.length > 0 && (
                <div className="relative group">
                  <button className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-lg hover:bg-blue-700 transition-colors">
                    <span>Advance Stage</span>
                    <span className="material-symbols-outlined text-[18px]">expand_more</span>
                  </button>
                  <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 p-1 z-50 hidden group-hover:block">
                    {project.allowed_transitions.map(stage => (
                      <button
                        key={stage}
                        onClick={() => handleStageTransition(stage)}
                        className="w-full text-left px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-md capitalize"
                      >
                        Move to {stage.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          <button
            onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(project.id)}/memo`)}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg shadow-md hover:bg-blue-700 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
            <span>Generate Memo</span>
          </button>
        </div>
      </div>


      {/* Lifecycle Timeline */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <ProjectLifecycleTimeline project={project} />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Funding Ask */}
        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex justify-between items-start">
            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Investment Size</p>
            <span className="material-symbols-outlined text-slate-400">payments</span>
          </div>
          <p className="text-slate-900 dark:text-white text-2xl font-bold">
            {formatCurrency(project.investment_size)} <span className="text-base font-medium text-slate-400">USD</span>
          </p>
          <p className="text-emerald-600 dark:text-emerald-400 text-xs font-bold bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 rounded w-fit">
            Estimated
          </p>
        </div>

        {/* Readiness Score */}
        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
            <span className="material-symbols-outlined text-6xl text-primary">speed</span>
          </div>
          <div className="flex justify-between items-start z-10">
            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Readiness Score</p>
            <span className="material-symbols-outlined text-primary">check_circle</span>
          </div>
          <p className="text-slate-900 dark:text-white text-2xl font-bold">
            {project.readiness_score}
            <span className="text-slate-400 text-lg">/100</span>
          </p>
          <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 mt-2">
            <div
              className={`${getProgressColor(project.readiness_score)} h-1.5 rounded-full`}
              style={{ width: `${project.readiness_score}%` }}
            ></div>
          </div>
        </div>

        {/* AfCEN Score (New) */}
        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex justify-between items-start">
            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">AfCEN Score</p>
            <span className="material-symbols-outlined text-purple-400">stars</span>
          </div>
          <p className="text-slate-900 dark:text-white text-2xl font-bold">{project.afcen_score ? Number(project.afcen_score).toFixed(1) : 'N/A'}</p>
          <button
            onClick={handleRescore}
            disabled={rescoring}
            className="mt-2 w-full py-1.5 bg-purple-50 hover:bg-purple-100 dark:bg-purple-900/20 dark:hover:bg-purple-900/40 text-purple-600 dark:text-purple-400 text-xs font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1"
            title="Manually trigger AfCEN scoring assessment"
          >
            <span className="material-symbols-outlined text-[14px]">{rescoring ? 'hourglass_empty' : 'refresh'}</span>
            {rescoring ? 'Scoring...' : 'Rescore Project'}
          </button>
        </div>

        {/* Pillar */}
        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex justify-between items-start">
            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Pillar</p>
            <span className="material-symbols-outlined text-slate-400">category</span>
          </div>
          <p className="text-slate-900 dark:text-white text-xl font-bold truncate" title={project.pillar}>
            {project.pillar || 'General'}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="sticky top-[72px] bg-background-light dark:bg-background-dark z-40 pt-2 pb-0 mb-6">
        <div className="flex border-b border-slate-200 dark:border-slate-700 gap-8 overflow-x-auto">
          {['overview', 'matches', 'financials', 'documents', 'history'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`flex items-center justify-center border-b-[3px] pb-3 pt-2 min-w-fit transition-colors capitalize ${activeTab === tab
                ? 'border-primary text-slate-900 dark:text-white'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
            >
              <span className="text-sm font-bold">
                {tab === 'matches' ? 'Deal Room / Investors' : tab}
              </span>
              {tab === 'matches' && matches.length > 0 && (
                <span className="ml-2 bg-primary text-white text-[10px] px-1.5 py-0.5 rounded-full">
                  {matches.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-12">
        {/* Left Column (Primary Content) */}
        <div className="lg:col-span-2 flex flex-col gap-6">

          {/* Overview Tab Content */}
          {activeTab === 'overview' && (
            <>
              {/* Executive Summary */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Description</h3>
                <div className="prose prose-slate dark:prose-invert max-w-none text-slate-600 dark:text-slate-300">
                  <p className="mb-4">{project.description || 'No description provided.'}</p>
                </div>
              </div>

              {/* Investment Template — Full Sections A–D */}
              <div className="space-y-4">

                {/* Section A — Basic Project Information */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-xs font-bold px-2 py-0.5 rounded">Section A</span>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">Basic Project Information</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
                    {project.lead_country && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Country / Host State</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.lead_country}</p>
                      </div>
                    )}
                    <div>
                      <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Regional Dimension</span>
                      <p className="text-slate-900 dark:text-white mt-1">{project.is_cross_border ? 'Cross-border' : 'National'}</p>
                    </div>
                    {project.subsector && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Subsector</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.subsector}</p>
                      </div>
                    )}
                    {project.project_sponsor && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Project Sponsor</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.project_sponsor}</p>
                      </div>
                    )}
                    {project.key_contact_name && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Key Contact</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.key_contact_name}</p>
                      </div>
                    )}
                    {project.key_contact_email && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Contact Email</span>
                        <p className="text-slate-900 dark:text-white mt-1">
                          <a href={`mailto:${project.key_contact_email}`} className="text-blue-600 dark:text-blue-400 hover:underline">{project.key_contact_email}</a>
                        </p>
                      </div>
                    )}
                    {project.submitted_by && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Submitted By</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.submitted_by}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Section B — Project Development Status */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300 text-xs font-bold px-2 py-0.5 rounded">Section B</span>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">Project Development Status</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
                    {project.technical_studies && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Technical Studies</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.technical_studies}</p>
                      </div>
                    )}
                    {project.permits_licences && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Permits & Licences</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.permits_licences}</p>
                      </div>
                    )}
                    {project.land_status && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Land Status</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.land_status}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Section C — Investment Profile */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs font-bold px-2 py-0.5 rounded">Section C</span>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">Investment Profile</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
                    {project.financing_structure && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Financing Structure</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.financing_structure}</p>
                      </div>
                    )}
                    {project.investment_stage_label && (
                      <div>
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Investment Stage</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.investment_stage_label}</p>
                      </div>
                    )}
                    {project.revenue_model && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Revenue Model</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.revenue_model}</p>
                      </div>
                    )}
                    {project.macroeconomic_roi && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Macroeconomic ROI</span>
                        <p className="text-slate-900 dark:text-white mt-1">{project.macroeconomic_roi}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Section D — Climate & Social Impact */}
                {(project.climate_impact || project.esg_compliance || project.ghg_avoided_target || project.jobs_construction || project.jobs_om || project.smallholder_farmers_reached || project.electricity_connections || project.digital_connections) && (
                  <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 text-xs font-bold px-2 py-0.5 rounded">Section D</span>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white">Climate & Social Impact</h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
                      {project.climate_impact && (
                        <div className="md:col-span-2">
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Climate & ESG Notes</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.climate_impact}</p>
                        </div>
                      )}
                      {project.ghg_avoided_target && (
                        <div>
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">GHG Avoided (tCO₂e)</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.ghg_avoided_target}</p>
                        </div>
                      )}
                      {project.jobs_construction && (
                        <div>
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Jobs — Construction</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.jobs_construction}</p>
                        </div>
                      )}
                      {project.jobs_om && (
                        <div>
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Jobs — O&M (ongoing)</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.jobs_om}</p>
                        </div>
                      )}
                      {project.smallholder_farmers_reached && (
                        <div>
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Smallholder Farmers Reached</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.smallholder_farmers_reached}</p>
                        </div>
                      )}
                      {project.electricity_connections && (
                        <div>
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">New Electricity Connections</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.electricity_connections}</p>
                        </div>
                      )}
                      {project.digital_connections && (
                        <div>
                          <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide text-xs">Digital Connections / SMEs</span>
                          <p className="text-slate-900 dark:text-white mt-1">{project.digital_connections}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

              </div>

              {/* Data for Strategic Rationale */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
                  Scores Breakdown
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Strategic Alignment */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3">Strategic Fit</h4>
                    <div className="space-y-3">
                      {scoreDetails.filter(d => d.criterion.criterion_type === 'strategic_fit').map(d => (
                        <div key={d.id} className="flex justify-between items-center text-sm">
                          <span className="text-slate-600 dark:text-slate-400">{d.criterion.criterion_name}</span>
                          <span className="font-bold text-slate-900 dark:text-white">{d.score}/10</span>
                        </div>
                      ))}
                      {scoreDetails.filter(d => d.criterion.criterion_type === 'strategic_fit').length === 0 && (
                        <div className="text-xs text-slate-400 italic">No details available.</div>
                      )}
                    </div>
                  </div>

                  {/* Readiness */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3">Readiness Factors</h4>
                    <div className="space-y-3">
                      {scoreDetails.filter(d => d.criterion.criterion_type === 'readiness').map(d => (
                        <div key={d.id} className="flex justify-between items-center text-sm">
                          <span className="text-slate-600 dark:text-slate-400">{d.criterion.criterion_name}</span>
                          <span className={`font-bold ${d.score >= 5 ? 'text-green-600' : 'text-slate-400'}`}>
                            {d.score >= 5 ? 'Yes' : 'No'}
                          </span>
                        </div>
                      ))}
                      {scoreDetails.filter(d => d.criterion.criterion_type === 'readiness').length === 0 && (
                        <div className="text-xs text-slate-400 italic">No details available. Defaulting to estimated score.</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Matches Tab */}
          {activeTab === 'matches' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">Investor Matching</h3>
                  <button
                    onClick={handleTriggerMatching}
                    disabled={triggeringMatch}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-bold shadow-md hover:bg-primary-hover disabled:opacity-50">
                    <span className="material-symbols-outlined">restart_alt</span>
                    {triggeringMatch ? 'Running Engine...' : 'Run Matching Engine'}
                  </button>
                </div>

                {loadingMatches ? (
                  <div className="text-center py-8 text-slate-500">Loading matches...</div>
                ) : matches.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 bg-slate-50 rounded-lg border border-dashed border-slate-300">
                    <span className="material-symbols-outlined text-4xl mb-2">person_search</span>
                    <p>No investors matched yet. Run the matching engine to find potential investors.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {matches.map((match) => (
                      <div key={match.match_id} className="flex flex-col md:flex-row gap-4 p-4 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-base font-bold text-slate-900 dark:text-white">{match.investor?.name || 'Unknown Investor'}</h4>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${match.status === InvestorMatchStatus.INTERESTED ? 'bg-green-100 text-green-700' :
                              match.status === InvestorMatchStatus.CONTACTED ? 'bg-blue-100 text-blue-700' :
                                'bg-slate-100 text-slate-600'
                              }`}>
                              {match.status}
                            </span>
                          </div>
                          <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                            {/* Use sector preferences or investment instruments */}
                            {match.investor?.sector_preferences?.join(', ') || 'No specific strategy'}
                          </p>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            <span className="font-medium">Ticket:</span> {match.investor?.ticket_size_min ? `$${match.investor.ticket_size_min}M - $${match.investor.ticket_size_max}M` : 'N/A'}
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            <span className="font-medium">Focus:</span> {match.investor?.geographic_focus?.join(', ') || 'N/A'}
                          </div>
                        </div>

                        <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-4 min-w-[140px]">
                          <div className="text-right">
                            <div className="text-2xl font-bold text-primary">{Math.round(match.score)}%</div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Match Score</div>
                          </div>

                          <div className="relative group">
                            <select
                              value={match.status}
                              onChange={(e) => handleUpdateMatchStatus(match.match_id, e.target.value as InvestorMatchStatus)}
                              className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-xs font-bold py-2 pl-3 pr-8 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 cursor-pointer hover:bg-slate-50"
                            >
                              <option value={InvestorMatchStatus.DETECTED}>Detected</option>
                              <option value={InvestorMatchStatus.CONTACTED}>Contacted</option>
                              <option value={InvestorMatchStatus.INTERESTED}>Interested</option>
                              <option value={InvestorMatchStatus.COMMITTED}>Committed</option>
                              <option value={InvestorMatchStatus.DECLINED}>Declined</option>
                            </select>
                            <span className="material-symbols-outlined absolute right-2 top-1.5 text-[18px] pointer-events-none text-slate-500">expand_more</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Matches Tab as "Financials" */}
          {activeTab === 'financials' && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm space-y-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Financial Structure</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800">
                  <div className="text-sm text-slate-500 mb-1">Total Investment</div>
                  <div className="text-2xl font-bold text-slate-900 dark:text-white">
                    {formatCurrency(project.investment_size)}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800">
                  <div className="text-sm text-slate-500 mb-1">Funding Secured</div>
                  <div className="text-2xl font-bold text-green-700 dark:text-green-400">
                    {formatCurrency(project.funding_secured_usd)}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {((project.funding_secured_usd || 0) / project.investment_size * 100).toFixed(1)}% of total
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-100 dark:border-orange-800">
                  <div className="text-sm text-slate-500 mb-1">Funding Gap</div>
                  <div className="text-2xl font-bold text-orange-700 dark:text-orange-400">
                    {formatCurrency(project.investment_size - (project.funding_secured_usd || 0))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Project Documents</h3>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">upload_file</span>
                  Upload Document
                </button>
              </div>
              {documents.length === 0 ? (
                <div className="text-center py-8 text-slate-500 italic">No documents found.</div>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-700">
                  {documents.map(doc => (
                    <div key={doc.id} className="py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-slate-400">description</span>
                        <div>
                          <div className="font-medium text-slate-900 dark:text-white text-sm">{doc.file_name}</div>
                          <div className="text-xs text-slate-500">{new Date(doc.created_at).toLocaleDateString()}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => documentService.downloadDocument(doc.id)}
                          className="text-slate-400 hover:text-primary"
                          title="Download"
                        >
                          <span className="material-symbols-outlined text-[20px]">download</span>
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(doc.id, doc.file_name)}
                          className="text-slate-400 hover:text-red-600"
                          title="Delete"
                        >
                          <span className="material-symbols-outlined text-[20px]">delete</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
              <ProjectHistoryTimeline projectId={projectId!} />
            </div>
          )}

        </div>

        {/* Right Column (Sidebar) */}
        <div className="flex flex-col gap-6">
          {/* AI Insight Card */}
          <div className="rounded-xl p-5 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/40 dark:to-indigo-950/20 border border-blue-100 dark:border-blue-900 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 opacity-10">
              <span className="material-symbols-outlined text-6xl text-primary">psychology</span>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-primary">auto_awesome</span>
              <h4 className="text-sm font-bold text-primary">AI Agent Insight</h4>
            </div>
            {isLoadingInsight ? (
              <div className="flex flex-col items-center justify-center py-4">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-2"></div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Analyzing project...</p>
              </div>
            ) : (
              <>
                <p className="text-sm text-slate-700 dark:text-slate-300 mb-3 font-medium">
                  {aiInsight || 'No insights available yet.'}
                </p>
                <div className="bg-white/60 dark:bg-black/20 rounded-lg p-3 text-xs text-slate-600 dark:text-slate-400 backdrop-blur-sm border border-white/50 dark:border-white/10">
                  <strong>Recommendation:</strong> {aiRecommendation || 'Review matches.'}
                </div>
              </>
            )}
            <button
              onClick={fetchAIInsights}
              disabled={isLoadingInsight}
              className="mt-3 w-full py-2 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[16px]">psychology</span>
              {isLoadingInsight ? 'Analyzing...' : 'Refresh AI Insight'}
            </button>
          </div>
        </div>
      </div>

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Upload Document</h3>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Document Type
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="feasibility_study">Feasibility Study</option>
                  <option value="esia">ESIA Report</option>
                  <option value="financial_model">Financial Model</option>
                  <option value="government_support">Government Support Letter</option>
                  <option value="investment_memo">Investment Memo</option>
                  <option value="technical_spec">Technical Specification</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Select File
                </label>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                  className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-blue-700"
                />
                {selectedFile && (
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                    Selected: {selectedFile.name}
                  </p>
                )}
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUploadDocument}
                  disabled={!selectedFile || uploadingDoc}
                  className="flex-1 px-4 py-2 bg-primary text-white rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploadingDoc ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDetails;
