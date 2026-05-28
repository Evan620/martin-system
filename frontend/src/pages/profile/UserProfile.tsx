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
                    <h1 className="text-3xl font-black text-[#0d121b] dark:text-white tracking-tight">
                        {activeTab === 'profile' ? 'User Profile' : 'Settings'}
                    </h1>
                    <p className="text-[#4c669a] dark:text-[#a0aec0] font-medium">
                        {activeTab === 'profile'
                            ? 'Manage your personal information and preferences.'
                            : 'Configure system integrations and preferences.'}
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="mb-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                <div className="flex gap-8">
                    <button
                        onClick={() => setActiveTab('profile')}
                        className={`pb-3 px-1 text-sm font-bold transition-colors relative ${activeTab === 'profile'
                            ? 'text-[#1152d4] dark:text-blue-400'
                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white'
                            }`}
                    >
                        <span className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px]">person</span>
                            Profile
                        </span>
                        {activeTab === 'profile' && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1152d4] dark:bg-blue-400"></div>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className={`pb-3 px-1 text-sm font-bold transition-colors relative ${activeTab === 'settings'
                            ? 'text-[#1152d4] dark:text-blue-400'
                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white'
                            }`}
                    >
                        <span className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px]">settings</span>
                            Settings
                        </span>
                        {activeTab === 'settings' && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1152d4] dark:bg-blue-400"></div>
                        )}
                    </button>
                </div>
            </div>

            {/* Tab Content */}
            {activeTab === 'profile' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Profile Overview Card */}
                    <div className="lg:col-span-1">
                        <div className="glass-card rounded-xl p-6">
                            <div className="flex flex-col items-center text-center">
                                <div className="size-24 rounded-full bg-blue-100 flex items-center justify-center text-[#1152d4] mb-4">
                                    <span className="material-symbols-outlined text-[48px]">person</span>
                                </div>
                                <h2 className="text-xl font-bold text-[#0d121b] dark:text-white">
                                    {user?.full_name || 'Admin User'}
                                </h2>
                                <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">WAIIS Administrator</p>
                                <div className="mt-4 flex flex-wrap justify-center gap-2">
                                    <span className="px-2 py-1 bg-blue-50 text-blue-600 dark:bg-blue-900/20 text-blue-400 text-xs font-bold rounded uppercase">
                                        {user?.role || 'ADMIN'}
                                    </span>
                                    <span className="px-2 py-1 bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs font-bold rounded">VERIFIED</span>
                                </div>
                            </div>
                            <div className="mt-8 space-y-4">
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="material-symbols-outlined text-[#4c669a] text-[20px]">mail</span>
                                    <span className="text-[#0d121b] dark:text-white">{user?.email || 'admin@ecowas.int'}</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="material-symbols-outlined text-[#4c669a] text-[20px]">location_on</span>
                                    <span className="text-[#0d121b] dark:text-white">Abuja, Nigeria</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="material-symbols-outlined text-[#4c669a] text-[20px]">calendar_today</span>
                                    <span className="text-[#0d121b] dark:text-white">Joined October 2023</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Profile Details & Tabs */}
                    <div className="lg:col-span-2 space-y-8">
                        {/* Personal Details Section */}
                        <div className="glass-card rounded-xl p-6">
                            <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-6">Personal Details</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-[#4c669a] uppercase">First Name</label>
                                    <input className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-4 py-2 text-sm text-[#0d121b] dark:text-white" type="text" defaultValue={user?.full_name?.split(' ')[0] || 'Admin'} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-[#4c669a] uppercase">Last Name</label>
                                    <input className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-4 py-2 text-sm text-[#0d121b] dark:text-white" type="text" defaultValue={user?.full_name?.split(' ').slice(1).join(' ') || 'User'} />
                                </div>
                                <div className="space-y-2 md:col-span-2">
                                    <label className="text-xs font-bold text-[#4c669a] uppercase">Work Email</label>
                                    <input className="w-full bg-[#f6f6f8] dark:bg-[#0d121b] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-4 py-2 text-sm text-[#0d121b] dark:text-white" type="email" defaultValue={user?.email || 'admin@ecowas.int'} disabled />
                                    <p className="text-[10px] text-[#4c669a]">Email address cannot be changed by the user.</p>
                                </div>
                            </div>
                            <div className="mt-8 flex justify-end">
                                <button className="px-6 py-2 bg-[#1152d4] text-white text-sm font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
                                    Save Profile
                                </button>
                            </div>
                        </div>

                        {/* Account Security */}
                        <div className="glass-card rounded-xl p-6">
                            <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-6">Account Security</h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-4 bg-white/40 dark:bg-white/5 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined text-[#4c669a]">password</span>
                                        <div>
                                            <p className="text-sm font-bold text-[#0d121b] dark:text-white">Change Password</p>
                                            <p className="text-xs text-[#4c669a]">Update your account password regularly.</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setIsPasswordModalOpen(true)}
                                        className="px-4 py-1.5 text-sm font-bold border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg hover:bg-white dark:hover:bg-[#4a5568] transition-colors"
                                    >
                                        Change
                                    </button>
                                </div>
                                <div className="flex items-center justify-between p-4 bg-white/40 dark:bg-white/5 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined text-emerald-500">verified_user</span>
                                        <div>
                                            <p className="text-sm font-bold text-[#0d121b] dark:text-white">Two-Factor Authentication</p>
                                            <p className="text-xs text-[#4c669a]">Currently enabled via Google Authenticator.</p>
                                        </div>
                                    </div>
                                    <button className="px-4 py-1.5 text-sm font-bold text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">Disable</button>
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
