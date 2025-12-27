export default function NotificationCenter() {
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
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/documents">Documents</a>
                            <a className="text-[#1152d4] dark:text-white text-sm font-semibold border-b-2 border-[#1152d4] pb-[22px] -mb-[17px] transition-colors" href="/notifications">Notifications</a>
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
                        {/* Views Section */}
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Views
                            </div>
                            <div className="space-y-1">
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa] font-medium text-sm hover:bg-[#dce7fe] dark:hover:bg-[#1e3a8a]/30 transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">inbox</span>
                                    <span className="flex-1 text-left">All Notifications</span>
                                    <span className="bg-[#1152d4] dark:bg-[#3b82f6] text-white text-xs font-bold px-2 py-0.5 rounded-full">24</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">mark_email_unread</span>
                                    <span className="flex-1 text-left">Unread</span>
                                    <span className="bg-[#94a3b8] dark:bg-[#4a5568] text-white text-xs font-bold px-2 py-0.5 rounded-full">12</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">priority_high</span>
                                    <span className="flex-1 text-left">Urgent / Priority</span>
                                    <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">3</span>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#4c669a] dark:text-[#a0aec0] font-medium text-sm hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors">
                                    <span className="material-symbols-outlined text-[20px]">archive</span>
                                    <span className="flex-1 text-left">Archived</span>
                                </button>
                            </div>
                        </div>

                        {/* Filter by Type */}
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Filter by Type
                            </div>
                            <div className="space-y-1">
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" defaultChecked />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Schedule Updates</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" defaultChecked />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Document Changes</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" defaultChecked />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">Mentions & Replies</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">AI Agent Updates</span>
                                </label>
                                <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] cursor-pointer transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-[#cfd7e7] dark:border-[#4a5568] text-[#1152d4] focus:ring-[#1152d4]" />
                                    <span className="text-sm font-medium text-[#0d121b] dark:text-white">System Alerts</span>
                                </label>
                            </div>
                        </div>

                        {/* Filter by TWG */}
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Filter by TWG
                            </div>
                            <select className="w-full px-3 py-2 rounded-lg bg-[#f6f6f8] dark:bg-[#2d3748] border border-[#cfd7e7] dark:border-[#4a5568] text-sm font-medium text-[#0d121b] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1152d4]">
                                <option>All TWGs</option>
                                <option>Energy & Power Infrastructure</option>
                                <option>Critical Minerals & Mining</option>
                                <option>Digital Economy</option>
                            </select>
                        </div>
                    </div>
                </aside>

                {/* Main Notification Area */}
                <div className="flex-1 flex flex-col bg-[#f6f6f8] dark:bg-[#0d121b] overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-6">
                        <div className="max-w-4xl mx-auto space-y-4">
                            {/* Header */}
                            <div className="flex items-center justify-between mb-6">
                                <h1 className="text-2xl font-bold text-[#0d121b] dark:text-white">Notifications</h1>
                                <button className="text-sm font-medium text-[#1152d4] dark:text-[#60a5fa] hover:underline">
                                    Mark all as read
                                </button>
                            </div>

                            {/* Critical Schedule Conflict - Priority */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border-l-4 border-red-500 shadow-sm overflow-hidden">
                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center shrink-0">
                                            <span className="material-symbols-outlined text-red-600 dark:text-red-400 text-[24px]">warning</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4 mb-2">
                                                <div>
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="inline-block px-2 py-0.5 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-xs font-bold rounded uppercase">Urgent</span>
                                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium">Schedule Update • Energy & Power Infrastructure</span>
                                                    </div>
                                                    <h3 className="text-base font-bold text-[#0d121b] dark:text-white">Critical Schedule Conflict Detected</h3>
                                                </div>
                                                <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] shrink-0">2 min ago</span>
                                            </div>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mb-4">
                                                TWG Meeting on Jan 15 at 2:00 PM overlaps with another summit event. Immediate rescheduling required.
                                            </p>
                                            <div className="flex items-center gap-3">
                                                <button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors">
                                                    Resolve Conflict
                                                </button>
                                                <button className="px-4 py-2 bg-[#f6f6f8] dark:bg-[#2d3748] hover:bg-[#e7ebf3] dark:hover:bg-[#4a5568] text-[#0d121b] dark:text-white text-sm font-medium rounded-lg transition-colors">
                                                    View Calendar
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Draft Minutes Ready */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden">
                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center shrink-0">
                                            <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-[24px]">description</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4 mb-2">
                                                <div>
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium">Document • Digital Economy & Connectivity</span>
                                                    </div>
                                                    <h3 className="text-base font-bold text-[#0d121b] dark:text-white">Draft Minutes Ready for Review</h3>
                                                </div>
                                                <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] shrink-0">15 min ago</span>
                                            </div>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mb-4">
                                                Secretariat Assistant has prepared draft meeting minutes from Jan 10 session. Review and approve before distribution.
                                            </p>
                                            <div className="flex items-center gap-3">
                                                <button className="px-4 py-2 bg-[#1152d4] hover:bg-[#0a3d8f] text-white text-sm font-medium rounded-lg transition-colors">
                                                    Review Minutes
                                                </button>
                                                <button className="px-4 py-2 bg-[#f6f6f8] dark:bg-[#2d3748] hover:bg-[#e7ebf3] dark:hover:bg-[#4a5568] text-[#0d121b] dark:text-white text-sm font-medium rounded-lg transition-colors">
                                                    Dismiss
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* New Comment - Mention */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden">
                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center shrink-0">
                                            <span className="material-symbols-outlined text-purple-600 dark:text-purple-400 text-[24px]">alternate_email</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4 mb-2">
                                                <div>
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium">Mention • Critical Minerals & Mining</span>
                                                    </div>
                                                    <h3 className="text-base font-bold text-[#0d121b] dark:text-white">Sarah Johnson mentioned you in a comment</h3>
                                                </div>
                                                <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] shrink-0">1 hour ago</span>
                                            </div>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mb-4">
                                                "@AdminPortal Can you review the latest environmental compliance section? We need your sign-off before the deadline."
                                            </p>
                                            <div className="flex items-center gap-3">
                                                <button className="px-4 py-2 bg-[#1152d4] hover:bg-[#0a3d8f] text-white text-sm font-medium rounded-lg transition-colors">
                                                    View Comment
                                                </button>
                                                <button className="px-4 py-2 bg-[#f6f6f8] dark:bg-[#2d3748] hover:bg-[#e7ebf3] dark:hover:bg-[#4a5568] text-[#0d121b] dark:text-white text-sm font-medium rounded-lg transition-colors">
                                                    Reply
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Document Updated */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden opacity-60">
                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center shrink-0">
                                            <span className="material-symbols-outlined text-green-600 dark:text-green-400 text-[24px]">check_circle</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4 mb-2">
                                                <div>
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium">Document • Trade & Customs Harmonization</span>
                                                    </div>
                                                    <h3 className="text-base font-bold text-[#0d121b] dark:text-white">Policy Framework v2.3 has been updated</h3>
                                                </div>
                                                <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] shrink-0">3 hours ago</span>
                                            </div>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                                Michael Chen made 12 changes to the trade policy framework document.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Schedule Reminder */}
                            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden opacity-60">
                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className="w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/20 flex items-center justify-center shrink-0">
                                            <span className="material-symbols-outlined text-orange-600 dark:text-orange-400 text-[24px]">event</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4 mb-2">
                                                <div>
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] font-medium">Schedule • Agribusiness & Food Security</span>
                                                    </div>
                                                    <h3 className="text-base font-bold text-[#0d121b] dark:text-white">Upcoming Meeting Reminder</h3>
                                                </div>
                                                <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] shrink-0">Yesterday</span>
                                            </div>
                                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                                TWG session scheduled for Jan 25, 2026 at 10:00 AM. Agenda has been uploaded.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}
