import { useEffect, useState } from 'react'
import { settingsService, SystemSettings, TwgSettings } from '../../services/settingsService'
import { useAppSelector } from '../../hooks/useRedux'
import { UserRole } from '../../types/auth'

export default function Settings() {
    const user = useAppSelector((state) => state.auth.user)

    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [settings, setSettings] = useState<SystemSettings | null>(null)
    const [twgSettings, setTwgSettings] = useState<TwgSettings | null>(null)

    // System Form State (Admin)
    const [formState, setFormState] = useState({
        enable_google_calendar: false,
        enable_zoom: false,
        enable_teams: false,
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        google_credentials_json: '',
        zoom_credentials_json: '',
        teams_credentials_json: ''
    })

    // TWG Form State (Facilitator)
    const [twgFormState, setTwgFormState] = useState({
        meeting_cadence: 'monthly'
    })

    useEffect(() => {
        if (user) {
            loadSettings()
        }
    }, [user])

    const loadSettings = async () => {
        try {
            setLoading(true)

            // Admin View
            if (user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD) {
                const data = await settingsService.getSystemSettings()
                setSettings(data)
                setFormState(prev => ({
                    ...prev,
                    enable_google_calendar: data.enable_google_calendar,
                    enable_zoom: data.enable_zoom,
                    enable_teams: data.enable_teams,
                    llm_provider: data.llm_provider,
                    llm_model: data.llm_model
                }))
            }
            // Facilitator View
            else if (user?.role === UserRole.FACILITATOR && user.twgs && user.twgs.length > 0) {
                // Load settings for the first TWG (assuming single TWG active for now)
                const twgId = user.twgs[0].id
                const data = await settingsService.getTwgSettings(twgId)
                setTwgSettings(data)
                setTwgFormState(prev => ({
                    ...prev,
                    meeting_cadence: data.meeting_cadence || 'monthly'
                }))
            }
        } catch (error) {
            console.error("Failed to load settings:", error)
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (field: string, value: any) => {
        setFormState(prev => ({ ...prev, [field]: value }))
    }

    const handleTwgChange = (field: string, value: any) => {
        setTwgFormState(prev => ({ ...prev, [field]: value }))
    }

    const handleSave = async () => {
        try {
            setSaving(true)

            if (user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD) {
                const updateData: any = { ...formState }
                if (!updateData.google_credentials_json) delete updateData.google_credentials_json;
                if (!updateData.zoom_credentials_json) delete updateData.zoom_credentials_json;
                if (!updateData.teams_credentials_json) delete updateData.teams_credentials_json;

                const updated = await settingsService.updateSystemSettings(updateData)
                setSettings(updated)
            } else if (twgSettings) {
                const updated = await settingsService.updateTwgSettings(twgSettings.twg_id, twgFormState)
                setTwgSettings(updated)
            }

            console.log('Settings saved successfully')
        } catch (error) {
            console.error("Failed to save settings:", error)
        } finally {
            setSaving(false)
        }
    }

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        )
    }

    // --- RENDER FACILITATOR VIEW ---
    if (user?.role === UserRole.FACILITATOR) {
        if (!user.twgs || user.twgs.length === 0) {
            return <div className="p-8 text-center text-gray-500">You are not assigned to any TWG.</div>
        }
        return (
            <>
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="font-bold text-[#0d121b] dark:text-white text-3xl">TWG Configuration</h1>
                        <p className="text-sm text-[#4c669a] mt-1">Manage preferences for {user.twgs[0].name}</p>
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-4 py-2 bg-[#1152d4] text-white text-sm font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm flex items-center gap-2 disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>

                <div className="bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 shadow-sm">
                    <h3 className="font-bold text-[#0d121b] dark:text-white mb-4">Meeting Preferences</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Default Meeting Cadence</label>
                            <select
                                value={twgFormState.meeting_cadence}
                                onChange={(e) => handleTwgChange('meeting_cadence', e.target.value)}
                                className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-3 py-2 text-sm text-[#0d121b] dark:text-white"
                            >
                                <option value="weekly">Weekly</option>
                                <option value="biweekly">Bi-Weekly</option>
                                <option value="monthly">Monthly</option>
                                <option value="ad-hoc">Ad-Hoc</option>
                            </select>
                        </div>
                    </div>
                </div>
            </>
        )
    }

    // --- RENDER ADMIN VIEW ---
    return (
        <>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="font-bold text-[#0d121b] dark:text-white text-3xl">System Integrations & Configuration</h1>
                    <p className="text-sm text-[#4c669a] mt-1">Manage external connections, security protocols, and AI parameters.</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => loadSettings()}
                        className="px-4 py-2 text-sm font-medium text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white transition-colors"
                    >
                        Discard Changes
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-4 py-2 bg-[#1152d4] text-white text-sm font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm flex items-center gap-2 disabled:opacity-50"
                    >
                        {saving ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                        ) : (
                            <span className="material-symbols-outlined text-[18px]">save</span>
                        )}
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>

            <div className="space-y-8">
                {/* AI Configuration Section */}
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-base font-bold text-[#0d121b] dark:text-white flex items-center gap-2">
                            <span className="material-symbols-outlined text-[#1152d4]">smart_toy</span>
                            AI Model Configuration
                        </h3>
                    </div>
                    <div className="bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 shadow-sm">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">LLM Provider</label>
                                <select
                                    value={formState.llm_provider}
                                    onChange={(e) => handleChange('llm_provider', e.target.value)}
                                    className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-3 py-2 text-sm text-[#0d121b] dark:text-white focus:ring-[#1152d4] focus:border-[#1152d4]"
                                >
                                    <option value="openai">OpenAI</option>
                                    <option value="github">GitHub Models (Azure)</option>
                                    <option value="gemini">Google Gemini</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Model Name</label>
                                <input
                                    type="text"
                                    value={formState.llm_model}
                                    onChange={(e) => handleChange('llm_model', e.target.value)}
                                    className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-3 py-2 text-sm text-[#0d121b] dark:text-white focus:ring-[#1152d4] focus:border-[#1152d4]"
                                    placeholder="e.g. gpt-4o-mini"
                                />
                                <p className="text-xs text-gray-500 mt-1">Specify the model ID to use for agents.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* External Integrations Section */}
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-base font-bold text-[#0d121b] dark:text-white flex items-center gap-2">
                            <span className="material-symbols-outlined text-[#1152d4]">hub</span>
                            External Integrations
                        </h3>
                        {settings?.enable_google_calendar && (
                            <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded font-bold uppercase">System Operational</span>
                        )}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Google Calendar */}
                        <div className="bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 shadow-sm flex flex-col justify-between h-full">
                            <div>
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-lg bg-orange-100 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-orange-600">calendar_month</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white">Calendar Services</h4>
                                            <p className="text-xs text-[#4c669a]">Google Workspace</p>
                                        </div>
                                    </div>
                                    <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                                        <input
                                            type="checkbox"
                                            checked={formState.enable_google_calendar}
                                            onChange={(e) => handleChange('enable_google_calendar', e.target.checked)}
                                            id="toggle-gcal"
                                            className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer checked:right-0 checked:border-green-400 right-5"
                                        />
                                        <label htmlFor="toggle-gcal" className="toggle-label block overflow-hidden h-5 rounded-full bg-green-400 cursor-pointer"></label>
                                    </div>
                                </div>
                                <p className="text-sm text-[#4c669a] mb-4">Allows agents to check availability and schedule meetings directly on user calendars.</p>
                            </div>
                            <div className="pt-4 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                {settings?.has_google_creds ? (
                                    <span className="text-xs font-medium text-green-600 dark:text-green-400 flex items-center gap-1 mb-2">
                                        <span className="material-symbols-outlined text-[14px]">check_circle</span> Credentials Configured
                                    </span>
                                ) : (
                                    <span className="text-xs font-medium text-amber-600 dark:text-amber-400 flex items-center gap-1 mb-2">
                                        <span className="material-symbols-outlined text-[14px]">warning</span> No Credentials
                                    </span>
                                )}
                                <label className="text-xs font-bold text-[#4c669a] uppercase mb-1 block">Update Service Account JSON</label>
                                <textarea
                                    className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded px-3 py-1.5 text-sm text-[#0d121b] dark:text-white h-20"
                                    value={formState.google_credentials_json}
                                    onChange={(e) => handleChange('google_credentials_json', e.target.value)}
                                    placeholder="Paste full JSON content here to update..."
                                />
                            </div>
                        </div>

                        {/* Conferencing API */}
                        <div className="bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 shadow-sm flex flex-col justify-between h-full">
                            <div>
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-lg bg-blue-100 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-blue-600">video_camera_front</span>
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white">Conferencing API</h4>
                                            <p className="text-xs text-[#4c669a]">Zoom</p>
                                        </div>
                                    </div>
                                    <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                                        <input
                                            type="checkbox"
                                            checked={formState.enable_zoom}
                                            onChange={(e) => handleChange('enable_zoom', e.target.checked)}
                                            id="toggle-zoom"
                                            className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer checked:right-0 checked:border-green-400 right-5"
                                        />
                                        <label htmlFor="toggle-zoom" className="toggle-label block overflow-hidden h-5 rounded-full bg-green-400 cursor-pointer"></label>
                                    </div>
                                </div>
                                <p className="text-sm text-[#4c669a] mb-4">Enable automatic generation of meeting links via Zoom API.</p>
                            </div>
                            <div className="pt-4 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                <label className="text-xs font-bold text-[#4c669a] uppercase mb-1 block">JWT Token / OAuth Credentials</label>
                                <input
                                    className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded px-3 py-1.5 text-sm text-[#0d121b] dark:text-white"
                                    type="password"
                                    placeholder="Update credentials..."
                                    value={formState.zoom_credentials_json}
                                    onChange={(e) => handleChange('zoom_credentials_json', e.target.value)}
                                />
                            </div>
                        </div>
                    </div>
                </section>

                <div className="text-center pt-8 pb-4">
                    <p className="text-xs text-[#9ca3af] dark:text-gray-500">
                        Changes to Security settings may require system restart. <br />
                        WAIIS TWG Support System v2.5.0
                    </p>
                </div>
            </div>

            <style>{`
                .toggle-checkbox:checked {
                    right: 0;
                    border-color: #1152d4;
                }
                .toggle-checkbox:checked + .toggle-label {
                    background-color: #1152d4;
                }
            `}</style>
        </>
    )
}
