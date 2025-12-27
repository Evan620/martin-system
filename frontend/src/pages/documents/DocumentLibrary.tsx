export default function DocumentLibrary() {
    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white h-screen flex flex-col overflow-hidden">
            {/* Top Navbar */}
            <header className="sticky top-0 z-50 w-full bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748] shrink-0">
                <div className="px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-8">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-[#1152d4] to-[#0a3d8f] rounded-xl flex items-center justify-center shadow-lg">
                                <span className="text-white font-black text-lg">E</span>
                            </div>
                            <div>
                                <div className="font-bold text-base text-[#0d121b] dark:text-white">ECOWAS Summit</div>
                                <div className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium">2024 TWG Support</div>
                            </div>
                        </div>

                        <nav className="flex items-center gap-6">
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/dashboard">Dashboard</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/twgs">TWGs</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/my-twgs">My Workspaces</a>
                            <a className="text-[#1152d4] dark:text-white text-sm font-semibold border-b-2 border-[#1152d4] pb-[22px] -mb-[17px] transition-colors" href="/documents">Documents</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/notifications">Notifications</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/integrations">Settings</a>
                        </nav>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <input
                                type="text"
                                placeholder="Search..."
                                className="w-64 pl-9 pr-4 py-2 rounded-lg bg-[#f6f6f8] dark:bg-[#2d3748] border border-[#cfd7e7] dark:border-[#4a5568] text-sm placeholder-[#4c669a] dark:placeholder-[#a0aec0] focus:outline-none focus:ring-2 focus:ring-[#1152d4] dark:focus:ring-[#3b82f6]"
                            />
                            <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[#4c669a] dark:text-[#a0aec0] text-[20px]">search</span>
                        </div>

                        <button className="p-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors relative">
                            <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">notifications</span>
                            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
                        </button>

                        <div className="flex items-center gap-3 pl-4 border-l border-[#e7ebf3] dark:border-[#2d3748]">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
                                AP
                            </div>
                            <div>
                                <div className="text-sm font-semibold text-[#0d121b] dark:text-white">Admin Portal</div>
                                <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Administrator</div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex overflow-hidden">
                {/* Left Sidebar */}
                <aside className="w-72 bg-white dark:bg-[#1a202c] border-r border-[#e7ebf3] dark:border-[#2d3748] overflow-y-auto shrink-0">
                    <div className="p-6 space-y-6">
                        {/* Upload Button */}
                        <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#1152d4] hover:bg-[#0a3d8f] text-white font-semibold text-sm rounded-lg transition-colors shadow-lg">
                            <span className="material-symbols-outlined text-[20px]">upload_file</span>
                            Upload Document
                        </button>

                        {/* Library Sections */}
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Library
                            </div>
                            <div className="space-y-1">
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa] font-medium text-sm hover:bg-[#dce7fe] dark:hover:bg-[#1e3a8a]/30 transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">folder</span>
                                    <span className="flex-1 text-left">All Documents</span>
                                    <span className="text-xs font-bold text-[#1152d4] dark:text-[#60a5fa]">1,247</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">schedule</span>
                                    <span className="flex-1 text-left">Recent</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">star</span>
                                    <span className="flex-1 text-left">Starred</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">share</span>
                                    <span className="flex-1 text-left">Shared with Me</span>
                                </button>
                            </div>
                        </div>

                        {/* Document Types */}
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Document Types
                            </div>
                            <div className="space-y-1">
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" defaultChecked />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Meeting Minutes</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" defaultChecked />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Policy Drafts</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Reports</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Legal Documents</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Presentations</span>
                                </label>
                            </div>
                        </div>

                        {/* Labels */}
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Labels
                            </div>
                            <div className="space-y-1">
                                <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="w-3 h-3 rounded-full bg-red-500"></span>
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Confidential</span>
                                </button>
                                <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="w-3 h-3 rounded-full bg-orange-500"></span>
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Internal</span>
                                </button>
                                <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="w-3 h-3 rounded-full bg-green-500"></span>
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Public</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </aside>

                {/* Main Document Area */}
                <div className="flex-1 flex flex-col bg-[#f6f6f8] dark:bg-[#0d121b] overflow-hidden">
                    <div className="flex-1 overflow-y-auto">
                        {/* Header with Search and Filters */}
                        <div className="bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748] p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h1 className="text-2xl font-bold text-[#0d121b] dark:text-white">All Documents</h1>
                                <div className="flex items-center gap-3">
                                    <button className="flex items-center gap-2 px-4 py-2 bg-[#f6f6f8] dark:bg-[#2d3748] hover:bg-[#e7ebf3] dark:hover:bg-[#4a5568] text-[#0d121b] dark:text-white text-sm font-medium rounded-lg transition-colors">
                                        <span className="material-symbols-outlined text-[18px]">filter_list</span>
                                        Filter
                                    </button>
                                    <button className="flex items-center gap-2 px-4 py-2 bg-[#f6f6f8] dark:bg-[#2d3748] hover:bg-[#e7ebf3] dark:hover:bg-[#4a5568] text-[#0d121b] dark:text-white text-sm font-medium rounded-lg transition-colors">
                                        <span className="material-symbols-outlined text-[18px]">sort</span>
                                        Sort
                                    </button>
                                </div>
                            </div>

                            {/* Search Bar */}
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder="Search by name, owner, or tag..."
                                    className="w-full pl-10 pr-4 py-3 rounded-lg bg-[#f6f6f8] dark:bg-[#2d3748] border border-[#cfd7e7] dark:border-[#4a5568] text-sm placeholder-[#4c669a] dark:placeholder-[#a0aec0] focus:outline-none focus:ring-2 focus:ring-[#1152d4] dark:focus:ring-[#3b82f6]"
                                />
                                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#4c669a] dark:text-[#a0aec0] text-[20px]">search</span>
                            </div>
                        </div>

                        {/* Document Table */}
                        <div className="p-6">
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden">
                                <table className="w-full">
                                    <thead>
                                        <tr className="bg-[#f6f6f8] dark:bg-[#2d3748] border-b border-[#e7ebf3] dark:border-[#4a5568]">
                                            <th className="px-6 py-4 text-left">
                                                <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Name</th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Owner</th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Modified</th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Size</th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Label</th>
                                            <th className="px-6 py-4 text-right text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                                        {/* Document Row 1 */}
                                        <tr className="hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                            <td className="px-6 py-4">
                                                <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-red-600 dark:text-red-400 text-[20px]">picture_as_pdf</span>
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white">Energy_TWG_Minutes_Dec15.pdf</div>
                                                        <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Meeting Minutes</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">Dr. Amara Koné</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">2 hours ago</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0] font-medium">2.4 MB</td>
                                            <td className="px-6 py-4">
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-xs font-bold rounded-full">
                                                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                    Confidential
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="View">
                                                        <span className="material-symbols-outlined text-[20px]">visibility</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Download">
                                                        <span className="material-symbols-outlined text-[20px]">download</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Share">
                                                        <span className="material-symbols-outlined text-[20px]">share</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="More">
                                                        <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Document Row 2 */}
                                        <tr className="hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                            <td className="px-6 py-4">
                                                <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-green-600 dark:text-green-400 text-[20px]">table_chart</span>
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white">Regional_Infrastructure_Budget_Q4.xlsx</div>
                                                        <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Budget Report</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">Finance Team</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">5 hours ago</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0] font-medium">1.8 MB</td>
                                            <td className="px-6 py-4">
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400 text-xs font-bold rounded-full">
                                                    <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                                                    Internal
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="View">
                                                        <span className="material-symbols-outlined text-[20px]">visibility</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Download">
                                                        <span className="material-symbols-outlined text-[20px]">download</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Share">
                                                        <span className="material-symbols-outlined text-[20px]">share</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="More">
                                                        <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Document Row 3 */}
                                        <tr className="hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                            <td className="px-6 py-4">
                                                <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-[20px]">description</span>
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white">Trade_Policy_Framework_Draft_v3.docx</div>
                                                        <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Policy Draft</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">Legal Affairs</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">Yesterday</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0] font-medium">845 KB</td>
                                            <td className="px-6 py-4">
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-xs font-bold rounded-full">
                                                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                                    Public
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="View">
                                                        <span className="material-symbols-outlined text-[20px]">visibility</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Download">
                                                        <span className="material-symbols-outlined text-[20px]">download</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Share">
                                                        <span className="material-symbols-outlined text-[20px]">share</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="More">
                                                        <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Document Row 4 */}
                                        <tr className="hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                            <td className="px-6 py-4">
                                                <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-red-600 dark:text-red-400 text-[20px]">picture_as_pdf</span>
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white">Minerals_Export_Analysis_2025.pdf</div>
                                                        <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Research Report</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">Research Unit</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">2 days ago</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0] font-medium">3.2 MB</td>
                                            <td className="px-6 py-4">
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-xs font-bold rounded-full">
                                                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                    Confidential
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="View">
                                                        <span className="material-symbols-outlined text-[20px]">visibility</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Download">
                                                        <span className="material-symbols-outlined text-[20px]">download</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Share">
                                                        <span className="material-symbols-outlined text-[20px]">share</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="More">
                                                        <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>

                                        {/* Document Row 5 */}
                                        <tr className="hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                            <td className="px-6 py-4">
                                                <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-lg bg-orange-100 dark:bg-orange-900/20 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-orange-600 dark:text-orange-400 text-[20px]">slideshow</span>
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white">Digital_Economy_Roadmap_Final.pptx</div>
                                                        <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Presentation</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">Strategy Team</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">3 days ago</td>
                                            <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0] font-medium">5.1 MB</td>
                                            <td className="px-6 py-4">
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400 text-xs font-bold rounded-full">
                                                    <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                                                    Internal
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="View">
                                                        <span className="material-symbols-outlined text-[20px]">visibility</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Download">
                                                        <span className="material-symbols-outlined text-[20px]">download</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="Share">
                                                        <span className="material-symbols-outlined text-[20px]">share</span>
                                                    </button>
                                                    <button className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-[#60a5fa] transition-colors" title="More">
                                                        <span className="material-symbols-outlined text-[20px]">more_vert</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}
