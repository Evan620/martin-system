import { useState, useEffect, useRef } from 'react'
import {
    organizationInvitationService,
    OrganizationInvitation,
    OrganizationInvitationStatus,
    OrganizationInvitationCreate
} from '../../services/organizationInvitationService'
import { twgs as twgService } from '../../services/api'
import InvitationChat from '../../components/invitations/InvitationChat'
import { toast } from 'react-toastify'

const STATUS_COLORS: Record<OrganizationInvitationStatus, string> = {
    pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    accepted: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    declined: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    expired: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400'
}

export default function OrganizationInvitations() {
    const [invitations, setInvitations] = useState<OrganizationInvitation[]>([])
    const [twgs, setTwgs] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize] = useState(20)
    const [pages, setPages] = useState(0)

    // Filters
    const [statusFilter, setStatusFilter] = useState<OrganizationInvitationStatus | ''>('')
    const [twgFilter, setTwgFilter] = useState<string>('')

    // Modal state
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [createForm, setCreateForm] = useState<OrganizationInvitationCreate>({
        organization_name: '',
        contact_email: '',
        twg_id: '',
        custom_message: '',
        send_email: true
    })

    // File attachments
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [attachments, setAttachments] = useState<File[]>([])

    // Resend state
    const [resendingId, setResendingId] = useState<string | null>(null)

    // Chat modal state
    const [isChatModalOpen, setIsChatModalOpen] = useState(false)
    const [selectedInvitation, setSelectedInvitation] = useState<OrganizationInvitation | null>(null)

    useEffect(() => {
        loadInvitations()
        loadTwgs()
    }, [page, statusFilter, twgFilter])

    const loadInvitations = async () => {
        setIsLoading(true)
        try {
            const params: any = { page, page_size: pageSize }
            if (statusFilter) params.status = statusFilter
            if (twgFilter) params.twg_id = twgFilter

            const data = await organizationInvitationService.getInvitations(params)
            setInvitations(data.items)
            setTotal(data.total)
            setPages(data.pages)
        } catch (error) {
            console.error('Failed to load invitations', error)
            toast.error('Failed to load invitations')
        } finally {
            setIsLoading(false)
        }
    }

    const loadTwgs = async () => {
        try {
            const response = await twgService.list()
            setTwgs(response.data)
        } catch (error) {
            console.error('Failed to load TWGs', error)
        }
    }

    const handleCreateInvitation = async () => {
        if (!createForm.organization_name || !createForm.contact_email || !createForm.twg_id) {
            toast.error('Please fill in all required fields')
            return
        }

        setIsSubmitting(true)
        try {
            await organizationInvitationService.createInvitation(createForm, attachments)
            toast.success('Invitation sent successfully')
            setIsCreateModalOpen(false)
            resetCreateForm()
            loadInvitations()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to create invitation'
            toast.error(message)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleResendInvitation = async (invitation: OrganizationInvitation) => {
        if (!window.confirm(`Resend invitation to ${invitation.organization_name} (${invitation.contact_email})?`)) return

        setResendingId(invitation.id)
        try {
            const result = await organizationInvitationService.resendInvitation(invitation.id)
            toast.success(result.message)
            loadInvitations()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to resend invitation'
            toast.error(message)
        } finally {
            setResendingId(null)
        }
    }

    const handleDeleteInvitation = async (invitationId: string, orgName: string) => {
        if (!window.confirm(`Delete invitation for ${orgName}? This cannot be undone.`)) return

        try {
            await organizationInvitationService.deleteInvitation(invitationId)
            toast.success('Invitation deleted')
            loadInvitations()
        } catch (error: any) {
            const message = error.response?.data?.detail || 'Failed to delete invitation'
            toast.error(message)
        }
    }

    const resetCreateForm = () => {
        setCreateForm({
            organization_name: '',
            contact_email: '',
            twg_id: '',
            custom_message: '',
            send_email: true
        })
        setAttachments([])
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || [])
        // Limit to 5 files and max 10MB each
        const validFiles = files.filter(file => {
            if (file.size > 10 * 1024 * 1024) {
                toast.error(`${file.name} is too large (max 10MB)`)
                return false
            }
            return true
        })

        if (attachments.length + validFiles.length > 5) {
            toast.error('Maximum 5 attachments allowed')
            return
        }

        setAttachments(prev => [...prev, ...validFiles])
    }

    const removeAttachment = (index: number) => {
        setAttachments(prev => prev.filter((_, i) => i !== index))
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const formatDate = (dateString: string | null) => {
        if (!dateString) return '-'
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        })
    }

    return (
        <>
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div>
                    <h1 className="text-3xl font-black text-[#0d121b] dark:text-white tracking-tight">
                        Organization Invitations
                    </h1>
                    <p className="text-[#4c669a] dark:text-[#a0aec0] font-medium">
                        Invite external organizations to join Technical Working Groups
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={loadInvitations}
                        className="px-4 py-2 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-sm font-bold text-[#0d121b] dark:text-white hover:bg-gray-50 dark:hover:bg-[#2d3748] transition-colors shadow-sm flex items-center gap-2"
                    >
                        <span className="material-symbols-outlined text-sm">refresh</span>
                        Refresh
                    </button>
                    <button
                        onClick={() => {
                            if (twgs.length === 0) loadTwgs()
                            setIsCreateModalOpen(true)
                        }}
                        className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white rounded-lg text-sm font-bold transition-all shadow-md shadow-blue-500/20 flex items-center gap-2"
                    >
                        <span className="material-symbols-outlined text-sm">mail</span>
                        New Invitation
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] p-4 mb-6">
                <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase mb-2">
                            Status
                        </label>
                        <select
                            value={statusFilter}
                            onChange={(e) => {
                                setStatusFilter(e.target.value as OrganizationInvitationStatus | '')
                                setPage(1)
                            }}
                            className="w-full bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-3 py-2 text-sm"
                        >
                            <option value="">All Statuses</option>
                            <option value="pending">Pending</option>
                            <option value="accepted">Accepted</option>
                            <option value="declined">Declined</option>
                            <option value="expired">Expired</option>
                        </select>
                    </div>
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase mb-2">
                            TWG
                        </label>
                        <select
                            value={twgFilter}
                            onChange={(e) => {
                                setTwgFilter(e.target.value)
                                setPage(1)
                            }}
                            className="w-full bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg px-3 py-2 text-sm"
                        >
                            <option value="">All TWGs</option>
                            {twgs.map(twg => (
                                <option key={twg.id} value={twg.id}>{twg.name}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Invitations Table */}
            <div className="bg-white dark:bg-[#1a202c] rounded-xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="w-8 h-8 border-4 border-[#1152d4] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-50 dark:bg-[#2d3748]/30">
                                    <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">
                                        Organization
                                    </th>
                                    <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">
                                        TWG
                                    </th>
                                    <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">
                                        Sent
                                    </th>
                                    <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">
                                        Expires
                                    </th>
                                    <th className="px-6 py-4 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider text-right">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                                {invitations.map((invitation) => (
                                    <tr key={invitation.id} className="hover:bg-gray-50 dark:hover:bg-[#2d3748]/30 transition-colors">
                                        <td className="px-6 py-4">
                                            <div>
                                                <div className="font-bold text-[#0d121b] dark:text-white text-sm">
                                                    {invitation.organization_name}
                                                </div>
                                                <div className="text-xs text-[#4c669a] dark:text-[#a0aec0]">
                                                    {invitation.contact_email}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm text-[#0d121b] dark:text-white">
                                                {invitation.twg_name || 'Unknown'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${STATUS_COLORS[invitation.status]}`}>
                                                {invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                            {formatDate(invitation.sent_at)}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                            {formatDate(invitation.expires_at)}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2 items-center">
                                                {/* Chat button */}
                                                <button
                                                    onClick={() => {
                                                        setSelectedInvitation(invitation)
                                                        setIsChatModalOpen(true)
                                                    }}
                                                    className={`p-2 rounded-lg transition-colors relative ${
                                                        invitation.unread_message_count > 0
                                                            ? 'text-[#1152d4] bg-blue-50 dark:bg-blue-900/20'
                                                            : 'text-[#4c669a] hover:bg-gray-100 dark:hover:bg-[#2d3748]'
                                                    }`}
                                                    title={invitation.has_messages ? 'View Conversation' : 'Start Conversation'}
                                                >
                                                    <span className="material-symbols-outlined text-[20px]">chat</span>
                                                    {invitation.unread_message_count > 0 && (
                                                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                                                            {invitation.unread_message_count > 9 ? '9+' : invitation.unread_message_count}
                                                        </span>
                                                    )}
                                                </button>

                                                {/* Copy Link button */}
                                                <button
                                                    onClick={() => {
                                                        const baseUrl = window.location.origin
                                                        const link = `${baseUrl}/invitations/${invitation.id}/respond`
                                                        navigator.clipboard.writeText(link)
                                                        toast.success('Invitation link copied!')
                                                    }}
                                                    className="p-2 text-[#4c669a] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
                                                    title="Copy Invitation Link"
                                                >
                                                    <span className="material-symbols-outlined text-[20px]">link</span>
                                                </button>

                                                {/* Pending-only actions */}
                                                {invitation.status === 'pending' && (
                                                    <>
                                                        <button
                                                            onClick={() => handleResendInvitation(invitation)}
                                                            disabled={resendingId === invitation.id}
                                                            className="p-2 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors disabled:opacity-50"
                                                            title="Resend Invitation"
                                                        >
                                                            {resendingId === invitation.id ? (
                                                                <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                                                            ) : (
                                                                <span className="material-symbols-outlined text-[20px]">forward_to_inbox</span>
                                                            )}
                                                        </button>
                                                    </>
                                                )}

                                                {/* Delete button for all invitations */}
                                                <button
                                                    onClick={() => handleDeleteInvitation(invitation.id, invitation.organization_name)}
                                                    className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                    title="Delete Invitation"
                                                >
                                                    <span className="material-symbols-outlined text-[20px]">delete</span>
                                                </button>

                                                {/* Response date for non-pending */}
                                                {invitation.status !== 'pending' && invitation.responded_at && (
                                                    <span className="text-xs text-[#4c669a] dark:text-[#a0aec0] ml-2 whitespace-nowrap">
                                                        {formatDate(invitation.responded_at)}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {!isLoading && invitations.length === 0 && (
                    <div className="p-12 text-center">
                        <div className="size-16 bg-gray-100 dark:bg-[#2d3748] rounded-full flex items-center justify-center mx-auto mb-4 text-[#4c669a]">
                            <span className="material-symbols-outlined text-3xl">mail_off</span>
                        </div>
                        <h3 className="text-lg font-bold text-[#0d121b] dark:text-white">No invitations found</h3>
                        <p className="text-[#4c669a] dark:text-[#a0aec0]">
                            {statusFilter || twgFilter
                                ? 'Try adjusting your filters'
                                : 'Click "New Invitation" to invite an organization'
                            }
                        </p>
                    </div>
                )}

                {/* Pagination */}
                {!isLoading && pages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                        <div className="text-sm text-[#4c669a] dark:text-[#a0aec0]">
                            Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total} invitations
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="px-3 py-1 rounded-lg text-sm font-medium bg-gray-100 dark:bg-[#2d3748] text-[#0d121b] dark:text-white disabled:opacity-50"
                            >
                                Previous
                            </button>
                            <button
                                onClick={() => setPage(p => Math.min(pages, p + 1))}
                                disabled={page === pages}
                                className="px-3 py-1 rounded-lg text-sm font-medium bg-gray-100 dark:bg-[#2d3748] text-[#0d121b] dark:text-white disabled:opacity-50"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Create Invitation Modal */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-lg border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden">
                        <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                            <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">New Organization Invitation</h3>
                            <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">Invite an external organization to join a TWG</p>
                        </div>

                        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">
                                    Organization Name *
                                </label>
                                <input
                                    type="text"
                                    value={createForm.organization_name}
                                    onChange={(e) => setCreateForm({ ...createForm, organization_name: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                    placeholder="Acme Corporation"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">
                                    Contact Email *
                                </label>
                                <input
                                    type="email"
                                    value={createForm.contact_email}
                                    onChange={(e) => setCreateForm({ ...createForm, contact_email: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                    placeholder="contact@acme.com"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">
                                    TWG to Join *
                                </label>
                                <select
                                    value={createForm.twg_id}
                                    onChange={(e) => setCreateForm({ ...createForm, twg_id: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm"
                                >
                                    <option value="">Select a TWG</option>
                                    {twgs.map(twg => (
                                        <option key={twg.id} value={twg.id}>{twg.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">
                                    Custom Message
                                </label>
                                <textarea
                                    value={createForm.custom_message || ''}
                                    onChange={(e) => setCreateForm({ ...createForm, custom_message: e.target.value })}
                                    className="w-full px-3 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-lg text-sm min-h-[100px] resize-y"
                                    placeholder="Optional personal message to include in the invitation..."
                                />
                            </div>

                            {/* Attachments */}
                            <div>
                                <label className="block text-sm font-bold text-[#0d121b] dark:text-white mb-2">
                                    Attachments
                                </label>
                                <div
                                    onClick={() => fileInputRef.current?.click()}
                                    className="border-2 border-dashed border-[#e7ebf3] dark:border-[#4a5568] rounded-lg p-4 text-center cursor-pointer hover:border-[#1152d4] dark:hover:border-[#1152d4] transition-colors"
                                >
                                    <span className="material-symbols-outlined text-3xl text-[#4c669a] dark:text-[#a0aec0]">attach_file</span>
                                    <p className="text-sm text-[#4c669a] dark:text-[#a0aec0] mt-1">
                                        Click to attach files (PDF, images, documents)
                                    </p>
                                    <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">
                                        Max 5 files, 10MB each
                                    </p>
                                </div>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                                    onChange={handleFileSelect}
                                    className="hidden"
                                />

                                {/* Selected files */}
                                {attachments.length > 0 && (
                                    <div className="mt-3 space-y-2">
                                        {attachments.map((file, index) => (
                                            <div key={index} className="flex items-center justify-between bg-gray-50 dark:bg-[#2d3748] rounded-lg px-3 py-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="material-symbols-outlined text-[20px] text-[#4c669a]">description</span>
                                                    <div>
                                                        <p className="text-sm font-medium text-[#0d121b] dark:text-white">{file.name}</p>
                                                        <p className="text-xs text-[#4c669a]">{formatFileSize(file.size)}</p>
                                                    </div>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => removeAttachment(index)}
                                                    className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                                                >
                                                    <span className="material-symbols-outlined text-[18px]">close</span>
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    id="send_email"
                                    checked={createForm.send_email}
                                    onChange={(e) => setCreateForm({ ...createForm, send_email: e.target.checked })}
                                    className="w-4 h-4 rounded border-gray-300 text-[#1152d4]"
                                />
                                <label htmlFor="send_email" className="text-sm text-[#0d121b] dark:text-white">
                                    Send invitation email immediately
                                </label>
                            </div>
                        </div>

                        <div className="p-6 bg-gray-50 dark:bg-[#2d3748]/30 flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setIsCreateModalOpen(false)
                                    resetCreateForm()
                                }}
                                className="px-4 py-2 text-sm font-bold text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateInvitation}
                                disabled={!createForm.organization_name || !createForm.contact_email || !createForm.twg_id || isSubmitting}
                                className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white text-sm font-bold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isSubmitting && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                                Send Invitation
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Chat Modal */}
            {isChatModalOpen && selectedInvitation && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-[#1a202c] rounded-2xl shadow-2xl w-full max-w-2xl border border-[#e7ebf3] dark:border-[#2d3748] overflow-hidden flex flex-col max-h-[80vh]">
                        <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748] flex items-center justify-between">
                            <div>
                                <h3 className="text-xl font-bold text-[#0d121b] dark:text-white">
                                    Conversation with {selectedInvitation.organization_name}
                                </h3>
                                <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                    {selectedInvitation.twg_name} • {selectedInvitation.contact_email}
                                </p>
                            </div>
                            <button
                                onClick={() => {
                                    setIsChatModalOpen(false)
                                    setSelectedInvitation(null)
                                    loadInvitations() // Refresh to update unread counts
                                }}
                                className="p-2 text-[#4c669a] hover:text-[#0d121b] dark:text-[#a0aec0] dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-[#2d3748]"
                            >
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>
                        <div className="flex-1 min-h-0">
                            <InvitationChat
                                invitationId={selectedInvitation.id}
                                isPublic={false}
                                organizationName={selectedInvitation.organization_name}
                            />
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
