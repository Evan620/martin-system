import { useState, useEffect } from 'react'
import { userService, UserUpdateData } from '../../services/userService'
import { twgs as twgService } from '../../services/api'
import api from '../../services/api'
import { User, UserRole } from '../../types/auth'
import { toast } from 'react-toastify'


import { useAppSelector } from '../../hooks/useRedux'

export default function TeamManagement() {
    const currentUser = useAppSelector((state) => state.auth.user)
    const [users, setUsers] = useState<User[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [activeTab, setActiveTab] = useState<'users' | 'governance'>('users')
    const [hoveredRow, setHoveredRow] = useState<string | null>(null)
    const [currentPage, setCurrentPage] = useState(1)

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
            const data = await userService.getUsers({ limit: 1000 })
            setUsers(data)
        } catch (error) {
            console.error('Failed to load users', error)
            toast.error('Failed to load users')
        } finally {
            setIsLoading(false)
        }
    }

    const handleExportAllMembers = async () => {
        try {
            const response = await twgService.exportAllMembers()
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const a = document.createElement('a')
            a.href = url
            const today = new Date().toISOString().slice(0, 10)
            a.download = `all_twg_members_${today}.csv`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            window.URL.revokeObjectURL(url)
        } catch {
            toast.error('Failed to export TWG members')
        }
    }

    const loadTwgs = async () => {
        setLoadingTwgs(true)
        try {
            // Governance binds to twg.political_lead_id / technical_lead_id and needs
            // each TWG's members, none of which the lightweight /dropdown payload returns.
            const response = await twgService.list(0, 1000)
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

                    const parsedUsersList = lines.slice(1).map(line => {
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

                    resolve(parsedUsersList)
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
            const parsedList = await parseCSV(file)
            if (parsedList.length === 0) {
                setParseError('No valid users found. Each row needs at least an email and full name.')
            } else {
                setParsedUsers(parsedList)
                toast.success(`Parsed ${parsedList.length} user(s) from CSV`)
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
                        .filter(twg => twgNames.some((name: string) => {
                            const twgLower = twg.name.toLowerCase()
                            const pillarLower = twg.pillar?.toLowerCase() || ''
                            const nameWords = name.replace(/\btwg\b/gi, '').trim().split(/\s+/).filter(Boolean)
                            return twgLower.includes(name) || name.includes(twgLower) ||
                                   pillarLower.includes(name) || name.includes(pillarLower) ||
                                   nameWords.some(w => twgLower.startsWith(w) || pillarLower.startsWith(w))
                        }))
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

    // Pagination — show at most 20 members per page
    const PAGE_SIZE = 20
    const totalPages = Math.max(1, Math.ceil(filteredUsers.length / PAGE_SIZE))
    const safePage = Math.min(currentPage, totalPages)
    const pagedUsers = filteredUsers.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

    // Compute role counts
    const activeUsers = users.filter(u => u.is_active)
    const secretariatLeads = activeUsers.filter(u => u.role === UserRole.SECRETARIAT_LEAD || u.role === UserRole.ADMIN).length
    const facilitators = activeUsers.filter(u => u.role === UserRole.FACILITATOR).length
    const members = activeUsers.filter(u => u.role === UserRole.MEMBER).length
    const observers = activeUsers.filter(u => (u.role as string) === 'OBSERVER').length

    // Valid lead candidates for a TWG: active governance roles plus that TWG's own members,
    // plus whoever is already assigned (so the saved value always renders).
    const leadCandidates = (twg: any): User[] => {
        const memberIds = new Set((twg?.members || []).map((m: any) => String(m.id)))
        const assignedIds = new Set([twg?.political_lead_id, twg?.technical_lead_id].filter(Boolean).map((id: any) => String(id)))
        return users.filter(u =>
            u.is_active && (
                u.role === UserRole.ADMIN ||
                u.role === UserRole.SECRETARIAT_LEAD ||
                u.role === UserRole.FACILITATOR ||
                memberIds.has(String(u.id)) ||
                assignedIds.has(String(u.id))
            )
        )
    }

    const getInitials = (name: string) => name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

    if (isLoading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 256 }}>
                <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
            </div>
        )
    }

    const inputStyle: React.CSSProperties = {
        width: '100%', padding: '8px 12px', background: 'var(--surface)',
        border: '1px solid var(--border)', fontSize: 13, color: 'var(--ink-700)',
        fontFamily: 'inherit', boxSizing: 'border-box', outline: 'none'
    }
    const labelStyle: React.CSSProperties = {
        display: 'block', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase',
        color: 'var(--ink-500)', fontWeight: 500, marginBottom: 6
    }

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            {/* Page header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)', marginBottom: 6 }}>
                    Management · roster
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <h1 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        Team
                    </h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={loadUsers} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>refresh</span>
                            Refresh
                        </button>
                        <button onClick={handleExportAllMembers} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>download</span>
                            Export
                        </button>
                        <button onClick={async () => { if (twgs.length === 0) await loadTwgs(); setIsBulkUploadModalOpen(true); }} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>upload</span>
                            Bulk Upload
                        </button>
                        <button onClick={() => { if (twgs.length === 0) loadTwgs(); setIsInviteModalOpen(true); }} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>mail</span>
                            Invite User
                        </button>
                    </div>
                </div>
            </div>

            {/* LedgerStat strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', background: 'var(--surface)', border: '1px solid var(--border)', padding: '22px 32px', marginBottom: 24 }}>
                {[
                    { label: 'Secretariat Leads', value: secretariatLeads },
                    { label: 'Facilitators', value: facilitators },
                    { label: 'Members', value: members },
                    { label: 'Observers', value: observers },
                ].map((stat, i, arr) => (
                    <div key={stat.label} style={{ paddingRight: 24, borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none', paddingLeft: i > 0 ? 24 : 0 }}>
                        <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{stat.label}</div>
                        <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 28, color: 'var(--ink-900)', letterSpacing: '-0.02em', marginTop: 4, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{stat.value}</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6 }}>active users</div>
                    </div>
                ))}
            </div>

            {/* Tab switcher */}
            <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
                {[{ id: 'users', label: 'Users & Roles' }, { id: 'governance', label: 'TWG Governance' }].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as 'users' | 'governance')}
                        style={{
                            background: 'transparent', border: 'none',
                            borderBottom: activeTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
                            color: activeTab === tab.id ? 'var(--accent)' : 'var(--ink-500)',
                            padding: '10px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                            fontFamily: 'inherit', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: -1
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {activeTab === 'users' ? (
                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    {/* Search bar */}
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'var(--ink-50)' }}>
                        <div style={{ position: 'relative', maxWidth: 400 }}>
                            <span className="material-symbols-outlined" style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: 'var(--ink-400)' }}>search</span>
                            <input
                                type="text"
                                placeholder="Search by name or email..."
                                value={searchTerm}
                                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1) }}
                                style={{ ...inputStyle, paddingLeft: 34, maxWidth: 400 }}
                            />
                        </div>
                    </div>

                    {/* Table */}
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', textAlign: 'left', fontSize: 13, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ background: 'var(--ink-50)', borderBottom: '1px solid var(--border)' }}>
                                    {['Member', 'Role', 'TWG(s)', 'Organisation', 'Status', 'Actions'].map(col => (
                                        <th key={col} style={{ padding: '10px 16px', fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{col}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {pagedUsers.map((user, idx) => (
                                    <tr
                                        key={user.id}
                                        onMouseEnter={() => setHoveredRow(user.id)}
                                        onMouseLeave={() => setHoveredRow(null)}
                                        style={{
                                            borderBottom: idx < pagedUsers.length - 1 ? '1px solid var(--border)' : 'none',
                                            background: hoveredRow === user.id ? 'var(--ink-50)' : 'transparent'
                                        }}
                                    >
                                        {/* Member */}
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                <div style={{ position: 'relative', flexShrink: 0 }}>
                                                    <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--accent-soft)', color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600 }}>
                                                        {getInitials(user.full_name)}
                                                    </div>
                                                    {user.is_active && (
                                                        <div style={{ position: 'absolute', bottom: -1, right: -1, width: 9, height: 9, borderRadius: '50%', background: 'var(--sage)', border: '2px solid var(--surface)' }}></div>
                                                    )}
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 500, color: 'var(--ink-900)', fontSize: 13 }}>{user.full_name}</div>
                                                    <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{user.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        {/* Role */}
                                        <td style={{ padding: '12px 16px' }}>
                                            <select
                                                style={{ background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 11, fontWeight: 500, padding: '4px 8px', cursor: 'pointer', fontFamily: 'inherit', color: 'var(--ink-700)', outline: 'none' }}
                                                value={user.role}
                                                onChange={(e) => handleRoleChange(user, e.target.value as UserRole)}
                                            >
                                                {Object.values(UserRole).map((role) => (
                                                    <option key={role} value={role}>{role.replace(/_/g, ' ')}</option>
                                                ))}
                                            </select>
                                        </td>
                                        {/* TWGs */}
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                                {user.twgs && user.twgs.length > 0 ? user.twgs.map((twg) => (
                                                    <span key={twg.id} style={{ fontSize: 10, background: 'var(--accent-soft)', color: 'var(--accent)', padding: '2px 8px', fontWeight: 500 }}>
                                                        {twg.name.replace(/ TWG$/i, '')}
                                                    </span>
                                                )) : (
                                                    <span style={{ fontSize: 11, color: 'var(--ink-400)', fontStyle: 'italic' }}>None</span>
                                                )}
                                            </div>
                                        </td>
                                        {/* Organisation */}
                                        <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--ink-600)' }}>
                                            {user.organization || '—'}
                                        </td>
                                        {/* Status */}
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
                                                    <div style={{ width: 7, height: 7, borderRadius: '50%', background: user.is_active ? 'var(--sage)' : 'var(--amber)', flexShrink: 0 }}></div>
                                                    <span style={{ color: 'var(--ink-700)' }}>{user.is_active ? 'Active' : 'Inactive'}</span>
                                                </span>
                                                {user.invite_sent_at && !user.invite_accepted_at && (
                                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
                                                        <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--amber)', flexShrink: 0 }}></div>
                                                        <span style={{ color: 'var(--ink-500)' }}>Invite pending</span>
                                                    </span>
                                                )}
                                                {user.invite_accepted_at && (
                                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
                                                        <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--sage)', flexShrink: 0 }}></div>
                                                        <span style={{ color: 'var(--ink-500)' }}>Accepted</span>
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        {/* Actions */}
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', gap: 2 }}>
                                                <button onClick={() => openEditModal(user)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)', padding: 5 }} title="Edit">
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>edit</span>
                                                </button>
                                                <button onClick={() => handleUpdateUser(user.id, { is_active: !user.is_active })} disabled={user.id === currentUser?.id} style={{ background: 'none', border: 'none', cursor: 'pointer', color: user.is_active ? 'var(--amber)' : 'var(--sage)', padding: 5, opacity: user.id === currentUser?.id ? 0.4 : 1 }} title={user.is_active ? 'Deactivate' : 'Activate'}>
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{user.is_active ? 'person_off' : 'person_check'}</span>
                                                </button>
                                                <button onClick={() => openTeamModal(user)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)', padding: 5 }} title="Manage Teams">
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>groups</span>
                                                </button>
                                                <button onClick={() => handleResendInvite(user)} disabled={resendingUserId === user.id} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)', padding: 5, opacity: resendingUserId === user.id ? 0.5 : 1 }} title="Resend Invite">
                                                    {resendingUserId === user.id ? (
                                                        <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                                                    ) : (
                                                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>forward_to_inbox</span>
                                                    )}
                                                </button>
                                                <button onClick={() => handleDeleteUser(user.id)} disabled={user.id === currentUser?.id} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--terra)', padding: 5, opacity: user.id === currentUser?.id ? 0.4 : 1 }} title="Delete">
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>delete</span>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {filteredUsers.length > PAGE_SIZE && (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', borderTop: '1px solid var(--border)', background: 'var(--ink-50)' }}>
                            <span style={{ fontSize: 11, color: 'var(--ink-500)' }}>
                                Showing {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filteredUsers.length)} of {filteredUsers.length}
                            </span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={safePage === 1} style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '4px 12px', fontSize: 12, cursor: safePage === 1 ? 'default' : 'pointer', fontFamily: 'inherit', opacity: safePage === 1 ? 0.4 : 1 }}>Previous</button>
                                <span style={{ fontSize: 12, color: 'var(--ink-600)' }}>Page {safePage} of {totalPages}</span>
                                <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={safePage === totalPages} style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '4px 12px', fontSize: 12, cursor: safePage === totalPages ? 'default' : 'pointer', fontFamily: 'inherit', opacity: safePage === totalPages ? 0.4 : 1 }}>Next</button>
                            </div>
                        </div>
                    )}

                    {filteredUsers.length === 0 && (
                        <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--ink-400)' }}>
                            <p style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>No members found</p>
                            <p style={{ fontSize: 13, marginTop: 4 }}>Try adjusting your search criteria.</p>
                        </div>
                    )}
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {loadingTwgs && (
                        <div style={{ display: 'flex', justifyContent: 'center', padding: '48px 0' }}>
                            <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                        </div>
                    )}
                    {!loadingTwgs && twgs.map((twg) => (
                        <div key={twg.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 24 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                                <div>
                                    <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 18, color: 'var(--ink-900)', margin: '0 0 4px' }}>{twg.name}</h3>
                                    <p style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
                                        {twg.pillar?.replace(/_/g, ' ')}
                                    </p>
                                </div>
                                <span style={{ fontSize: 10, color: 'var(--sage)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'flex', alignItems: 'center', gap: 4 }}>
                                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--sage)' }}></div>
                                    {twg.status}
                                </span>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                <div style={{ padding: 16, background: 'var(--ink-50)', border: '1px solid var(--border)' }}>
                                    <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 8 }}>Political Lead</div>
                                    <select
                                        style={{ width: '100%', background: 'var(--surface)', border: '1px solid var(--border)', padding: '8px 10px', fontSize: 12, fontFamily: 'inherit', color: 'var(--ink-700)', cursor: 'pointer', outline: 'none' }}
                                        value={twg.political_lead_id || ''}
                                        onChange={(e) => handleUpdateTwg(twg.id, { political_lead_id: e.target.value || null })}
                                    >
                                        <option value="">Unassigned</option>
                                        {leadCandidates(twg).map(u => (<option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>))}
                                    </select>
                                </div>
                                <div style={{ padding: 16, background: 'var(--ink-50)', border: '1px solid var(--border)' }}>
                                    <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 8 }}>Technical Lead</div>
                                    <select
                                        style={{ width: '100%', background: 'var(--surface)', border: '1px solid var(--border)', padding: '8px 10px', fontSize: 12, fontFamily: 'inherit', color: 'var(--ink-700)', cursor: 'pointer', outline: 'none' }}
                                        value={twg.technical_lead_id || ''}
                                        onChange={(e) => handleUpdateTwg(twg.id, { technical_lead_id: e.target.value || null })}
                                    >
                                        <option value="">Unassigned</option>
                                        {leadCandidates(twg).map(u => (<option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>))}
                                    </select>
                                </div>
                            </div>
                        </div>
                    ))}
                    {twgs.length === 0 && !loadingTwgs && (
                        <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--ink-400)', fontSize: 13 }}>
                            No TWGs found. System seed required?
                        </div>
                    )}
                </div>
            )}

            {/* Manage Teams Modal */}
            {isTeamModalOpen && editingUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 440, overflow: 'hidden' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: '0 0 4px' }}>Manage Teams</h3>
                            <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: 0 }}>Assign TWGs for {editingUser.full_name}</p>
                        </div>
                        <div style={{ padding: 24, maxHeight: '60vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {loadingTwgs ? (
                                <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 0' }}>
                                    <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                                </div>
                            ) : twgs.map(twg => (
                                <label key={twg.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', border: '1px solid var(--border)', cursor: 'pointer', background: selectedTwgs.includes(twg.id) ? 'var(--accent-soft)' : 'transparent' }}>
                                    <input type="checkbox" checked={selectedTwgs.includes(twg.id)} onChange={() => toggleTwgSelection(twg.id)} style={{ accentColor: 'var(--accent)' }} />
                                    <div>
                                        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-900)' }}>{twg.name}</div>
                                        <div style={{ fontSize: 10, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{twg.pillar?.replace(/_/g, ' ')}</div>
                                    </div>
                                </label>
                            ))}
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                            <button onClick={handleCancelTeamModal} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                                {enforceTwgSelection ? 'Cancel (Revert to Member)' : 'Cancel'}
                            </button>
                            <button onClick={handleSaveTeams} disabled={(enforceTwgSelection && selectedTwgs.length === 0) || isSavingTeams} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6, opacity: (enforceTwgSelection && selectedTwgs.length === 0) || isSavingTeams ? 0.5 : 1 }}>
                                {isSavingTeams && <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#fff', borderTopColor: 'transparent' }}></div>}
                                {enforceTwgSelection && selectedTwgs.length === 0 ? 'Select at least 1 TWG' : 'Save Changes'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Invite User Modal */}
            {isInviteModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 480, overflow: 'hidden' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: '0 0 4px' }}>Invite New User</h3>
                            <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: 0 }}>Create account and assign access</p>
                        </div>

                        {tempPassword ? (
                            <div style={{ padding: 24 }}>
                                <div style={{ background: 'var(--accent-soft)', borderLeft: '2px solid var(--sage)', padding: '12px 16px', marginBottom: 20 }}>
                                    <p style={{ fontSize: 13, color: 'var(--ink-700)', fontWeight: 500, margin: '0 0 8px' }}>User Created Successfully</p>
                                    <p style={{ fontSize: 12, color: 'var(--ink-500)', margin: '0 0 12px' }}>Share this temporary password. User must change it on first login.</p>
                                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '8px 12px', fontFamily: "'Geist Mono', monospace", fontSize: 13, wordBreak: 'break-all' }}>{tempPassword}</div>
                                </div>
                                <button onClick={resetInviteForm} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '8px 16px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', width: '100%' }}>Done</button>
                            </div>
                        ) : (
                            <>
                                <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16, maxHeight: '60vh', overflowY: 'auto' }}>
                                    <div><label style={labelStyle}>Email *</label><input type="email" value={inviteForm.email} onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })} style={inputStyle} placeholder="user@example.com" /></div>
                                    <div><label style={labelStyle}>Full Name *</label><input type="text" value={inviteForm.full_name} onChange={(e) => setInviteForm({ ...inviteForm, full_name: e.target.value })} style={inputStyle} placeholder="John Doe" /></div>
                                    <div><label style={labelStyle}>Role *</label>
                                        <select value={inviteForm.role} onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value as UserRole })} style={{ ...inputStyle, cursor: 'pointer' }}>
                                            {Object.values(UserRole).map(role => (<option key={role} value={role}>{role.replace(/_/g, ' ')}</option>))}
                                        </select>
                                    </div>
                                    <div><label style={labelStyle}>Organization</label><input type="text" value={inviteForm.organization} onChange={(e) => setInviteForm({ ...inviteForm, organization: e.target.value })} style={inputStyle} placeholder="Optional" /></div>
                                    <div>
                                        <label style={labelStyle}>Assign to TWGs</label>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 160, overflowY: 'auto', border: '1px solid var(--border)', padding: 10 }}>
                                            {twgs.map(twg => (
                                                <label key={twg.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'var(--ink-700)' }}>
                                                    <input type="checkbox" checked={inviteForm.twg_ids.includes(twg.id)} onChange={(e) => setInviteForm({ ...inviteForm, twg_ids: e.target.checked ? [...inviteForm.twg_ids, twg.id] : inviteForm.twg_ids.filter(id => id !== twg.id) })} style={{ accentColor: 'var(--accent)' }} />
                                                    {twg.name}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                                    <button onClick={resetInviteForm} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>Cancel</button>
                                    <button onClick={handleInviteUser} disabled={!inviteForm.email || !inviteForm.full_name || isInviting} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6, opacity: !inviteForm.email || !inviteForm.full_name || isInviting ? 0.5 : 1 }}>
                                        {isInviting && <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#fff', borderTopColor: 'transparent' }}></div>}
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
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 420, overflow: 'hidden' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: '0 0 4px' }}>Edit User Details</h3>
                            <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: 0 }}>Update user information</p>
                        </div>
                        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <div><label style={labelStyle}>Full Name *</label><input type="text" value={editForm.full_name} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} style={inputStyle} placeholder="John Doe" disabled={isSavingEdit} /></div>
                            <div><label style={labelStyle}>Email *</label><input type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} style={inputStyle} placeholder="user@example.com" disabled={isSavingEdit} /></div>
                            <div><label style={labelStyle}>Organization</label><input type="text" value={editForm.organization} onChange={(e) => setEditForm({ ...editForm, organization: e.target.value })} style={inputStyle} placeholder="Organization name" disabled={isSavingEdit} /></div>
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                            <button onClick={closeEditModal} disabled={isSavingEdit} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', opacity: isSavingEdit ? 0.5 : 1 }}>Cancel</button>
                            <button onClick={handleSaveEdit} disabled={!editForm.full_name.trim() || !editForm.email.trim() || isSavingEdit} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6, opacity: !editForm.full_name.trim() || !editForm.email.trim() || isSavingEdit ? 0.5 : 1 }}>
                                {isSavingEdit && <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#fff', borderTopColor: 'transparent' }}></div>}
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bulk Upload Modal */}
            {isBulkUploadModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 600, overflow: 'hidden' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: '0 0 4px' }}>Bulk Upload Users</h3>
                            <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: 0 }}>Import multiple users from a CSV file</p>
                        </div>
                        <div style={{ padding: 24, maxHeight: '60vh', overflowY: 'auto' }}>
                            {!bulkUploadResults ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                                    {/* Step 1 */}
                                    <div style={{ background: 'var(--ink-50)', border: '1px solid var(--border)', padding: 16 }}>
                                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Step 1: Download Template</div>
                                        <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: '0 0 12px' }}>Download the CSV template and fill in user details.</p>
                                        <button onClick={downloadTemplate} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '6px 12px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>download</span>
                                            Download Template
                                        </button>
                                    </div>
                                    {/* Step 2 */}
                                    <div>
                                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Step 2: Upload CSV File</div>
                                        <div style={{ border: '1px dashed var(--border)', padding: 32, textAlign: 'center' }}>
                                            <input type="file" accept=".csv" onChange={handleFileSelect} disabled={isParsing} className="hidden" id="csv-upload" />
                                            <label htmlFor="csv-upload" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                                                <span className="material-symbols-outlined" style={{ fontSize: 36, color: 'var(--ink-300)' }}>cloud_upload</span>
                                                <p style={{ fontSize: 13, color: 'var(--ink-700)', margin: 0 }}>{isParsing ? 'Parsing...' : csvFile ? csvFile.name : 'Click to upload CSV'}</p>
                                                <p style={{ fontSize: 11, color: 'var(--ink-400)', margin: 0 }}>CSV files only</p>
                                            </label>
                                        </div>
                                    </div>
                                    {/* Error */}
                                    {parseError && parsedUsers.length === 0 && (
                                        <div style={{ borderLeft: '2px solid var(--terra)', padding: '10px 14px', background: 'var(--ink-50)' }}>
                                            <p style={{ fontSize: 13, color: 'var(--terra)', margin: 0 }}>{parseError}</p>
                                        </div>
                                    )}
                                    {/* Step 3 */}
                                    {parsedUsers.length > 0 && (
                                        <div>
                                            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Step 3: Preview ({parsedUsers.length} users)</div>
                                            <div style={{ border: '1px solid var(--border)', overflow: 'hidden', maxHeight: 192, overflowY: 'auto' }}>
                                                <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', textAlign: 'left' }}>
                                                    <thead>
                                                        <tr style={{ background: 'var(--ink-50)', borderBottom: '1px solid var(--border)' }}>
                                                            {['Name', 'Email', 'Role', 'TWGs'].map(h => <th key={h} style={{ padding: '8px 10px', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{h}</th>)}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {parsedUsers.map((user, idx) => (
                                                            <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                                                                <td style={{ padding: '7px 10px', color: 'var(--ink-800)' }}>{user['full name'] || user.full_name}</td>
                                                                <td style={{ padding: '7px 10px', color: 'var(--ink-500)' }}>{user.email}</td>
                                                                <td style={{ padding: '7px 10px' }}><span style={{ fontSize: 10, background: 'var(--ink-50)', border: '1px solid var(--border)', padding: '2px 6px' }}>{(user.role || 'TWG_MEMBER').replace('_', ' ')}</span></td>
                                                                <td style={{ padding: '7px 10px', color: 'var(--ink-500)' }}>{user['twg names (comma-separated)'] || '-'}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div>
                                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Upload Complete</div>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                                        <div style={{ background: 'var(--ink-50)', border: '1px solid var(--border)', padding: 16 }}>
                                            <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 28, color: 'var(--sage)' }}>{bulkUploadResults.successful.length}</div>
                                            <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 4 }}>Successful</div>
                                        </div>
                                        <div style={{ background: 'var(--ink-50)', border: '1px solid var(--border)', padding: 16 }}>
                                            <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 28, color: 'var(--terra)' }}>{bulkUploadResults.failed.length}</div>
                                            <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 4 }}>Failed</div>
                                        </div>
                                    </div>
                                    {bulkUploadResults.successful.length > 0 && (
                                        <div style={{ borderLeft: '2px solid var(--amber)', padding: '10px 14px', background: 'var(--ink-50)', marginBottom: 12 }}>
                                            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 6 }}>Save Temporary Passwords</div>
                                            <div style={{ maxHeight: 120, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                {bulkUploadResults.successful.map((user: any) => (
                                                    <div key={user.user_id} style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, background: 'var(--surface)', border: '1px solid var(--border)', padding: '4px 8px' }}>
                                                        {user.email}: {user.temporary_password}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {bulkUploadResults.failed.length > 0 && (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--terra)', marginBottom: 6 }}>Failed Users</div>
                                            {bulkUploadResults.failed.map((user: any, idx: number) => (
                                                <div key={idx} style={{ fontSize: 11, background: 'var(--ink-50)', border: '1px solid var(--border)', padding: '4px 8px', color: 'var(--ink-600)' }}>
                                                    {user.email}: {user.error}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                            <button onClick={resetBulkUpload} disabled={isUploading} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', opacity: isUploading ? 0.5 : 1 }}>
                                {bulkUploadResults ? 'Close' : 'Cancel'}
                            </button>
                            {!bulkUploadResults && parsedUsers.length > 0 && (
                                <button onClick={handleBulkUpload} disabled={isUploading} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6, opacity: isUploading ? 0.5 : 1 }}>
                                    {isUploading && <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#fff', borderTopColor: 'transparent' }}></div>}
                                    Upload {parsedUsers.length} User{parsedUsers.length !== 1 ? 's' : ''}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
