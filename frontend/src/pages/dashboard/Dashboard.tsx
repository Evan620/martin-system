export default function Dashboard() {
    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white min-h-screen flex flex-col">
            {/* Top Navbar */}
            <header className="sticky top-0 z-50 w-full bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748]">
                <div className="px-6 lg:px-10 py-3 flex items-center justify-between gap-6">
                    <div className="flex items-center gap-8">
                        {/* Brand */}
                        <div className="flex items-center gap-3">
                            <div className="size-8 rounded-full bg-[#1152d4]/10 flex items-center justify-center text-[#1152d4]">
                                <span className="material-symbols-outlined">shield_person</span>
                            </div>
                            <h2 className="text-lg font-bold leading-tight tracking-[-0.015em] hidden sm:block">ECOWAS Summit TWG Support</h2>
                        </div>
                        {/* Search */}
                        <div className="hidden md:flex items-center bg-[#f0f2f5] dark:bg-[#2d3748] rounded-lg h-10 w-64 px-3 gap-2">
                            <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">search</span>
                            <input
                                className="bg-transparent border-none outline-none text-sm w-full placeholder:text-[#4c669a] dark:placeholder:text-[#a0aec0] text-[#0d121b] dark:text-white focus:ring-0 p-0"
                                placeholder="Search TWGs, Agents, Reports..."
                                type="text"
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        {/* Nav Links */}
                        <nav className="hidden lg:flex items-center gap-6">
                            <a className="text-[#1152d4] font-medium text-sm" href="/dashboard">Dashboard</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/twgs">TWGs</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Reports</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Settings</a>
                        </nav>
                        {/* User Profile */}
                        <div className="flex items-center gap-4 border-l border-[#e7ebf3] dark:border-[#2d3748] pl-6">
                            <button className="relative text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] transition-colors">
                                <span className="material-symbols-outlined">notifications</span>
                                <span className="absolute top-0 right-0 size-2 bg-red-500 rounded-full border-2 border-white dark:border-[#1a202c]"></span>
                            </button>
                            <div className="h-10 w-10 rounded-full bg-cover bg-center border border-[#e7ebf3] dark:border-[#2d3748] bg-gray-300"></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content with Sidebar */}
            <div className="flex-1 flex">
                {/* Left Sidebar Navigation */}
                <aside className="w-64 bg-white dark:bg-[#1a202c] border-r border-[#e7ebf3] dark:border-[#2d3748] hidden lg:block">
                    <div className="p-6 space-y-6">
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Navigation
                            </div>
                            <div className="space-y-1">
                                <a href="/dashboard" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa] font-medium text-sm hover:bg-[#dce7fe] dark:hover:bg-[#1e3a8a]/30 transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">dashboard</span>
                                    <span>Dashboard</span>
                                </a>
                                <a href="/twgs" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">groups</span>
                                    <span>TWGs</span>
                                </a>
                                <a href="/documents" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">folder</span>
                                    <span>Documents</span>
                                </a>
                                <a href="/notifications" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">notifications</span>
                                    <span>Notifications</span>
                                    <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">3</span>
                                </a>
                            </div>
                        </div>

                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Admin
                            </div>
                            <div className="space-y-1">
                                <a href="/integrations" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">settings</span>
                                    <span>Settings</span>
                                </a>
                            </div>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col p-6 lg:p-10 max-w-[1440px] mx-auto w-full gap-8">
                {/* Header Section */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-3xl md:text-4xl font-black text-[#0d121b] dark:text-white tracking-tight mb-1">Summit Overview Dashboard</h1>
                        <p className="text-[#4c669a] dark:text-[#a0aec0] font-medium">2024 ECOWAS Session • Admin View</p>
                    </div>
                    <div className="flex gap-3">
                        <button className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-[#2d3748] border border-[#cfd7e7] dark:border-[#4a5568] rounded-lg text-sm font-medium text-[#0d121b] dark:text-white hover:bg-gray-50 dark:hover:bg-[#4a5568] transition-colors shadow-sm">
                            <span className="material-symbols-outlined text-[20px]">download</span>
                            Export Report
                        </button>
                        <button className="flex items-center gap-2 px-4 py-2.5 bg-[#1152d4] hover:bg-[#0d3ea8] text-white rounded-lg text-sm font-medium transition-colors shadow-md">
                            <span className="material-symbols-outlined text-[20px] text-white">add</span>
                            New TWG
                        </button>
                    </div>
                </div>

                {/* KPI Metrics Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Active TWGs */}
                    <div className="bg-white dark:bg-[#1a202c] p-5 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col justify-between h-32 relative overflow-hidden group">
                        <div className="absolute right-[-10px] top-[-10px] opacity-5 group-hover:opacity-10 transition-opacity">
                            <span className="material-symbols-outlined text-[100px] text-primary">groups</span>
                        </div>
                        <div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium mb-1">Active TWGs</p>
                            <h3 className="text-3xl font-bold text-[#0d121b] dark:text-white">12</h3>
                        </div>
                        <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 w-fit px-2 py-1 rounded-full">
                            <span className="material-symbols-outlined text-[14px]">trending_up</span>
                            <span>2 New this week</span>
                        </div>
                    </div>

                    {/* Deals in Pipeline */}
                    <div className="bg-white dark:bg-[#1a202c] p-5 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col justify-between h-32 relative overflow-hidden group">
                        <div className="absolute right-[-10px] top-[-10px] opacity-5 group-hover:opacity-10 transition-opacity">
                            <span className="material-symbols-outlined text-[100px] text-blue-500">handshake</span>
                        </div>
                        <div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium mb-1">Deals in Pipeline</p>
                            <h3 className="text-3xl font-bold text-[#0d121b] dark:text-white">45</h3>
                        </div>
                        <div className="flex items-center gap-1 text-blue-600 dark:text-blue-400 text-xs font-medium bg-blue-50 dark:bg-blue-900/20 w-fit px-2 py-1 rounded-full">
                            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                            <span>5 Ready for Review</span>
                        </div>
                    </div>

                    {/* Pending Approvals */}
                    <div className="bg-white dark:bg-[#1a202c] p-5 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col justify-between h-32 relative overflow-hidden group">
                        <div className="absolute right-[-10px] top-[-10px] opacity-5 group-hover:opacity-10 transition-opacity">
                            <span className="material-symbols-outlined text-[100px] text-amber-500">pending_actions</span>
                        </div>
                        <div>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm font-medium mb-1">Pending Approvals</p>
                            <h3 className="text-3xl font-bold text-[#0d121b] dark:text-white">8</h3>
                        </div>
                        <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400 text-xs font-medium bg-amber-50 dark:bg-amber-900/20 w-fit px-2 py-1 rounded-full">
                            <span className="material-symbols-outlined text-[14px]">warning</span>
                            <span>3 High Priority</span>
                        </div>
                    </div>

                    {/* Next Plenary */}
                    <div className="bg-[#1152d4] p-5 rounded-xl border border-[#1152d4] shadow-md flex flex-col justify-between h-32 relative overflow-hidden text-white group">
                        <div className="absolute right-[-10px] top-[-10px] opacity-10 group-hover:opacity-20 transition-opacity">
                            <span className="material-symbols-outlined text-[100px] text-white">event_available</span>
                        </div>
                        <div>
                            <p className="text-white text-sm font-medium mb-1 opacity-90">Next Plenary Session</p>
                            <h3 className="text-3xl font-bold text-white">3 Days</h3>
                        </div>
                        <div className="flex items-center gap-1 text-white text-xs font-medium bg-white/30 w-fit px-2 py-1 rounded-full backdrop-blur-sm">
                            <span className="material-symbols-outlined text-[14px] text-white">calendar_month</span>
                            <span className="text-white">Oct 24, 2024</span>
                        </div>
                    </div>
                </div>

                {/* Main Dashboard Content Area */}
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                    {/* Left Column: Pipeline & TWG Grid (Span 2) */}
                    <div className="xl:col-span-2 flex flex-col gap-8">
                        {/* Pipeline Funnel Section */}
                        <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">Deal Progression by Stage</h3>
                                <button className="text-sm text-primary font-medium hover:underline">View Full Report</button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
                                {/* Connecting Line (Desktop) */}
                                <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-[#e7ebf3] dark:bg-[#2d3748] -z-0"></div>

                                {/* Stage 1 */}
                                <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                    <div className="flex items-center gap-2">
                                        <div className="size-3 rounded-full bg-blue-200"></div>
                                        <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Drafting</span>
                                    </div>
                                    <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                        <div className="h-full bg-primary w-[80%] rounded-full"></div>
                                    </div>
                                    <div>
                                        <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">18</span>
                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Active drafts</span>
                                    </div>
                                </div>

                                {/* Stage 2 */}
                                <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                    <div className="flex items-center gap-2">
                                        <div className="size-3 rounded-full bg-blue-400"></div>
                                        <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Negotiation</span>
                                    </div>
                                    <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                        <div className="h-full bg-blue-500 w-[60%] rounded-full"></div>
                                    </div>
                                    <div>
                                        <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">12</span>
                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">In discussion</span>
                                    </div>
                                </div>

                                {/* Stage 3 */}
                                <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                    <div className="flex items-center gap-2">
                                        <div className="size-3 rounded-full bg-indigo-500"></div>
                                        <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Final Review</span>
                                    </div>
                                    <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                        <div className="h-full bg-indigo-600 w-[40%] rounded-full"></div>
                                    </div>
                                    <div>
                                        <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">10</span>
                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Pending sign-off</span>
                                    </div>
                                </div>

                                {/* Stage 4 */}
                                <div className="relative z-10 flex flex-col gap-3 bg-white dark:bg-[#1a202c] md:bg-transparent md:dark:bg-transparent">
                                    <div className="flex items-center gap-2">
                                        <div className="size-3 rounded-full bg-emerald-500"></div>
                                        <span className="text-xs font-bold uppercase tracking-wider text-[#4c669a] dark:text-[#a0aec0]">Signed</span>
                                    </div>
                                    <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                        <div className="h-full bg-emerald-500 w-[100%] rounded-full"></div>
                                    </div>
                                    <div>
                                        <span className="text-2xl font-bold block text-[#0d121b] dark:text-white">5</span>
                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Completed</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* TWG Status Grid */}
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">Technical Working Groups Status</h3>
                                <div className="flex gap-2">
                                    <button className="p-2 text-[#0d121b] dark:text-[#a0aec0] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                        <span className="material-symbols-outlined">filter_list</span>
                                    </button>
                                    <button className="p-2 text-[#0d121b] dark:text-[#a0aec0] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                        <span className="material-symbols-outlined">grid_view</span>
                                    </button>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Card 1: Trade */}
                                <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4">
                                        <div className="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs font-bold px-2 py-1 rounded">ON TRACK</div>
                                    </div>
                                    <div className="flex items-start gap-4 mb-4">
                                        <div className="size-12 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-primary shrink-0">
                                            <span className="material-symbols-outlined">local_shipping</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white text-lg">Trade & Customs</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Lead: Sarah Oladipo</p>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-[#4c669a] dark:text-[#a0aec0]">Completion</span>
                                                <span className="font-bold text-[#0d121b] dark:text-white">85%</span>
                                            </div>
                                            <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                                <div className="h-full bg-emerald-500 w-[85%] rounded-full"></div>
                                            </div>
                                        </div>
                                        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-3 flex items-start gap-2 border border-indigo-100 dark:border-indigo-800/30">
                                            <span className="material-symbols-outlined text-indigo-500 text-sm mt-0.5">auto_awesome</span>
                                            <div>
                                                <p className="text-xs text-[#0d121b] dark:text-white font-medium">AI Insight</p>
                                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Draft harmonization protocol 98% consistent with 2023 mandate.</p>
                                            </div>
                                        </div>
                                        <div className="flex justify-end pt-2 border-t border-[#f0f2f5] dark:border-[#2d3748]">
                                            <button className="text-sm text-primary font-medium hover:text-blue-700 flex items-center gap-1">
                                                View Details <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Card 2: Security */}
                                <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4">
                                        <div className="bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400 text-xs font-bold px-2 py-1 rounded">ACTION REQUIRED</div>
                                    </div>
                                    <div className="flex items-start gap-4 mb-4">
                                        <div className="size-12 rounded-lg bg-orange-50 dark:bg-orange-900/20 flex items-center justify-center text-orange-600 shrink-0">
                                            <span className="material-symbols-outlined">security</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white text-lg">Regional Security</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Lead: Col. Musa Diop</p>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-[#4c669a] dark:text-[#a0aec0]">Completion</span>
                                                <span className="font-bold text-[#0d121b] dark:text-white">40%</span>
                                            </div>
                                            <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                                <div className="h-full bg-red-500 w-[40%] rounded-full"></div>
                                            </div>
                                        </div>
                                        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 flex items-start gap-2 border border-red-100 dark:border-red-800/30">
                                            <span className="material-symbols-outlined text-red-500 text-sm mt-0.5">warning</span>
                                            <div>
                                                <p className="text-xs text-[#0d121b] dark:text-white font-medium">Critical Blocker</p>
                                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Missing signatures from 3 member states on Annex B.</p>
                                            </div>
                                        </div>
                                        <div className="flex justify-end pt-2 border-t border-[#f0f2f5] dark:border-[#2d3748]">
                                            <button className="text-sm text-primary font-medium hover:text-blue-700 flex items-center gap-1">
                                                View Details <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Card 3: Digital Infra */}
                                <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4">
                                        <div className="bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400 text-xs font-bold px-2 py-1 rounded">REVIEWING</div>
                                    </div>
                                    <div className="flex items-start gap-4 mb-4">
                                        <div className="size-12 rounded-lg bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center text-purple-600 shrink-0">
                                            <span className="material-symbols-outlined">wifi</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white text-lg">Digital Infrastructure</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Lead: Dr. Amina K.</p>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-[#4c669a] dark:text-[#a0aec0]">Completion</span>
                                                <span className="font-bold text-[#0d121b] dark:text-white">60%</span>
                                            </div>
                                            <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                                <div className="h-full bg-amber-500 w-[60%] rounded-full"></div>
                                            </div>
                                        </div>
                                        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-3 flex items-start gap-2 border border-indigo-100 dark:border-indigo-800/30">
                                            <span className="material-symbols-outlined text-indigo-500 text-sm mt-0.5">auto_awesome</span>
                                            <div>
                                                <p className="text-xs text-[#0d121b] dark:text-white font-medium">AI Insight</p>
                                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Suggested cross-reference with AU Data Policy detected.</p>
                                            </div>
                                        </div>
                                        <div className="flex justify-end pt-2 border-t border-[#f0f2f5] dark:border-[#2d3748]">
                                            <button className="text-sm text-primary font-medium hover:text-blue-700 flex items-center gap-1">
                                                View Details <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Card 4: Agriculture */}
                                <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4">
                                        <div className="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs font-bold px-2 py-1 rounded">ON TRACK</div>
                                    </div>
                                    <div className="flex items-start gap-4 mb-4">
                                        <div className="size-12 rounded-lg bg-green-50 dark:bg-green-900/20 flex items-center justify-center text-green-600 shrink-0">
                                            <span className="material-symbols-outlined">agriculture</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white text-lg">Agriculture & Food</h4>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Lead: Jean-Paul M.</p>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-[#4c669a] dark:text-[#a0aec0]">Completion</span>
                                                <span className="font-bold text-[#0d121b] dark:text-white">92%</span>
                                            </div>
                                            <div className="h-2 w-full bg-[#f0f2f5] dark:bg-[#2d3748] rounded-full overflow-hidden">
                                                <div className="h-full bg-emerald-500 w-[92%] rounded-full"></div>
                                            </div>
                                        </div>
                                        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-3 flex items-start gap-2 border border-indigo-100 dark:border-indigo-800/30">
                                            <span className="material-symbols-outlined text-indigo-500 text-sm mt-0.5">auto_awesome</span>
                                            <div>
                                                <p className="text-xs text-[#0d121b] dark:text-white font-medium">AI Insight</p>
                                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Food security annex successfully validated by 14 states.</p>
                                            </div>
                                        </div>
                                        <div className="flex justify-end pt-2 border-t border-[#f0f2f5] dark:border-[#2d3748]">
                                            <button className="text-sm text-primary font-medium hover:text-blue-700 flex items-center gap-1">
                                                View Details <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Timeline & Action Center (Span 1) */}
                    <div className="flex flex-col gap-8">
                        {/* Upcoming Deadlines */}
                        <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm p-6 flex-1">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">Upcoming Deadlines</h3>
                                <span className="material-symbols-outlined text-[#4c669a]">calendar_month</span>
                            </div>
                            <div className="space-y-6 relative">
                                {/* Vertical line */}
                                <div className="absolute left-[27px] top-4 bottom-4 w-0.5 bg-[#e7ebf3] dark:bg-[#2d3748] -z-0"></div>

                                {/* Item 1 */}
                                <div className="flex gap-4 relative z-10">
                                    <div className="flex flex-col items-center gap-1 w-14 shrink-0 bg-white dark:bg-[#1a202c]">
                                        <span className="text-xs font-bold text-primary uppercase">Oct</span>
                                        <span className="text-xl font-black text-[#0d121b] dark:text-white">24</span>
                                    </div>
                                    <div className="pb-6 border-b border-[#f0f2f5] dark:border-[#2d3748] w-full">
                                        <h4 className="font-bold text-[#0d121b] dark:text-white text-sm">Draft Submission Deadline</h4>
                                        <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mt-1">Trade & Customs TWG</p>
                                        <div className="mt-2 flex items-center gap-2">
                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                                                CRITICAL
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Item 2 */}
                                <div className="flex gap-4 relative z-10">
                                    <div className="flex flex-col items-center gap-1 w-14 shrink-0 bg-white dark:bg-[#1a202c]">
                                        <span className="text-xs font-bold text-[#4c669a] uppercase">Oct</span>
                                        <span className="text-xl font-black text-[#0d121b] dark:text-white">27</span>
                                    </div>
                                    <div className="pb-6 border-b border-[#f0f2f5] dark:border-[#2d3748] w-full">
                                        <h4 className="font-bold text-[#0d121b] dark:text-white text-sm">Stakeholder Review</h4>
                                        <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mt-1">All Active TWGs</p>
                                        <div className="mt-2 flex -space-x-2 overflow-hidden">
                                            <div className="inline-block h-6 w-6 rounded-full ring-2 ring-white dark:ring-[#1a202c] bg-gray-200"></div>
                                            <div className="inline-block h-6 w-6 rounded-full ring-2 ring-white dark:ring-[#1a202c] bg-gray-300"></div>
                                            <div className="inline-block h-6 w-6 rounded-full ring-2 ring-white dark:ring-[#1a202c] bg-gray-400"></div>
                                        </div>
                                    </div>
                                </div>

                                {/* Item 3 */}
                                <div className="flex gap-4 relative z-10">
                                    <div className="flex flex-col items-center gap-1 w-14 shrink-0 bg-white dark:bg-[#1a202c]">
                                        <span className="text-xs font-bold text-[#4c669a] uppercase">Nov</span>
                                        <span className="text-xl font-black text-[#0d121b] dark:text-white">02</span>
                                    </div>
                                    <div className="w-full">
                                        <h4 className="font-bold text-[#0d121b] dark:text-white text-sm">Plenary Session Opening</h4>
                                        <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mt-1">Main Hall, Abuja</p>
                                    </div>
                                </div>
                            </div>
                            <button className="w-full mt-6 py-2 text-sm text-[#0d121b] dark:text-[#a0aec0] font-medium border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg hover:bg-gray-50 dark:hover:bg-[#2d3748] transition-colors">
                                View All Calendar
                            </button>
                        </div>

                        {/* Action Center */}
                        <div className="bg-primary/5 dark:bg-primary/10 rounded-xl border border-primary/20 p-6">
                            <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-4">Quick Actions</h3>
                            <div className="grid grid-cols-2 gap-3">
                                <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                    <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">article</span>
                                    <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Generate Report</span>
                                </button>
                                <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                    <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">broadcast_on_personal</span>
                                    <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Broadcast Msg</span>
                                </button>
                                <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                    <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">smart_toy</span>
                                    <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Run AI Analysis</span>
                                </button>
                                <button className="flex flex-col items-center justify-center gap-2 p-4 bg-white dark:bg-[#1a202c] rounded-lg border border-[#e7ebf3] dark:border-[#2d3748] hover:border-primary transition-colors hover:shadow-sm group">
                                    <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">person_add</span>
                                    <span className="text-xs font-medium text-[#0d121b] dark:text-white text-center">Invite Lead</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
            </div>
        </div>
    )
}
