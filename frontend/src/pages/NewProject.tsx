import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const NewProject: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const [formData, setFormData] = useState({
    name: '',
    pillar: 'Infrastructure',
    leadCountry: '',
    leadCompany: '',
    investment: '',
    description: '',
    currency: 'USD',
    icon: 'business',
    iconColor: 'blue',
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

  const handlePillarChange = (pillar: string) => {
    const selectedPillar = pillars.find(p => p.value === pillar);
    setFormData({
      ...formData,
      pillar,
      icon: selectedPillar?.icon || 'business',
      iconColor: selectedPillar?.color || 'blue',
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      console.log('Starting project creation...');

      // Parse investment amount (remove $ and convert M/B to number)
      const investmentStr = formData.investment.replace(/[$,]/g, '');
      let investmentAmount = 0;

      if (investmentStr.includes('B')) {
        investmentAmount = parseFloat(investmentStr.replace('B', '')) * 1000000000;
      } else if (investmentStr.includes('M')) {
        investmentAmount = parseFloat(investmentStr.replace('M', '')) * 1000000;
      } else {
        investmentAmount = parseFloat(investmentStr);
      }

      console.log('Investment amount:', investmentAmount);

      // Get token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found. Please log in again.');
      }

      let investmentMemoId = null;

      // Skip document upload for now - will be added after project creation
      // Document upload requires TWG to be set up first
      if (uploadedFiles.length > 0) {
        console.log(`Note: ${uploadedFiles.length} documents selected. Documents will need to be uploaded separately after project creation.`);
        // TODO: Implement document upload after TWGs are properly set up
      }

      // First, get the TWG ID based on the pillar
      console.log('Fetching TWGs...');
      let twgId = null;

      try {
        const twgsResponse = await api.get('/twgs/');

        console.log('Available TWGs:', twgsResponse.data);

        if (twgsResponse.data && twgsResponse.data.length > 0) {
          // Map pillar to TWG pillar enum
          const pillarMap: Record<string, string> = {
            'Infrastructure': 'critical_minerals_industrialization',
            'Energy': 'energy_infrastructure',
            'Agribusiness and Food Systems Transformation': 'agriculture_food_systems',
            'Technology': 'digital_economy_transformation',
          };

          const targetPillar = pillarMap[formData.pillar];
          const twg = twgsResponse.data.find((t: any) => t.pillar === targetPillar);

          if (twg) {
            twgId = twg.id;
            console.log('Found TWG:', twgId);
          } else {
            // Use first available TWG as fallback
            twgId = twgsResponse.data[0].id;
            console.log('Using first available TWG as fallback:', twgId);
          }
        } else {
          console.warn('No TWGs found in the system');
        }
      } catch (twgErr: any) {
        console.error('Failed to fetch TWGs:', twgErr);
        // Continue without TWG - we'll use a placeholder
      }

      if (!twgId) {
        // Use a placeholder UUID for now
        // In production, this should create a default TWG or require admin setup
        console.warn('No TWG available - using placeholder. Projects may need TWG assignment later.');
        twgId = '00000000-0000-0000-0000-000000000001';
      }

      // Create project via API
      const projectData: any = {
        twg_id: twgId,
        name: formData.name,
        description: formData.description,
        investment_size: investmentAmount,
        currency: formData.currency,
        readiness_score: 0,
        strategic_alignment_score: 0,
        pillar: formData.pillar,
        lead_country: formData.leadCountry,
        status: 'identified',
        metadata_json: {
          leadCompany: formData.leadCompany,
          icon: formData.icon,
          iconColor: formData.iconColor,
        }
      };

      // Add investment memo ID if document was uploaded
      if (investmentMemoId) {
        projectData.investment_memo_id = investmentMemoId;
      }

      console.log('Creating project with data:', projectData);

      const response = await api.post('/pipeline/ingest', projectData, {
        timeout: 30000 // 30 second timeout
      });

      console.log('Project created successfully:', response.data);

      // Show success message
      alert('Project created successfully!');

      // Navigate to the project details page or back to pipeline
      navigate('/deal-pipeline');
    } catch (err: any) {
      console.error('Error creating project:', err);
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });

      let errorMessage = 'Failed to create project. Please try again.';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else {
          errorMessage = JSON.stringify(err.response.data.detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
      console.log('Form submission complete');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <a href="/dashboard" className="hover:text-primary transition-colors">
          Dashboard
        </a>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <a href="/deal-pipeline" className="hover:text-primary transition-colors">
          Deal Pipeline
        </a>
        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
        <span className="text-slate-900 dark:text-white font-medium">New Project</span>
      </div>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Create New Investment Project
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Add a new regional investment opportunity to the pipeline.
          </p>
        </div>
        <button
          onClick={() => navigate('/deal-pipeline')}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          Back to Pipeline
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
          <span className="material-symbols-outlined text-red-600 dark:text-red-400">error</span>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 dark:text-red-200">Error</h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm">
        <div className="p-6 space-y-6">
          {/* Project Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Project Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="e.g., West African Rail Link"
            />
          </div>

          {/* Pillar */}
          <div>
            <label htmlFor="pillar" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Investment Pillar <span className="text-red-500">*</span>
            </label>
            <select
              id="pillar"
              required
              value={formData.pillar}
              onChange={(e) => handlePillarChange(e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {pillars.map((p) => (
                <option key={p.value} value={p.value}>{p.value}</option>
              ))}
            </select>
          </div>

          {/* Lead Country & Company Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="leadCountry" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Lead Country <span className="text-red-500">*</span>
              </label>
              <select
                id="leadCountry"
                required
                value={formData.leadCountry}
                onChange={(e) => setFormData({ ...formData, leadCountry: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Select a country...</option>
                {ecowasCountries.map((country) => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="leadCompany" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Lead Company <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="leadCompany"
                required
                value={formData.leadCompany}
                onChange={(e) => setFormData({ ...formData, leadCompany: e.target.value })}
                className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., RailCo Ltd."
              />
            </div>
          </div>

          {/* Investment Amount */}
          <div>
            <label htmlFor="investment" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Investment Amount <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">$</span>
              <input
                type="text"
                id="investment"
                required
                value={formData.investment}
                onChange={(e) => setFormData({ ...formData, investment: e.target.value })}
                className="w-full pl-8 pr-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="e.g., 1.2B or 450M"
              />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Use 'M' for millions or 'B' for billions (e.g., 1.2B, 450M)
            </p>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Project Description <span className="text-red-500">*</span>
            </label>
            <textarea
              id="description"
              required
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
              placeholder="Provide a detailed description of the investment project..."
            />
          </div>

          {/* Document Upload */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
              Supporting Documents
            </label>
            <div className="space-y-3">
              {/* Upload Area */}
              <div className="relative">
                <input
                  type="file"
                  id="documents"
                  multiple
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg p-6 text-center hover:border-primary dark:hover:border-primary transition-colors cursor-pointer">
                  <span className="material-symbols-outlined text-4xl text-slate-400 dark:text-slate-500 mb-2">
                    upload_file
                  </span>
                  <p className="text-sm text-slate-600 dark:text-slate-300 font-medium">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    PDF, DOC, XLS, PPT files up to 10MB
                  </p>
                </div>
              </div>

              {/* Uploaded Files List */}
              {uploadedFiles.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    Uploaded Files ({uploadedFiles.length})
                  </p>
                  {uploadedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <span className="material-symbols-outlined text-primary">
                          description
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                            {file.name}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {(file.size / 1024).toFixed(2)} KB
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="ml-2 p-1 text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                      >
                        <span className="material-symbols-outlined text-[20px]">close</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Upload investment memos, feasibility studies, or other supporting documents
            </p>
          </div>
        </div>

        {/* Form Actions */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700 rounded-b-xl flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/deal-pipeline')}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => {
                // Save as draft logic
                alert('Save as draft functionality coming soon!');
              }}
              className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              Save as Draft
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-bold shadow-md shadow-primary/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Creating...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[20px]">add</span>
                  Create Project
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Bottom spacing */}
      <div className="h-10"></div>
    </div>
  );
};

export default NewProject;
