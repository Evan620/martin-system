import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { Project, PipelineStats, ProjectStatus } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { UserRole } from '../types/auth';
import DealRoomDashboard from './DealRoomDashboard';
import InvestorDatabase from './InvestorDatabase';

const DealPipeline: React.FC = () => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'pipeline' | 'deal_room' | 'investors'>('pipeline');
  const [activeTab, setActiveTab] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showAIInsight, setShowAIInsight] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importToast, setImportToast] = useState<string | null>(null);
  const [showWeightsModal, setShowWeightsModal] = useState(false);
  const [criteria, setCriteria] = useState<any[]>([]);
  const [weightEdits, setWeightEdits] = useState<Record<string, string>>({});
  const [weightsSaving, setWeightsSaving] = useState(false);
  const [weightsToast, setWeightsToast] = useState<string | null>(null);

  const { user } = useAppSelector((state) => state.auth);
  const canEdit = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR].includes(user.role);
  const canAccessInvestorDB = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD].includes(user.role);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [projectsData, statsData] = await Promise.all([
          pipelineService.listProjects(
            statusFilter !== '' ? (statusFilter as ProjectStatus) : undefined,
            activeTab !== 'all' ? activeTab : undefined
          ),
          pipelineService.getStats()
        ]);
        setProjects(projectsData);
        setStats(statsData);
      } catch (err) {
        console.error('Failed to fetch pipeline data', err);
        setError('Unable to load pipeline data. Please check your connection and try again.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [activeTab, statusFilter]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DRAFT':              return 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300';
      case 'PIPELINE':           return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
      case 'UNDER_REVIEW':       return 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300';
      case 'SUMMIT_READY':       return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
      case 'DEAL_ROOM_FEATURED': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
      case 'IN_NEGOTIATION':     return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300';
      case 'COMMITTED':          return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300';
      case 'IMPLEMENTED':        return 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300';
      case 'DECLINED':           return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
      case 'NEEDS_REVISION':     return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
      case 'ON_HOLD':            return 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300';
      default:                   return 'bg-slate-100 text-slate-800';
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      DRAFT: 'Draft', PIPELINE: 'Pipeline', UNDER_REVIEW: 'Under Review',
      SUMMIT_READY: 'Summit Ready', DEAL_ROOM_FEATURED: 'Deal Room Featured',
      IN_NEGOTIATION: 'In Negotiation', COMMITTED: 'Committed',
      IMPLEMENTED: 'Implemented', DECLINED: 'Declined',
      NEEDS_REVISION: 'Needs Revision', ON_HOLD: 'On Hold',
    };
    return labels[status] || status;
  };

  const getPillarIcon = (pillar?: string) => {
    const p = pillar?.toLowerCase() || '';
    if (p.includes('infra')) return 'train';
    if (p.includes('energy')) return 'solar_power';
    if (p.includes('agri')) return 'agriculture';
    if (p.includes('tech') || p.includes('digital')) return 'computer';
    return 'business';
  };

  const getIconColorClasses = (pillar?: string) => {
    const p = pillar?.toLowerCase() || '';
    if (p.includes('infra')) return 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400';
    if (p.includes('energy')) return 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400';
    if (p.includes('agri')) return 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400';
    if (p.includes('tech') || p.includes('digital')) return 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400';
    return 'bg-slate-100 dark:bg-slate-900/30 text-slate-600 dark:text-slate-400';
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-primary';
    return 'bg-yellow-500';
  };

  const formatCurrency = (amount: number) => {
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  const totalPipelineValue = projects.reduce((sum, p) => sum + (Number(p.investment_size) || 0), 0);
  const pendingAIReview = projects.filter(p => p.afcen_score == null).length;

  const handleExport = () => {
    const headers = ['ID', 'Name', 'Pillar', 'Lead Country', 'Investment', 'Readiness Score', 'Status'];
    const csvContent = [
      headers.join(','),
      ...projects.map(p =>
        [p.id, p.name, p.pillar, p.lead_country, p.investment_size, p.afcen_score ?? p.readiness_score, p.status].join(',')
      )
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deal-pipeline-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const handleImportExcel = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx';
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const twgId = (user as any)?.twg_ids?.[0] ?? (user as any)?.assigned_twg_id ?? '';
      try {
        const result = await pipelineService.importFromExcel(file, twgId);
        const count = result?.imported ?? result?.count ?? result?.projects?.length ?? '?';
        setImportToast(`Imported ${count} projects successfully`);
        setTimeout(() => setImportToast(null), 5000);
        const refreshed = await pipelineService.listProjects();
        setProjects(refreshed);
      } catch (err: any) {
        const msg = err?.response?.data?.detail ?? err?.message ?? 'Import failed';
        setImportToast(`Error: ${msg}`);
        setTimeout(() => setImportToast(null), 5000);
      }
    };
    input.click();
  };

  const handleOpenWeights = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const data = await pipelineService.getScoringCriteria();
      setCriteria(data);
      const edits: Record<string, string> = {};
      data.forEach((c: any) => { edits[c.id] = String(c.weight); });
      setWeightEdits(edits);
      setShowWeightsModal(true);
    } catch (err: any) {
      setWeightsToast(`Error loading criteria: ${err?.response?.data?.detail ?? err?.message}`);
      setTimeout(() => setWeightsToast(null), 5000);
    }
  };

  const handleSaveWeights = async () => {
    setWeightsSaving(true);
    try {
      await Promise.all(
        criteria.map((c: any) =>
          pipelineService.updateCriterionWeight(c.id, parseFloat(weightEdits[c.id] ?? c.weight))
        )
      );
      setShowWeightsModal(false);
      setWeightsToast('Weights saved. Rescore projects to apply.');
      setTimeout(() => setWeightsToast(null), 5000);
    } catch (e: any) {
      setWeightsToast(`Error: ${e?.response?.data?.detail ?? e?.message}`);
      setTimeout(() => setWeightsToast(null), 5000);
    } finally {
      setWeightsSaving(false);
    }
  };

  const totalWeight = criteria.reduce((s, c) => s + parseFloat(weightEdits[c.id] ?? c.weight), 0);

  const handleNewProject = () => navigate('/deal-pipeline/new');

  const itemsPerPage = 10;
  const totalPages = Math.ceil(projects.length / itemsPerPage);
  const paginatedProjects = projects.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const vm = viewMode as string;
  if (vm === 'deal_room') return <DealRoomDashboard />;
  if (vm === 'investors' && canAccessInvestorDB) return <InvestorDatabase />;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Import Toast */}
      {importToast && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ${importToast.startsWith('Error') ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
          <span className="material-symbols-outlined text-[20px]">
            {importToast.startsWith('Error') ? 'error' : 'check_circle'}
          </span>
          {importToast}
          <button onClick={() => setImportToast(null)} className="ml-2 opacity-75 hover:opacity-100">
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* Weights Toast */}
      {weightsToast && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${weightsToast.startsWith('Error') ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
          <span className="material-symbols-outlined text-[20px]">{weightsToast.startsWith('Error') ? 'error' : 'check_circle'}</span>
          {weightsToast}
          <button onClick={() => setWeightsToast(null)} className="ml-2 opacity-75 hover:opacity-100">
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* Scoring Weights Modal */}
      {showWeightsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">WAIIS Scoring Weights</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Adjust how each criterion contributes to the AfCEN score. Weights are relative — higher weight = more influence.</p>
              </div>
              <button onClick={() => setShowWeightsModal(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="px-6 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
              {criteria.map((c: any) => {
                const w = parseFloat(weightEdits[c.id] ?? c.weight);
                const pct = totalWeight > 0 ? ((w / totalWeight) * 100).toFixed(1) : '0';
                return (
                  <div key={c.id} className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{c.criterion_name}</div>
                      <div className="text-xs text-slate-400 mt-0.5">{pct}% of AfCEN score</div>
                      <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 mt-1">
                        <div className="bg-primary h-1.5 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                    <input
                      type="number"
                      min="0"
                      max="9.99"
                      step="0.1"
                      value={weightEdits[c.id] ?? c.weight}
                      onChange={e => setWeightEdits(prev => ({ ...prev, [c.id]: e.target.value }))}
                      className="w-20 text-center border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1.5 text-sm font-bold text-slate-900 dark:text-white bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                );
              })}
            </div>
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <span className="text-xs text-slate-400">Total weight: <strong className="text-slate-700 dark:text-slate-200">{totalWeight.toFixed(2)}</strong></span>
              <div className="flex gap-2">
                <button onClick={() => setShowWeightsModal(false)} className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">
                  Cancel
                </button>
                <button onClick={handleSaveWeights} disabled={weightsSaving} className="px-4 py-2 text-sm font-bold text-white bg-primary rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-60">
                  {weightsSaving ? 'Saving...' : 'Save Weights'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <a href="/dashboard" className="hover:text-primary transition-colors">Dashboard</a>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-slate-900 dark:text-white font-medium">Deal Pipeline</span>
      </div>

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Deal Pipeline - Investment Opportunities
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage and evaluate regional investment opportunities.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode tabs */}
          <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setViewMode('pipeline')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'pipeline' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            >
              All Projects
            </button>
            <button
              onClick={() => setViewMode('deal_room')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${'deal_room' === vm ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            >
              Deal Room
            </button>
            {canAccessInvestorDB && (
              <button
                onClick={() => setViewMode('investors')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${'investors' === vm ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Investor DB
              </button>
            )}
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            <span className="material-symbols-outlined text-[20px]">download</span>
            Export
          </button>
          {canEdit && (
            <button
              onClick={handleImportExcel}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
            >
              <span className="material-symbols-outlined text-[20px]">upload_file</span>
              Import from Excel
            </button>
          )}
          {canEdit && (
            <button
              onClick={handleNewProject}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-bold shadow-md shadow-primary/20 transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">add</span>
              New Project
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Pipeline Value</p>
            <span className="material-symbols-outlined text-green-600 bg-green-100 dark:bg-green-900/30 p-1 rounded">trending_up</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {loading ? '—' : formatCurrency(totalPipelineValue)}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mt-1">
            Across {stats?.total_projects ?? projects.length} projects
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">High Readiness Projects</p>
            <span className="material-symbols-outlined text-primary bg-primary/10 dark:bg-primary/20 p-1 rounded">verified</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {loading ? '—' : (stats?.healthy_projects ?? 0)}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mt-1">
            Ready for immediate investment
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Pending AI Review</p>
            <span className="material-symbols-outlined text-purple-600 bg-purple-100 dark:bg-purple-900/30 p-1 rounded">smart_toy</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {loading ? '—' : pendingAIReview}
          </p>
          <p className="text-xs text-purple-600 font-medium mt-1">Awaiting agent analysis</p>
        </div>
      </div>

      {/* AI Insight Widget */}
      {showAIInsight && (
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 border border-indigo-100 dark:border-indigo-800/50 rounded-xl p-4 flex items-start gap-4 shadow-sm relative overflow-hidden">
          <div className="absolute -right-10 -top-10 h-32 w-32 bg-indigo-200 dark:bg-indigo-800 rounded-full blur-3xl opacity-20"></div>
          <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm shrink-0 text-indigo-600 dark:text-indigo-400">
            <span className="material-symbols-outlined">auto_awesome</span>
          </div>
          <div className="flex-1 z-10">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">AfCEN AI Agent Insight</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
              {pendingAIReview > 0
                ? `${pendingAIReview} project${pendingAIReview > 1 ? 's' : ''} ${pendingAIReview > 1 ? 'are' : 'is'} awaiting AfCEN algorithm scoring. Completing financial data submissions could significantly improve overall readiness.`
                : 'All projects have been scored by the AfCEN algorithm. Review individual projects for detailed investment insights.'}
            </p>
          </div>
          <button
            onClick={() => setShowAIInsight(false)}
            className="absolute top-2 right-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 z-10"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* Filters & Toolbar */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-white dark:bg-slate-800 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
        {/* Pillar Tabs */}
        <div className="flex p-1 bg-slate-100 dark:bg-slate-700 rounded-lg w-full sm:w-auto overflow-x-auto">
          {['all', 'infrastructure', 'energy', 'agriculture'].map((tab) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setCurrentPage(1); }}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all whitespace-nowrap capitalize ${
                activeTab === tab
                  ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {tab === 'all' ? 'All Projects' : tab === 'energy' ? 'Energy Trade and Industrial Growth' : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-52">
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
              className="w-full appearance-none bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-sm rounded-lg focus:ring-primary focus:border-primary block px-3 py-2 pr-8"
            >
              <option value="">Status: All</option>
              <option value={ProjectStatus.DRAFT}>Draft</option>
              <option value={ProjectStatus.PIPELINE}>Pipeline</option>
              <option value={ProjectStatus.UNDER_REVIEW}>Under Review</option>
              <option value={ProjectStatus.SUMMIT_READY}>Summit Ready</option>
              <option value={ProjectStatus.DEAL_ROOM_FEATURED}>Deal Room Featured</option>
              <option value={ProjectStatus.IN_NEGOTIATION}>In Negotiation</option>
              <option value={ProjectStatus.COMMITTED}>Committed</option>
              <option value={ProjectStatus.IMPLEMENTED}>Implemented</option>
              <option value={ProjectStatus.ON_HOLD}>On Hold</option>
              <option value={ProjectStatus.DECLINED}>Declined</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
              <span className="material-symbols-outlined text-[20px]">expand_more</span>
            </div>
          </div>
          <button className="p-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-600">
            <span className="material-symbols-outlined text-[20px]">filter_list</span>
          </button>
          {canAccessInvestorDB && (
            <button
              onClick={handleOpenWeights}
              className="p-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-600"
              title="Configure WAIIS scoring weights"
            >
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </button>
          )}
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
        {error ? (
          <div className="p-12 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 mb-4">
              <span className="material-symbols-outlined text-red-600 dark:text-red-400 text-4xl">error</span>
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">Failed to Load Pipeline</h3>
            <p className="text-slate-600 dark:text-slate-400 mb-6 max-w-md mx-auto">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">refresh</span>
              Retry
            </button>
          </div>
        ) : loading ? (
          <div className="p-8 text-center text-slate-500">Loading projects...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Project Name</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Pillar</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Lead Country/Co.</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Investment</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Readiness Score</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {paginatedProjects.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-500 dark:text-slate-400">
                      No projects found.
                    </td>
                  </tr>
                ) : paginatedProjects.map((project) => {
                  const score = Number(project.afcen_score ?? project.readiness_score ?? 0);
                  const isAIScored = project.afcen_score != null;
                  return (
                    <tr
                      key={project.id}
                      onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(project.id)}`)}
                      className="group hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
                    >
                      {/* Project Name */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${getIconColorClasses(project.pillar)}`}>
                            <span className="material-symbols-outlined">{getPillarIcon(project.pillar)}</span>
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-slate-900 dark:text-white">{project.name}</p>
                            <p className="text-xs text-slate-500">ID: {project.id.slice(0, 8)}</p>
                          </div>
                        </div>
                      </td>

                      {/* Pillar */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                          {project.pillar || '—'}
                        </span>
                      </td>

                      {/* Lead Country/Co. */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="text-sm text-slate-900 dark:text-white">{project.lead_country || '—'}</span>
                          <span className="text-xs text-slate-500">{project.project_sponsor || ''}</span>
                        </div>
                      </td>

                      {/* Investment */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-slate-900 dark:text-white">
                          {project.investment_size ? formatCurrency(project.investment_size) : '—'}
                        </span>
                      </td>

                      {/* Readiness Score */}
                      <td className="px-6 py-4 whitespace-nowrap min-w-[180px]">
                        <div className="flex flex-col gap-1">
                          <div className="flex justify-between items-center text-xs">
                            <span className="font-medium text-slate-700 dark:text-slate-200">{score.toFixed(0)}%</span>
                            {isAIScored && (
                              <div className="flex items-center gap-1 text-purple-600 dark:text-purple-400" title="AI Calculated Score">
                                <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
                                <span className="text-[10px] font-bold">AI SCORED</span>
                              </div>
                            )}
                          </div>
                          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                            <div
                              className={`${getProgressColor(score)} h-2 rounded-full`}
                              style={{ width: `${score}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                          {getStatusLabel(project.status)}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/deal-pipeline/${encodeURIComponent(project.id)}`); }}
                          className="text-slate-400 hover:text-primary transition-colors p-1"
                        >
                          <span className="material-symbols-outlined text-[20px]">visibility</span>
                        </button>
                        <button
                          onClick={(e) => e.stopPropagation()}
                          className="text-slate-400 hover:text-primary transition-colors p-1 ml-2"
                        >
                          <span className="material-symbols-outlined text-[20px]">more_vert</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && !error && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
            <div className="text-sm text-slate-500 dark:text-slate-400">
              Showing{' '}
              <span className="font-medium text-slate-900 dark:text-white">
                {Math.min((currentPage - 1) * itemsPerPage + 1, projects.length)}
              </span>
              {' '}to{' '}
              <span className="font-medium text-slate-900 dark:text-white">
                {Math.min(currentPage * itemsPerPage, projects.length)}
              </span>
              {' '}of{' '}
              <span className="font-medium text-slate-900 dark:text-white">{projects.length}</span> results
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-600"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="px-3 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-600"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="h-10"></div>
    </div>
  );
};

export default DealPipeline;
