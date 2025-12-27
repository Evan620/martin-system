import { Card, Badge, Avatar } from '../../components/ui'

export default function TwgWorkspace() {
    const members = [
        { name: 'Dr. A. Sow', role: 'Chairperson', avatar: 'AS' },
        { name: 'John Doe', role: 'Member', avatar: 'JD' },
        { name: 'Maria Kone', role: 'Member', avatar: 'MK' },
        { name: 'Sarah Lee', role: 'Member', avatar: 'SL' },
    ]

    const actions = [
        { task: 'Review Renewable Energy Annex', assignee: 'John Doe', avatar: 'JD', date: 'Oct 10', status: 'In Progress' },
        { task: 'Approve Minutes from Sept 1st', assignee: 'Dr. A. Sow', avatar: 'AS', date: 'Sept 15', status: 'Overdue' },
        { task: 'Draft Logistics Plan', assignee: 'M. Kone', avatar: 'MK', date: 'Oct 20', status: 'Not Started' },
    ]

    return (
        <div className="flex h-full gap-6">
            <div className="flex-1 space-y-6">
                {/* Banner Section */}
                <div className="relative h-56 rounded-2xl overflow-hidden bg-gradient-to-br from-blue-900 via-blue-950 to-slate-950 border border-slate-800 shadow-2xl">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_-20%,_var(--tw-gradient-stops))] from-blue-500/20 via-transparent to-transparent"></div>

                    <div className="relative z-10 h-full flex flex-col justify-between p-8">
                        <div className="flex justify-between items-start">
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">PILLAR: INFRASTRUCTURE</Badge>
                                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-bold">ECOWAS SUMMIT '24</Badge>
                                </div>
                                <h1 className="text-4xl font-display font-bold text-white tracking-tight">Energy Technical Working Group</h1>
                                <p className="text-blue-200/70 text-sm max-w-2xl leading-relaxed">
                                    Strategic coordination for regional power pool integration and sustainable energy transition frameworks.
                                </p>
                            </div>

                            <div className="flex gap-3">
                                <button className="p-2.5 bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-xl text-white transition-all">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    </svg>
                                </button>
                                <button className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-lg shadow-blue-900/40 transition-all flex items-center gap-2">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                                    New Meeting
                                </button>
                            </div>
                        </div>

                        {/* Governance Row */}
                        <div className="flex gap-8 pt-6 border-t border-white/10">
                            <div className="flex items-center gap-3">
                                <Avatar fallback="FD" size="sm" className="ring-2 ring-blue-500/30" />
                                <div>
                                    <p className="text-[10px] uppercase font-black text-blue-400 tracking-widest">Political Lead</p>
                                    <p className="text-sm font-bold text-white">Hon. Fatima Diallo</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Avatar fallback="KA" size="sm" className="ring-2 ring-blue-500/30" />
                                <div>
                                    <p className="text-[10px] uppercase font-black text-blue-400 tracking-widest">Technical Lead</p>
                                    <p className="text-sm font-bold text-white">Eng. Kwesi Arthur</p>
                                </div>
                            </div>
                            <div className="ml-auto flex items-center gap-6">
                                <div className="text-right">
                                    <p className="text-[10px] uppercase font-black text-slate-500 tracking-widest">Next Meeting</p>
                                    <p className="text-sm font-bold text-white">Feb 10 • 10:00 AM</p>
                                </div>
                                <div className="h-8 w-px bg-white/10"></div>
                                <div className="flex -space-x-2">
                                    {members.map((m, i) => (
                                        <Avatar key={i} fallback={m.avatar} size="sm" className="ring-2 ring-blue-900" />
                                    ))}
                                    <div className="w-8 h-8 rounded-full bg-blue-600 border-2 border-blue-900 flex items-center justify-center text-[10px] font-black text-white">
                                        +12
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Quick Stats Grid */}
                <div className="grid grid-cols-4 gap-6">
                    <Card className="p-5 flex items-center gap-4 group hover:border-blue-500/50 transition-all">
                        <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Meetings Held</p>
                            <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">08</h3>
                        </div>
                    </Card>
                    <Card className="p-5 flex items-center gap-4 group hover:border-orange-500/50 transition-all">
                        <div className="p-3 rounded-xl bg-orange-50 dark:bg-orange-900/20 text-orange-500 dark:text-orange-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Open Actions</p>
                            <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">15</h3>
                        </div>
                    </Card>
                    <Card className="p-5 flex items-center gap-4 group hover:border-emerald-500/50 transition-all">
                        <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Pipeline Projects</p>
                            <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">04</h3>
                        </div>
                    </Card>
                    <Card className="p-5 flex items-center gap-4 group hover:border-purple-500/50 transition-all">
                        <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Resources Out</p>
                            <h3 className="text-2xl font-display font-bold text-slate-900 dark:text-white transition-colors">12</h3>
                        </div>
                    </Card>
                </div>

                <div className="grid grid-cols-12 gap-6">
                    {/* Meeting Tracker */}
                    <div className="col-span-12 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-display font-bold text-slate-900 dark:text-white transition-colors">Meeting History & Schedule</h2>
                            <button className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors uppercase tracking-widest">Full Calendar →</button>
                        </div>
                        <Card className="p-0 overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-none border-slate-100 dark:border-dark-border transition-colors">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm border-collapse">
                                    <thead>
                                        <tr className="bg-slate-50 dark:bg-slate-800/50 text-[10px] font-black text-slate-400 uppercase tracking-widest transition-colors">
                                            <th className="px-6 py-4">Meeting Date / Title</th>
                                            <th className="px-6 py-4">Type</th>
                                            <th className="px-6 py-4">Status</th>
                                            <th className="px-6 py-4 text-center">Resources</th>
                                            <th className="px-6 py-4 text-right">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 transition-colors">
                                        {[
                                            { title: 'Regional Power Pool Integration', date: 'Feb 10, 2024 • 10:00 AM', status: 'Upcoming', type: 'High-Level Review', resources: ['agenda'] },
                                            { title: 'Sustainability Policy Framework', date: 'Feb 01, 2024 • 02:00 PM', status: 'Completed', type: 'Technical Session', resources: ['agenda', 'minutes', 'attendance', 'actions'] },
                                            { title: 'Governance & Funding Round', date: 'Jan 24, 2024 • 09:00 AM', status: 'Completed', type: 'Facilitator Sync', resources: ['agenda', 'minutes', 'attendance', 'actions'] },
                                        ].map((m, i) => (
                                            <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors group">
                                                <td className="px-6 py-4">
                                                    <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">{m.title}</div>
                                                    <div className="text-[10px] text-slate-400 uppercase font-black">{m.date}</div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <Badge variant="neutral" size="sm" className="font-bold">{m.type}</Badge>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <Badge variant={m.status === 'Upcoming' ? 'info' : 'success'} size="sm" className="font-bold tracking-tighter uppercase">{m.status}</Badge>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex justify-center gap-2">
                                                        {['agenda', 'minutes', 'attendance', 'actions'].map(res => (
                                                            <div key={res} className={`p-1.5 rounded-lg border ${m.resources.includes(res)
                                                                ? 'bg-blue-50 border-blue-100 text-blue-600 dark:bg-blue-900/20 dark:border-blue-900/30 dark:text-blue-400 cursor-pointer hover:scale-110'
                                                                : 'bg-slate-50 border-slate-100 text-slate-300 dark:bg-slate-800 dark:border-slate-700/50 opacity-50'
                                                                } transition-all`}>
                                                                {res === 'agenda' && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
                                                                {res === 'minutes' && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>}
                                                                {res === 'attendance' && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>}
                                                                {res === 'actions' && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <button className="text-[10px] font-black text-blue-600 hover:text-blue-700 uppercase tracking-widest transition-all">View Details</button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </Card>
                    </div>

                    {/* Action Items List */}
                    <div className="col-span-7 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white transition-colors">Critical Action Items</h2>
                            <button className="text-xs font-bold text-slate-500 hover:text-slate-700 transition-colors uppercase">View All</button>
                        </div>
                        <div className="space-y-3">
                            {actions.map((action, i) => (
                                <Card key={i} className="p-4 flex items-center gap-4 hover:border-blue-500/30 transition-all cursor-pointer group">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs ${action.status === 'Overdue' ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-400'} transition-colors`}>
                                        0{i + 1}
                                    </div>
                                    <div className="flex-1">
                                        <h4 className="font-bold text-sm text-slate-900 dark:text-white transition-colors capitalize">{action.task}</h4>
                                        <div className="flex items-center gap-2 mt-1">
                                            <Avatar size="xs" fallback={action.avatar} />
                                            <span className="text-[10px] text-slate-500 font-bold uppercase">{action.assignee} • Due {action.date}</span>
                                        </div>
                                    </div>
                                    <Badge variant={action.status === 'In Progress' ? 'info' : action.status === 'Overdue' ? 'danger' : 'neutral'} size="sm" className="font-bold uppercase tracking-tighter">
                                        {action.status}
                                    </Badge>
                                </Card>
                            ))}
                        </div>
                    </div>

                    {/* Document Repository */}
                    <div className="col-span-5 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white transition-colors">Document Library</h2>
                        </div>
                        <Card className="p-4 space-y-5">
                            <div>
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Templates & Guidance</h4>
                                <div className="space-y-2">
                                    {['Agenda_Template_2024.docx', 'Reporting_Framework.pdf'].map(doc => (
                                        <div key={doc} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group cursor-pointer">
                                            <svg className="w-5 h-5 text-slate-400 group-hover:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                                            <span className="text-xs font-medium text-slate-600 dark:text-slate-400 truncate">{doc}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">TWG Outputs</h4>
                                <div className="space-y-2">
                                    {['Regional_Power_Pool_Draft_v1.pdf', 'Technical_Standards_Review.xlsx'].map(doc => (
                                        <div key={doc} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors group cursor-pointer">
                                            <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                                            <span className="text-xs font-medium text-slate-600 dark:text-slate-400 truncate">{doc}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <button className="w-full py-2 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-lg text-xs font-bold text-slate-500 hover:text-slate-700 transition-all">
                                Open Full Repository →
                            </button>
                        </Card>
                    </div>
                </div>
            </div>

            {/* AI Copilot Sidebar */}
            <div className="w-80 flex flex-col gap-6">
                <Card className="flex-1 flex flex-col p-0 overflow-hidden bg-white dark:bg-dark-card border-slate-100 dark:border-dark-border transition-colors">
                    {/* Header */}
                    <div className="p-4 border-b border-slate-100 dark:border-dark-border flex items-center justify-between transition-colors">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                            </div>
                            <div>
                                <h3 className="font-bold text-sm text-slate-900 dark:text-white">ECOWAS AI Copilot</h3>
                                <p className="text-[10px] text-green-500 font-bold uppercase flex items-center gap-1 transition-colors">
                                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                                    Online • Energy Context
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Chat Messages */}
                    <div className="flex-1 overflow-auto p-4 space-y-4">
                        <div className="flex gap-3">
                            <div className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 transition-colors">
                                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-2xl rounded-tl-none transition-colors">
                                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed transition-colors">
                                    Hello Dr. Sow. I've analyzed the <span className="text-blue-600 font-bold underline cursor-pointer">Energy_Policy_Draft_v2.pdf</span> uploaded today. It appears 85% compliant with the 2023 sustainability framework.
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <div className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 transition-colors">
                                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-2xl rounded-tl-none transition-colors">
                                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed transition-colors">
                                    Would you like me to draft an agenda for the 'Draft Policy Review' meeting based on the missing compliance items?
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-3 flex-row-reverse">
                            <div className="bg-blue-600 text-white p-3 rounded-2xl rounded-tr-none transition-colors">
                                <p className="text-xs leading-relaxed">
                                    Yes, please draft the agenda. Also, summarize the main conflicts in section 4.
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <div className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 transition-colors">
                                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                            </div>
                            <div className="flex gap-1 p-2 bg-slate-50 dark:bg-slate-800/50 rounded-full transition-colors">
                                <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce"></div>
                                <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                                <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                            </div>
                        </div>
                    </div>

                    {/* Input */}
                    <div className="p-4 border-t border-slate-100 dark:border-dark-border space-y-3 transition-colors">
                        {/* Pending Review Alert */}
                        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-900/30 rounded-xl space-y-2">
                            <div className="flex items-center justify-between">
                                <p className="text-[10px] font-black text-amber-600 dark:text-amber-400 uppercase tracking-widest">Pending Review</p>
                                <Badge variant="warning" size="sm" className="text-[8px]">Agent Draft</Badge>
                            </div>
                            <p className="text-[11px] font-bold text-slate-700 dark:text-slate-300">Draft Agenda: Regional Power Pool Integration</p>
                            <div className="flex gap-2 pt-1">
                                <button className="flex-1 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-all">Edit</button>
                                <button className="flex-1 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-500 transition-all">Approve</button>
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-2">
                            <button className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-[10px] font-bold text-slate-500 hover:text-slate-700 transition-colors">Generate Summary</button>
                            <button className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-[10px] font-bold text-slate-500 hover:text-slate-700 transition-colors">Schedule Meeting</button>
                        </div>
                        <div className="relative">
                            <input
                                type="text"
                                placeholder="Ask AI Copilot..."
                                className="w-full bg-slate-50 dark:bg-slate-800 border-0 rounded-xl px-4 py-3 text-xs focus:ring-2 focus:ring-blue-500 transition-colors pr-10"
                            />
                            <button className="absolute right-2 top-1.5 p-1.5 bg-blue-600 text-white rounded-lg">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                            </button>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    )
}
