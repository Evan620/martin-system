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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-full bg-[#1152d4]/10 flex items-center justify-center">
                            <span className="material-symbols-outlined text-[#1152d4]">extension</span>
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-[#0d121b] dark:text-white">System Integrations & Configuration</h2>
                            <p className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Manage external connections, security protocols, and AI parameters</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
                    >
                        <span className="material-symbols-outlined text-[#6b7280]">close</span>
                    </button>
                </div>

                {/* Main Content */}
                <div className="flex-1 overflow-y-auto p-8 space-y-8">
                    {/* External Integrations */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold text-[#0d121b] dark:text-white flex items-center gap-2">
                                <span className="material-symbols-outlined text-[#1152d4]">hub</span>
                                External Integrations
                            </h3>
                            <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded font-bold uppercase">
                                All Systems Operational
                            </span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Calendar Services */}
                            <div className="bg-white dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 shadow-sm">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-lg bg-orange-100 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-orange-600">calendar_month</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white">Calendar Services</h4>
                                            <p className="text-xs text-[#4c669a]">Google Workspace & Office 365</p>
                                        </div>
                                    </div>
                                    <div className="relative inline-block w-10 align-middle select-none">
                                        <input
                                            type="checkbox"
                                            checked={calendarEnabled}
                                            onChange={(e) => setCalendarEnabled(e.target.checked)}
                                            className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer"
                                        />
                                        <label className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer ${calendarEnabled ? 'bg-[#1152d4]' : 'bg-gray-300'}`}></label>
                                    </div>
                                </div>
                                <p className="text-sm text-[#4c669a] mb-4">Allows agents to check availability and schedule meetings directly on user calendars.</p>
                                <div className="pt-4 border-t border-[#e7ebf3] dark:border-[#2d3748] flex items-center justify-between">
                                    <span className="text-xs font-medium text-green-600 dark:text-green-400 flex items-center gap-1">
                                        <span className="material-symbols-outlined text-[14px]">check_circle</span> Connected
                                    </span>
                                    <button className="text-sm font-medium text-[#1152d4] hover:underline">Configure Scopes</button>
                                </div>
                            </div>

                            {/* Conferencing API */}
                            <div className="bg-white dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 shadow-sm">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-lg bg-blue-100 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-blue-600">video_camera_front</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white">Conferencing API</h4>
                                            <p className="text-xs text-[#4c669a]">Zoom & Microsoft Teams</p>
                                        </div>
                                    </div>
                                    <button className="text-xs bg-[#f0f2f5] dark:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] px-2 py-1 rounded hover:bg-gray-200 transition-colors">
                                        Setup
                                    </button>
                                </div>
                                <p className="text-sm text-[#4c669a] mb-4">Enable automatic generation of meeting links for agenda items.</p>
                                <div className="pt-4 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                    <label className="text-xs font-bold text-[#4c669a] uppercase mb-1 block">API Key</label>
                                    <div className="flex gap-2">
                                        <input
                                            className="flex-1 bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded px-3 py-1.5 text-sm text-[#0d121b] dark:text-white"
                                            disabled
                                            type="password"
                                            value="************************"
                                        />
                                        <button className="text-[#1152d4] hover:text-blue-700 p-1">
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
                            <h3 className="text-base font-bold text-[#0d121b] dark:text-white flex items-center gap-2">
                                <span className="material-symbols-outlined text-[#1152d4]">lock</span>
                                Security & Compliance
                            </h3>
                        </div>
                        <div className="bg-white dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl shadow-sm divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                            {/* SSO */}
                            <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex-1">
                                    <h4 className="text-sm font-bold text-[#0d121b] dark:text-white mb-1">Single Sign-On (SSO)</h4>
                                    <p className="text-xs text-[#4c669a]">Require users to sign in via their organizational identity provider.</p>
                                </div>
                                <select
                                    value={ssoProvider}
                                    onChange={(e) => setSsoProvider(e.target.value)}
                                    className="bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm px-3 py-2 text-[#0d121b] dark:text-white focus:ring-[#1152d4] focus:border-[#1152d4]"
                                >
                                    <option>Azure Active Directory</option>
                                    <option>Google Workspace</option>
                                    <option>Okta</option>
                                    <option>Disabled</option>
                                </select>
                            </div>

                            {/* Data Residency */}
                            <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex-1">
                                    <h4 className="text-sm font-bold text-[#0d121b] dark:text-white mb-1">Data Residency</h4>
                                    <p className="text-xs text-[#4c669a]">Specify the geographical region where TWG data is stored and processed.</p>
                                </div>
                                <div className="w-full md:w-64 relative">
                                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#4c669a] pointer-events-none">
                                        <span className="material-symbols-outlined text-[18px]">public</span>
                                    </span>
                                    <select
                                        value={dataResidency}
                                        onChange={(e) => setDataResidency(e.target.value)}
                                        className="pl-10 w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm px-3 py-2 text-[#0d121b] dark:text-white focus:ring-[#1152d4] focus:border-[#1152d4]"
                                    >
                                        <option>West Africa (Lagos)</option>
                                        <option>Europe (Frankfurt)</option>
                                        <option>North America (Virginia)</option>
                                    </select>
                                </div>
                            </div>

                            {/* Two-Factor Auth */}
                            <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex-1">
                                    <h4 className="text-sm font-bold text-[#0d121b] dark:text-white mb-1">Enforce Two-Factor Authentication</h4>
                                    <p className="text-xs text-[#4c669a]">Mandatory 2FA for all users with Administrator privileges.</p>
                                </div>
                                <div className="relative inline-block w-10 align-middle select-none">
                                    <input
                                        type="checkbox"
                                        checked={twoFactorEnabled}
                                        onChange={(e) => setTwoFactorEnabled(e.target.checked)}
                                        className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer"
                                    />
                                    <label className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer ${twoFactorEnabled ? 'bg-[#1152d4]' : 'bg-gray-300'}`}></label>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* AI Agent Behaviors */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold text-[#0d121b] dark:text-white flex items-center gap-2">
                                <span className="material-symbols-outlined text-[#1152d4]">psychology</span>
                                AI Agent Behaviors
                            </h3>
                        </div>
                        <div className="bg-white dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl shadow-sm p-6">
                            <div className="mb-6">
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Knowledge Base Access</label>
                                <p className="text-xs text-[#4c669a] mb-3">Define which document repositories the AI agents can access to generate answers.</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <label className="flex items-center p-3 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-[#1a202c] transition-colors">
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.officialProtocols}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, officialProtocols: e.target.checked })}
                                            className="form-checkbox text-[#1152d4] rounded border-gray-300 focus:ring-[#1152d4] h-4 w-4 mr-3"
                                        />
                                        <span className="text-sm text-[#0d121b] dark:text-white">Official Protocols (PDF)</span>
                                    </label>
                                    <label className="flex items-center p-3 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-[#1a202c] transition-colors">
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.meetingMinutes}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, meetingMinutes: e.target.checked })}
                                            className="form-checkbox text-[#1152d4] rounded border-gray-300 focus:ring-[#1152d4] h-4 w-4 mr-3"
                                        />
                                        <span className="text-sm text-[#0d121b] dark:text-white">Meeting Minutes Archive</span>
                                    </label>
                                    <label className="flex items-center p-3 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-[#1a202c] transition-colors">
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.draftDocuments}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, draftDocuments: e.target.checked })}
                                            className="form-checkbox text-[#1152d4] rounded border-gray-300 focus:ring-[#1152d4] h-4 w-4 mr-3"
                                        />
                                        <span className="text-sm text-[#0d121b] dark:text-white">Draft/Unpublished Documents</span>
                                    </label>
                                    <label className="flex items-center p-3 border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-[#1a202c] transition-colors">
                                        <input
                                            type="checkbox"
                                            checked={knowledgeBase.memberContacts}
                                            onChange={(e) => setKnowledgeBase({ ...knowledgeBase, memberContacts: e.target.checked })}
                                            className="form-checkbox text-[#1152d4] rounded border-gray-300 focus:ring-[#1152d4] h-4 w-4 mr-3"
                                        />
                                        <span className="text-sm text-[#0d121b] dark:text-white">Member Contact Details</span>
                                    </label>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-sm font-bold text-[#0d121b] dark:text-white">Drafting Style Strictness</label>
                                    <span className="text-xs font-mono bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 rounded">
                                        {draftingStrictness < 33 ? 'Formal' : draftingStrictness < 66 ? 'Balanced' : 'Creative'} ({(draftingStrictness / 100).toFixed(1)})
                                    </span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={draftingStrictness}
                                    onChange={(e) => setDraftingStrictness(Number(e.target.value))}
                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-[#1152d4]"
                                />
                                <div className="flex justify-between text-[10px] text-[#4c669a] mt-1 uppercase font-bold tracking-wider">
                                    <span>Conservative</span>
                                    <span>Creative</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <div className="text-center pt-8 pb-4">
                        <p className="text-xs text-[#9ca3af] dark:text-gray-500">
                            Changes to Security settings may require users to re-login. <br />
                            ECOWAS Summit TWG Support System v2.4.0
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4 border-t border-[#e7ebf3] dark:border-[#2d3748] bg-gray-50 dark:bg-[#0d121b]">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white transition-colors"
                    >
                        Discard Changes
                    </button>
                    <button
                        onClick={() => {
                            // Save logic here
                            onClose();
                        }}
                        className="px-4 py-2 bg-[#1152d4] text-white text-sm font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm flex items-center gap-2"
                    >
                        <span className="material-symbols-outlined text-[18px]">save</span>
                        Save Changes
                    </button>
                </div>

                <style>{`
                    .toggle-checkbox:checked {
                        right: 0;
                        border-color: #1152d4;
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
