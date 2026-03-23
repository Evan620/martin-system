import { Card, Badge, Avatar } from '../../components/ui'

export default function KnowledgeBase() {
    const tabs = ['All', 'Projects', 'Meetings', 'Documents', 'Decisions']
    const activeTab = 'Projects'

    const filters = [
        { label: 'Mining & Energy', checked: true },
        { label: 'Trade & Customs', checked: false },
        { label: 'Infrastructure', checked: true },
    ]

    const documents = [
        {
            title: 'Cobalt Extraction Framework Draft v2.4',
            twg: 'Mining TWG',
            date: 'Oct 24, 2023',
            status: 'CONFIDENTIAL',
            statusColor: 'bg-orange-900/40 text-orange-400 border-orange-500/30',
            type: 'pdf'
        },
        {
            title: 'Q3 Mineral Export Analysis Report',
            twg: 'Trade TWG',
            date: 'Sep 15, 2023',
            status: 'PUBLIC',
            statusColor: 'bg-green-900/40 text-green-400 border-green-500/30',
            type: 'doc'
        },
        {
            title: 'Project Cobalt Budget Estimates 2024',
            twg: 'Finance TWG',
            date: 'Oct 10, 2023',
            status: 'INTERNAL',
            statusColor: 'bg-blue-900/40 text-blue-400 border-blue-500/30',
            type: 'ppt'
        }
    ]

    const meetings = [
        { title: 'Strategic Planning for Cobalt Initiatives', date: 'Oct 24', time: '2h 15m', attendees: 14, status: 'DECISION MADE', snippet: '...committee agreed to proceed with phase 2 of the Cobalt project subject to environmental review...' },
        { title: 'Regional Infrastructure Alignment', date: 'Sep 02', time: '1h 45m', attendees: 8, status: '', snippet: '...discussion on cross-border logistics impacting the Cobalt project supply chain routes...' }
    ]

    return (
        <div className="max-w-6xl mx-auto space-y-8 py-4">
            {/* Search Header */}
            <div className="text-center space-y-6">
                <h1 className="text-4xl font-display font-bold text-slate-900 dark:text-white transition-colors">Global Knowledge Base</h1>
                <div className="max-w-2xl mx-auto relative group">
                    <div className="absolute inset-0 bg-blue-600/20 blur-xl group-focus-within:bg-blue-600/30 transition-all rounded-full"></div>
                    <div className="relative flex items-center bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border rounded-2xl p-1 shadow-2xl transition-all">
                        <div className="pl-4 pr-2 text-slate-400">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                        </div>
                        <input
                            type="text"
                            placeholder="Search Cobalt project..."
                            className="flex-1 bg-transparent border-0 py-3 text-lg focus:ring-0 text-slate-900 dark:text-white placeholder:text-slate-400"
                        />
                        <div className="flex items-center gap-2 pr-2">
                            <button className="p-2 text-slate-400 hover:text-blue-500 transition-colors">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
                            </button>
                            <button className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 px-6 rounded-xl transition-all shadow-lg shadow-blue-900/20 flex items-center gap-2">
                                Search
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
                            </button>
                        </div>
                    </div>
                </div>

                <div className="flex justify-center gap-2 flex-wrap">
                    {tabs.map(tab => (
                        <button
                            key={tab}
                            className={`px-4 py-1.5 rounded-full text-sm font-bold transition-all ${tab === activeTab ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'}`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex flex-col lg:flex-row gap-8">
                {/* Filters Sidebar */}
                <aside className="hidden lg:block w-56 space-y-8 flex-shrink-0">
                    <div className="bg-white dark:bg-dark-card border border-slate-200 dark:border-dark-border rounded-2xl p-5 space-y-6 transition-colors shadow-sm">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
                                Filters
                            </h3>
                            <button className="text-[10px] text-blue-600 font-bold hover:underline">Reset</button>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-3">
                                <label className="text-[10px] font-bold text-slate-500 uppercase">Date Range</label>
                                <select className="w-full bg-slate-50 dark:bg-slate-800 border-0 rounded-lg py-2 px-3 text-sm font-medium text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-colors">
                                    <option>Past month</option>
                                    <option>Past 6 months</option>
                                    <option>Past year</option>
                                </select>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[10px] font-bold text-slate-500 uppercase">Working Group</label>
                                <div className="space-y-2">
                                    {filters.map(f => (
                                        <label key={f.label} className="flex items-center gap-3 cursor-pointer group">
                                            <div className={`w-4 h-4 rounded border transition-colors flex items-center justify-center ${f.checked ? 'bg-blue-600 border-blue-600' : 'bg-slate-50 dark:bg-slate-800 border-slate-300 dark:border-dark-border'}`}>
                                                {f.checked && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                                            </div>
                                            <span className={`text-xs font-medium transition-colors ${f.checked ? 'text-slate-900 dark:text-white' : 'text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300'}`}>{f.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[10px] font-bold text-slate-500 uppercase">Format</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <button className="flex items-center gap-2 px-2 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-dark-border text-[10px] font-bold text-slate-500">
                                        <svg className="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" /></svg>
                                        PDF
                                    </button>
                                    <button className="flex items-center gap-2 px-2 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-dark-border text-[10px] font-bold text-slate-500">
                                        <svg className="w-3 h-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" /></svg>
                                        DOCX
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </aside>

                {/* Results Area */}
                <div className="flex-1 space-y-8">
                    {/* AI Summary Card */}
                    <Card className="p-0 overflow-hidden bg-gradient-to-br from-blue-600/10 to-transparent border-blue-500/20 shadow-none">
                        <div className="p-6 flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-900/40 shrink-0">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                            </div>
                            <div className="space-y-2">
                                <h3 className="font-bold text-slate-900 dark:text-white tracking-wide">AI Summary</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                                    Based on your search for <span className="text-blue-600 font-bold">"Cobalt project"</span>, I found 12 documents and 3 relevant meeting records. The most significant activity occurred in the <span className="font-bold">Mining Regulation TWG</span> during October 2023, focusing on extraction rights and environmental compliance frameworks.
                                </p>
                            </div>
                        </div>
                    </Card>

                    {/* Top Documents */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Top Documents</h2>
                            <button className="text-sm font-bold text-blue-600 hover:underline flex items-center gap-1">
                                View all
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 5l7 7-7 7" /></svg>
                            </button>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                            {documents.map((doc, i) => (
                                <Card key={i} className="group hover:ring-2 hover:ring-blue-500/50 transition-all cursor-pointer">
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-start">
                                            <div className={`p-2 rounded-lg ${doc.type === 'pdf' ? 'bg-red-50 text-red-600 dark:bg-red-900/20' : doc.type === 'doc' ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20' : 'bg-orange-50 text-orange-600 dark:bg-orange-900/20'} transition-colors`}>
                                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                            </div>
                                            <Badge className={`${doc.statusColor} text-[8px] font-black tracking-widest`}>{doc.status}</Badge>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-sm text-slate-900 dark:text-white transition-colors leading-snug group-hover:text-blue-600">{doc.title}</h4>
                                            <p className="text-[10px] text-slate-400 font-bold uppercase mt-1 tracking-tighter">{doc.twg} • {doc.date}</p>
                                        </div>
                                        <div className="flex items-center justify-between pt-2">
                                            <div className="flex -space-x-1.5">
                                                <Avatar size="xs" fallback="JD" />
                                                <Avatar size="xs" fallback="AS" />
                                            </div>
                                            <button className="p-1.5 text-slate-400 hover:text-blue-500 transition-colors">
                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                            </button>
                                        </div>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>

                    {/* Related Meetings */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Related Meetings</h2>
                        <div className="space-y-3">
                            {meetings.map((meeting, i) => (
                                <Card key={i} className="p-5 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all cursor-pointer group">
                                    <div className="flex gap-6">
                                        <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-800 flex flex-col items-center justify-center border border-slate-200 dark:border-dark-border transition-colors">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">{meeting.date.split(' ')[0]}</span>
                                            <span className="text-2xl font-display font-black text-slate-900 dark:text-white">{meeting.date.split(' ')[1]}</span>
                                        </div>
                                        <div className="flex-1 space-y-2">
                                            <div className="flex items-center justify-between">
                                                <h4 className="font-bold text-slate-900 dark:text-white transition-colors group-hover:text-blue-600">{meeting.title}</h4>
                                                {meeting.status && <Badge variant="info" size="sm" className="font-bold text-[9px] tracking-wider">{meeting.status}</Badge>}
                                            </div>
                                            <p className="text-xs text-slate-500 italic leading-relaxed font-serif">"{meeting.snippet}"</p>
                                            <div className="flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-tight pt-1">
                                                <span className="flex items-center gap-1"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>{meeting.time}</span>
                                                <span className="flex items-center gap-1"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>{meeting.attendees} Attendees</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center pl-4 border-l border-slate-100 dark:border-slate-800">
                                            <button className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all shadow-xl shadow-blue-900/0 group-hover:shadow-blue-900/40">
                                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                                            </button>
                                        </div>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
