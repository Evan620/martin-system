import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';


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

  // Project data mapping
  const projectsData: Record<string, ProjectData> = {
    '#ECW-2024-001': {
      id: '#ECW-2024-001',
      name: 'West African Rail Link',
      pillar: 'Infrastructure',
      fundingAsk: '$1.2B',
      leadCountry: 'Nigeria',
    },
    '#ECW-2024-042': {
      id: '#ECW-2024-042',
      name: 'Solar Grid Expansion',
      pillar: 'Energy',
      fundingAsk: '$450M',
      leadCountry: 'Ghana',
    },
    '#ECW-2024-088': {
      id: '#ECW-2024-088',
      name: 'Agribusiness Hub',
      pillar: 'Agribusiness and Food Systems Transformation',
      fundingAsk: '$85M',
      leadCountry: "Côte d'Ivoire",
    },
    '#ECW-2024-102': {
      id: '#ECW-2024-102',
      name: 'Tech City Phase 1',
      pillar: 'Technology',
      fundingAsk: '$2.1B',
      leadCountry: 'Senegal',
    },
  };

  const projectData = projectsData[decodeURIComponent(projectId || '')] || projectsData['#ECW-2024-001'];

  useEffect(() => {
    // Auto-generate memo when page loads
    generateMemo();
  }, [projectId]);

  const generateMemo = async () => {
    setIsGenerating(true);
    setError('');
    setMemoContent('');

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
          message: `Write a 500-word investment memo for ${projectData.name} (ID: ${projectData.id}, Sector: ${projectData.pillar}, Investment: ${projectData.fundingAsk}, Country: ${projectData.leadCountry}).

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
    }
  };

  const exportMemo = () => {
    const blob = new Blob([memoContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectData.name.replace(/\s+/g, '_')}_Investment_Memo.txt`;
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
          onClick={() => navigate(`/deal-pipeline/${encodeURIComponent(projectData.id)}`)}
          className="hover:text-primary transition-colors"
        >
          {projectData.name}
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
              <div className="flex items-center gap-2 px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm font-medium">
                <div className="w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                <span>AI Generating...</span>
              </div>
            )}
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            AI-Generated Investment Analysis for {projectData.name}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={copyToClipboard}
            disabled={!memoContent || isGenerating}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">content_copy</span>
            Copy
          </button>
          <button
            onClick={exportMemo}
            disabled={!memoContent || isGenerating}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            Export
          </button>
          <button
            onClick={generateMemo}
            disabled={isGenerating}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg shadow-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[18px]">refresh</span>
            Regenerate
          </button>
        </div>
      </div>

      {/* AI Info Banner */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-100 dark:border-purple-800/50 rounded-xl p-4 flex items-start gap-4">
        <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm shrink-0 text-purple-600 dark:text-purple-400">
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

          {!isGenerating && !memoContent && !error && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <span className="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600 mb-4">
                description
              </span>
              <p className="text-slate-600 dark:text-slate-400 font-medium">No memo generated yet</p>
              <button
                onClick={generateMemo}
                className="mt-4 flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg shadow-md hover:bg-blue-700 transition-colors"
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
