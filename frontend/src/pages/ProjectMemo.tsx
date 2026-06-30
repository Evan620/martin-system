import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';


// UUID generator function
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

interface ProjectData {
  id: string;
  name: string;
  pillar: string;
  fundingAsk: string;
  leadCountry: string;
}

const ProjectMemo: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [isGenerating, setIsGenerating] = useState(false);
  const [memoContent, setMemoContent] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [projectData, setProjectData] = useState<ProjectData | null>(null);
  const [hasGenerated, setHasGenerated] = useState(false);

  const fmtMoney = (amount?: number) => {
    if (!amount) return 'N/A';
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(0)}M`;
    return `$${amount.toLocaleString()}`;
  };

  // Fetch the real project for this route, then auto-generate the memo.
  useEffect(() => {
    let cancelled = false;
    const id = decodeURIComponent(projectId || '');

    const load = async () => {
      try {
        const project = await pipelineService.getProject(id);
        if (cancelled) return;
        const data: ProjectData = {
          id: project.id || id,
          name: project.name || id,
          pillar: project.pillar || 'N/A',
          fundingAsk: fmtMoney(project.investment_size),
          leadCountry: project.lead_country || 'N/A',
        };
        setProjectData(data);
        generateMemo(data);
      } catch (err) {
        if (cancelled) return;
        console.error('Error loading project:', err);
        // Graceful fallback: show the id rather than a fake name.
        const data: ProjectData = {
          id,
          name: id,
          pillar: 'N/A',
          fundingAsk: 'N/A',
          leadCountry: 'N/A',
        };
        setProjectData(data);
        generateMemo(data);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const generateMemo = async (project?: ProjectData) => {
    const target = project || projectData;
    if (!target) return;

    setIsGenerating(true);
    setError('');
    setMemoContent('');
    setHasGenerated(false);

    try {
      // Use API_URL from services/api to ensure HTTPS and authorization
      const baseUrl = (await import('../services/api')).API_URL;

      const response = await fetch(`${baseUrl}/agents/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          message: `Write a 500-word investment memo for ${target.name} (ID: ${target.id}, Sector: ${target.pillar}, Investment: ${target.fundingAsk}, Country: ${target.leadCountry}).

Include: Executive Summary, Strategic Rationale (3-4 bullets), Financial Overview, Regional Impact (2-3 bullets), Risk Considerations (2-3 risks), Recommendation.

Use formal business language, clear headings, bullet points. No emojis.`,
          conversation_id: generateUUID(),
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error Response:', errorText);
        throw new Error(`Failed to generate memo: ${response.status} - ${errorText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');

          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                // Handle response event with the agent's message
                if (data.type === 'response' && data.message?.content) {
                  setMemoContent(data.message.content);
                }
                // Handle error event
                else if (data.type === 'error') {
                  setError(data.error || data.message || 'An error occurred');
                }
                // Handle done event
                else if (data.type === 'done') {
                  console.log('Memo generation completed');
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e, 'Line:', line);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Error generating memo:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate memo. Please try again.';
      setError(errorMessage);
    } finally {
      setIsGenerating(false);
      setHasGenerated(true);
    }
  };

  const exportMemo = () => {
    const blob = new Blob([memoContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(projectData?.name || 'Project').replace(/\s+/g, '_')}_Investment_Memo.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(memoContent);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
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
        <button
          onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(projectData?.id || decodeURIComponent(projectId || ''))}`)}
          className="hover:text-primary transition-colors"
        >
          {projectData?.name || 'Project'}
        </button>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-slate-900 dark:text-white font-medium">Investment Memo</span>
      </div>

      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-start gap-3">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white leading-tight tracking-tight">
              Investment Memo
            </h1>
            {isGenerating && (
              <div className="flex items-center gap-2 px-3 py-1 bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded-full text-sm font-medium">
                <div className="w-4 h-4 border-2 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
                <span>AI Generating...</span>
              </div>
            )}
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            AI-Generated Investment Analysis for {projectData?.name || 'this project'}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={copyToClipboard}
            disabled={!memoContent || isGenerating}
            className="clickable-scale flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">content_copy</span>
            Copy
          </button>
          <button
            onClick={exportMemo}
            disabled={!memoContent || isGenerating}
            className="clickable-scale flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            Export
          </button>
          <button
            onClick={() => generateMemo()}
            disabled={isGenerating}
            className="clickable-scale flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg shadow-md hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">refresh</span>
            Regenerate
          </button>
        </div>
      </div>

      {/* AI Info Banner */}
      <div className="bg-teal-50 dark:bg-teal-900/20 border border-teal-100 dark:border-teal-800/50 rounded-xl p-4 flex items-start gap-4">
        <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm shrink-0 text-teal-600 dark:text-teal-400">
          <span className="material-symbols-outlined">auto_awesome</span>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">AI-Powered Analysis</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
            This investment memo has been generated by our AI Supervisor Agent using advanced analysis of project
            data, market conditions, and regional development priorities.
          </p>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3">
          <span className="material-symbols-outlined text-red-600 dark:text-red-400">error</span>
          <div>
            <h4 className="text-sm font-bold text-red-900 dark:text-red-200">Error Generating Memo</h4>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Memo Content */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="p-6 md:p-8">
          {isGenerating && !memoContent && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-slate-600 dark:text-slate-400 font-medium">
                Generating investment memo with AI...
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">
                This may take 30-60 seconds
              </p>
            </div>
          )}

          {memoContent && (
            <div className="prose prose-slate dark:prose-invert max-w-none">
              <div className="whitespace-pre-wrap text-slate-800 dark:text-slate-200 leading-relaxed">
                {memoContent}
              </div>
            </div>
          )}

          {!isGenerating && !memoContent && !error && hasGenerated && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <span className="material-symbols-outlined text-6xl text-amber-400 dark:text-amber-500 mb-4">
                error_outline
              </span>
              <p className="text-slate-700 dark:text-slate-300 font-medium">
                The memo generator returned no content
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-500 mt-2 max-w-md">
                The AI completed without producing a memo. This is usually a temporary issue &mdash; try regenerating.
              </p>
              <button
                onClick={() => generateMemo()}
                className="clickable-scale mt-4 flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg shadow-md hover:bg-teal-700 transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">refresh</span>
                Regenerate
              </button>
            </div>
          )}

          {!isGenerating && !memoContent && !error && !hasGenerated && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <span className="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600 mb-4">
                description
              </span>
              <p className="text-slate-600 dark:text-slate-400 font-medium">No memo generated yet</p>
              <button
                onClick={() => generateMemo()}
                className="clickable-scale mt-4 flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg shadow-md hover:bg-teal-700 transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                Generate Memo
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProjectMemo;
