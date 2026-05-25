import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { documentService, Document } from '../services/documentService';
import { Project, InvestorMatch, InvestorMatchStatus, ProjectScoreDetail, ProjectStatus, BuyerMatch, BuyerMatchStatus, DFIMatch, DFIMatchStatus, DFIWindow, FinancingMemo, IncubationChecklist } from '../types/pipeline';
import { useAppSelector } from '../hooks/useRedux';
import { ProjectLifecycleTimeline } from '../components/pipeline/ProjectLifecycleTimeline';
import { ProjectHistoryTimeline } from '../components/pipeline/ProjectHistoryTimeline';
import { UserRole } from '../types/auth';
import api from '../services/api';
import ReadinessTab from '../components/pipeline/ReadinessTab';
import ScoutCoordsModal from '../components/geospatial/ScoutCoordsModal';

// Format a USD value as compact millions/thousands. Backend now stores all ticket
// sizes as raw USD (e.g. 25_000_000 → "$25M", 250_000 → "$250K").
const formatUSD = (val?: number | string | null): string => {
  if (val == null || val === '') return '—';
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (!isFinite(n)) return '—';
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
};

const formatTicketRange = (
  min?: number | string | null,
  max?: number | string | null,
): string => {
  if (min == null && max == null) return 'Ticket range N/A';
  if (min != null && max != null) return `${formatUSD(min)} – ${formatUSD(max)}`;
  if (min != null) return `${formatUSD(min)}+`;
  return `up to ${formatUSD(max)}`;
};

// Tier-group a list of matches into Strong (≥70) / Moderate (40-69) / Weak (<40).
type Tier = 'strong' | 'moderate' | 'weak';
const tierForScore = (score: number): Tier => {
  if (score >= 70) return 'strong';
  if (score >= 40) return 'moderate';
  return 'weak';
};
const TIER_META: Record<Tier, { label: string; color: string; defaultOpen: boolean }> = {
  strong:   { label: 'Strong fit (≥70)',    color: 'var(--sage)',  defaultOpen: true },
  moderate: { label: 'Moderate fit (40–69)', color: 'var(--navy)',  defaultOpen: true },
  weak:     { label: 'Weak fit (<40)',       color: 'var(--ink-400)', defaultOpen: false },
};

const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'financials' | 'documents' | 'history' | 'matches' | 'readiness' | 'impact'>('overview');
  // R8 — geospatial site analysis state (loaded on Overview tab)
  const [siteAnalysis, setSiteAnalysis] = useState<import('../types/pipeline').ProjectGeospatial | null>(null);
  const [analysingSite, setAnalysingSite] = useState(false);
  const [scoutModalOpen, setScoutModalOpen] = useState(false);
  // Polish 2 — all DFI windows in the catalogue, used to look up by investor name
  // for the "Windows offered" expansion under each investor card.
  const [allDfiWindows, setAllDfiWindows] = useState<DFIWindow[]>([]);
  const [expandedInvestors, setExpandedInvestors] = useState<Set<string>>(new Set());
  // R9 — impact monitoring state (loaded on Impact tab)
  const [impactEntries, setImpactEntries] = useState<import('../types/pipeline').ImpactLogEntry[]>([]);
  const [impactSummary, setImpactSummary] = useState<import('../types/pipeline').ImpactSummary | null>(null);
  const [showImpactModal, setShowImpactModal] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [matches, setMatches] = useState<InvestorMatch[]>([]);
  // Polish 4 — tier-grouping. Keys look like "investor-strong", "buyer-weak", etc.
  // When a key is in the set, the user has TOGGLED that tier (closed if default-open, opened if default-closed).
  const [expandedTiers, setExpandedTiers] = useState<Set<string>>(new Set());
  const toggleTier = (tierKey: string, defaultOpen: boolean) => {
    setExpandedTiers((prev) => {
      const next = new Set(prev);
      // We store the "toggled" state; the render uses defaultOpen XOR toggled.
      if (defaultOpen) {
        // Default open → toggling adds "closed" marker
        const closedKey = `${tierKey}-closed`;
        if (next.has(closedKey)) next.delete(closedKey); else next.add(closedKey);
      } else {
        // Default closed → toggling adds the key itself
        if (next.has(tierKey)) next.delete(tierKey); else next.add(tierKey);
      }
      return next;
    });
  };
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
  const [incubationChecklist, setIncubationChecklist] = useState<IncubationChecklist | null>(null);

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
        // R5 — only meaningful for INCUBATION projects, but endpoint enforces it.
        if (data?.status === ProjectStatus.INCUBATION) {
          fetchIncubationChecklist(projectId);
        }
        // R8 — cached site analysis (may not exist yet; returns null if so)
        pipelineService.getSiteAnalysis(projectId).then(setSiteAnalysis).catch(() => {});
        // Polish 2 — load DFI windows catalogue so investor cards can show offered windows
        pipelineService.listDFIWindows().then(setAllDfiWindows).catch(() => {});
        // R9 — impact monitoring data for COMMITTED / IMPLEMENTED projects
        if (data?.status === ProjectStatus.COMMITTED || data?.status === ProjectStatus.IMPLEMENTED) {
          pipelineService.listImpactLogEntries(projectId).then(setImpactEntries).catch(() => {});
          pipelineService.getImpactSummary(projectId).then(setImpactSummary).catch(() => {});
        }
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

  const fetchIncubationChecklist = async (id: string) => {
    try {
      const cl = await pipelineService.getIncubationChecklist(id);
      setIncubationChecklist(cl);
    } catch (e) {
      console.error("Failed to load incubation checklist", e);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const blob = await pipelineService.downloadFinancialModelTemplate();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'waiis_financial_model_template.xlsx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('template download failed', e);
      alert('Failed to download template.');
    }
  };

  const handleOpenChecklistUpload = (code: string) => {
    setDocumentType(code);
    setShowUploadModal(true);
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
      if (project?.status === ProjectStatus.INCUBATION) {
        await fetchIncubationChecklist(projectId);
      }

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

      {/* R5 — Incubation document checklist strip. Uses translucent rgba tints
          so it reads correctly against both light AND dark theme surfaces, with
          a purple left-border accent to mark its incubation context. */}
      {project?.status === ProjectStatus.INCUBATION && incubationChecklist && (
        <div style={{
          marginBottom: 16, padding: '16px 20px',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderLeft: '3px solid #7c3aed',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#a78bfa', fontWeight: 600 }}>⚗ Incubation checklist</div>
              <div style={{ fontSize: 13, color: 'var(--ink-700)', marginTop: 2 }}>
                {incubationChecklist.completed_count} of {incubationChecklist.total_count} documents attached
              </div>
            </div>
            <button
              onClick={handleDownloadTemplate}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: 'transparent', border: '1px solid rgba(124, 58, 237, 0.6)', color: '#a78bfa',
                padding: '6px 10px', fontSize: 12, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>download</span>
              Financial model template
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
            {incubationChecklist.items.map(item => (
              <button
                key={item.code}
                onClick={() => canEdit && !item.completed && handleOpenChecklistUpload(item.code)}
                disabled={!canEdit || item.completed}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 12px', fontSize: 12, fontFamily: 'inherit',
                  textAlign: 'left',
                  background: item.completed ? 'rgba(16, 185, 129, 0.08)' : 'transparent',
                  border: `1px solid ${item.completed ? 'rgba(16, 185, 129, 0.5)' : 'var(--border)'}`,
                  color: item.completed ? '#34d399' : 'var(--ink-700)',
                  cursor: canEdit && !item.completed ? 'pointer' : 'default',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: item.completed ? '#34d399' : 'var(--ink-400)' }}>
                  {item.completed ? 'check_circle' : 'radio_button_unchecked'}
                </span>
                <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ paddingTop: 8 }}>
        <div style={{ display: 'flex', gap: 28, borderBottom: '1px solid var(--border)', marginBottom: 28 }}>
          {[
            { key: 'overview', label: 'Overview' },
            { key: 'matches', label: 'Investor matches' },
            { key: 'financials', label: 'Financials' },
            { key: 'documents', label: 'Documents' },
            // R9 — Impact Monitoring tab only for COMMITTED / IMPLEMENTED projects
            ...((project?.status === ProjectStatus.COMMITTED || project?.status === ProjectStatus.IMPLEMENTED)
              ? [{ key: 'impact', label: '📊 Impact monitoring' }]
              : []),
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
                    ) : (() => {
                      const MATCH_STATUS_COLOR: Record<string, string> = {
                        INTERESTED: 'var(--sage)', CONTACTED: 'var(--navy)', DETECTED: 'var(--ink-500)',
                        COMMITTED: 'var(--accent)', DECLINED: 'var(--terra)',
                      };
                      // Group by tier so 20 rows don't dump into a flat list.
                      const grouped: Record<Tier, InvestorMatch[]> = { strong: [], moderate: [], weak: [] };
                      for (const m of matches) grouped[tierForScore(m.score)].push(m);

                      const renderCard = (match: InvestorMatch, last: boolean) => {
                        // Polish 2 — Match windows to this investor by name. The FK
                        // is one-way (window → investor), so we filter the catalogue
                        // here. String match against institution is forgiving across
                        // "African Development Bank (AfDB)" / "AfDB" variations.
                        const investorName = match.investor?.name || '';
                        const investorWindows = investorName
                          ? allDfiWindows.filter(w =>
                              w.institution && (
                                w.institution.toLowerCase().includes(investorName.toLowerCase()) ||
                                investorName.toLowerCase().includes(w.institution.toLowerCase())
                              )
                            )
                          : [];
                        const isExpanded = expandedInvestors.has(match.match_id);
                        return (
                        <React.Fragment key={match.match_id}>
                        <div style={{
                          display: 'grid', gridTemplateColumns: '1fr 80px 160px',
                          gap: 16, alignItems: 'center',
                          padding: '16px 24px',
                          borderBottom: (last && !isExpanded) ? 'none' : '1px solid var(--border)',
                        }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                              <span style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500 }}>
                                {match.investor?.name || 'Unknown Investor'}
                              </span>
                              {investorWindows.length > 0 && (
                                <button
                                  onClick={() => {
                                    setExpandedInvestors(prev => {
                                      const next = new Set(prev);
                                      next.has(match.match_id) ? next.delete(match.match_id) : next.add(match.match_id);
                                      return next;
                                    });
                                  }}
                                  style={{
                                    background: 'transparent', cursor: 'pointer',
                                    padding: '1px 6px', fontSize: 10, color: '#a78bfa',
                                    fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 3,
                                    borderRadius: 3, border: '1px solid rgba(124,58,237,0.4)',
                                  }}
                                  title="Show DFI windows offered by this investor"
                                >
                                  {investorWindows.length} window{investorWindows.length !== 1 ? 's' : ''}
                                  <span className="material-symbols-outlined" style={{ fontSize: 12, transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
                                    expand_more
                                  </span>
                                </button>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--ink-500)', lineHeight: 1.45 }}>
                              {match.investor?.sector_preferences?.join(', ') || 'No specific strategy'}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--ink-600)', marginTop: 6, fontFamily: "'Geist Mono', monospace" }}>
                              {formatTicketRange(match.investor?.ticket_size_min, match.investor?.ticket_size_max)}
                              {match.investor?.geographic_focus?.length ? ` · ${match.investor.geographic_focus[0]}` : ''}
                            </div>
                            {match.notes && (
                              <div style={{ fontSize: 10, color: 'var(--ink-500)', marginTop: 8, lineHeight: 1.55, fontStyle: 'italic' }}>
                                {match.notes}
                              </div>
                            )}
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
                        {/* Polish 2 — Expanded "Windows offered" row */}
                        {isExpanded && investorWindows.length > 0 && (
                          <div style={{
                            padding: '10px 24px 14px 40px',
                            background: 'rgba(124, 58, 237, 0.04)',
                            borderBottom: last ? 'none' : '1px solid var(--border)',
                          }}>
                            <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#a78bfa', fontWeight: 600, marginBottom: 6 }}>
                              Windows offered by {investorName}
                            </div>
                            <div style={{ display: 'grid', gap: 4 }}>
                              {investorWindows.map(w => (
                                <div key={w.id} style={{
                                  display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 12,
                                  padding: '6px 10px', fontSize: 11,
                                  border: '1px solid var(--border)',
                                  background: 'var(--surface)',
                                  alignItems: 'center',
                                }}>
                                  <div>
                                    <span style={{ color: 'var(--ink-900)', fontWeight: 500 }}>{w.name}</span>
                                    {w.description && (
                                      <span style={{ color: 'var(--ink-500)', marginLeft: 6 }}>· {w.description.slice(0, 80)}{w.description.length > 80 ? '…' : ''}</span>
                                    )}
                                  </div>
                                  <span style={{ fontSize: 9, padding: '1px 6px', background: 'rgba(124,58,237,0.18)', color: '#a78bfa', borderRadius: 3, letterSpacing: '0.04em' }}>
                                    {w.instrument_type}
                                  </span>
                                  <span style={{ fontSize: 10, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace" }}>
                                    {w.min_size_usd ? `$${(w.min_size_usd / 1e6).toFixed(0)}M` : '—'}
                                    {w.max_size_usd ? `–$${(w.max_size_usd / 1e6).toFixed(0)}M` : '+'}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        </React.Fragment>
                        );
                      };

                      return (['strong', 'moderate', 'weak'] as Tier[]).map((tier) => {
                        const items = grouped[tier];
                        if (items.length === 0) return null;
                        const meta = TIER_META[tier];
                        const showOpen = meta.defaultOpen
                          ? !expandedTiers.has(`investor-${tier}-closed`)
                          : expandedTiers.has(`investor-${tier}`);
                        return (
                          <div key={tier}>
                            <button
                              onClick={() => toggleTier(`investor-${tier}`, meta.defaultOpen)}
                              style={{
                                width: '100%', padding: '10px 24px', textAlign: 'left',
                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                background: 'var(--surface-elevated, rgba(255,255,255,0.02))',
                                border: 'none', borderTop: tier !== 'strong' ? '1px solid var(--border)' : 'none',
                                borderBottom: '1px solid var(--border)',
                                cursor: 'pointer', color: 'var(--ink-700)',
                              }}
                            >
                              <span style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                                <span style={{ width: 6, height: 6, borderRadius: '50%', background: meta.color }} />
                                {meta.label}
                                <span style={{ color: 'var(--ink-400)', fontWeight: 400 }}>· {items.length}</span>
                              </span>
                              <span className="material-symbols-outlined" style={{ fontSize: 16, transform: showOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
                                expand_more
                              </span>
                            </button>
                            {showOpen && items.map((m, idx) => renderCard(m, idx === items.length - 1))}
                          </div>
                        );
                      });
                    })()}
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

          {/* R9 — Impact Monitoring Tab */}
          {activeTab === 'impact' && (
            <section>
              <div style={sectionHeadStyle}>
                <h2 style={sectionTitleStyle}>Impact monitoring</h2>
                {canEdit && (
                  <button
                    onClick={() => setShowImpactModal(true)}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                      padding: '7px 14px', fontSize: 12, fontWeight: 500,
                      cursor: 'pointer', fontFamily: 'inherit',
                    }}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
                    Log quarter
                  </button>
                )}
              </div>

              {/* Metric cards — actual vs target with progress bars */}
              {impactSummary && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 20 }}>
                  {[
                    { label: 'Jobs created', actual: impactSummary.actual_jobs, target: impactSummary.target_jobs, color: 'var(--accent)' },
                    { label: 'GHG avoided (tCO₂e)', actual: impactSummary.actual_ghg_tco2, target: impactSummary.target_ghg_tco2, color: '#34d399' },
                    { label: 'Smallholders reached', actual: impactSummary.actual_smallholders, target: impactSummary.target_smallholders, color: '#60a5fa' },
                    { label: 'Investment deployed (USD)', actual: Number(impactSummary.actual_investment_deployed) || 0, target: Number(impactSummary.target_investment_usd) || 0, color: '#fbbf24' },
                  ].map(({ label, actual, target, color }) => {
                    const pct = target && target > 0 ? Math.min(100, (Number(actual) / Number(target)) * 100) : 0;
                    return (
                      <div key={label} style={{
                        background: 'var(--surface)', border: '1px solid var(--border)',
                        padding: 14,
                      }}>
                        <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 6 }}>{label}</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                          <span style={{ fontFamily: "'Source Serif 4', serif", fontSize: 22, color: 'var(--ink-900)' }}>
                            {typeof actual === 'number' && actual >= 1000 ? actual.toLocaleString() : actual}
                          </span>
                          <span style={{ fontSize: 11, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace" }}>
                            / {target == null ? '—' : (typeof target === 'number' && target >= 1000 ? target.toLocaleString() : target)}
                          </span>
                        </div>
                        <div style={{ height: 3, background: 'var(--ink-100)', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: color }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Historical table */}
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                {impactEntries.length === 0 ? (
                  <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)' }}>
                    No quarterly entries yet. Click "Log quarter" to record actuals for the most recent reporting period.
                  </div>
                ) : (
                  <>
                    <div style={{
                      display: 'grid', gridTemplateColumns: '1fr 0.8fr 0.8fr 1fr 1fr 1.2fr',
                      padding: '10px 20px', borderBottom: '1px solid var(--border)',
                      background: 'rgba(255,255,255,0.02)',
                      fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-500)',
                    }}>
                      <div>Period</div>
                      <div style={{ textAlign: 'right' }}>Jobs</div>
                      <div style={{ textAlign: 'right' }}>Smallholders</div>
                      <div style={{ textAlign: 'right' }}>GHG (tCO₂)</div>
                      <div style={{ textAlign: 'right' }}>$ Deployed</div>
                      <div>Notes</div>
                    </div>
                    {impactEntries.map((e, i) => (
                      <div key={e.id} style={{
                        display: 'grid', gridTemplateColumns: '1fr 0.8fr 0.8fr 1fr 1fr 1.2fr',
                        padding: '12px 20px',
                        borderBottom: i < impactEntries.length - 1 ? '1px solid var(--border)' : 'none',
                        fontSize: 12, color: 'var(--ink-700)', alignItems: 'center',
                      }}>
                        <div style={{ fontWeight: 500, color: 'var(--ink-900)' }}>{e.period_label}</div>
                        <div style={{ textAlign: 'right', fontFamily: "'Geist Mono', monospace" }}>{e.jobs_created ?? '—'}</div>
                        <div style={{ textAlign: 'right', fontFamily: "'Geist Mono', monospace" }}>{e.smallholders_reached ?? '—'}</div>
                        <div style={{ textAlign: 'right', fontFamily: "'Geist Mono', monospace" }}>{e.ghg_avoided_tco2 ?? '—'}</div>
                        <div style={{ textAlign: 'right', fontFamily: "'Geist Mono', monospace" }}>
                          {e.investment_deployed_usd ? `$${(Number(e.investment_deployed_usd) / 1e6).toFixed(2)}M` : '—'}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--ink-500)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {e.notes || ''}
                        </div>
                      </div>
                    ))}
                  </>
                )}
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

          {/* Site analysis — sidebar widget (replaces Quick facts) */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '18px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)' }}>
                Site analysis
              </div>
              {(project.site_lat != null && project.site_lon != null) && (
                <button
                  onClick={async () => {
                    if (!projectId) return;
                    setAnalysingSite(true);
                    try {
                      const res = await pipelineService.analyseSite(projectId);
                      setSiteAnalysis(res);
                    } catch (e) {
                      console.error('analyse-site failed', e);
                    } finally {
                      setAnalysingSite(false);
                    }
                  }}
                  disabled={analysingSite}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    background: 'transparent', border: '1px solid var(--border)',
                    color: 'var(--ink-700)', padding: '3px 8px', fontSize: 11,
                    cursor: analysingSite ? 'default' : 'pointer', fontFamily: 'inherit',
                    opacity: analysingSite ? 0.6 : 1,
                  }}
                  title={siteAnalysis ? 'Re-run analysis (bypass cache)' : 'Run analysis'}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 14 }}>satellite_alt</span>
                  {analysingSite ? '…' : (siteAnalysis ? 'Re-analyse' : 'Run')}
                </button>
              )}
            </div>

            {/* No coordinates yet */}
            {(project.site_lat == null || project.site_lon == null) && (
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 12, color: 'var(--ink-500)', lineHeight: 1.6 }}>
                  No site coordinates yet. Edit the project to drop a pin, or let Martin scout plausible coordinates from the project content.
                </div>
                <button
                  onClick={() => setScoutModalOpen(true)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    background: '#4f46e5', color: '#fff', border: 'none',
                    padding: '7px 12px', fontSize: 12, fontWeight: 500,
                    cursor: 'pointer', borderRadius: 4, fontFamily: 'inherit',
                    width: 'fit-content',
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 15 }}>auto_awesome</span>
                  Scout coordinates with Martin
                </button>
              </div>
            )}

            {/* Coordinates set, analysis not yet run */}
            {(project.site_lat != null && project.site_lon != null && !siteAnalysis) && (
              <div style={{ marginTop: 14, fontSize: 12, color: 'var(--ink-500)' }}>
                Pinned at {project.site_lat.toFixed(3)}, {project.site_lon.toFixed(3)}. Click <strong>Run</strong> to fetch satellite signals.
              </div>
            )}

            {/* Analysis present */}
            {siteAnalysis && (
              <div style={{ marginTop: 12 }}>
                {/* Source banner — compact */}
                {siteAnalysis.source === 'copernicus' && (
                  <div style={{
                    background: 'rgba(34, 197, 94, 0.12)', borderLeft: '3px solid #16a34a',
                    padding: '6px 10px', borderRadius: 4, fontSize: 11, color: 'var(--ink-700)', marginBottom: 10,
                  }}>
                    ✓ Live Sentinel-2 — {siteAnalysis.analysed_at ? new Date(siteAnalysis.analysed_at).toLocaleDateString() : '—'}
                  </div>
                )}
                {siteAnalysis.source === 'fixture' && (
                  <div style={{
                    background: 'rgba(245, 158, 11, 0.12)', borderLeft: '3px solid #f59e0b',
                    padding: '6px 10px', borderRadius: 4, fontSize: 11, color: 'var(--ink-700)', marginBottom: 10,
                  }}>
                    Reference fixture — credentials not configured
                  </div>
                )}
                {siteAnalysis.source === 'stub' && (
                  <div style={{
                    background: 'rgba(245, 158, 11, 0.12)', borderLeft: '3px solid #f59e0b',
                    padding: '6px 10px', borderRadius: 4, fontSize: 11, color: 'var(--ink-700)', marginBottom: 10,
                  }}>
                    ⚠ Synthetic placeholder
                  </div>
                )}

                {/* Metric rows */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {[
                    ['NDVI', siteAnalysis.ndvi.toFixed(3)],
                    ['Water proximity', `${siteAnalysis.water_proximity_km.toFixed(1)} km`],
                    ['Smallholder land', `${siteAnalysis.land_use_smallholder_pct.toFixed(0)}%`],
                    ['EUDR risk', null],
                    ['Land cover', siteAnalysis.land_use_description],
                  ].map(([k, v], i, arr) => (
                    <div key={k as string} style={{
                      display: 'grid', gridTemplateColumns: '100px 1fr', gap: 12,
                      padding: '8px 0', fontSize: 12,
                      borderBottom: i === arr.length - 1 ? 'none' : '1px solid var(--border)',
                      alignItems: 'center',
                    }}>
                      <span style={{ color: 'var(--ink-500)' }}>{k}</span>
                      {k === 'EUDR risk' ? (
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', fontSize: 10, fontWeight: 600,
                          width: 'fit-content',
                          background: siteAnalysis.deforestation_risk === 'high' ? 'rgba(239,68,68,0.18)'
                            : siteAnalysis.deforestation_risk === 'medium' ? 'rgba(245,158,11,0.18)'
                            : 'rgba(16,185,129,0.18)',
                          color: siteAnalysis.deforestation_risk === 'high' ? '#f87171'
                            : siteAnalysis.deforestation_risk === 'medium' ? '#fbbf24'
                            : '#34d399',
                          textTransform: 'uppercase', letterSpacing: '0.06em',
                          borderRadius: 3,
                        }}>{siteAnalysis.deforestation_risk}</span>
                      ) : (
                        <span style={{ color: 'var(--ink-900)' }}>{v}</span>
                      )}
                    </div>
                  ))}
                </div>

                {/* Boost summary */}
                <div style={{
                  marginTop: 10, padding: '7px 10px', background: 'rgba(124,58,237,0.06)',
                  border: '1px solid var(--border)', fontSize: 11,
                  display: 'flex', justifyContent: 'flex-end',
                }}>
                  <span style={{ color: '#a78bfa', fontWeight: 600 }}>
                    +{siteAnalysis.geo_score_boost} pts → Readiness
                  </span>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Scout coordinates modal */}
      {scoutModalOpen && projectId && (
        <ScoutCoordsModal
          projectId={projectId}
          onClose={() => setScoutModalOpen(false)}
          onConfirm={async (lat, lon, place_name) => {
            // Persist coords + optional place name, then run analyse
            await pipelineService.updateProject(projectId, {
              site_lat: lat,
              site_lon: lon,
              site_location_name: place_name || undefined,
            });
            // Refresh project so the widget shows the new coords
            const fresh = await pipelineService.getProject(projectId);
            setProject(fresh);
            // Trigger analysis (force=true bypasses cache for a fresh first read)
            try {
              const res = await pipelineService.analyseSite(projectId, true);
              setSiteAnalysis(res);
            } catch (e) {
              console.error('Post-scout analyse failed', e);
            }
          }}
        />
      )}

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
                  <optgroup label="Incubation checklist (R5)">
                    <option value="FEASIBILITY">Preliminary Feasibility Study</option>
                    <option value="LAND_RIGHTS">Land Rights / Site Control</option>
                    <option value="GOV_SUPPORT">Government Support Letter</option>
                    <option value="ENV_ASSESSMENT">Environmental Pre-Assessment</option>
                    <option value="FINANCIAL_MODEL">Financial Model</option>
                    <option value="CORE_TEAM">Core Project Team</option>
                  </optgroup>
                  <optgroup label="Other / legacy">
                    <option value="feasibility_study">Feasibility Study (legacy)</option>
                    <option value="esia">ESIA Report</option>
                    <option value="financial_model">Financial Model (legacy)</option>
                    <option value="government_support">Government Support Letter (legacy)</option>
                    <option value="investment_memo">Investment Memo</option>
                    <option value="technical_spec">Technical Specification</option>
                    <option value="other">Other</option>
                  </optgroup>
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
              {financingMemo.source === 'default_fallback' && (
                <div style={{
                  padding: '12px 14px', marginBottom: 16,
                  background: 'rgba(255, 184, 0, 0.08)',
                  border: '1px solid rgba(255, 184, 0, 0.4)',
                  borderLeft: '3px solid #f5a623',
                  borderRadius: 2,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#f5a623' }}>warning</span>
                    <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#a87000' }}>
                      AI advisor unavailable
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--ink-700)', lineHeight: 1.55 }}>
                    The capital-stack breakdown below is a static default (60/30/10), <strong>not</strong> a recommendation grounded in this project. Please retry, or have a finance specialist structure manually.
                    {financingMemo.error_class && (
                      <span style={{ display: 'block', marginTop: 4, fontSize: 10, fontFamily: "'Geist Mono', monospace", color: 'var(--ink-500)' }}>
                        Error class: {financingMemo.error_class}
                      </span>
                    )}
                  </div>
                </div>
              )}
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
              {/* R7 — Capital-stack tranches with seniority, amounts, terms */}
              {financingMemo.tranches && financingMemo.tranches.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>
                    Tranche Structure
                  </div>
                  {[...financingMemo.tranches].sort((a, b) => a.seniority - b.seniority).map((t, i) => {
                    const instrColor =
                      t.instrument_type === 'GRANT' ? 'var(--sage)'
                      : t.instrument_type === 'CONCESSIONAL_LOAN' ? 'var(--navy)'
                      : t.instrument_type === 'EQUITY' ? '#a855f7'
                      : 'var(--accent)';
                    return (
                      <div key={i} style={{
                        padding: '10px 12px', marginBottom: 6,
                        border: '1px solid var(--border)', borderLeft: `3px solid ${instrColor}`,
                        background: 'var(--surface-elevated, rgba(255,255,255,0.02))',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-900)' }}>
                            {t.label}
                            {t.is_first_loss && (
                              <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 5px', background: '#f5a623', color: '#000', borderRadius: 2, letterSpacing: '0.05em' }}>
                                FIRST-LOSS
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: 13, fontFamily: "'Geist Mono', monospace", color: 'var(--ink-800)' }}>
                            ${(t.amount_usd / 1e6).toFixed(2)}M
                          </div>
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--ink-500)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                          <span>Seniority {t.seniority}</span>
                          <span>{t.instrument_type.replace('_', ' ')}</span>
                          {t.tenor_years != null && <span>{t.tenor_years}yr tenor</span>}
                          {t.coupon_pct != null && <span>{t.coupon_pct}% coupon</span>}
                          {t.dfi_window_name && <span>· {t.dfi_window_name}</span>}
                        </div>
                        {t.notes && (
                          <div style={{ marginTop: 4, fontSize: 11, color: 'var(--ink-600)', lineHeight: 1.5 }}>{t.notes}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
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

      {/* R9 — Log impact entry modal */}
      {showImpactModal && projectId && (
        <ImpactLogModal
          projectId={projectId}
          onClose={() => setShowImpactModal(false)}
          onCreated={async () => {
            setShowImpactModal(false);
            const [entries, summary] = await Promise.all([
              pipelineService.listImpactLogEntries(projectId),
              pipelineService.getImpactSummary(projectId),
            ]);
            setImpactEntries(entries);
            setImpactSummary(summary);
          }}
        />
      )}
    </div>
  );
};

// R9 — Log quarter modal. Local component so it stays close to the data it writes.
const ImpactLogModal: React.FC<{ projectId: string; onClose: () => void; onCreated: () => void }> = ({ projectId, onClose, onCreated }) => {
  const today = new Date();
  const q = Math.floor(today.getMonth() / 3) + 1;
  const [periodLabel, setPeriodLabel] = useState(`Q${q} ${today.getFullYear()}`);
  const [periodStart, setPeriodStart] = useState(`${today.getFullYear()}-${String((q-1)*3 + 1).padStart(2, '0')}-01`);
  const [periodEnd, setPeriodEnd] = useState(`${today.getFullYear()}-${String(q*3).padStart(2, '0')}-${q === 1 ? 31 : q === 2 ? 30 : q === 3 ? 30 : 31}`);
  const [jobs, setJobs] = useState('');
  const [smallholders, setSmallholders] = useState('');
  const [ghg, setGhg] = useState('');
  const [women, setWomen] = useState('');
  const [youth, setYouth] = useState('');
  const [deployed, setDeployed] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await pipelineService.createImpactLogEntry(projectId, {
        period_label: periodLabel,
        period_start: periodStart,
        period_end: periodEnd,
        jobs_created: jobs ? Number(jobs) : null,
        smallholders_reached: smallholders ? Number(smallholders) : null,
        ghg_avoided_tco2: ghg ? Number(ghg) : null,
        women_jobs_actual: women ? Number(women) : null,
        youth_jobs_actual: youth ? Number(youth) : null,
        investment_deployed_usd: deployed ? Number(deployed) : null,
        notes: notes || null,
      });
      onCreated();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create entry');
    } finally {
      setSubmitting(false);
    }
  };

  const fieldStyle: React.CSSProperties = {
    background: 'var(--surface)', border: '1px solid var(--border)',
    color: 'var(--ink-900)', padding: '7px 10px', fontSize: 13,
    fontFamily: 'inherit', outline: 'none', width: '100%',
  };
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
    color: 'var(--ink-500)', marginBottom: 4,
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 600, margin: 16, maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-400)', marginBottom: 4 }}>R9 · Impact Monitoring</div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink-900)', margin: 0 }}>Log quarterly actuals</h3>
        </div>
        <div style={{ padding: '20px 24px', display: 'grid', gap: 14 }}>
          <div>
            <label style={labelStyle}>Period label</label>
            <input style={fieldStyle} value={periodLabel} onChange={e => setPeriodLabel(e.target.value)} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Period start</label>
              <input style={fieldStyle} type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>Period end</label>
              <input style={fieldStyle} type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Jobs created</label>
              <input style={fieldStyle} type="number" value={jobs} onChange={e => setJobs(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>Smallholders reached</label>
              <input style={fieldStyle} type="number" value={smallholders} onChange={e => setSmallholders(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>GHG avoided (tCO₂e)</label>
              <input style={fieldStyle} type="number" step="0.1" value={ghg} onChange={e => setGhg(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>Investment deployed (USD)</label>
              <input style={fieldStyle} type="number" value={deployed} onChange={e => setDeployed(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>Women jobs</label>
              <input style={fieldStyle} type="number" value={women} onChange={e => setWomen(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>Youth jobs</label>
              <input style={fieldStyle} type="number" value={youth} onChange={e => setYouth(e.target.value)} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Notes</label>
            <textarea style={{ ...fieldStyle, minHeight: 60, resize: 'vertical' }} value={notes} onChange={e => setNotes(e.target.value)} />
          </div>
          {error && (
            <div style={{ padding: '8px 12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.4)', fontSize: 12, color: '#f87171' }}>
              {error}
            </div>
          )}
        </div>
        <div style={{ padding: '14px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button onClick={onClose} disabled={submitting} style={{ padding: '8px 16px', fontSize: 12, fontWeight: 500, cursor: 'pointer', background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', fontFamily: 'inherit' }}>
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={submitting || !periodLabel || !periodStart || !periodEnd} style={{ padding: '8px 16px', fontSize: 12, fontWeight: 500, cursor: 'pointer', background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)', fontFamily: 'inherit' }}>
            {submitting ? 'Saving…' : 'Save entry'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProjectDetails;
