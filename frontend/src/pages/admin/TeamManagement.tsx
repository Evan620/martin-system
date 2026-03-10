import { useState, useEffect } from 'react'
import { userService, UserUpdateData } from '../../services/userService'
import { twgs as twgService } from '../../services/api'
import api from '../../services/api'
import { User, UserRole } from '../../types/auth'
import { Avatar } from '../../components/ui'
import { toast } from 'react-toastify'


import { useAppSelector } from '../../hooks/useRedux'

export default function TeamManagement() {
    const currentUser = useAppSelector((state) => state.auth.user)
    const [users, setUsers] = useState<User[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [activeTab, setActiveTab] = useState<'users' | 'governance'>('users')

    // Governance State
    const [twgs, setTwgs] = useState<any[]>([])
    const [loadingTwgs, setLoadingTwgs] = useState(false)

    // Team Assignment Modal State
    const [isTeamModalOpen, setIsTeamModalOpen] = useState(false)
    const [editingUser, setEditingUser] = useState<User | null>(null)
    const [selectedTwgs, setSelectedTwgs] = useState<string[]>([])

    // Track if we're enforcing TWG selection (for facilitator role)
    const [enforceTwgSelection, setEnforceTwgSelection] = useState(false)

    // Invite User Modal State
    const [isInviteModalOpen, setIsInviteModalOpen] = useState(false)
    const [inviteForm, setInviteForm] = useState({
        email: '',
        full_name: '',
        role: UserRole.MEMBER,
        organization: '',
        twg_ids: [] as string[]
    })
    const [tempPassword, setTempPassword] = useState<string | null>(null)

    // Edit User Details Modal State
    const [isEditModalOpen, setIsEditModalOpen] = useState(false)
    const [editForm, setEditForm] = useState({
        id: '',
        full_name: '',
        email: '',
        organization: ''
    })
    const [isSavingEdit, setIsSavingEdit] = useState(false)

    // Bulk Upload Modal State
    const [isBulkUploadModalOpen, setIsBulkUploadModalOpen] = useState(false)
    const [csvFile, setCsvFile] = useState<File | null>(null)
    const [parsedUsers, setParsedUsers] = useState<any[]>([])
    const [isParsing, setIsParsing] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [parseError, setParseError] = useState<string | null>(null)
    const [bulkUploadResults, setBulkUploadResults] = useState<{
        successful: any[]
        failed: any[]
    } | null>(null)

    useEffect(() => {
        loadUsers()
    }, [])

    const loadUsers = async () => {
        setIsLoading(true)
        try {
            const data = await userService.getUsers()
            setUsers(data)
        } catch (error) {
            console.error('Failed to load users', error)
            toast.error('Failed to load users')
        } finally {
            setIsLoading(false)
        }
    }

    const loadTwgs = async () => {
        setLoadingTwgs(true)
        try {
            const response = await twgService.list()
            setTwgs(response.data)
        } catch (error) {
            console.error('Failed to load TWGs', error)
            toast.error('Failed to load TWGs')
        } finally {
            setLoadingTwgs(false)
        }
    }

    useEffect(() => {
        if (activeTab === 'governance') {
            loadTwgs()
        }
    }, [activeTab])

    const handleUpdateTwg = async (twgId: string, data: any) => {
        try {
            await twgService.update(twgId, data)
            toast.success('TWG Leadership updated')
            loadTwgs()
        } catch (error) {
            console.error('Failed to update TWG', error)
            toast.error('Failed to update TWG')
        }
    }

    const handleUpdateUser = async (userId: string, data: UserUpdateData) => {
        try {
            await userService.updateUser(userId, data)
            toast.success('User updated successfully')
            loadUsers()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to update user'
            console.error('Failed to update user:', error)
            toast.error(message)
        }
    }

    const handleRoleChange = async (user: User, newRole: UserRole) => {
        // If changing to FACILITATOR or MEMBER, prompt for TWG assignment
        if (newRole === UserRole.FACILITATOR || newRole === UserRole.MEMBER) {
            // First update the role
            await handleUpdateUser(user.id, { role: newRole })
            // Mark that we're enforcing TWG selection for facilitators
            setEnforceTwgSelection(newRole === UserRole.FACILITATOR)
            // Then open the teams modal
            toast.info(newRole === UserRole.FACILITATOR
                ? 'Facilitators must be assigned to at least one TWG'
                : 'Please assign TWGs for this user'
            )
            openTeamModal({ ...user, role: newRole })
        } else {
            // For ADMIN or SECRETARIAT_LEAD, just update the role
            await handleUpdateUser(user.id, { role: newRole })
        }
    }

    const [resendingUserId, setResendingUserId] = useState<string | null>(null)

    const handleResendInvite = async (user: User) => {
        if (!window.confirm(`Resend invite to ${user.full_name} (${user.email})? This will reset their password.`)) return
        setResendingUserId(user.id)
        try {
            const result = await userService.resendInvite(user.id)
            toast.success(`Invite resent! New temporary password: ${result.temporary_password}`)
            loadUsers()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to resend invite'
            console.error('Failed to resend invite:', error)
            toast.error(message)
        } finally {
            setResendingUserId(null)
        }
    }

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm('Are you sure you want to delete this user?')) return
        try {
            await userService.deleteUser(userId)
            toast.success('User deleted successfully')
            loadUsers()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to delete user'
            console.error('Failed to delete user:', error)
            toast.error(message)
        }
    }

    const openTeamModal = (user: User) => {
        setEditingUser(user)
        // Ensure all TWG IDs are strings for consistent comparison
        setSelectedTwgs((user.twg_ids || []).map(id => String(id)))
        setIsTeamModalOpen(true)
        if (twgs.length === 0) {
            loadTwgs()
        }
    }

    const [isSavingTeams, setIsSavingTeams] = useState(false)

    const handleSaveTeams = async () => {
        if (!editingUser) return

        // If enforcing TWG selection (facilitator) and no TWGs selected, show error
        if (enforceTwgSelection && selectedTwgs.length === 0) {
            toast.error('Facilitators must be assigned to at least one TWG')
            return
        }

        setIsSavingTeams(true)
        try {
            await userService.updateUser(editingUser.id, { twg_ids: selectedTwgs })
            toast.success('Teams updated successfully')
            setIsTeamModalOpen(false)
            setEnforceTwgSelection(false)
            loadUsers()
        } catch (error) {
            console.error('Failed to update teams', error)
            toast.error('Failed to update teams')
        } finally {
            setIsSavingTeams(false)
        }
    }

    const handleCancelTeamModal = async () => {
        // If we were enforcing TWG selection (facilitator) and they cancel, revert to MEMBER
        if (enforceTwgSelection && editingUser) {
            await handleUpdateUser(editingUser.id, { role: UserRole.MEMBER })
            toast.warning('Role changed to Member (read-only) - no TWG assignment required')
        }
        setIsTeamModalOpen(false)
        setEnforceTwgSelection(false)
        loadUsers()
    }

    const toggleTwgSelection = (twgId: string) => {
        setSelectedTwgs(prev =>
            prev.includes(twgId)
                ? prev.filter(id => id !== twgId)
                : [...prev, twgId]
        )
    }

    const [isInviting, setIsInviting] = useState(false)

    const handleInviteUser = async () => {
        setIsInviting(true)
        try {
            const response = await api.post('/users/invite', {
                ...inviteForm,
                send_email: true
            })
            setTempPassword(response.data.temporary_password)
            toast.success(`User invited! Temporary password: ${response.data.temporary_password}`)
            loadUsers()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to invite user'
            toast.error(message)
        } finally {
            setIsInviting(false)
        }
    }

    const resetInviteForm = () => {
        setInviteForm({
            email: '',
            full_name: '',
            role: UserRole.MEMBER,
            organization: '',
            twg_ids: []
        })
        setTempPassword(null)
        setIsInviteModalOpen(false)
    }

    const openEditModal = (user: User) => {
        setEditForm({
            id: user.id,
            full_name: user.full_name,
            email: user.email,
            organization: user.organization || ''
        })
        setIsEditModalOpen(true)
    }

    const handleSaveEdit = async () => {
        if (!editForm.full_name.trim() || !editForm.email.trim()) {
            toast.error('Name and email are required')
            return
        }

        setIsSavingEdit(true)
        try {
            await userService.updateUser(editForm.id, {
                full_name: editForm.full_name.trim(),
                email: editForm.email.trim(),
                organization: editForm.organization.trim() || undefined
            })
            toast.success('User details updated successfully')
            setIsEditModalOpen(false)
            loadUsers()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to update user details'
            toast.error(message)
        } finally {
            setIsSavingEdit(false)
        }
    }

    const closeEditModal = () => {
        setIsEditModalOpen(false)
        setEditForm({ id: '', full_name: '', email: '', organization: '' })
    }

    // Bulk Upload Handlers
    const downloadTemplate = () => {
        const headers = ['Email', 'Full Name', 'Role', 'Organization', 'TWG Names (comma-separated)']
        const rows = [
            headers.join(','),
            'john@example.com,John Doe,TWG_MEMBER,Example Organization,"Energy TWG, Agriculture TWG"',
            'jane@example.com,Jane Smith,SECRETARIAT_LEAD,Secretariat,',
        ]
        const csvContent = rows.join('\n')
        const blob = new Blob([csvContent], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'bulk_users_template.csv'
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Template downloaded')
    }

    const parseCSV = (file: File): Promise<any[]> => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = (e) => {
                try {
                    const text = e.target?.result as string
                    const lines = text.split('\n').filter(line => line.trim())
                    const headers = lines[0].split(',').map(h => h.trim().toLowerCase())

                    const users = lines.slice(1).map(line => {
                        const values: string[] = []
                        let inQuotes = false
                        let currentValue = ''

                        for (let i = 0; i < line.length; i++) {
                            const char = line[i]
                            if (char === '"') {
                                inQuotes = !inQuotes
                            } else if (char === ',' && !inQuotes) {
                                values.push(currentValue.trim())
                                currentValue = ''
                            } else {
                                currentValue += char
                            }
                        }
                        values.push(currentValue.trim())

                        const user: any = {}
                        headers.forEach((header, index) => {
                            user[header] = values[index] || ''
                        })
                        return user
                    }).filter(user => user.email && (user.full_name || user['full name']))

                    resolve(users)
                } catch (error) {
                    reject(error)
                }
            }
            reader.onerror = () => reject(new Error('Failed to read file'))
            reader.readAsText(file)
        })
    }

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        if (!file.name.endsWith('.csv')) {
            toast.error('Please upload a CSV file')
            return
        }

        setCsvFile(file)
        setIsParsing(true)
        setParsedUsers([])
        setParseError(null)
        setBulkUploadResults(null)

        try {
            const users = await parseCSV(file)
            if (users.length === 0) {
                setParseError('No valid users found. Each row needs at least an email and full name.')
            } else {
                setParsedUsers(users)
                toast.success(`Parsed ${users.length} user(s) from CSV`)
            }
        } catch (error) {
            setParseError('Failed to parse CSV file. Please check the format and try again.')
            console.error(error)
        } finally {
            setIsParsing(false)
        }
    }

    const handleBulkUpload = async () => {
        if (parsedUsers.length === 0) {
            toast.error('No users to upload')
            return
        }

        setIsUploading(true)

        try {
            // Convert TWG names to IDs
            const usersWithTwgIds = parsedUsers.map(user => {
                let twgIds: string[] = []
                if (user['twg names (comma-separated)'] || user['twg_ids'] || user['twgs']) {
                    const twgNames = (user['twg names (comma-separated)'] || user['twg_ids'] || user['twgs'] || '')
                        .toString()
                        .split(',')
                        .map((t: string) => t.trim().toLowerCase())
                        .filter((t: string) => t)

                    twgIds = twgs
                        .filter(twg => twgNames.some((name: string) => twg.name.toLowerCase().includes(name) || twg.pillar?.toLowerCase().includes(name)))
                        .map(twg => twg.id)
                }

                return {
                    email: user.email,
                    full_name: user['full name'] || user.full_name,
                    role: (user.role || 'TWG_MEMBER').toUpperCase().replace(' ', '_'),
                    organization: user.organization || undefined,
                    twg_ids: twgIds.length > 0 ? twgIds : undefined
                }
            })

            const response = await api.post('/users/bulk-invite', {
                users: usersWithTwgIds,
                send_emails: true
            })

            setBulkUploadResults(response.data)
            toast.success(`Created ${response.data.success_count} user(s), ${response.data.failure_count} failed`)
            loadUsers()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to upload users'
            toast.error(message)
        } finally {
            setIsUploading(false)
        }
    }

    const resetBulkUpload = () => {
        setCsvFile(null)
        setParsedUsers([])
        setParseError(null)
        setBulkUploadResults(null)
        setIsBulkUploadModalOpen(false)
    }

    const filteredUsers = users.filter(user =>
        user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase())
    )

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-4 border-[#1152d4] border-t-transparent rounded-full animate-spin"></div>
            </div>
        )
    }

    return (
        <>
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div>
                    <h1 className="text-3xl font-black text-[#0d121b] dark:text-white tracking-tight">Team Management</h1>
                    <p className="text-[#4c669a] dark:text-[#a0aec0] font-medium">Manage user roles, access permissions, and account status.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={loadUsers}
                        className="px-4 py-2 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-sm font-bold text-[#0d121b] dark:text-white hover:bg-gray-50 dark:hover:bg-[#2d3748] transition-colors shadow-sm flex items-center gap-2"
                    >
                        <span className="material-symbols-outlined text-sm">refresh</span>
                        Refresh
                    </button>
                    <button
                        onClick={() => {
                            if (twgs.length === 0) loadTwgs();
                            setIsBulkUploadModalOpen(true);
                        }}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-bold transition-all shadow-md shadow-emerald-500/20 flex items-center gap-2"
                    >
                        <span className="material-symbols-outlined text-sm">upload</span>
                        Bulk Upload
                    </button>
                    <button
                        onClick={() => {
                            if (twgs.length === 0) loadTwgs();
                            setIsInviteModalOpen(true);
                        }}
                        className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white rounded-lg text-sm font-bold transition-all shadow-md shadow-blue-500/20 flex items-center gap-2"
                    >
                        <span className="material-symbols-outlined text-sm">mail</span>
                        Invite User
                    </button>
                </div>
            </div>



            {/* Tabs */}
            <div className="flex gap-6 border-b border-[#e7ebf3] dark:border-[#2d3748] mb-6">
                <button
                    onClick={() => setActiveTab('users')}
                    className={`pb-3 text-sm font-bold border-b-2 transition-colors ${activeTab === 'users'
                        ? 'border-[#1152d4] text-[#1152d4] dark:text-blue-400 dark:border-blue-400'
                        : 'border-transparent text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white'
                        }`}
                >
                    Users & Roles
                </button>
                <button
                    onClick={() => setActiveTab('governance')}
                    className={`pb-3 text-sm font-bold border-b-2 transition-colors ${activeTab === 'governance'
                        ? 'border-[#1152d4] text-[#1152d4] dark:text-blue-400 dark:border-blue-400'
                        : 'border-transparent text-[#4c669a] dark:text-[#a0aec0] hover:text-[#0d121b] dark:hover:text-white'
                        }`}
                >
                    TWG Governance
                </button>
            </div>

            {
                activeTab === 'users' ? (
                    <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden mb-6">
                        <div className="p-4 border-b border-[#e7ebf3] dark:border-[#2d3748] bg-gray-50/50 dark:bg-gray-800/10">
                            <div className="relative max-w-md">
                                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#4c669a] text-lg">search</span>
                                <input
                                    type="text"
                                    placeholder="Search members by name or email..."
                                    className="w-full pl-10 pr-4 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1152d4]/20 focus:border-[#1152d4] transition-all"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-gray-50 dark:bg-[#2d3748]/30">
                                        <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">User Member</th>
                                        <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Role</th>
                                        <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">TWG(s)</th>
                                        <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                                    {filteredUsers.map((user) => (
                                        <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-[#2d3748]/30 transition-colors group">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="relative">
                                                        <Avatar alt={user.full_name} size="md" />
                                                        {user.is_active && (
                                                            <div className="absolute -bottom-0.5 -right-0.5 size-3 bg-green-500 border-2 border-white dark:border-[#1a202c] rounded-full"></div>
                                                        )}
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-[#0d121b] dark:text-white text-sm">{user.full_name}</div>
                                                        <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">{user.email}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <select
                                                    className="bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] text-xs font-medium rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#1152d4]/20 text-[#0d121b] dark:text-white"
                                                    value={user.role}
                                                    onChange={(e) => handleRoleChange(user, e.target.value as UserRole)}
                                                >
                                                    {Object.values(UserRole).map((role) => (
                                                        <option key={role} value={role}>
                                                            {role.replace(/_/g, ' ').toUpperCase()}
                                                        </option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-1">
                                                    {user.twgs && user.twgs.length > 0 ? (
                                                        user.twgs.map((twg) => (
                                                            <span
                                                                key={twg.id}
                                                                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#1152d4]/10 text-[#1152d4] dark:bg-[#1152d4]/20 dark:text-[#6b9aff]"
                                                            >
                                                                {twg.name.replace(/ TWG$/i, '')}
                                                            </span>
                                                        ))
                                                    ) : (
                                                        <span className="text-xs text-[#4c669a]/50 dark:text-[#a0aec0]/50 italic">None</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-1">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${user.is_active
                                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                                        : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                                                        }`}>
                                                        {user.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                    {user.invite_sent_at && !user.invite_accepted_at && (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                                                            Invite Pending
                                                        </span>
                                                    )}
                                                    {user.invite_accepted_at && (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                                                            Invite Accepted
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex justify-end gap-2">
                                                    <button
                                                        onClick={() => openEditModal(user)}
                                                        className="p-2 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors"
                                                        title="Edit Details"
                                                    >
                                                        <span className="material-symbols-outlined text-[20px]">edit</span>
                                                    </button>
                                                    <button
                                                        onClick={() => handleUpdateUser(user.id, { is_active: !user.is_active })}
                                                        disabled={user.id === currentUser?.id}
                                                        className={`p-2 rounded-lg transition-colors ${user.is_active
                                                            ? 'text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                                                            : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                                                            } ${user.id === currentUser?.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                        title={user.id === currentUser?.id ? 'You cannot deactivate yourself' : (user.is_active ? 'Deactivate' : 'Activate')}
                                                    >
                                                        <span className="material-symbols-outlined text-[20px]">
                                                            {user.is_active ? 'person_off' : 'person_check'}
                                                        </span>
                                                    </button>
                                                    <button
                                                        onClick={() => openTeamModal(user)}
                                                        className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                                                        title="Manage Teams"
                                                    >
                                                        <span className="material-symbols-outlined text-[20px]">groups</span>
                                                    </button>
                                                    <button
                                                        onClick={() => handleResendInvite(user)}
                                                        disabled={resendingUserId === user.id}
                                                        className="p-2 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors disabled:opacity-50"
                                                        title="Resend Invite"
                                                    >
                                                        {resendingUserId === user.id ? (
                                                            <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                                                        ) : (
                                                            <span className="material-symbols-outlined text-[20px]">forward_to_inbox</span>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteUser(user.id)}
                                                        disabled={user.id === currentUser?.id}
                                                        className={`p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors ${user.id === currentUser?.id ? 'opacity-50 cursor-not-allowed' : ''
                                                            }`}
                                                        title={user.id === currentUser?.id ? 'You cannot delete yourself' : 'Delete User'}
                                                    >
                                                        <span className="material-symbols-outlined text-[20px]">delete</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {filteredUsers.length === 0 && (
                            <div className="p-12 text-center">
                                <div className="size-16 bg-gray-100 dark:bg-[#2d3748] rounded-full flex items-center justify-center mx-auto mb-4 text-[#4c669a]">
                                    <span className="material-symbols-outlined text-3xl">group_off</span>
                                </div>
                                <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">No members found</h3>
                                <p className="text-[#4c669a] dark:text-[#a0aec0]">Try adjusting your search criteria or add a new member.</p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="space-y-6">
                        {loadingTwgs && (
                            <div className="flex justify-center p-12">
                                <div className="w-8 h-8 border-4 border-[#1152d4] border-t-transparent rounded-full animate-spin"></div>
                            </div>
                        )}
                        {!loadingTwgs && twgs.map((twg) => (
                            <div key={twg.id} className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-6 shadow-sm">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">{twg.name}</h3>
                                        <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider font-bold mt-1">
                                            Pillar: {twg.pillar?.replace(/_/g, ' ')}
                                        </p>
                                    </div>
                                    <div className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full text-xs font-bold uppercase">
                                        {twg.status}
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Political Lead */}
                                    <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-800/30">
                                        <h4 className="text-xs font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest mb-3">Political Lead</h4>
                                        <select
                                            className="w-full bg-white dark:bg-[#2d3748] border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-blue-500 text-[#0d121b] dark:text-white"
                                            value={twg.political_lead_id || ''}
                                            onChange={(e) => handleUpdateTwg(twg.id, { political_lead_id: e.target.value || null })}
                                        >
                                            <option value="">Unassigned</option>
                                            {users.map(u => (
                                                <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Technical Lead */}
                                    <div className="p-4 bg-emerald-50 dark:bg-emerald-900/10 rounded-xl border border-emerald-100 dark:border-emerald-800/30">
                                        <h4 className="text-xs font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest mb-3">Technical Lead</h4>
                                        <select
                                            className="w-full bg-white dark:bg-[#2d3748] border border-emerald-200 dark:border-emerald-800 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-emerald-500 text-[#0d121b] dark:text-white"
                                            value={twg.technical_lead_id || ''}
                                            onChange={(e) => handleUpdateTwg(twg.id, { technical_lead_id: e.target.value || null })}
                                        >
                                            <option value="">Unassigned</option>
                                            {users.map(u => (
                                                <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {twgs.length === 0 && (
                            <div className="p-12 text-center text-slate-400">
                                No TWGs found. System seed required?
                            </div>
                        )}
                    </div>
                )
            }

            {/* Manage Teams Modal */}
            {isTeamModalOpen && editingUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-md border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden">
                        <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                            <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">Manage Teams</h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Assign TWGs for {editingUser.full_name}</p>
                        </div>

                        <div className="p-6 max-h-[60vh] overflow-y-auto space-y-3">
                            {loadingTwgs ? (
                                <div className="flex justify-center py-8">
                                    <div className="w-6 h-6 border-2 border-[#1152d4] border-t-transparent rounded-full animate-spin"></div>
                                </div>
                            ) : (
                                twgs.map(twg => (
                                    <label key={twg.id} className="flex items-center gap-3 p-3 rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] hover:bg-gray-50 dark:hover:bg-[#2d3748]/50 cursor-pointer transition-colors">
                                        <input
                                            type="checkbox"
                                            checked={selectedTwgs.includes(twg.id)}
                                            onChange={() => toggleTwgSelection(twg.id)}
                                            className="w-5 h-5 rounded border-gray-300 text-[#1152d4] focus:ring-[#1152d4]"
                                        />
                                        <div>
                                            <div className="font-bold text-[#0d121b] dark:text-white text-sm">{twg.name}</div>
                                            <div className="text-xs text-[#4c669a] dark:text-[#a0aec0] uppercase">{twg.pillar?.replace(/_/g, ' ')}</div>
                                        </div>
                                    </label>
                                ))
                            )}
                        </div>

                        <div className="p-6 bg-gray-50 dark:bg-[#2d3748]/30 flex justify-end gap-3">
                            <button
                                onClick={handleCancelTeamModal}
                                className="px-4 py-2 text-sm font-bold text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white transition-colors"
                            >
                                {enforceTwgSelection ? 'Cancel (Revert to Member)' : 'Cancel'}
                            </button>
                            <button
                                onClick={handleSaveTeams}
                                disabled={(enforceTwgSelection && selectedTwgs.length === 0) || isSavingTeams}
                                className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white text-sm font-bold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isSavingTeams && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                                {enforceTwgSelection && selectedTwgs.length === 0 ? 'Select at least 1 TWG' : 'Save Changes'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Invite User Modal */}
            {isInviteModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-lg border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden">
                        <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                            <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">Invite New User</h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Create account and assign access</p>
                        </div>

                        {tempPassword ? (
                            <div className="p-6 space-y-4">
                                <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
                                    <p className="text-sm font-bold text-green-800 dark:text-green-400 mb-2">✓ User Created Successfully!</p>
                                    <p className="text-xs text-green-700 dark:text-green-500 mb-3">Share this temporary password with the user. They must change it on first login.</p>
                                    <div className="bg-white dark:bg-[#2d3748] p-3 rounded-lg font-mono text-sm break-all">
                                        {tempPassword}
                                    </div>
                                </div>
                                <button
                                    onClick={resetInviteForm}
                                    className="w-full px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white text-sm font-bold rounded-lg"
                                >
                                    Done
                                </button>
                            </div>
                        ) : (
                            <>
                                <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                                    <div>
                                        <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Email *</label>
                                        <input
                                            type="email"
                                            value={inviteForm.email}
                                            onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                                            className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                            placeholder="user@example.com"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Full Name *</label>
                                        <input
                                            type="text"
                                            value={inviteForm.full_name}
                                            onChange={(e) => setInviteForm({ ...inviteForm, full_name: e.target.value })}
                                            className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                            placeholder="John Doe"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Role *</label>
                                        <select
                                            value={inviteForm.role}
                                            onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value as UserRole })}
                                            className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                        >
                                            {Object.values(UserRole).map(role => (
                                                <option key={role} value={role}>{role.replace(/_/g, ' ').toUpperCase()}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Organization</label>
                                        <input
                                            type="text"
                                            value={inviteForm.organization}
                                            onChange={(e) => setInviteForm({ ...inviteForm, organization: e.target.value })}
                                            className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                            placeholder="Optional"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Assign to TWGs</label>
                                        <div className="space-y-2 max-h-40 overflow-y-auto">
                                            {twgs.map(twg => (
                                                <label key={twg.id} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-[#2d3748]/50 cursor-pointer">
                                                    <input
                                                        type="checkbox"
                                                        checked={inviteForm.twg_ids.includes(twg.id)}
                                                        onChange={(e) => {
                                                            setInviteForm({
                                                                ...inviteForm,
                                                                twg_ids: e.target.checked
                                                                    ? [...inviteForm.twg_ids, twg.id]
                                                                    : inviteForm.twg_ids.filter(id => id !== twg.id)
                                                            })
                                                        }}
                                                        className="w-4 h-4 rounded border-gray-300 text-[#1152d4]"
                                                    />
                                                    <span className="text-sm text-[#0d121b] dark:text-white">{twg.name}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="p-6 bg-gray-50 dark:bg-[#2d3748]/30 flex justify-end gap-3">
                                    <button
                                        onClick={resetInviteForm}
                                        className="px-4 py-2 text-sm font-bold text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleInviteUser}
                                        disabled={!inviteForm.email || !inviteForm.full_name || isInviting}
                                        className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white text-sm font-bold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                    >
                                        {isInviting && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                                        Create & Invite
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Edit User Details Modal */}
            {isEditModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-md border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden">
                        <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                            <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">Edit User Details</h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Update user information</p>
                        </div>

                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Full Name *</label>
                                <input
                                    type="text"
                                    value={editForm.full_name}
                                    onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                    placeholder="John Doe"
                                    disabled={isSavingEdit}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Email *</label>
                                <input
                                    type="email"
                                    value={editForm.email}
                                    onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                    placeholder="user@example.com"
                                    disabled={isSavingEdit}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">Organization</label>
                                <input
                                    type="text"
                                    value={editForm.organization}
                                    onChange={(e) => setEditForm({ ...editForm, organization: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                    placeholder="Organization name"
                                    disabled={isSavingEdit}
                                />
                            </div>
                        </div>

                        <div className="p-6 bg-gray-50 dark:bg-[#2d3748]/30 flex justify-end gap-3">
                            <button
                                onClick={closeEditModal}
                                disabled={isSavingEdit}
                                className="px-4 py-2 text-sm font-bold text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white transition-colors disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveEdit}
                                disabled={!editForm.full_name.trim() || !editForm.email.trim() || isSavingEdit}
                                className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white text-sm font-bold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isSavingEdit && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bulk Upload Modal */}
            {isBulkUploadModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-2xl border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden">
                        <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                            <h3 className="text-xl font-bold text-[#0d121b] dark:text-white flex items-center gap-2">
                                <span className="material-symbols-outlined text-emerald-600">upload</span>
                                Bulk Upload Users
                            </h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Import multiple users from a CSV file</p>
                        </div>

                        <div className="p-6 max-h-[60vh] overflow-y-auto">
                            {!bulkUploadResults ? (
                                <>
                                    {/* Step 1: Download Template */}
                                    <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
                                        <h4 className="font-bold text-blue-800 dark:text-blue-400 mb-2">Step 1: Download Template</h4>
                                        <p className="text-sm text-blue-700 dark:text-blue-500 mb-3">Download the CSV template and fill in user details.</p>
                                        <button
                                            onClick={downloadTemplate}
                                            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold rounded-lg flex items-center gap-2"
                                        >
                                            <span className="material-symbols-outlined text-sm">download</span>
                                            Download Template
                                        </button>
                                    </div>

                                    {/* Step 2: Upload CSV */}
                                    <div className="mb-6">
                                        <h4 className="font-bold text-[#0d121b] dark:text-white mb-2">Step 2: Upload CSV File</h4>
                                        <div className="border-2 border-dashed border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-6 text-center hover:border-emerald-500 transition-colors">
                                            <input
                                                type="file"
                                                accept=".csv"
                                                onChange={handleFileSelect}
                                                disabled={isParsing}
                                                className="hidden"
                                                id="csv-upload"
                                            />
                                            <label
                                                htmlFor="csv-upload"
                                                className="cursor-pointer flex flex-col items-center"
                                            >
                                                <span className="material-symbols-outlined text-4xl text-[#4c669a] dark:text-[#a0aec0] mb-2">cloud_upload</span>
                                                <p className="text-sm font-bold text-[#0d121b] dark:text-white">
                                                    {isParsing ? 'Parsing...' : csvFile ? csvFile.name : 'Click to upload CSV file'}
                                                </p>
                                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">CSV files only</p>
                                            </label>
                                        </div>
                                    </div>

                                    {/* Parse Error Banner */}
                                    {parseError && parsedUsers.length === 0 && (
                                        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
                                            <div className="flex items-center gap-2">
                                                <span className="material-symbols-outlined text-red-600 dark:text-red-400 text-lg">error</span>
                                                <p className="text-sm font-medium text-red-700 dark:text-red-400">{parseError}</p>
                                            </div>
                                            <p className="text-xs text-red-600 dark:text-red-500 mt-1 ml-7">
                                                Required columns: <strong>email</strong>, <strong>full name</strong> (or full_name). Optional: role, organization, twg names.
                                            </p>
                                        </div>
                                    )}

                                    {/* Step 3: Preview */}
                                    {parsedUsers.length > 0 && (
                                        <div>
                                            <h4 className="font-bold text-[#0d121b] dark:text-white mb-2">Step 3: Preview ({parsedUsers.length} users)</h4>
                                            <div className="border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl overflow-hidden max-h-48 overflow-y-auto">
                                                <table className="w-full text-sm text-left">
                                                    <thead className="bg-gray-50 dark:bg-[#2d3748]/30">
                                                        <tr>
                                                            <th className="px-3 py-2 font-bold text-xs">Name</th>
                                                            <th className="px-3 py-2 font-bold text-xs">Email</th>
                                                            <th className="px-3 py-2 font-bold text-xs">Role</th>
                                                            <th className="px-3 py-2 font-bold text-xs">TWGs</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                                                        {parsedUsers.map((user, idx) => (
                                                            <tr key={idx}>
                                                                <td className="px-3 py-2">{user['full name'] || user.full_name}</td>
                                                                <td className="px-3 py-2 text-[#4c669a]">{user.email}</td>
                                                                <td className="px-3 py-2">
                                                                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs">
                                                                        {(user.role || 'TWG_MEMBER').replace('_', ' ')}
                                                                    </span>
                                                                </td>
                                                                <td className="px-3 py-2 text-xs text-[#4c669a]">
                                                                    {user['twg names (comma-separated)'] || '-'}
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                /* Results */
                                <div>
                                    <h4 className="font-bold text-[#0d121b] dark:text-white mb-4">Upload Complete</h4>
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-200 dark:border-green-800">
                                            <p className="text-2xl font-bold text-green-600 dark:text-green-400">{bulkUploadResults.successful.length}</p>
                                            <p className="text-sm text-green-700 dark:text-green-500">Successful</p>
                                        </div>
                                        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
                                            <p className="text-2xl font-bold text-red-600 dark:text-red-400">{bulkUploadResults.failed.length}</p>
                                            <p className="text-sm text-red-700 dark:text-red-500">Failed</p>
                                        </div>
                                    </div>

                                            {/* Show temporary passwords for successful users */}
                                    {bulkUploadResults.successful.length > 0 && (
                                        <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800">
                                            <h5 className="font-bold text-amber-800 dark:text-amber-400 mb-2 flex items-center gap-2">
                                                <span className="material-symbols-outlined text-sm">warning</span>
                                                Important: Save Temporary Passwords
                                            </h5>
                                            <p className="text-xs text-amber-700 dark:text-amber-500 mb-3">
                                                These passwords are shown only once. Copy them now or share with users.
                                            </p>
                                            <div className="max-h-32 overflow-y-auto space-y-1">
                                                {bulkUploadResults.successful.map((user: any) => (
                                                    <div key={user.user_id} className="text-xs bg-white dark:bg-[#2d3748] p-2 rounded font-mono">
                                                        {user.email}: {user.temporary_password}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Show failed users */}
                                    {bulkUploadResults.failed.length > 0 && (
                                        <div className="mb-4">
                                            <h5 className="font-bold text-red-600 dark:text-red-400 mb-2">Failed Users</h5>
                                            <div className="max-h-32 overflow-y-auto space-y-1">
                                                {bulkUploadResults.failed.map((user: any, idx: number) => (
                                                    <div key={idx} className="text-xs bg-red-50 dark:bg-red-900/10 p-2 rounded">
                                                        {user.email}: {user.error}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="p-6 bg-gray-50 dark:bg-[#2d3748]/30 flex justify-end gap-3">
                            <button
                                onClick={resetBulkUpload}
                                disabled={isUploading}
                                className="px-4 py-2 text-sm font-bold text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white transition-colors disabled:opacity-50"
                            >
                                {bulkUploadResults ? 'Close' : 'Cancel'}
                            </button>
                            {!bulkUploadResults && parsedUsers.length > 0 && (
                                <button
                                    onClick={handleBulkUpload}
                                    disabled={isUploading}
                                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {isUploading && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                                    Upload {parsedUsers.length} User{parsedUsers.length !== 1 ? 's' : ''}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
