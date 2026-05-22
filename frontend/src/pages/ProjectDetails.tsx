import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { documentService, Document } from '../services/documentService';
import { Project, InvestorMatch, InvestorMatchStatus, ProjectScoreDetail, ProjectStatus, BuyerMatch, BuyerMatchStatus, DFIMatch, DFIMatchStatus, FinancingMemo } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { ProjectLifecycleTimeline } from '../components/pipeline/ProjectLifecycleTimeline';
import { ProjectHistoryTimeline } from '../components/pipeline/ProjectHistoryTimeline';
import { UserRole } from '../types/auth';
import api from '../services/api';
import ReadinessTab from '../components/pipeline/ReadinessTab';

const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'financials' | 'documents' | 'history' | 'matches' | 'readiness'>('overview');
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
  const [buyerMatches, setBuyerMatches] = useState<BuyerMatch[]>([]);
  const [loadingBuyerMatches, setLoadingBuyerMatches] = useState(false);
  const [triggeringBuyerMatch, setTriggeringBuyerMatch] = useState(false);
  const [matchSubTab, setMatchSubTab] = useState<'investor' | 'buyer' | 'dfi'>('investor');
  const [dfiMatches, setDFIMatches] = useState<DFIMatch[]>([]);
  const [loadingDFIMatches, setLoadingDFIMatches] = useState(false);
  const [triggeringDFIMatch, setTriggeringDFIMatch] = useState(false);
  const [generatingMemo, setGeneratingMemo] = useState(false);
  const [financingMemo, setFinancingMemo] = useState<FinancingMemo | null>(null);
  const [showMemoModal, setShowMemoModal] = useState(false);

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
        fetchBuyerMatches(projectId);
        fetchDFIMatches(projectId);
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

  const fetchBuyerMatches = async (id: string) => {
    setLoadingBuyerMatches(true);
    try {
      const data = await pipelineService.getBuyerMatches(id);
      setBuyerMatches(data);
    } catch (e) {
      console.error("Failed to load buyer matches", e);
    } finally {
      setLoadingBuyerMatches(false);
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

  const handleTriggerBuyerMatch = async () => {
    if (!project) return;
    setTriggeringBuyerMatch(true);
    try {
      await pipelineService.triggerBuyerMatching(project.id);
      await fetchBuyerMatches(project.id);
    } catch (error: any) {
      console.error("Failed to trigger buyer matching", error);
      alert(error.response?.data?.detail || 'Failed to trigger buyer matching.');
    } finally {
      setTriggeringBuyerMatch(false);
    }
  };

  const handleUpdateBuyerMatchStatus = async (matchId: string, newStatus: BuyerMatchStatus) => {
    try {
      await pipelineService.updateBuyerMatchStatus(matchId, { status: newStatus });
      setBuyerMatches(prev => prev.map(m => m.match_id === matchId ? { ...m, status: newStatus } : m));
    } catch (error) {
      console.error("Failed to update buyer match status", error);
      alert("Failed to update status.");
    }
  };

  const fetchDFIMatches = async (id: string) => {
    setLoadingDFIMatches(true);
    try {
      const data = await pipelineService.getDFIMatches(id);
      setDFIMatches(data);
    } catch (e) {
      console.error('Failed to load DFI matches', e);
    } finally {
      setLoadingDFIMatches(false);
    }
  };

  const handleTriggerDFIMatch = async () => {
    if (!projectId || triggeringDFIMatch) return;
    setTriggeringDFIMatch(true);
    try {
      await pipelineService.triggerDFIMatching(projectId);
      await fetchDFIMatches(projectId);
    } catch (e) {
      console.error('DFI matching failed', e);
    } finally {
      setTriggeringDFIMatch(false);
    }
  };

  const handleUpdateDFIMatchStatus = async (matchId: string, newStatus: DFIMatchStatus) => {
    try {
      await pipelineService.updateDFIMatchStatus(matchId, { status: newStatus });
      if (projectId) await fetchDFIMatches(projectId);
    } catch (e) {
      console.error('Failed to update DFI match status', e);
    }
  };

  const handleGenerateMemo = async () => {
    if (!projectId || generatingMemo) return;
    setGeneratingMemo(true);
    try {
      const memo = await pipelineService.getFinancingMemo(projectId);
      setFinancingMemo(memo);
      setShowMemoModal(true);
    } catch (e) {
      console.error('Failed to generate financing memo', e);
    } finally {
      setGeneratingMemo(false);
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
      await api.post(`/pipeline/${project.id}/rescore`);
      // Refresh project data to get new score
      const updatedProject = await pipelineService.getProject(project.id);
      setProject(updatedProject);
      await fetchScoreDetails(project.id);
    } catch (error: any) {
      console.error('Rescore failed:', error);
    } finally {
      setRescoring(false);
    }
  };


  const fmtMoney = (amount?: number) => {
    if (!amount) return 'N/A';
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(0)}M`;
    return `$${amount.toLocaleString()}`;
  };

  const STATUS_DOT: Record<string, string> = {
    UNDER_REVIEW: 'var(--amber)', PIPELINE: 'var(--ink-400)',
    DEAL_ROOM_FEATURED: 'var(--accent)', IN_NEGOTIATION: 'var(--navy)',
    SUMMIT_READY: 'var(--sage)', COMMITTED: 'var(--sage)',
    IMPLEMENTED: 'var(--sage)', NEEDS_REVISION: 'var(--terra)',
    DECLINED: 'var(--terra)', ON_HOLD: 'var(--ink-400)', DRAFT: 'var(--ink-400)',
  };
  const STATUS_LABEL: Record<string, string> = {
    DRAFT: 'Draft', PIPELINE: 'Pipeline', UNDER_REVIEW: 'Under review',
    SUMMIT_READY: 'Summit ready', DEAL_ROOM_FEATURED: 'Deal room',
    IN_NEGOTIATION: 'In negotiation', COMMITTED: 'Committed',
    IMPLEMENTED: 'Implemented', DECLINED: 'Declined',
    NEEDS_REVISION: 'Needs revision', ON_HOLD: 'On hold',
  };

  if (loading || !project) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div className="size-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
          <p style={{ fontSize: 12, color: 'var(--ink-500)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Loading project…</p>
        </div>
      </div>
    );
  }

  const blockStyle: React.CSSProperties = {
    background: 'var(--surface)', border: '1px solid var(--border)', padding: '24px 28px',
  };
  const sectionHeadStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 14,
  };
  const sectionTitleStyle: React.CSSProperties = {
    fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 18,
    letterSpacing: '-0.01em', color: 'var(--ink-900)', margin: 0,
  };

  return (
    <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>

      {/* Breadcrumbs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--ink-500)', marginBottom: 18 }}>
        <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, fontSize: 11 }}>
          Dashboard
        </button>
        <span style={{ color: 'var(--ink-300)' }}>/</span>
        <button onClick={() => navigate('/deal-pipeline')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, fontSize: 11 }}>
          Deal pipeline
        </button>
        <span style={{ color: 'var(--ink-300)' }}>/</span>
        <span style={{ color: 'var(--ink-900)' }}>{project.name}</span>
      </div>

      {/* Page Header */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr auto', gap: 24, alignItems: 'flex-end',
        paddingBottom: 14, borderBottom: '1px solid var(--border)', marginBottom: 16,
      }}>
        <div style={{ minWidth: 0 }}>
          {project.is_flagship && (
            <div style={{ marginBottom: 6 }}>
              <span style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600 }}>
                ★ Flagship project
              </span>
            </div>
          )}
          <h1 style={{
            fontFamily: "'Source Serif 4', serif", fontWeight: 400,
            fontSize: 26, letterSpacing: '-0.02em', color: 'var(--ink-900)',
            margin: 0, lineHeight: 1.1,
          }}>{project.name}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginTop: 8, fontSize: 12, color: 'var(--ink-600)' }}>
            {project.pillar && <span>{project.pillar}</span>}
            {project.lead_country && <><span style={{ color: 'var(--ink-300)' }}>·</span><span>{project.lead_country}</span></>}
            {project.project_sponsor && <><span style={{ color: 'var(--ink-300)' }}>·</span><span>{project.project_sponsor}</span></>}
            <span style={{ color: 'var(--ink-300)' }}>·</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: 6, background: STATUS_DOT[project.status] ?? 'var(--ink-400)', display: 'inline-block' }} />
              {STATUS_LABEL[project.status] ?? project.status}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          {canEdit && (
            <>
              <button onClick={toggleFlagship} disabled={togglingFlagship} style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: 'transparent', border: '1px solid var(--border)',
                color: project.is_flagship ? 'var(--amber)' : 'var(--ink-700)',
                padding: '6px 11px', fontSize: 11, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                  {project.is_flagship ? 'star' : 'star_outline'}
                </span>
                {project.is_flagship ? 'Flagship' : 'Mark flagship'}
              </button>
              <button onClick={() => navigate(`/deal-pipeline/${project.id}/edit`)} style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: 'transparent', border: '1px solid var(--border)',
                color: 'var(--ink-700)', padding: '6px 11px', fontSize: 11, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>edit</span>
                Edit
              </button>
              {project.allowed_transitions && project.allowed_transitions.length > 0 && (
                <div className="relative group">
                  <div style={{ display: 'flex' }}>
                    <button onClick={() => handleStageTransition(project.allowed_transitions![0])} style={{
                      background: 'var(--accent)', color: 'var(--accent-ink)', border: '1px solid var(--accent)',
                      padding: '7px 14px 7px 12px', fontSize: 11, fontWeight: 500,
                      cursor: 'pointer', fontFamily: 'inherit',
                      display: 'inline-flex', alignItems: 'center', gap: 8,
                    }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_forward</span>
                      Advance stage
                    </button>
                  </div>
                  <div className="absolute right-0 mt-2 w-48 z-50 hidden group-hover:block" style={{
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    boxShadow: '0 8px 24px rgba(0,0,0,.12)',
                  }}>
                    {project.allowed_transitions.map(stage => (
                      <button key={stage} onClick={() => handleStageTransition(stage)} style={{
                        width: '100%', textAlign: 'left', padding: '10px 14px',
                        fontSize: 12, color: 'var(--ink-700)', cursor: 'pointer',
                        background: 'none', border: 'none', borderBottom: '1px solid var(--border)',
                        fontFamily: 'inherit',
                      }}>
                        Move to {stage.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          <button onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(project.id)}/memo`)} style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'var(--accent)', border: '1px solid var(--accent)',
            color: 'var(--accent-ink)', padding: '6px 12px', fontSize: 11, fontWeight: 500,
            cursor: 'pointer', fontFamily: 'inherit',
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>auto_awesome</span>
            Generate memo
          </button>
        </div>
      </div>

      {/* Lifecycle Timeline */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', overflow: 'hidden', marginBottom: 12 }}>
        <ProjectLifecycleTimeline project={project} />
      </div>

      {/* KPI strip */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        background: 'var(--surface)', border: '1px solid var(--border)',
        padding: '12px 20px', marginBottom: 16,
      }}>
        {[
          { label: 'Investment ask', value: fmtMoney(project.investment_size), sub: 'USD · estimated' },
          { label: 'Readiness score', value: project.readiness_score ? `${project.readiness_score}/100` : 'N/A', sub: 'WAIIS assessment' },
          { label: 'AfCEN score', value: project.afcen_score ? Number(project.afcen_score).toFixed(1) : 'N/A', sub: 'AI-calculated', accent: true },
          { label: 'Pillar', value: (project.pillar || 'General').split(',')[0].split('&')[0].trim(), sub: project.lead_country || 'Regional', last: true },
        ].map(({ label, value, sub, accent, last }) => (
          <div key={label} style={{ paddingRight: 24, borderRight: last ? 'none' : '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{label}</div>
            <div style={{
              fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20,
              color: accent ? 'var(--accent)' : 'var(--ink-900)', letterSpacing: '-0.01em',
              marginTop: 2, lineHeight: 1, fontVariantNumeric: 'tabular-nums',
            }}>{value}</div>
            <div style={{ fontSize: 10, color: 'var(--ink-500)', marginTop: 3 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ position: 'sticky', top: 56, background: 'var(--bg)', zIndex: 40, paddingTop: 8 }}>
        <div style={{ display: 'flex', gap: 28, borderBottom: '1px solid var(--border)', marginBottom: 28 }}>
          {[
            { key: 'overview', label: 'Overview' },
            { key: 'matches', label: 'Investor matches' },
            { key: 'financials', label: 'Financials' },
            { key: 'documents', label: 'Documents' },
            { key: 'history', label: 'History' },
            ...(project?.status === ProjectStatus.INCUBATION
              ? [{ key: 'readiness', label: '⚗ Readiness' }]
              : []),
          ].map(({ key, label }) => {
            const on = activeTab === (key as any);
            return (
              <button key={key} onClick={() => setActiveTab(key as any)} style={{
                fontSize: 13,
                color: on ? (key === 'readiness' ? '#7c3aed' : 'var(--ink-900)') : 'var(--ink-500)',
                fontWeight: on ? 500 : 400, padding: '10px 0',
                borderTop: 'none', borderLeft: 'none', borderRight: 'none',
                borderBottom: on ? `2px solid ${key === 'readiness' ? '#7c3aed' : 'var(--accent)'}` : '2px solid transparent',
                marginBottom: -1, cursor: 'pointer',
                background: 'none',
                fontFamily: 'inherit',
              }}>
                {label}
                {key === 'matches' && (matches.length + buyerMatches.length + dfiMatches.length) > 0 && (
                  <span style={{
                    marginLeft: 6, fontSize: 10, padding: '1px 6px',
                    background: 'var(--ink-100)', color: 'var(--ink-600)',
                    fontFamily: "'Geist Mono', monospace",
                  }}>{matches.length + buyerMatches.length + dfiMatches.length}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 32, paddingBottom: 48 }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

          {/* Overview Tab Content */}
          {activeTab === 'overview' && (
            <>
              {/* Executive Summary */}
              <section>
                <div style={sectionHeadStyle}>
                  <h2 style={sectionTitleStyle}>Executive summary</h2>
                </div>
                <div style={blockStyle}>
                  <p style={{
                    fontFamily: "'Source Serif 4', serif", fontSize: 17, color: 'var(--ink-800)',
                    lineHeight: 1.55, margin: 0, letterSpacing: '-0.005em',
                  }}>{project.description || 'No description provided.'}</p>
                </div>
              </section>

              {/* Project Particulars */}
              {(project.subsector || project.project_sponsor || project.land_status || project.revenue_model || project.climate_impact || project.esg_compliance || project.is_cross_border) && (
                <section>
                  <div style={sectionHeadStyle}><h2 style={sectionTitleStyle}>Project particulars</h2></div>
                  <div style={blockStyle}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 40, rowGap: 18 }}>
                      {[
                        project.subsector && { label: 'Subsector', value: project.subsector },
                        project.project_sponsor && { label: 'Project sponsor', value: project.project_sponsor },
                        project.lead_country && { label: 'Country / region', value: project.lead_country },
                        { label: 'Regional dimension', value: project.is_cross_border ? 'Cross-border · multi-country' : 'National' },
                        project.land_status && { label: 'Land status', value: project.land_status, span: true },
                        project.revenue_model && { label: 'Revenue model', value: project.revenue_model, span: true },
                        project.climate_impact && { label: 'Climate impact', value: project.climate_impact, span: true },
                        project.esg_compliance && { label: 'ESG / safeguards', value: project.esg_compliance, span: true },
                      ].filter(Boolean).map((item: any) => (
                        <div key={item.label} style={item.span ? { gridColumn: 'span 2' } : {}}>
                          <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 6 }}>
                            {item.label}
                          </div>
                          <div style={{ fontSize: 13, color: 'var(--ink-800)', lineHeight: 1.5 }}>{item.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              )}

              {/* AfCEN Score Breakdown */}
              <section>
                <div style={sectionHeadStyle}>
                  <h2 style={sectionTitleStyle}>AfCEN score breakdown</h2>
                  <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--ink-500)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ width: 5, height: 5, borderRadius: 5, background: 'var(--navy)', display: 'inline-block' }} />Core
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ width: 5, height: 5, borderRadius: 5, background: 'var(--accent)', display: 'inline-block' }} />Impact
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ width: 5, height: 5, borderRadius: 5, background: 'var(--gold)', display: 'inline-block' }} />Regional
                    </span>
                  </div>
                </div>
                <div style={blockStyle}>
                  {scoreDetails.length === 0 ? (
                    <div style={{ fontSize: 13, color: 'var(--ink-400)', fontStyle: 'italic' }}>
                      No score details available. Use "Rescore" to run the WAIIS assessment.
                    </div>
                  ) : (
                    (() => {
                      const GROUPS: Record<string, { label: string; color: string }> = {
                        core: { label: 'Core', color: 'var(--navy)' },
                        impact: { label: 'Impact', color: 'var(--accent)' },
                        regional: { label: 'Regional', color: 'var(--gold)' },
                      };
                      const IMPACT_NAMES = ['Climate Impact', 'Social Impact', 'Economic Impact'];
                      const REGIONAL_NAMES = ['ECOWAS Integration'];
                      const getGroup = (name: string) => {
                        if (REGIONAL_NAMES.some(n => name.includes(n.split(' ')[0]))) return 'regional';
                        if (IMPACT_NAMES.some(n => name.includes(n.split(' ')[0]))) return 'impact';
                        return 'core';
                      };
                      const grouped: Record<string, typeof scoreDetails> = { core: [], impact: [], regional: [] };
                      scoreDetails.forEach(d => {
                        const g = getGroup(d.criterion.criterion_name);
                        grouped[g].push(d);
                      });
                      return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
                          {(['core', 'impact', 'regional'] as const).filter(g => grouped[g].length > 0).map(g => (
                            <div key={g}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                                <span style={{ width: 5, height: 5, borderRadius: 5, background: GROUPS[g].color, display: 'inline-block' }} />
                                <span style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-700)', fontWeight: 500 }}>
                                  {GROUPS[g].label}
                                </span>
                                <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                                <span style={{ fontSize: 10, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace" }}>
                                  {grouped[g].reduce((s, d) => s + Number(d.criterion.weight ?? 0), 0).toFixed(0)} weight
                                </span>
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {grouped[g].map(d => {
                                  const pct = Math.min(100, Math.max(0, Number(d.score)));
                                  const weightPct = d.criterion.weight != null ? `${(Number(d.criterion.weight) * 100).toFixed(0)}%` : '';
                                  return (
                                    <div key={d.id} style={{ display: 'grid', gridTemplateColumns: '200px 1fr 50px 40px', gap: 16, alignItems: 'center' }}>
                                      <div style={{ fontSize: 12, color: 'var(--ink-800)' }}>{d.criterion.criterion_name}</div>
                                      <div style={{ height: 4, background: 'var(--ink-100)', position: 'relative' }}>
                                        <div style={{ position: 'absolute', inset: 0, width: `${pct}%`, background: GROUPS[g].color, opacity: 0.85 }} />
                                      </div>
                                      <div style={{ fontSize: 12, fontFamily: "'Geist Mono', monospace", color: 'var(--ink-900)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                                        {Math.round(pct)}
                                      </div>
                                      {weightPct && (
                                        <div style={{ fontSize: 11, color: 'var(--ink-400)', textAlign: 'right' }}>{weightPct}</div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })()
                  )}
                  <button onClick={handleRescore} disabled={rescoring} style={{
                    marginTop: 16, width: '100%', padding: '8px 10px', justifyContent: 'center',
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: 'transparent', border: '1px solid var(--border)',
                    color: 'var(--ink-700)', fontSize: 12, fontWeight: 500,
                    cursor: rescoring ? 'default' : 'pointer', fontFamily: 'inherit',
                    opacity: rescoring ? 0.6 : 1,
                  }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                      {rescoring ? 'hourglass_empty' : 'refresh'}
                    </span>
                    {rescoring ? 'Scoring…' : 'Rescore project'}
                  </button>
                </div>
              </section>
            </>
          )}

          {/* Matches Tab — Investor & Buyer sub-tabs */}
          {activeTab === 'matches' && (
            <section>
              {/* Sub-tab switcher */}
              <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
                {([
                  { key: 'investor' as const, label: 'Investor matches', count: matches.length },
                  { key: 'buyer' as const, label: 'Buyer / Offtake', count: buyerMatches.length },
                  { key: 'dfi' as const, label: 'DFI Windows', count: dfiMatches.length },
                ]).map(({ key, label, count }) => {
                  const on = matchSubTab === key;
                  return (
                    <button key={key} onClick={() => setMatchSubTab(key)} style={{
                      padding: '9px 16px', fontSize: 12,
                      background: 'none', border: 'none',
                      borderBottom: on ? '2px solid var(--accent)' : '2px solid transparent',
                      color: on ? 'var(--ink-900)' : 'var(--ink-500)',
                      fontWeight: on ? 500 : 400,
                      cursor: 'pointer', fontFamily: 'inherit', marginBottom: -1,
                    }}>
                      {label}
                      {count > 0 && (
                        <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 5px', background: 'var(--ink-100)', color: 'var(--ink-600)', fontFamily: "'Geist Mono', monospace" }}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Investor Matches */}
              {matchSubTab === 'investor' && (
                <>
                  <div style={sectionHeadStyle}>
                    <h2 style={sectionTitleStyle}>Investor matches</h2>
                    <button onClick={handleTriggerMatching} disabled={triggeringMatch} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                      padding: '7px 14px', fontSize: 12, fontWeight: 500,
                      cursor: triggeringMatch ? 'default' : 'pointer', fontFamily: 'inherit',
                      opacity: triggeringMatch ? 0.7 : 1,
                    }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>restart_alt</span>
                      {triggeringMatch ? 'Running…' : 'Run matching engine'}
                    </button>
                  </div>
                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    {loadingMatches ? (
                      <div style={{ padding: '32px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>Loading matches…</div>
                    ) : matches.length === 0 ? (
                      <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)' }}>
                        No investors matched yet. Run the matching engine to find potential investors.
                      </div>
                    ) : matches.map((match, i) => {
                      const MATCH_STATUS_COLOR: Record<string, string> = {
                        INTERESTED: 'var(--sage)', CONTACTED: 'var(--navy)', DETECTED: 'var(--ink-500)',
                        COMMITTED: 'var(--accent)', DECLINED: 'var(--terra)',
                      };
                      return (
                        <div key={match.match_id} style={{
                          display: 'grid', gridTemplateColumns: '1fr 80px 160px',
                          gap: 16, alignItems: 'center',
                          padding: '16px 24px',
                          borderBottom: i < matches.length - 1 ? '1px solid var(--border)' : 'none',
                        }}>
                          <div>
                            <div style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500, marginBottom: 4 }}>
                              {match.investor?.name || 'Unknown Investor'}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--ink-500)', lineHeight: 1.45 }}>
                              {match.investor?.sector_preferences?.join(', ') || 'No specific strategy'}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--ink-600)', marginTop: 6, fontFamily: "'Geist Mono', monospace" }}>
                              {match.investor?.ticket_size_min ? `$${match.investor.ticket_size_min}M – $${match.investor.ticket_size_max}M` : 'N/A'}
                              {match.investor?.geographic_focus?.length ? ` · ${match.investor.geographic_focus[0]}` : ''}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{
                              fontFamily: "'Source Serif 4', serif", fontSize: 24,
                              color: 'var(--ink-900)', lineHeight: 1, fontVariantNumeric: 'tabular-nums',
                            }}>{Math.round(match.score)}<span style={{ fontSize: 13, color: 'var(--ink-400)' }}>%</span></div>
                            <div style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-400)', marginTop: 4 }}>Match</div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ width: 6, height: 6, borderRadius: 6, background: MATCH_STATUS_COLOR[match.status] ?? 'var(--ink-400)', display: 'inline-block', flexShrink: 0 }} />
                            <select
                              value={match.status}
                              onChange={(e) => handleUpdateMatchStatus(match.match_id, e.target.value as InvestorMatchStatus)}
                              style={{
                                background: 'var(--surface)', border: '1px solid var(--border)',
                                color: 'var(--ink-700)', padding: '5px 8px', fontSize: 11,
                                fontFamily: 'inherit', cursor: 'pointer', outline: 'none', flex: 1,
                              }}
                            >
                              <option value={InvestorMatchStatus.DETECTED}>Detected</option>
                              <option value={InvestorMatchStatus.CONTACTED}>Contacted</option>
                              <option value={InvestorMatchStatus.INTERESTED}>Interested</option>
                              <option value={InvestorMatchStatus.COMMITTED}>Committed</option>
                              <option value={InvestorMatchStatus.DECLINED}>Declined</option>
                            </select>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}

              {/* Buyer / Offtake Matches */}
              {matchSubTab === 'buyer' && (
                <>
                  <div style={sectionHeadStyle}>
                    <h2 style={sectionTitleStyle}>Buyer / offtake matches</h2>
                    <button onClick={handleTriggerBuyerMatch} disabled={triggeringBuyerMatch} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                      padding: '7px 14px', fontSize: 12, fontWeight: 500,
                      cursor: triggeringBuyerMatch ? 'default' : 'pointer', fontFamily: 'inherit',
                      opacity: triggeringBuyerMatch ? 0.7 : 1,
                    }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>restart_alt</span>
                      {triggeringBuyerMatch ? 'Running…' : 'Run buyer matching'}
                    </button>
                  </div>
                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    {loadingBuyerMatches ? (
                      <div style={{ padding: '32px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>Loading…</div>
                    ) : buyerMatches.length === 0 ? (
                      <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)' }}>
                        No buyers matched yet. Run the buyer matching engine to find potential offtakers.
                      </div>
                    ) : buyerMatches.map((match, i) => {
                      const BUYER_STATUS_COLOR: Record<string, string> = {
                        DETECTED: 'var(--ink-500)', CONTACTED: 'var(--navy)',
                        INTERESTED: 'var(--sage)', NEGOTIATING: 'var(--amber)', COMMITTED: 'var(--accent)',
                      };
                      return (
                        <div key={match.match_id} style={{
                          display: 'grid', gridTemplateColumns: '1fr 80px 160px',
                          gap: 16, alignItems: 'start',
                          padding: '16px 24px',
                          borderBottom: i < buyerMatches.length - 1 ? '1px solid var(--border)' : 'none',
                        }}>
                          <div>
                            <div style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500, marginBottom: 4 }}>
                              {match.buyer?.name || 'Unknown Buyer'}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--ink-500)', lineHeight: 1.45 }}>
                              {match.buyer?.commodity_types?.join(', ') || 'No commodity data'}
                            </div>
                            {match.match_rationale && (
                              <div style={{ fontSize: 11, color: 'var(--ink-600)', marginTop: 6, lineHeight: 1.4 }}>
                                {match.match_rationale}
                              </div>
                            )}
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{
                              fontFamily: "'Source Serif 4', serif", fontSize: 24,
                              color: 'var(--ink-900)', lineHeight: 1, fontVariantNumeric: 'tabular-nums',
                            }}>{match.score}<span style={{ fontSize: 13, color: 'var(--ink-400)' }}>/100</span></div>
                            <div style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-400)', marginTop: 4 }}>Score</div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 2 }}>
                            <span style={{ width: 6, height: 6, borderRadius: 6, background: BUYER_STATUS_COLOR[match.status] ?? 'var(--ink-400)', display: 'inline-block', flexShrink: 0 }} />
                            <select
                              value={match.status}
                              onChange={(e) => handleUpdateBuyerMatchStatus(match.match_id, e.target.value as BuyerMatchStatus)}
                              style={{
                                background: 'var(--surface)', border: '1px solid var(--border)',
                                color: 'var(--ink-700)', padding: '5px 8px', fontSize: 11,
                                fontFamily: 'inherit', cursor: 'pointer', outline: 'none', flex: 1,
                              }}
                            >
                              <option value={BuyerMatchStatus.DETECTED}>Detected</option>
                              <option value={BuyerMatchStatus.CONTACTED}>Contacted</option>
                              <option value={BuyerMatchStatus.INTERESTED}>Interested</option>
                              <option value={BuyerMatchStatus.NEGOTIATING}>Negotiating</option>
                              <option value={BuyerMatchStatus.COMMITTED}>Committed</option>
                            </select>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}

              {/* DFI / Blended Finance Windows */}
              {matchSubTab === 'dfi' && (
                <>
                  <div style={sectionHeadStyle}>
                    <h2 style={sectionTitleStyle}>DFI / Blended Finance Windows</h2>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={handleGenerateMemo} disabled={generatingMemo} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        background: 'none', border: '1px solid var(--border)', color: 'var(--ink-700)',
                        padding: '7px 14px', fontSize: 12, fontWeight: 500,
                        cursor: generatingMemo ? 'default' : 'pointer', fontFamily: 'inherit',
                        opacity: generatingMemo ? 0.7 : 1,
                      }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>description</span>
                        {generatingMemo ? 'Generating…' : 'Financing memo'}
                      </button>
                      <button onClick={handleTriggerDFIMatch} disabled={triggeringDFIMatch} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                        padding: '7px 14px', fontSize: 12, fontWeight: 500,
                        cursor: triggeringDFIMatch ? 'default' : 'pointer', fontFamily: 'inherit',
                        opacity: triggeringDFIMatch ? 0.7 : 1,
                      }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>restart_alt</span>
                        {triggeringDFIMatch ? 'Running…' : 'Run DFI matching'}
                      </button>
                    </div>
                  </div>

                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    {loadingDFIMatches ? (
                      <div style={{ padding: '32px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>
                        Loading DFI windows…
                      </div>
                    ) : dfiMatches.length === 0 ? (
                      <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)' }}>
                        No DFI windows matched yet. Run the matching engine to find suitable instruments.
                      </div>
                    ) : dfiMatches.map((match, i) => {
                      const INSTRUMENT_COLOR: Record<string, string> = {
                        GRANT: 'var(--sage)',
                        CONCESSIONAL_LOAN: 'var(--navy)',
                        BLENDED: 'var(--accent)',
                        EQUITY: 'var(--terra)',
                      };
                      const instrColor = INSTRUMENT_COLOR[match.dfi_window.instrument_type] || 'var(--ink-500)';

                      return (
                        <div key={match.match_id} style={{
                          padding: '16px 20px',
                          borderBottom: i < dfiMatches.length - 1 ? '1px solid var(--border)' : 'none',
                        }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
                            <div style={{ flex: 1 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>
                                  {match.dfi_window.name}
                                </span>
                                <span style={{
                                  fontSize: 10, padding: '2px 6px', letterSpacing: '0.08em',
                                  textTransform: 'uppercase', color: instrColor,
                                  border: `1px solid ${instrColor}`,
                                }}>
                                  {match.dfi_window.instrument_type.replace('_', ' ')}
                                </span>
                                {match.dfi_window.gender_focus && (
                                  <span style={{ fontSize: 10, padding: '2px 6px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--sage)', border: '1px solid var(--sage)' }}>
                                    Gender
                                  </span>
                                )}
                                {match.dfi_window.climate_focus && (
                                  <span style={{ fontSize: 10, padding: '2px 6px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--navy)', border: '1px solid var(--navy)' }}>
                                    Climate
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                                {match.dfi_window.institution}
                              </div>
                              {match.fit_rationale && (
                                <div style={{ fontSize: 11, color: 'var(--ink-400)', lineHeight: 1.5 }}>
                                  {match.fit_rationale}
                                </div>
                              )}
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{
                                  fontSize: 20, fontWeight: 700, fontFamily: "'Geist Mono', monospace",
                                  color: match.fit_score >= 70 ? 'var(--sage)' : match.fit_score >= 50 ? 'var(--accent)' : 'var(--ink-500)',
                                }}>
                                  {match.fit_score}
                                </div>
                                <div style={{ fontSize: 10, color: 'var(--ink-400)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>fit score</div>
                              </div>
                              <select
                                value={match.status}
                                onChange={(e) => handleUpdateDFIMatchStatus(match.match_id, e.target.value as DFIMatchStatus)}
                                style={{
                                  fontSize: 11, padding: '4px 8px',
                                  background: 'var(--surface)', border: '1px solid var(--border)',
                                  color: 'var(--ink-700)', fontFamily: 'inherit', cursor: 'pointer',
                                }}
                              >
                                {Object.values(DFIMatchStatus).map(s => (
                                  <option key={s} value={s}>{s.replace('_', ' ')}</option>
                                ))}
                              </select>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </section>
          )}

          {/* Financials Tab */}
          {activeTab === 'financials' && (
            <section>
              <div style={sectionHeadStyle}><h2 style={sectionTitleStyle}>Financial structure</h2></div>
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr' }}>
                  {[
                    { label: 'Total ask', value: fmtMoney(project.investment_size) },
                    { label: 'Funding secured', value: fmtMoney(project.funding_secured_usd), sub: `${((project.funding_secured_usd || 0) / project.investment_size * 100).toFixed(0)}% committed`, color: 'var(--sage)' },
                    { label: 'Funding gap', value: fmtMoney(project.investment_size - (project.funding_secured_usd || 0)), color: 'var(--amber)' },
                  ].map((item, i) => (
                    <div key={item.label} style={{ padding: '20px 22px', borderRight: i < 2 ? '1px solid var(--border)' : 'none' }}>
                      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{item.label}</div>
                      <div style={{
                        fontFamily: "'Source Serif 4', serif", fontSize: 22,
                        color: item.color || 'var(--ink-900)', marginTop: 6, lineHeight: 1.15, letterSpacing: '-0.01em',
                      }}>{item.value}</div>
                      {item.sub && <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6 }}>{item.sub}</div>}
                    </div>
                  ))}
                </div>
                {project.investment_size > 0 && (
                  <div style={{ padding: '0 22px 20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--ink-500)', marginBottom: 6 }}>
                      <span>Funding progress</span>
                      <span style={{ fontFamily: "'Geist Mono', monospace" }}>
                        {((project.funding_secured_usd || 0) / project.investment_size * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ height: 4, background: 'var(--ink-100)', position: 'relative' }}>
                      <div style={{
                        position: 'absolute', inset: 0,
                        width: `${Math.min(100, (project.funding_secured_usd || 0) / project.investment_size * 100)}%`,
                        background: 'var(--accent)',
                      }} />
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Documents Tab */}
          {activeTab === 'documents' && (
            <section>
              <div style={sectionHeadStyle}>
                <h2 style={sectionTitleStyle}>Project documents</h2>
                <button onClick={() => setShowUploadModal(true)} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                  padding: '7px 14px', fontSize: 12, fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit',
                }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>upload_file</span>
                  Upload document
                </button>
              </div>
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                {documents.length === 0 ? (
                  <div style={{ padding: '32px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)', fontStyle: 'italic' }}>No documents found.</div>
                ) : documents.map((doc, i) => (
                  <div key={doc.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '14px 24px',
                    borderBottom: i < documents.length - 1 ? '1px solid var(--border)' : 'none',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--ink-400)' }}>description</span>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-900)' }}>{doc.file_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
                          {new Date(doc.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <button onClick={() => documentService.downloadDocument(doc.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>download</span>
                      </button>
                      <button onClick={() => handleDeleteDocument(doc.id, doc.file_name)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>delete</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <section>
              <div style={sectionHeadStyle}><h2 style={sectionTitleStyle}>History</h2></div>
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '24px 28px' }}>
                <ProjectHistoryTimeline projectId={projectId!} />
              </div>
            </section>
          )}

          {activeTab === 'readiness' && project && (
            <ReadinessTab
              project={project}
              scoreDetails={scoreDetails}
              canEdit={!!canEdit}
              onGraduate={() => {
                if (projectId) {
                  pipelineService.getProject(projectId).then(setProject);
                  setActiveTab('overview');
                }
              }}
            />
          )}

        </div>

        {/* Right Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* Martin's read — pull quote */}
          <div style={{
            padding: '24px 24px 22px',
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderTop: '2px solid var(--accent)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <span style={{ fontFamily: "'Source Serif 4', serif", fontStyle: 'italic', fontSize: 13, color: 'var(--accent)' }}>
                Martin's read
              </span>
              <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
            </div>
            {isLoadingInsight ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 0' }}>
                <div className="size-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
                <p style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 8 }}>Analyzing project…</p>
              </div>
            ) : (
              <>
                <p style={{
                  fontFamily: "'Source Serif 4', serif", fontSize: 16,
                  color: 'var(--ink-800)', lineHeight: 1.5, margin: 0,
                }}>{aiInsight || 'No insights available yet.'}</p>
                {aiRecommendation && (
                  <div style={{
                    marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--border)',
                    fontSize: 11, color: 'var(--ink-500)',
                  }}>
                    <div style={{ marginBottom: 6, fontWeight: 500, color: 'var(--ink-700)' }}>Recommended next step</div>
                    {aiRecommendation}
                  </div>
                )}
              </>
            )}
            <button onClick={fetchAIInsights} disabled={isLoadingInsight} style={{
              marginTop: 16, width: '100%',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              background: 'transparent', border: '1px solid var(--border)',
              color: 'var(--ink-700)', fontSize: 12, fontWeight: 500, padding: '7px 10px',
              cursor: isLoadingInsight ? 'default' : 'pointer', fontFamily: 'inherit',
              opacity: isLoadingInsight ? 0.6 : 1,
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>psychology</span>
              {isLoadingInsight ? 'Analyzing…' : 'Refresh insight'}
            </button>
          </div>

          {/* Quick facts */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '18px 24px' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)' }}>
              Quick facts
            </div>
            <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column' }}>
              {[
                ['Pillar', (project.pillar || 'General').split(',')[0]],
                ['Geography', project.lead_country || 'Regional'],
                ['Sponsor', project.project_sponsor || '—'],
                ['Stage', STATUS_LABEL[project.status] ?? project.status],
                ['Cross-border', project.is_cross_border ? 'Yes' : 'No'],
              ].map(([k, v], i, arr) => (
                <div key={k} style={{
                  display: 'grid', gridTemplateColumns: '90px 1fr', gap: 12,
                  padding: '10px 0', fontSize: 12,
                  borderBottom: i === arr.length - 1 ? 'none' : '1px solid var(--border)',
                }}>
                  <span style={{ color: 'var(--ink-500)' }}>{k}</span>
                  <span style={{ color: 'var(--ink-900)' }}>{v}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 480, margin: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink-900)', margin: 0 }}>Upload document</h3>
              <button onClick={() => setShowUploadModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, display: 'block', marginBottom: 8 }}>
                  Document type
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  style={{ width: '100%', background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '8px 10px', fontSize: 13, fontFamily: 'inherit', outline: 'none' }}
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
                <label style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, display: 'block', marginBottom: 8 }}>
                  Select file
                </label>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                  className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:font-medium"
                  style={{ fontSize: 13 }}
                />
                {selectedFile && (
                  <p style={{ marginTop: 8, fontSize: 12, color: 'var(--ink-600)' }}>Selected: {selectedFile.name}</p>
                )}
              </div>
            </div>
            <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
              <button onClick={() => setShowUploadModal(false)} style={{
                flex: 1, padding: '8px 16px', fontSize: 12, fontWeight: 500, cursor: 'pointer',
                background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', fontFamily: 'inherit',
              }}>Cancel</button>
              <button onClick={handleUploadDocument} disabled={!selectedFile || uploadingDoc} style={{
                flex: 1, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: !selectedFile || uploadingDoc ? 'default' : 'pointer',
                background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)', fontFamily: 'inherit',
                opacity: !selectedFile || uploadingDoc ? 0.6 : 1,
              }}>
                {uploadingDoc ? 'Uploading…' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Financing Memo Modal */}
      {showMemoModal && financingMemo && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
        }}>
          <div style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            width: '100%', maxWidth: 640, margin: 16, maxHeight: '90vh', overflowY: 'auto',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '20px 24px', borderBottom: '1px solid var(--border)',
              position: 'sticky', top: 0, background: 'var(--surface)',
            }}>
              <div>
                <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-400)', marginBottom: 4 }}>
                  Blended Finance Memo
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink-900)', margin: 0 }}>
                  {financingMemo.project_name}
                </h3>
              </div>
              <button onClick={() => setShowMemoModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)' }}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div style={{ padding: '20px 24px' }}>
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Recommended Capital Structure</div>
                <div style={{ fontSize: 13, color: 'var(--ink-800)', marginBottom: 12 }}>{financingMemo.recommended_structure}</div>
                <div style={{ display: 'flex', gap: 0, height: 8, borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ flex: financingMemo.grant_component_pct, background: 'var(--sage)' }} />
                  <div style={{ flex: financingMemo.concessional_component_pct, background: 'var(--navy)' }} />
                  <div style={{ flex: financingMemo.commercial_component_pct, background: 'var(--accent)' }} />
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 6 }}>
                  {[
                    { label: 'Grant', pct: financingMemo.grant_component_pct, color: 'var(--sage)' },
                    { label: 'Concessional', pct: financingMemo.concessional_component_pct, color: 'var(--navy)' },
                    { label: 'Commercial', pct: financingMemo.commercial_component_pct, color: 'var(--accent)' },
                  ].map(({ label, pct, color }) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                      <span style={{ fontSize: 11, color: 'var(--ink-500)' }}>{label}: {pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Priority DFI Windows</div>
                {financingMemo.priority_windows.map((w, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--ink-700)', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                    {i + 1}. {w}
                  </div>
                ))}
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Key Risks</div>
                {financingMemo.key_risks.map((r, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--ink-600)', padding: '3px 0' }}>• {r}</div>
                ))}
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Next Steps</div>
                {financingMemo.next_steps.map((s, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--ink-700)', padding: '3px 0' }}>
                    <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 10, color: 'var(--accent)', marginRight: 6 }}>{String(i+1).padStart(2,'0')}</span>
                    {s}
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Financing Rationale</div>
                <div style={{ fontSize: 12, color: 'var(--ink-700)', lineHeight: 1.7 }}>{financingMemo.full_memo}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDetails;
