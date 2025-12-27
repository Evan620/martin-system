import { useParams, useNavigate } from 'react-router-dom';

export default function ProjectDetails() {
    const { id } = useParams();
    const navigate = useNavigate();

    const handleGenerateMemo = () => {
        navigate(`/deal-pipeline/${id}/memo`);
    };

    // Mock data - replace with actual API call
    const project = {
        id: id || '8492',
        name: 'West African Rail Expansion',
        status: 'Feasibility Phase',
        fundingAsk: '$450M',
        fundingGrowth: '+5% vs last month',
        readinessScore: 85,
        currentPhase: 'Feasibility',
        nextPhase: 'Technical Design',
        twg: 'Infrastructure & Transport',
        lastUpdated: '2 hours ago',
        pillar: 'Infrastructure',
        leadCountry: 'Nigeria',
        leadCompany: 'RailCo Ltd.',
        investment: '$1.2B'
    };

    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white min-h-screen">
            {/* Top Navbar */}
            <header className="sticky top-0 z-50 w-full bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748]">
                <div className="px-6 lg:px-10 py-3 flex items-center justify-between gap-6">
                    <div className="flex items-center gap-8">
                        <div className="flex items-center gap-3">
                            <div className="size-8 rounded-full bg-[#1152d4]/10 flex items-center justify-center text-[#1152d4]">
                                <span className="material-symbols-outlined">shield_person</span>
                            </div>
                            <h2 className="text-lg font-bold leading-tight tracking-[-0.015em] hidden sm:block">ECOWAS TWG System</h2>
                        </div>
                        <div className="hidden md:flex items-center bg-[#f0f2f5] dark:bg-[#2d3748] rounded-lg h-10 w-64 px-3 gap-2">
                            <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">search</span>
                            <input
                                className="bg-transparent border-none outline-none text-sm w-full placeholder:text-[#4c669a] dark:placeholder:text-[#a0aec0] text-[#0d121b] dark:text-white focus:ring-0 p-0"
                                placeholder="Search projects..."
                                type="text"
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        <nav className="hidden lg:flex items-center gap-6">
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/dashboard">Dashboard</a>
                            <a className="text-[#1152d4] dark:text-white text-sm font-medium transition-colors border-b-2 border-[#1152d4] pb-0.5" href="/deal-pipeline">Deal Pipeline</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Reports</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Settings</a>
                        </nav>
                        <div className="flex items-center gap-4 border-l border-[#e7ebf3] dark:border-[#2d3748] pl-6">
                            <button className="relative text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white transition-colors">
                                <span className="material-symbols-outlined">notifications</span>
                            </button>
                            <div className="h-10 w-10 rounded-full bg-cover bg-center border border-[#e7ebf3] dark:border-[#2d3748] bg-gray-300"></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="px-6 lg:px-40 py-5">
                <div className="max-w-[1200px] mx-auto">
                    {/* Breadcrumbs */}
                    <div className="flex items-center gap-2 text-sm text-[#4c669a] dark:text-[#a0aec0] px-4 py-2">
                        <button onClick={() => navigate('/dashboard')} className="hover:text-[#1152d4] transition-colors">Home</button>
                        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                        <button onClick={() => navigate('/deal-pipeline')} className="hover:text-[#1152d4] transition-colors">Deal Pipeline</button>
                        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                        <span className="text-[#0d121b] dark:text-white font-medium">{project.name}</span>
                    </div>

                    {/* Page Heading */}
                    <div className="flex flex-wrap justify-between items-start gap-3 p-4">
                        <div className="flex min-w-72 flex-col gap-2">
                            <div className="flex items-center gap-3 mb-1">
                                <h1 className="text-[#0d121b] dark:text-white text-3xl md:text-4xl font-black leading-tight tracking-[-0.033em]">{project.name}</h1>
                                <span className="px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 text-xs font-bold uppercase tracking-wider border border-amber-200 dark:border-amber-800">{project.status}</span>
                            </div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm md:text-base font-normal leading-normal">
                                Project ID: #{project.id} • Last updated {project.lastUpdated} by <span className="inline-flex items-center gap-1 font-medium text-[#1152d4]"><span className="material-symbols-outlined text-[16px]">smart_toy</span> AI Agent</span>
                            </p>
                        </div>
                        <div className="flex gap-3">
                            <button className="flex min-w-[84px] items-center justify-center rounded-lg h-10 px-4 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] text-sm font-bold hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b] transition-colors">
                                <span>Edit Project</span>
                            </button>
                            <button onClick={handleGenerateMemo} className="flex min-w-[84px] items-center justify-center rounded-lg h-10 px-4 bg-[#1152d4] text-white text-sm font-bold shadow-md hover:bg-blue-700 transition-colors">
                                <span className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                                    <span>Generate Memo</span>
                                </span>
                            </button>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
                        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm">
                            <div className="flex justify-between items-start">
                                <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium">Funding Ask</p>
                                <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">payments</span>
                            </div>
                            <p className="text-[#0d121b] dark:text-white text-2xl font-bold">{project.fundingAsk} <span className="text-base font-medium text-[#6b7280]">USD</span></p>
                            <p className="text-emerald-600 dark:text-emerald-400 text-xs font-bold bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 rounded w-fit">{project.fundingGrowth}</p>
                        </div>

                        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                                <span className="material-symbols-outlined text-6xl text-[#1152d4]">speed</span>
                            </div>
                            <div className="flex justify-between items-start z-10">
                                <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium">Readiness Score</p>
                                <span className="material-symbols-outlined text-[#1152d4]">check_circle</span>
                            </div>
                            <p className="text-[#0d121b] dark:text-white text-2xl font-bold">{project.readinessScore}<span className="text-[#6b7280] text-lg">/100</span></p>
                            <div className="w-full bg-[#e7ebf3] dark:bg-[#2d3748] rounded-full h-1.5 mt-2">
                                <div className="bg-[#1152d4] h-1.5 rounded-full" style={{ width: `${project.readinessScore}%` }}></div>
                            </div>
                        </div>

                        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm">
                            <div className="flex justify-between items-start">
                                <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium">Current Phase</p>
                                <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">timeline</span>
                            </div>
                            <p className="text-[#0d121b] dark:text-white text-2xl font-bold">{project.currentPhase}</p>
                            <p className="text-[#6b7280] text-sm">Next: {project.nextPhase}</p>
                        </div>

                        <div className="flex flex-col gap-2 rounded-xl p-5 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm">
                            <div className="flex justify-between items-start">
                                <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium">Originating TWG</p>
                                <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">groups</span>
                            </div>
                            <p className="text-[#0d121b] dark:text-white text-xl font-bold truncate" title={project.twg}>{project.twg}</p>
                            <div className="flex -space-x-2 mt-1">
                                <div className="w-6 h-6 rounded-full bg-gray-300 dark:bg-gray-600 border-2 border-white dark:border-[#1a202c]"></div>
                                <div className="w-6 h-6 rounded-full bg-gray-300 dark:bg-gray-600 border-2 border-white dark:border-[#1a202c]"></div>
                                <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700 border-2 border-white dark:border-[#1a202c] flex items-center justify-center text-[10px] font-bold text-gray-600 dark:text-gray-300">+4</div>
                            </div>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="px-4 pb-0 mb-6 sticky top-[72px] bg-background-light dark:bg-background-dark z-40 pt-2">
                        <div className="flex border-b border-[#e7ebf3] dark:border-[#2d3748] gap-8 overflow-x-auto">
                            <button className="flex items-center justify-center border-b-[3px] border-[#1152d4] text-[#0d121b] dark:text-white pb-3 pt-2 min-w-fit">
                                <span className="text-sm font-bold">Overview</span>
                            </button>
                            <button className="flex items-center justify-center border-b-[3px] border-transparent text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white pb-3 pt-2 min-w-fit transition-colors">
                                <span className="text-sm font-bold">Financials</span>
                            </button>
                            <button className="flex items-center justify-center border-b-[3px] border-transparent text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white pb-3 pt-2 min-w-fit transition-colors">
                                <span className="text-sm font-bold flex gap-2 items-center">
                                    Documents
                                    <span className="bg-[#e7ebf3] dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] text-[10px] px-1.5 py-0.5 rounded-full">4</span>
                                </span>
                            </button>
                            <button className="flex items-center justify-center border-b-[3px] border-transparent text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white pb-3 pt-2 min-w-fit transition-colors">
                                <span className="text-sm font-bold">History</span>
                            </button>
                        </div>
                    </div>

                    {/* Main Content Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 px-4 pb-12">
                        {/* Left Column */}
                        <div className="lg:col-span-2 flex flex-col gap-6">
                            {/* Executive Summary */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-6 shadow-sm">
                                <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-4">Executive Summary</h3>
                                <div className="text-[#4c669a] dark:text-[#a0aec0] space-y-4">
                                    <p>
                                        The West African Rail Expansion project aims to rehabilitate and extend the rail corridor connecting Lagos (Nigeria) to Cotonou (Benin), facilitating the movement of goods and passengers across the key economic hubs of the ECOWAS region. This project is a critical component of the broader West African Railway Master Plan.
                                    </p>
                                    <p>
                                        Currently in the Feasibility Study phase, the project has secured preliminary backing from the African Development Bank and local stakeholders. The technical survey indicates no major geographical impediments, though urban displacement in Lagos suburbs remains a key risk factor requiring mitigation.
                                    </p>
                                </div>
                            </div>

                            {/* Strategic Rationale */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-6 shadow-sm">
                                <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-4">Strategic Rationale & Business Case</h3>
                                <ul className="space-y-4">
                                    <li className="flex gap-4 items-start">
                                        <div className="size-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0 text-[#1152d4]">
                                            <span className="material-symbols-outlined text-sm">hub</span>
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-[#0d121b] dark:text-white">Regional Connectivity</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mt-1">Directly supports ECOWAS Vision 2050 Goal 3: "Integrated Infrastructure". Expected to reduce transit times by 40%.</p>
                                        </div>
                                    </li>
                                    <li className="flex gap-4 items-start">
                                        <div className="size-8 rounded-full bg-green-50 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0 text-green-600 dark:text-green-400">
                                            <span className="material-symbols-outlined text-sm">eco</span>
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-[#0d121b] dark:text-white">Economic & Environmental Impact</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mt-1">Projected IRR of 14% over 25 years. Shifts 20% of road freight to rail, reducing regional carbon emissions by 150k tons annually.</p>
                                        </div>
                                    </li>
                                    <li className="flex gap-4 items-start">
                                        <div className="size-8 rounded-full bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0 text-purple-600 dark:text-purple-400">
                                            <span className="material-symbols-outlined text-sm">handshake</span>
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-[#0d121b] dark:text-white">Trade Facilitation</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mt-1">Will streamline customs procedures at the border through integrated rail terminals, boosting intra-regional trade volume.</p>
                                        </div>
                                    </li>
                                </ul>
                            </div>

                            {/* Map Visual */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden shadow-sm h-64 relative group">
                                <div className="absolute inset-0 bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/20 dark:to-blue-800/20"></div>
                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
                                <div className="absolute bottom-4 left-4 text-white">
                                    <p className="font-bold text-lg">Proposed Route</p>
                                    <p className="text-sm opacity-80">Lagos Terminus A <span className="material-symbols-outlined text-xs align-middle mx-1">arrow_forward</span> Cotonou Port</p>
                                </div>
                                <button className="absolute top-4 right-4 bg-white/90 dark:bg-black/50 backdrop-blur text-[#0d121b] dark:text-white p-2 rounded-lg hover:bg-white transition-colors">
                                    <span className="material-symbols-outlined">fullscreen</span>
                                </button>
                            </div>
                        </div>

                        {/* Right Column */}
                        <div className="flex flex-col gap-6">
                            {/* AI Insight Card */}
                            <div className="rounded-xl p-5 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/40 dark:to-indigo-950/20 border border-blue-100 dark:border-blue-900 shadow-sm relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-3 opacity-10">
                                    <span className="material-symbols-outlined text-6xl text-[#1152d4]">psychology</span>
                                </div>
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="material-symbols-outlined text-[#1152d4]">auto_awesome</span>
                                    <h4 className="text-sm font-bold text-[#1152d4]">AI Agent Insight</h4>
                                </div>
                                <p className="text-sm text-[#0d121b] dark:text-[#a0aec0] mb-3 font-medium">
                                    Readiness Score is high (85/100), but the "Environmental Impact Assessment" is older than 6 months.
                                </p>
                                <div className="bg-white/60 dark:bg-black/20 rounded-lg p-3 text-xs text-[#4c669a] dark:text-[#a0aec0] backdrop-blur-sm border border-white/50 dark:border-white/10">
                                    <strong>Recommendation:</strong> Request an updated addendum from the TWG lead before the next investment committee review.
                                </div>
                                <button className="mt-3 w-full py-2 bg-[#1152d4]/10 hover:bg-[#1152d4]/20 text-[#1152d4] text-xs font-bold rounded flex items-center justify-center gap-2 transition-colors">
                                    Ask AI Agent
                                </button>
                            </div>

                            {/* Action Items */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm">
                                <h4 className="text-xs font-bold text-[#6b7280] mb-4 uppercase tracking-wider">Action Required</h4>
                                <div className="space-y-3">
                                    <div className="flex gap-3 items-start p-3 bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-800/30 rounded-lg">
                                        <span className="material-symbols-outlined text-amber-600 text-lg mt-0.5">warning</span>
                                        <div>
                                            <p className="text-sm font-bold text-[#0d121b] dark:text-white">Missing Document</p>
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mt-0.5">Updated EIA Report pending upload.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-3 items-start p-3 bg-[#f6f6f8] dark:bg-[#2d3748]/50 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg">
                                        <span className="material-symbols-outlined text-[#6b7280] text-lg mt-0.5">pending_actions</span>
                                        <div>
                                            <p className="text-sm font-bold text-[#0d121b] dark:text-white">Sign-off Needed</p>
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mt-0.5">Finance Ministry approval for Phase 2 funding.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Recent Attachments */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm">
                                <div className="flex justify-between items-center mb-4">
                                    <h4 className="text-xs font-bold text-[#6b7280] uppercase tracking-wider">Recent Attachments</h4>
                                    <button className="text-[#1152d4] text-xs font-bold hover:underline">View All</button>
                                </div>
                                <ul className="space-y-3">
                                    <li className="flex items-center gap-3 group cursor-pointer">
                                        <div className="size-8 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded flex items-center justify-center">
                                            <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-[#0d121b] dark:text-white truncate group-hover:text-[#1152d4] transition-colors">Feasibility_Study_v2.pdf</p>
                                            <p className="text-xs text-[#6b7280]">2.4 MB • 2 days ago</p>
                                        </div>
                                        <span className="material-symbols-outlined text-[#6b7280] text-sm opacity-0 group-hover:opacity-100 transition-opacity">download</span>
                                    </li>
                                    <li className="flex items-center gap-3 group cursor-pointer">
                                        <div className="size-8 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded flex items-center justify-center">
                                            <span className="material-symbols-outlined text-sm">table_view</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-[#0d121b] dark:text-white truncate group-hover:text-[#1152d4] transition-colors">Financial_Model_2024.xlsx</p>
                                            <p className="text-xs text-[#6b7280]">1.1 MB • 1 week ago</p>
                                        </div>
                                        <span className="material-symbols-outlined text-[#6b7280] text-sm opacity-0 group-hover:opacity-100 transition-opacity">download</span>
                                    </li>
                                </ul>
                                <button className="w-full mt-4 border border-dashed border-[#e7ebf3] dark:border-[#2d3748] rounded-lg p-2 text-xs text-[#6b7280] hover:text-[#4c669a] dark:hover:text-[#a0aec0] hover:border-[#4c669a] dark:hover:border-[#a0aec0] transition-colors flex items-center justify-center gap-2">
                                    <span className="material-symbols-outlined text-sm">upload_file</span>
                                    Upload Document
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
