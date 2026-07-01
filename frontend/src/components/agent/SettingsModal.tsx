import { useState } from 'react';

interface SettingsModalProps {
    onClose: () => void;
}

export default function SettingsModal({ onClose }: SettingsModalProps) {
    const [calendarEnabled, setCalendarEnabled] = useState(true);
    const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
    const [ssoProvider, setSsoProvider] = useState('Azure Active Directory');
    const [dataResidency, setDataResidency] = useState('West Africa (Lagos)');
    const [draftingStrictness, setDraftingStrictness] = useState(20);
    const [knowledgeBase, setKnowledgeBase] = useState({
        officialProtocols: true,
        meetingMinutes: true,
        draftDocuments: false,
        memberContacts: false,
    });

    return (
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4" style={{ background: 'rgba(0,0,0,0.5)' }}>
            <div className="w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                {/* Header */}
                <div className="flex items-center justify-between p-6" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-full flex items-center justify-center" style={{ background: 'var(--accent-soft)' }}>
                            <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>extension</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>System Integrations & Configuration</h2>
                            <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Manage external connections, security protocols, and AI parameters</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="clickable-scale p-2 rounded-lg transition-colors"
                        style={{ borderRadius: 'var(--radius-ctl)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                        <span className="material-symbols-outlined" style={{ color: 'var(--ink-500)' }}>close</span>
                    </button>
                </div>

                {/* Main Content */}
                <div className="flex-1 overflow-y-auto p-8 space-y-8">
                    {/* External Integrations */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--ink-900)' }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>hub</span>
                                External Integrations
                            </h3>
                            <span className="text-xs px-2 py-1 rounded font-bold uppercase" style={{ background: 'color-mix(in srgb, var(--sage) 12%, transparent)', color: 'var(--sage)' }}>
                                All Systems Operational
                            </span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Calendar Services */}
                            <div className="p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-lg flex items-center justify-center" style={{ background: 'color-mix(in srgb, var(--amber) 12%, transparent)' }}>
                                            <span className="material-symbols-outlined" style={{ color: 'var(--amber)' }}>calendar_month</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold" style={{ color: 'var(--ink-900)' }}>Calendar Services</h4>
                                            <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Google Workspace & Office 365</p>
                                        </div>
                                    </div>
                                    <div className="relative inline-block w-10 align-middle select-none">
                                        <input
                                            type="checkbox"
                                            checked={calendarEnabled}
                                            onChange={(e) => setCalendarEnabled(e.target.checked)}
                                            className="toggle-checkbox absolute block w-5 h-5 rounded-full border-4 appearance-none cursor-pointer"
                                            style={{ background: 'var(--surface)' }}
                                        />
                                        <label className="toggle-label block overflow-hidden h-5 rounded-full cursor-pointer" style={{ background: calendarEnabled ? 'var(--accent)' : 'var(--ink-300)' }}></label>
                                    </div>
                                </div>
                                <p className="text-sm mb-4" style={{ color: 'var(--ink-600)' }}>Allows agents to check availability and schedule meetings directly on user calendars.</p>
                                <div className="pt-4 flex items-center justify-between" style={{ borderTop: '1px solid var(--border)' }}>
                                    <span className="text-xs font-medium flex items-center gap-1" style={{ color: 'var(--sage)' }}>
                                        <span className="material-symbols-outlined text-[14px]">check_circle</span> Connected
                                    </span>
                                    <button className="text-sm font-medium hover:underline" style={{ color: 'var(--accent)' }}>Configure Scopes</button>
                                </div>
                            </div>

                            {/* Conferencing API */}
                            <div className="p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-lg flex items-center justify-center" style={{ background: 'var(--accent-soft)' }}>
                                            <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>video_camera_front</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold" style={{ color: 'var(--ink-900)' }}>Conferencing API</h4>
                                            <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Zoom & Microsoft Teams</p>
                                        </div>
                                    </div>
                                    <button className="text-xs px-2 py-1 rounded transition-colors" style={{ background: 'var(--surface-2)', color: 'var(--ink-600)', border: '1px solid var(--border)' }}>
                                        Setup
                                    </button>
                                </div>
                                <p className="text-sm mb-4" style={{ color: 'var(--ink-600)' }}>Enable automatic generation of meeting links for agenda items.</p>
                                <div className="pt-4" style={{ borderTop: '1px solid var(--border)' }}>
                                    <label className="text-xs font-bold uppercase mb-1 block" style={{ color: 'var(--ink-500)', letterSpacing: '0.08em' }}>API Key</label>
                                    <div className="flex gap-2">
                                        <input
                                            className="flex-1 rounded px-3 py-1.5 text-sm"
                                            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--ink-900)', borderRadius: 'var(--radius-ctl)' }}
                                            disabled
                                            type="password"
                                            value="************************"
                                        />
                                        <button className="clickable-scale hover:opacity-80 p-1" style={{ color: 'var(--accent)' }}>
                                            <span className="material-symbols-outlined text-[18px]">edit</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Security & Compliance */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--ink-900)' }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>lock</span>
                                Security & Compliance
                            </h3>
                        </div>
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                            {/* SSO */}
                            <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex-1">
                                    <h4 className="text-sm font-bold mb-1" style={{ color: 'var(--ink-900)' }}>Single Sign-On (SSO)</h4>
                                    <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Require users to sign in via their organizational identity provider.</p>
                                </div>
                                <select
                                    value={ssoProvider}
                                    onChange={(e) => setSsoProvider(e.target.value)}
                                    className="rounded-lg text-sm px-3 py-2"
                                    style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--ink-900)', borderRadius: 'var(--radius-ctl)' }}
                                >
                                    <option>Azure Active Directory</option>
                                    <option>Google Workspace</option>
                                    <option>Okta</option>
                                    <option>Disabled</option>
                                </select>
                            </div>

                            {/* Data Residency */}
                            <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4" style={{ borderTop: '1px solid var(--border)' }}>
                                <div className="flex-1">
                                    <h4 className="text-sm font-bold mb-1" style={{ color: 'var(--ink-900)' }}>Data Residency</h4>
                                    <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Specify the geographical region where TWG data is stored and processed.</p>
                                </div>
                                <div className="w-full md:w-64 relative">
                                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none" style={{ color: 'var(--ink-500)' }}>
                                        <span className="material-symbols-outlined text-[18px]">public</span>
                                    </span>
                                    <select
                                        value={dataResidency}
                                        onChange={(e) => setDataResidency(e.target.value)}
                                        className="pl-10 w-full rounded-lg text-sm px-3 py-2"
                                        style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--ink-900)', borderRadius: 'var(--radius-ctl)' }}
                                    >
                                        <option>West Africa (Lagos)</option>
                                        <option>Europe (Frankfurt)</option>
                                        <option>North America (Virginia)</option>
                                    </select>
                                </div>
                            </div>

                            {/* Two-Factor Auth */}
                            <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4" style={{ borderTop: '1px solid var(--border)' }}>
                                <div className="flex-1">
                                    <h4 className="text-sm font-bold mb-1" style={{ color: 'var(--ink-900)' }}>Enforce Two-Factor Authentication</h4>
                                    <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Mandatory 2FA for all users with Administrator privileges.</p>
                                </div>
                                <div className="relative inline-block w-10 align-middle select-none">
                                    <input
                                        type="checkbox"
                                        checked={twoFactorEnabled}
                                        onChange={(e) => setTwoFactorEnabled(e.target.checked)}
                                        className="toggle-checkbox absolute block w-5 h-5 rounded-full border-4 appearance-none cursor-pointer"
                                        style={{ background: 'var(--surface)' }}
                                    />
                                    <label className="toggle-label block overflow-hidden h-5 rounded-full cursor-pointer" style={{ background: twoFactorEnabled ? 'var(--accent)' : 'var(--ink-300)' }}></label>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* AI Agent Behaviors */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--ink-900)' }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>psychology</span>
                                AI Agent Behaviors
                            </h3>
                        </div>
                        <div className="p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                            <div className="mb-6">
                                <label className="block text-sm font-bold mb-2" style={{ color: 'var(--ink-900)' }}>Knowledge Base Access</label>
                                <p className="text-xs mb-3" style={{ color: 'var(--ink-500)' }}>Define which document repositories the AI agents can access to generate answers.</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <label className="flex items-center p-3 rounded-lg cursor-pointer transition-colors" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)' }} onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.officialProtocols}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, officialProtocols: e.target.checked })}
                                            className="form-checkbox rounded h-4 w-4 mr-3"
                                            style={{ accentColor: 'var(--accent)' }}
                                        />
                                        <span className="text-sm" style={{ color: 'var(--ink-900)' }}>Official Protocols (PDF)</span>
                                    </label>
                                    <label className="flex items-center p-3 rounded-lg cursor-pointer transition-colors" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)' }} onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.meetingMinutes}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, meetingMinutes: e.target.checked })}
                                            className="form-checkbox rounded h-4 w-4 mr-3"
                                            style={{ accentColor: 'var(--accent)' }}
                                        />
                                        <span className="text-sm" style={{ color: 'var(--ink-900)' }}>Meeting Minutes Archive</span>
                                    </label>
                                    <label className="flex items-center p-3 rounded-lg cursor-pointer transition-colors" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)' }} onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.draftDocuments}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, draftDocuments: e.target.checked })}
                                            className="form-checkbox rounded h-4 w-4 mr-3"
                                            style={{ accentColor: 'var(--accent)' }}
                                        />
                                        <span className="text-sm" style={{ color: 'var(--ink-900)' }}>Draft/Unpublished Documents</span>
                                    </label>
                                    <label className="flex items-center p-3 rounded-lg cursor-pointer transition-colors" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)' }} onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.memberContacts}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, memberContacts: e.target.checked })}
                                            className="form-checkbox rounded h-4 w-4 mr-3"
                                            style={{ accentColor: 'var(--accent)' }}
                                        />
                                        <span className="text-sm" style={{ color: 'var(--ink-900)' }}>Member Contact Details</span>
                                    </label>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-sm font-bold" style={{ color: 'var(--ink-900)' }}>Drafting Style Strictness</label>
                                    <span className="text-xs font-mono px-2 rounded" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                        {draftingStrictness < 33 ? 'Formal' : draftingStrictness < 66 ? 'Balanced' : 'Creative'} ({(draftingStrictness / 100).toFixed(1)})
                                    </span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={draftingStrictness}
                                    onChange={(e) => setDraftingStrictness(Number(e.target.value))}
                                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                                    style={{ background: 'var(--surface-2)', accentColor: 'var(--accent)' }}
                                />
                                <div className="flex justify-between text-[10px] mt-1 uppercase font-bold tracking-wider" style={{ color: 'var(--ink-500)' }}>
                                    <span>Conservative</span>
                                    <span>Creative</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <div className="text-center pt-8 pb-4">
                        <p className="text-xs" style={{ color: 'var(--ink-400)' }}>
                            Changes to Security settings may require users to re-login. <br />
                            WAIIS TWG Support System v2.4.0
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                    <button
                        onClick={onClose}
                        className="clickable-scale px-4 py-2 text-sm font-medium transition-colors"
                        style={{ color: 'var(--ink-600)' }}
                        onMouseEnter={e => (e.currentTarget.style.color = 'var(--ink-900)')}
                        onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-600)')}
                    >
                        Discard Changes
                    </button>
                    <button
                        onClick={() => {
                            // Save logic here
                            onClose();
                        }}
                        className="clickable-scale px-4 py-2 text-sm font-bold rounded-lg hover:opacity-90 transition-colors flex items-center gap-2"
                        style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                    >
                        <span className="material-symbols-outlined text-[18px]">save</span>
                        Save Changes
                    </button>
                </div>

                <style>{`
                    .toggle-checkbox:checked {
                        right: 0;
                        border-color: var(--accent);
                    }
                    .toggle-checkbox {
                        right: 1.25rem;
                        transition: right 0.2s ease-in-out;
                    }
                `}</style>
            </div>
        </div>
    );
}
