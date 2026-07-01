import { Badge, Avatar } from '../../components/ui'

export default function AgentAssistant() {
    return (
        <div className="h-full flex flex-col -m-6" style={{ background: 'var(--bg)', color: 'var(--ink-700)' }}>
            {/* Header */}
            <header className="px-8 py-5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
                <div>
                    <div className="flex items-center gap-2 qp-eyebrow">
                        <span>Workspace</span>
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 5l7 7-7 7" /></svg>
                        <span>Infrastructure TWG</span>
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 5l7 7-7 7" /></svg>
                        <span className="flex items-center gap-1" style={{ color: 'var(--accent)' }}>
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" /></svg>
                            Agent Assistant
                        </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2">
                        <h1 className="text-2xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>TWG Assistant</h1>
                        <Badge variant="neutral" style={{ background: 'var(--surface-2)', color: 'var(--ink-500)', borderColor: 'var(--border)' }}>AI-Powered Support & Command Interface</Badge>
                    </div>
                </div>
                <div className="flex gap-2">
                    <button className="px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 clickable-scale" style={{ background: 'var(--surface-2)', color: 'var(--ink-700)', border: '1px solid var(--border)' }}>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        History
                    </button>
                    <button className="px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 clickable-scale" style={{ background: 'var(--surface-2)', color: 'var(--ink-700)', border: '1px solid var(--border)' }}>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m12 4a2 2 0 100-4m0 4a2 2 0 110-4m-6 0h4m-12 0h4M12 14v4" /></svg>
                        Configure Agent
                    </button>
                </div>
            </header>

            {/* Main Layout */}
            <div className="flex-1 flex overflow-hidden">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col p-8 overflow-y-auto space-y-8 scrollbar-hide">
                    {/* Date Divider */}
                    <div className="flex justify-center">
                        <span className="px-4 py-1 rounded-full qp-eyebrow" style={{ background: 'var(--surface-2)' }}>Today, 10:23 AM</span>
                    </div>

                    {/* Agent Message */}
                    <div className="flex gap-5 max-w-4xl opacity-0 animate-fade-in-up" style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}>
                            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" /><path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z" /></svg>
                        </div>
                        <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>ECOWAS Agent</span>
                                <span className="text-[10px] font-bold" style={{ color: 'var(--ink-500)' }}>10:23 AM</span>
                            </div>
                            <div className="rounded-2xl p-5 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                                <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-700)' }}>
                                    Good morning. I've analyzed the previous meeting minutes from the Lagos Summit. Based on the pending action items, would you like me to draft the agenda for tomorrow's infrastructure session? I can also summarize the outstanding transport corridor reports.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* User Message */}
                    <div className="flex gap-5 max-w-4xl ml-auto flex-row-reverse opacity-0 animate-fade-in-up" style={{ animationDelay: '400ms', animationFillMode: 'forwards' }}>
                        <Avatar size="sm" fallback="AK" alt="Amara Koné" className="shrink-0" />
                        <div className="space-y-2 flex-1 text-right">
                            <div className="flex items-center gap-2 justify-end">
                                <span className="text-[10px] font-bold" style={{ color: 'var(--ink-500)' }}>10:25 AM</span>
                                <span className="text-sm font-bold" style={{ color: 'var(--accent)' }}>You</span>
                            </div>
                            <div className="rounded-2xl p-5 inline-block text-left" style={{ background: 'var(--accent)', border: '1px solid var(--accent)' }}>
                                <p className="text-sm font-medium leading-relaxed" style={{ color: 'var(--accent-ink)' }}>
                                    Yes, please draft the agenda. Make sure to include a specific section on the cross-border transport initiative. That's a priority for the Minister.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Agent Processing */}
                    <div className="flex gap-5 max-w-4xl opacity-0 animate-fade-in-up" style={{ animationDelay: '600ms', animationFillMode: 'forwards' }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--surface-2)' }}>
                            <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: 'var(--ink-500)' }}><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>ECOWAS Agent</span>
                                <span className="text-[10px] font-bold animate-pulse" style={{ color: 'var(--accent)' }}>Processing...</span>
                            </div>
                        </div>
                    </div>

                    {/* Agent Result Message */}
                    <div className="flex gap-5 max-w-4xl opacity-0 animate-fade-in-up" style={{ animationDelay: '1s', animationFillMode: 'forwards' }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}>
                            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" /><path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z" /></svg>
                        </div>
                        <div className="space-y-2 flex-1 pb-20">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>ECOWAS Agent</span>
                                <span className="text-[10px] font-bold" style={{ color: 'var(--ink-500)' }}>10:26 AM</span>
                            </div>
                            <div className="rounded-2xl p-5 space-y-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                                <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-700)' }}>
                                    I have generated a draft agenda incorporating the Cross-Border Transport Initiative as a key discussion point (Item 3.2).
                                </p>
                                <div className="p-4 rounded-xl flex items-center justify-between group cursor-pointer transition-all" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-lg flex items-center justify-center" style={{ background: 'color-mix(in srgb, var(--terra) 12%, transparent)', color: 'var(--terra)' }}>
                                            <svg className="w-7 h-7" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" /></svg>
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold group-hover:opacity-80 transition-colors" style={{ color: 'var(--ink-900)' }}>Draft_Agenda_v1.pdf</p>
                                            <p className="qp-eyebrow" style={{ textTransform: 'uppercase', letterSpacing: '-0.01em' }}>Generated just now • 145 KB</p>
                                        </div>
                                    </div>
                                    <button className="p-2 transition-colors" style={{ color: 'var(--ink-500)' }}>
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" /></svg>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Sidebar Context */}
                <aside className="w-80 p-6 space-y-8 overflow-y-auto scrollbar-hide" style={{ borderLeft: '1px solid var(--border)', background: 'var(--surface)' }}>
                    <div className="space-y-4">
                        <h3 className="qp-eyebrow flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
                            Active Context
                        </h3>
                        <div className="space-y-6">
                            <div className="space-y-4">
                                <label className="qp-eyebrow">References</label>
                                <div className="rounded-xl p-4 text-center" style={{ background: 'var(--surface-2)', border: '1px dashed var(--border)' }}>
                                    <p className="text-[11px] font-bold" style={{ color: 'var(--ink-500)' }}>No references attached</p>
                                    <p className="text-[9px] font-bold uppercase mt-1" style={{ color: 'var(--ink-400)' }}>Files you share with the agent will appear here</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </aside>
            </div>

            {/* Input Footer */}
            <div className="p-8 pb-10" style={{ borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
                <div className="max-w-4xl mx-auto space-y-4">
                    <div className="flex gap-3">
                        {['Summarize Minutes', 'Check Schedule', 'Translate to French'].map(action => (
                            <button key={action} className="px-4 py-1.5 rounded-lg text-[10px] font-bold tracking-tight transition-all flex items-center gap-2 clickable-scale" style={{ background: 'var(--surface-2)', color: 'var(--ink-700)', border: '1px solid var(--border)' }}>
                                {action === 'Summarize Minutes' && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>}
                                {action === 'Check Schedule' && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>}
                                {action === 'Translate to French' && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M3 5h12M9 3v2m1.048 9.5a18.022 18.022 0 01-3.827-2.028m-1.391 2.308A11.013 11.013 0 014.5 12c.677-.34 1.566-.663 2.251-1.023m3.297 3.023c.33.165.666.33 1 .495M15 19v-1a4 4 0 00-4-4h-1" /></svg>}
                                {action}
                            </button>
                        ))}
                    </div>
                    <div className="relative group">
                        <div className="absolute inset-x-0 -top-px h-px" style={{ background: 'linear-gradient(to right, transparent, var(--accent), transparent)' }}></div>
                        <div className="rounded-2xl flex items-center p-2 transition-all group-focus-within:border-teal-500" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                            <button className="p-3 transition-colors" style={{ color: 'var(--ink-500)' }}>
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
                            </button>
                            <input
                                type="text"
                                placeholder="Message the Agent or type / for commands..."
                                className="flex-1 bg-transparent border-0 focus:ring-0 text-sm py-4"
                                style={{ color: 'var(--ink-900)' }}
                            />
                            <button className="w-10 h-10 rounded-xl flex items-center justify-center transition-all clickable-scale" style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}>
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                            </button>
                        </div>
                    </div>
                    <p className="text-center text-[8px] font-bold uppercase tracking-widest" style={{ color: 'var(--ink-400)' }}>
                        AI generated content may require verification. Protected under ECOWAS Digital Sovereignty Policy.
                    </p>
                </div>
            </div>
        </div>
    )
}
