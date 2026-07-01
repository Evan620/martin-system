import { useState } from 'react'
import { useAppSelector } from '../../hooks/useRedux'
import Settings from '../settings/Settings'
import ChangePasswordModal from '../../components/profile/ChangePasswordModal'

export default function UserProfile() {
    const user = useAppSelector((state) => state.auth.user)
    const [activeTab, setActiveTab] = useState<'profile' | 'settings'>('profile')
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false)

    return (
        <>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-black tracking-tight" style={{ color: 'var(--ink-900)' }}>
                        {activeTab === 'profile' ? 'User Profile' : 'Settings'}
                    </h1>
                    <p className="font-medium" style={{ color: 'var(--ink-500)' }}>
                        {activeTab === 'profile'
                            ? 'Manage your personal information and preferences.'
                            : 'Configure system integrations and preferences.'}
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="mb-6 border-b" style={{ borderColor: 'var(--border)' }}>
                <div className="flex gap-8">
                    <button
                        onClick={() => setActiveTab('profile')}
                        className="clickable-scale pb-3 px-1 text-sm font-bold transition-colors relative"
                        style={{ color: activeTab === 'profile' ? 'var(--accent)' : 'var(--ink-500)' }}
                    >
                        <span className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px]">person</span>
                            Profile
                        </span>
                        {activeTab === 'profile' && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: 'var(--accent)' }}></div>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className="clickable-scale pb-3 px-1 text-sm font-bold transition-colors relative"
                        style={{ color: activeTab === 'settings' ? 'var(--accent)' : 'var(--ink-500)' }}
                    >
                        <span className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px]">settings</span>
                            Settings
                        </span>
                        {activeTab === 'settings' && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: 'var(--accent)' }}></div>
                        )}
                    </button>
                </div>
            </div>

            {/* Tab Content */}
            {activeTab === 'profile' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Profile Overview Card */}
                    <div className="lg:col-span-1">
                        <div className="p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                            <div className="flex flex-col items-center text-center">
                                <div className="size-24 rounded-full flex items-center justify-center mb-4" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                    <span className="material-symbols-outlined text-[48px]">person</span>
                                </div>
                                <h2 className="text-xl font-bold" style={{ color: 'var(--ink-900)' }}>
                                    {user?.full_name || 'Admin User'}
                                </h2>
                                <p className="text-sm" style={{ color: 'var(--ink-500)' }}>WAIIS Administrator</p>
                                <div className="mt-4 flex flex-wrap justify-center gap-2">
                                    <span className="px-2 py-1 text-xs font-bold rounded uppercase" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                        {user?.role || 'ADMIN'}
                                    </span>
                                    <span className="px-2 py-1 text-xs font-bold rounded" style={{ background: 'var(--accent-soft)', color: 'var(--sage)' }}>VERIFIED</span>
                                </div>
                            </div>
                            <div className="mt-8 space-y-4">
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--ink-500)' }}>mail</span>
                                    <span style={{ color: 'var(--ink-900)' }}>{user?.email || 'admin@ecowas.int'}</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--ink-500)' }}>location_on</span>
                                    <span style={{ color: 'var(--ink-900)' }}>Abuja, Nigeria</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--ink-500)' }}>calendar_today</span>
                                    <span style={{ color: 'var(--ink-900)' }}>Joined October 2023</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Profile Details & Tabs */}
                    <div className="lg:col-span-2 space-y-8">
                        {/* Personal Details Section */}
                        <div className="p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                            <h3 className="text-lg font-bold mb-6" style={{ color: 'var(--ink-900)' }}>Personal Details</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="qp-eyebrow">First Name</label>
                                    <input className="w-full px-4 py-2 text-sm" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-900)' }} type="text" defaultValue={user?.full_name?.split(' ')[0] || 'Admin'} />
                                </div>
                                <div className="space-y-2">
                                    <label className="qp-eyebrow">Last Name</label>
                                    <input className="w-full px-4 py-2 text-sm" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-900)' }} type="text" defaultValue={user?.full_name?.split(' ').slice(1).join(' ') || 'User'} />
                                </div>
                                <div className="space-y-2 md:col-span-2">
                                    <label className="qp-eyebrow">Work Email</label>
                                    <input className="w-full px-4 py-2 text-sm" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-900)' }} type="email" defaultValue={user?.email || 'admin@ecowas.int'} disabled />
                                    <p className="text-[10px]" style={{ color: 'var(--ink-500)' }}>Email address cannot be changed by the user.</p>
                                </div>
                            </div>
                            <div className="mt-8 flex justify-end">
                                <button className="clickable-scale px-6 py-2 text-sm font-bold transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}>
                                    Save Profile
                                </button>
                            </div>
                        </div>

                        {/* Account Security */}
                        <div className="p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                            <h3 className="text-lg font-bold mb-6" style={{ color: 'var(--ink-900)' }}>Account Security</h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-4" style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-ctl)' }}>
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined" style={{ color: 'var(--ink-500)' }}>password</span>
                                        <div>
                                            <p className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>Change Password</p>
                                            <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Update your account password regularly.</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setIsPasswordModalOpen(true)}
                                        className="clickable-scale px-4 py-1.5 text-sm font-bold transition-colors"
                                        style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-700)', background: 'var(--surface)' }}
                                    >
                                        Change
                                    </button>
                                </div>
                                <div className="flex items-center justify-between p-4" style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-ctl)' }}>
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined" style={{ color: 'var(--sage)' }}>verified_user</span>
                                        <div>
                                            <p className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>Two-Factor Authentication</p>
                                            <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Currently enabled via Google Authenticator.</p>
                                        </div>
                                    </div>
                                    <button className="px-4 py-1.5 text-sm font-bold transition-colors" style={{ color: 'var(--terra)', borderRadius: 'var(--radius-ctl)' }}>Disable</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <Settings />
            )}

            <ChangePasswordModal
                isOpen={isPasswordModalOpen}
                onClose={() => setIsPasswordModalOpen(false)}
            />
        </>
    )
}
