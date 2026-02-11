import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { Project, PipelineStats, ProjectStatus } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { UserRole } from '../types/auth';
import DealRoomDashboard from './DealRoomDashboard';
import InvestorDatabase from './InvestorDatabase';
import ComingSoonOverlay from '../components/common/ComingSoonOverlay';

const DealPipeline: React.FC = () => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'pipeline' | 'deal_room' | 'investors'>('pipeline');
  const [activeTab, setActiveTab] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showAIInsight, setShowAIInsight] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch Data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [projectsData, statsData] = await Promise.all([
          pipelineService.listProjects(
            statusFilter !== 'all' ? (statusFilter as ProjectStatus) : undefined,
            activeTab !== 'all' ? activeTab : undefined
          ),
          pipelineService.getStats()
        ]);
        setProjects(projectsData);
        setStats(statsData);
      } catch (error) {
        console.error("Failed to fetch pipeline data", error);
        setError("Unable to load pipeline data. Please check your connection and try again.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [activeTab, statusFilter]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'committed':
      case 'implemented':
      case 'summit_ready':
      case 'approved':
      case 'bankable':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';

      case 'under_review':
      case 'vetting':
      case 'in_review':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';

      case 'needs_revision':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';

      case 'deal_room_featured':
      case 'deal_room':
        return 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300';

      case 'in_negotiation':
      case 'financing':
        return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300';

      case 'declined':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';

      case 'on_hold':
      case 'archived':
      case 'identified':
      case 'draft':
      case 'pipeline':
        return 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300';

      default:
        return 'bg-slate-100 text-slate-800';
    }
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

  const handleExport = () => {
    // Create CSV content
    const headers = ['ID', 'Name', 'Pillar', 'Investment', 'Readiness Score', 'Status'];
    const csvContent = [
      headers.join(','),
      ...projects.map(p =>
        [p.id, p.name, p.pillar, p.investment_size, p.readiness_score, p.status].join(',')
      )
    ].join('\n');

    // Download CSV
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

  const handleNewProject = () => {
    navigate('/deal-pipeline/new');
  };

  const formatCurrency = (amount: number) => {
    if (amount >= 1000000000) return `$${(amount / 1000000000).toFixed(1)}B`;
    if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
    return `$${amount.toLocaleString()}`;
  };

  // Pagination logic
  const itemsPerPage = 10;
  const totalPages = Math.ceil(projects.length / itemsPerPage);
  const paginatedProjects = projects.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handlePreviousPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1);
  };

  const { user } = useAppSelector((state) => state.auth);
  const canEdit = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR].includes(user.role);
  const canAccessInvestorDB = user?.role && [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD].includes(user.role);

  return (
    <div className="max-w-7xl mx-auto space-y-6 relative">
      <ComingSoonOverlay />
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <a href="/dashboard" className="hover:text-primary transition-colors">
          Dashboard
        </a>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-slate-900 dark:text-white font-medium">Deal Pipeline</span>
      </div>

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Deal Pipeline
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage regional investment opportunities.
          </p>
        </div>
        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
          <button
            onClick={() => setViewMode('pipeline')}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-all ${viewMode === 'pipeline' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            All Projects
          </button>
          <button
            onClick={() => setViewMode('deal_room')}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-all ${viewMode === 'deal_room' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Deal Room
          </button>
          {canAccessInvestorDB && (
            <button
              onClick={() => setViewMode('investors')}
              className={`px-4 py-2 text-sm font-bold rounded-md transition-all ${viewMode === 'investors' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
            >
              Investor DB
            </button>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm">
            <span className="material-symbols-outlined text-[20px]">download</span>
            Export
          </button>
          {canEdit && (
            <button
              onClick={handleNewProject}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-bold shadow-md shadow-primary/20 transition-all">
              <span className="material-symbols-outlined text-[20px]">add</span>
              New Project
            </button>
          )}
        </div>
      </div>



      {/* View Content */}
      {
        viewMode === 'pipeline' && (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Total Projects Card */}
              <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    Total Projects
                  </p>
                  <span className="material-symbols-outlined text-green-600 bg-green-100 dark:bg-green-900/30 p-1 rounded">
                    trending_up
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
                  {stats ? stats.total_projects : '-'}
                </p>
                <p className="text-xs text-green-600 font-medium flex items-center gap-1 mt-1">
                  Active Pipeline
                </p>
              </div>

              {/* Healthy Projects Card */}
              <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    Healthy Projects
                  </p>
                  <span className="material-symbols-outlined text-primary bg-primary/10 dark:bg-primary/20 p-1 rounded">
                    verified
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
                  {stats ? stats.healthy_projects : '-'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mt-1">
                  On track
                </p>
              </div>

              {/* Stalled Projects Card */}
              <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    Stalled / Attention
                  </p>
                  <span className="material-symbols-outlined text-red-600 bg-red-100 dark:bg-red-900/30 p-1 rounded">
                    warning
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
                  {stats ? stats.stalled_projects.length : '-'}
                </p>
                <p className="text-xs text-red-600 font-medium mt-1">Awaiting action</p>
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
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    AI Agent 'Alpha' Insight
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                    {stats && stats.stalled_projects.length > 0
                      ? `I've identified ${stats.stalled_projects.length} stalled projects that require your attention to move to the next stage.`
                      : "Pipeline looks healthy. No immediate actions required."}
                  </p>
                </div>
                <button
                  onClick={() => setShowAIInsight(false)}
                  className="absolute top-2 right-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>
            )}

            {/* Filters & Toolbar */}
            <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-white dark:bg-slate-800 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
              {/* Tabs */}
              <div className="flex p-1 bg-slate-100 dark:bg-slate-700 rounded-lg w-full sm:w-auto overflow-x-auto">
                <button
                  onClick={() => setActiveTab('all')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all whitespace-nowrap ${activeTab === 'all'
                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                >
                  All Projects
                </button>
                <button
                  onClick={() => setActiveTab('infrastructure')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all whitespace-nowrap ${activeTab === 'infrastructure'
                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                >
                  Infrastructure
                </button>
                <button
                  onClick={() => setActiveTab('energy')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all whitespace-nowrap ${activeTab === 'energy'
                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                >
                  Energy
                </button>
                <button
                  onClick={() => setActiveTab('agriculture')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all whitespace-nowrap ${activeTab === 'agriculture'
                    ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                >
                  Agribusiness
                </button>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <div className="relative w-full sm:w-48">
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full appearance-none bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-sm rounded-lg focus:ring-primary focus:border-primary block px-3 py-2 pr-8"
                  >
                    <option value="all">Status: All</option>
                    <option value={ProjectStatus.DRAFT}>Draft</option>
                    <option value={ProjectStatus.PIPELINE}>Pipeline</option>
                    <option value={ProjectStatus.UNDER_REVIEW}>Under Review</option>
                    <option value={ProjectStatus.SUMMIT_READY}>Summit Ready</option>
                    <option value={ProjectStatus.DEAL_ROOM_FEATURED}>Deal Room</option>
                    <option value={ProjectStatus.IN_NEGOTIATION}>In Negotiation</option>
                    <option value={ProjectStatus.COMMITTED}>Committed</option>
                    <option value={ProjectStatus.IMPLEMENTED}>Implemented</option>
                    <option value={ProjectStatus.ON_HOLD}>On Hold</option>
                    <option value={ProjectStatus.ARCHIVED}>Archived</option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
                    <span className="material-symbols-outlined text-[20px]">expand_more</span>
                  </div>
                </div>
                <button
                  className="p-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-600">
                  <span className="material-symbols-outlined text-[20px]">filter_list</span>
                </button>
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
                        <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Project Name
                        </th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Pillar
                        </th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Size
                        </th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Scores (AfCEN)
                        </th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                      {paginatedProjects.map((project) => (
                        <tr
                          key={project.id}
                          onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(project.id)}`)}
                          className="group hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
                        >
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-3">
                              <div
                                className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${getIconColorClasses(
                                  project.pillar
                                )}`}
                              >
                                <span className="material-symbols-outlined">{getPillarIcon(project.pillar)}</span>
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-slate-900 dark:text-white">
                                  {project.name}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {project.lead_country || 'Regional'}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                              {project.pillar || 'General'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="text-sm font-medium text-slate-900 dark:text-white">
                              {formatCurrency(project.investment_size)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap min-w-[180px]">
                            <div className="flex flex-col gap-1">
                              <div className="flex justify-between items-center text-xs">
                                <span className="font-medium text-slate-700 dark:text-slate-200">
                                  {project.afcen_score ? Number(project.afcen_score).toFixed(0) : 0}%
                                </span>
                                {project.afcen_score != null && (
                                  <div
                                    className="flex items-center gap-1 text-purple-600 dark:text-purple-400"
                                    title="AI Calculated Score"
                                  >
                                    <span className="material-symbols-outlined text-[14px]">
                                      auto_awesome
                                    </span>
                                    <span className="text-[10px] font-bold">AI SCORED</span>
                                  </div>
                                )}
                              </div>
                              <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                <div
                                  className={`${getProgressColor(project.afcen_score || 0)} h-2 rounded-full`}
                                  style={{ width: `${project.afcen_score || 0}%` }}
                                ></div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                                project.status
                              )}`}
                            >
                              {project.status.replace('_', ' ').toUpperCase()}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/deal-pipeline/${encodeURIComponent(project.id)}`);
                              }}
                              className="text-slate-400 hover:text-primary transition-colors p-1"
                            >
                              <span className="material-symbols-outlined text-[20px]">visibility</span>
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                              }}
                              className="text-slate-400 hover:text-primary transition-colors p-1 ml-2"
                            >
                              <span className="material-symbols-outlined text-[20px]">more_vert</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {paginatedProjects.length === 0 && !loading && !error && (
                    <div className="p-12 text-center border-t border-slate-200 dark:border-slate-700">
                      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 mb-4">
                        <span className="material-symbols-outlined text-slate-400 text-4xl">inbox</span>
                      </div>
                      <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">No Projects Found</h3>
                      <p className="text-slate-600 dark:text-slate-400 mb-6">
                        {statusFilter !== 'all' || activeTab !== 'all'
                          ? 'Try adjusting your filters to see more projects.'
                          : 'Get started by creating your first project.'}
                      </p>
                      {canEdit && statusFilter === 'all' && activeTab === 'all' && (
                        <button
                          onClick={handleNewProject}
                          className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-hover transition-colors"
                        >
                          <span className="material-symbols-outlined text-[20px]">add</span>
                          Create First Project
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Pagination */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  Showing <span className="font-medium text-slate-900 dark:text-white">{(currentPage - 1) * itemsPerPage + 1}</span> to{' '}
                  <span className="font-medium text-slate-900 dark:text-white">
                    {Math.min(currentPage * itemsPerPage, projects.length)}
                  </span>{' '}
                  of <span className="font-medium text-slate-900 dark:text-white">{projects.length}</span> results
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handlePreviousPage}
                    disabled={currentPage === 1}
                    className="px-3 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-600">
                    Previous
                  </button>
                  <button
                    onClick={handleNextPage}
                    disabled={currentPage >= totalPages}
                    className="px-3 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">
                    Next
                  </button>
                </div>
              </div>
            </div>
          </>
        )
      }

      {viewMode === 'deal_room' && <DealRoomDashboard />}
      {viewMode === 'investors' && <InvestorDatabase />}

      {/* Bottom spacing */}
      <div className="h-10"></div>
    </div>
  );
};

export default DealPipeline;
