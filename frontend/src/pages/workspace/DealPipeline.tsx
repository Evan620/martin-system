import { useNavigate } from 'react-router-dom';

export default function DealPipeline() {
    const navigate = useNavigate();

    const handleProjectClick = (projectId: string) => {
        navigate(`/deal-pipeline/${projectId}`);
    };

    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white h-screen flex flex-col overflow-hidden">
            {/* Top Navbar */}
            <header className="sticky top-0 z-50 w-full bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748] shrink-0">
                <div className="px-6 lg:px-10 py-3 flex items-center justify-between gap-6">
                    <div className="flex items-center gap-8">
                        <div className="flex items-center gap-3">
                            <div className="size-8 rounded-full bg-[#1152d4]/10 flex items-center justify-center text-[#1152d4]">
                                <span className="material-symbols-outlined">shield_person</span>
                            </div>
                            <h2 className="text-lg font-bold leading-tight tracking-[-0.015em] hidden sm:block">ECOWAS Summit TWG Support</h2>
                        </div>
                        <div className="hidden md:flex items-center bg-[#f0f2f5] dark:bg-[#2d3748] rounded-lg h-10 w-64 px-3 gap-2">
                            <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">search</span>
                            <input
                                className="bg-transparent border-none outline-none text-sm w-full placeholder:text-[#4c669a] dark:placeholder:text-[#a0aec0] text-[#0d121b] dark:text-white focus:ring-0 p-0"
                                placeholder="Search projects, pillars, or tags..."
                                type="text"
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        <nav className="hidden lg:flex items-center gap-6">
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/dashboard">Dashboard</a>
                            <a className="text-[#1152d4] dark:text-white text-sm font-medium transition-colors border-b-2 border-[#1152d4] pb-0.5" href="/deal-pipeline">Deal Pipeline</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/twgs">TWGs</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Reports</a>
                        </nav>
                        <div className="flex items-center gap-4 border-l border-[#e7ebf3] dark:border-[#2d3748] pl-6">
                            <button className="relative text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white transition-colors">
                                <span className="material-symbols-outlined">notifications</span>
                                <span className="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-500 border-2 border-white dark:border-[#1a202c]"></span>
                            </button>
                            <button className="relative text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white transition-colors">
                                <span className="material-symbols-outlined">chat_bubble</span>
                            </button>
                            <button className="relative text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white transition-colors">
                                <span className="material-symbols-outlined">help</span>
                            </button>
                            <div className="h-10 w-10 rounded-full bg-cover bg-center border border-[#e7ebf3] dark:border-[#2d3748] bg-gray-300"></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
                <div className="max-w-7xl mx-auto space-y-6">
                    {/* Breadcrumbs */}
                    <div className="flex items-center gap-2 text-sm text-[#4c669a] dark:text-[#a0aec0]">
                        <a className="hover:text-[#1152d4] transition-colors" href="/dashboard">Dashboard</a>
                        <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                        <span className="text-[#0d121b] dark:text-white font-medium">Deal Pipeline</span>
                    </div>

                    {/* Page Header */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <h2 className="text-2xl font-bold text-[#0d121b] dark:text-white tracking-tight">Deal Pipeline</h2>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] mt-1">Manage and evaluate regional investment opportunities.</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b] transition-colors shadow-sm">
                                <span className="material-symbols-outlined text-[20px]">download</span>
                                Export
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-[#1152d4] hover:bg-blue-700 text-white rounded-lg text-sm font-bold shadow-md shadow-[#1152d4]/20 transition-all">
                                <span className="material-symbols-outlined text-[20px]">add</span>
                                New Project
                            </button>
                        </div>
                    </div>

                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Total Pipeline Value */}
                        <div className="bg-white dark:bg-[#1a202c] p-5 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-[#4c669a] dark:text-[#a0aec0]">Total Pipeline Value</p>
                                <span className="material-symbols-outlined text-green-600 bg-green-100 dark:bg-green-900/30 p-1 rounded">trending_up</span>
                            </div>
                            <p className="text-2xl font-bold text-[#0d121b] dark:text-white mt-2">$45.2B</p>
                            <p className="text-xs text-green-600 font-medium flex items-center gap-1 mt-1">
                                <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
                                12% vs last month
                            </p>
                        </div>

                        {/* High Readiness Projects */}
                        <div className="bg-white dark:bg-[#1a202c] p-5 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-[#4c669a] dark:text-[#a0aec0]">High Readiness Projects</p>
                                <span className="material-symbols-outlined text-[#1152d4] bg-[#1152d4]/10 dark:bg-[#1152d4]/20 p-1 rounded">verified</span>
                            </div>
                            <p className="text-2xl font-bold text-[#0d121b] dark:text-white mt-2">12</p>
                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium mt-1">Ready for immediate investment</p>
                        </div>

                        {/* Pending AI Review */}
                        <div className="bg-white dark:bg-[#1a202c] p-5 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-[#4c669a] dark:text-[#a0aec0]">Pending AI Review</p>
                                <span className="material-symbols-outlined text-purple-600 bg-purple-100 dark:bg-purple-900/30 p-1 rounded">smart_toy</span>
                            </div>
                            <p className="text-2xl font-bold text-[#0d121b] dark:text-white mt-2">5</p>
                            <p className="text-xs text-purple-600 font-medium mt-1">Awaiting agent analysis</p>
                        </div>
                    </div>

                    {/* AI Insight Widget */}
                    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 border border-indigo-100 dark:border-indigo-800/50 rounded-xl p-4 flex items-start gap-4 shadow-sm relative overflow-hidden">
                        <div className="absolute -right-10 -top-10 h-32 w-32 bg-indigo-200 dark:bg-indigo-800 rounded-full blur-3xl opacity-20"></div>
                        <div className="p-2 bg-white dark:bg-[#2d3748] rounded-lg shadow-sm shrink-0 text-indigo-600 dark:text-indigo-400">
                            <span className="material-symbols-outlined">auto_awesome</span>
                        </div>
                        <div className="flex-1 z-10">
                            <h3 className="text-sm font-bold text-[#0d121b] dark:text-white">AI Agent 'Alpha' Insight</h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mt-1">I've identified missing financial data in 3 new project submissions. Updating these could increase the overall readiness score by ~15%.</p>
                        </div>
                        <button className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline px-2 z-10 whitespace-nowrap self-center">Review Suggestions</button>
                        <button className="absolute top-2 right-2 text-[#6b7280] hover:text-[#4c669a] dark:hover:text-white">
                            <span className="material-symbols-outlined text-[18px]">close</span>
                        </button>
                    </div>

                    {/* Filters & Toolbar */}
                    <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-white dark:bg-[#1a202c] p-1 rounded-lg border border-[#e7ebf3] dark:border-[#2d3748]">
                        {/* Tabs */}
                        <div className="flex p-1 bg-[#f6f6f8] dark:bg-[#0d121b] rounded-lg w-full sm:w-auto overflow-x-auto">
                            <button className="px-4 py-1.5 text-sm font-medium rounded-md bg-white dark:bg-[#2d3748] text-[#0d121b] dark:text-white shadow-sm transition-all whitespace-nowrap">All Projects</button>
                            <button className="px-4 py-1.5 text-sm font-medium rounded-md text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white hover:bg-gray-200/50 dark:hover:bg-[#2d3748]/50 transition-all whitespace-nowrap">Infrastructure</button>
                            <button className="px-4 py-1.5 text-sm font-medium rounded-md text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white hover:bg-gray-200/50 dark:hover:bg-[#2d3748]/50 transition-all whitespace-nowrap">Energy</button>
                            <button className="px-4 py-1.5 text-sm font-medium rounded-md text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white hover:bg-gray-200/50 dark:hover:bg-[#2d3748]/50 transition-all whitespace-nowrap">Agriculture</button>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 w-full sm:w-auto">
                            <div className="relative w-full sm:w-48">
                                <select className="w-full appearance-none bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] text-sm rounded-lg focus:ring-[#1152d4] focus:border-[#1152d4] block px-3 py-2 pr-8">
                                    <option>Status: All</option>
                                    <option>Approved</option>
                                    <option>In Review</option>
                                    <option>Draft</option>
                                </select>
                                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-[#4c669a]">
                                    <span className="material-symbols-outlined text-[20px]">expand_more</span>
                                </div>
                            </div>
                            <button className="p-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b]">
                                <span className="material-symbols-outlined text-[20px]">filter_list</span>
                            </button>
                        </div>
                    </div>

                    {/* Data Table */}
                    <div className="bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl overflow-hidden shadow-sm">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-[#f6f6f8] dark:bg-[#0d121b] border-b border-[#e7ebf3] dark:border-[#2d3748]">
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Project Name</th>
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Pillar</th>
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Lead Country/Co.</th>
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Investment</th>
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Readiness Score</th>
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-4 text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                                    {/* Row 1 - West African Rail Link */}
                                    <tr onClick={() => handleProjectClick('8492')} className="group hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b] transition-colors cursor-pointer">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                                                    <span className="material-symbols-outlined text-blue-600 dark:text-blue-400">train</span>
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-[#0d121b] dark:text-white">West African Rail Link</p>
                                                    <p className="text-xs text-[#4c669a]">ID: #ECW-2024-001</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] border border-gray-200 dark:border-[#2d3748]">
                                                Infrastructure
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <span className="text-sm text-[#0d121b] dark:text-white">Nigeria</span>
                                                <span className="text-xs text-[#4c669a]">RailCo Ltd.</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm font-medium text-[#0d121b] dark:text-white">$1.2B</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap min-w-[180px]">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex justify-between items-center text-xs">
                                                    <span className="font-medium text-[#4c669a] dark:text-[#a0aec0]">82%</span>
                                                    <div className="flex items-center gap-1 text-purple-600 dark:text-purple-400" title="AI Calculated Score">
                                                        <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
                                                        <span className="text-[10px] font-bold">AI SCORED</span>
                                                    </div>
                                                </div>
                                                <div className="w-full bg-gray-200 dark:bg-[#2d3748] rounded-full h-2">
                                                    <div className="bg-[#1152d4] h-2 rounded-full" style={{ width: '82%' }}></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">
                                                In Review
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1">
                                                <span className="material-symbols-outlined text-[20px]">visibility</span>
                                            </button>
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1 ml-2">
                                                <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                            </button>
                                        </td>
                                    </tr>

                                    {/* Row 2 - Solar Grid Expansion */}
                                    <tr onClick={() => handleProjectClick('7823')} className="group hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b] transition-colors cursor-pointer">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center shrink-0">
                                                    <span className="material-symbols-outlined text-orange-600 dark:text-orange-400">solar_power</span>
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-[#0d121b] dark:text-white">Solar Grid Expansion</p>
                                                    <p className="text-xs text-[#4c669a]">ID: #ECW-2024-042</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] border border-gray-200 dark:border-[#2d3748]">
                                                Energy
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <span className="text-sm text-[#0d121b] dark:text-white">Ghana</span>
                                                <span className="text-xs text-[#4c669a]">Volta Energy</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm font-medium text-[#0d121b] dark:text-white">$450M</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap min-w-[180px]">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex justify-between items-center text-xs">
                                                    <span className="font-medium text-[#4c669a] dark:text-[#a0aec0]">95%</span>
                                                </div>
                                                <div className="w-full bg-gray-200 dark:bg-[#2d3748] rounded-full h-2">
                                                    <div className="bg-green-500 h-2 rounded-full" style={{ width: '95%' }}></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                                                Approved
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1">
                                                <span className="material-symbols-outlined text-[20px]">visibility</span>
                                            </button>
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1 ml-2">
                                                <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                            </button>
                                        </td>
                                    </tr>

                                    {/* Row 3 - Agribusiness Hub */}
                                    <tr onClick={() => handleProjectClick('6541')} className="group hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b] transition-colors cursor-pointer">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center shrink-0">
                                                    <span className="material-symbols-outlined text-green-600 dark:text-green-400">agriculture</span>
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-[#0d121b] dark:text-white">Agribusiness Hub</p>
                                                    <p className="text-xs text-[#4c669a]">ID: #ECW-2024-088</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] border border-gray-200 dark:border-[#2d3748]">
                                                Agriculture
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <span className="text-sm text-[#0d121b] dark:text-white">Côte d'Ivoire</span>
                                                <span className="text-xs text-[#4c669a]">AgriCorp Int.</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm font-medium text-[#0d121b] dark:text-white">$85M</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap min-w-[180px]">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex justify-between items-center text-xs">
                                                    <span className="font-medium text-[#4c669a] dark:text-[#a0aec0]">45%</span>
                                                    <div className="flex items-center gap-1 text-[#6b7280]" title="Manually Scored">
                                                        <span className="material-symbols-outlined text-[14px]">edit_note</span>
                                                    </div>
                                                </div>
                                                <div className="w-full bg-gray-200 dark:bg-[#2d3748] rounded-full h-2">
                                                    <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '45%' }}></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-[#2d3748] dark:text-[#a0aec0]">
                                                Draft
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1">
                                                <span className="material-symbols-outlined text-[20px]">visibility</span>
                                            </button>
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1 ml-2">
                                                <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                            </button>
                                        </td>
                                    </tr>

                                    {/* Row 4 - Tech City Phase 1 */}
                                    <tr onClick={() => handleProjectClick('5392')} className="group hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b] transition-colors cursor-pointer">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
                                                    <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400">smart_toy</span>
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-[#0d121b] dark:text-white">Tech City Phase 1</p>
                                                    <p className="text-xs text-[#4c669a]">ID: #ECW-2024-102</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] border border-gray-200 dark:border-[#2d3748]">
                                                Technology
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <span className="text-sm text-[#0d121b] dark:text-white">Senegal</span>
                                                <span className="text-xs text-[#4c669a]">Dakar Innovations</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm font-medium text-[#0d121b] dark:text-white">$2.1B</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap min-w-[180px]">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex justify-between items-center text-xs">
                                                    <span className="font-medium text-[#4c669a] dark:text-[#a0aec0]">78%</span>
                                                    <div className="flex items-center gap-1 text-purple-600 dark:text-purple-400" title="AI Calculated Score">
                                                        <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
                                                        <span className="text-[10px] font-bold">AI SCORED</span>
                                                    </div>
                                                </div>
                                                <div className="w-full bg-gray-200 dark:bg-[#2d3748] rounded-full h-2">
                                                    <div className="bg-[#1152d4] h-2 rounded-full" style={{ width: '78%' }}></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">
                                                In Review
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1">
                                                <span className="material-symbols-outlined text-[20px]">visibility</span>
                                            </button>
                                            <button onClick={(e) => e.stopPropagation()} className="text-[#6b7280] hover:text-[#1152d4] transition-colors p-1 ml-2">
                                                <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                            </button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        <div className="flex items-center justify-between px-6 py-4 border-t border-[#e7ebf3] dark:border-[#2d3748] bg-white dark:bg-[#1a202c]">
                            <div className="text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                Showing <span className="font-medium text-[#0d121b] dark:text-white">1</span> to <span className="font-medium text-[#0d121b] dark:text-white">4</span> of <span className="font-medium text-[#0d121b] dark:text-white">24</span> results
                            </div>
                            <div className="flex gap-2">
                                <button className="px-3 py-1 text-sm border border-[#e7ebf3] dark:border-[#2d3748] rounded bg-white dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] disabled:opacity-50" disabled>Previous</button>
                                <button className="px-3 py-1 text-sm border border-[#e7ebf3] dark:border-[#2d3748] rounded bg-white dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#0d121b]">Next</button>
                            </div>
                        </div>
                    </div>

                    {/* Bottom spacing */}
                    <div className="h-10"></div>
                </div>
            </main>
        </div>
    );
}
