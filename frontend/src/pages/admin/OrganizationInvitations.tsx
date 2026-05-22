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

const STATUS_DOT: Record<OrganizationInvitationStatus, string> = {
    pending: 'var(--amber)',
    accepted: 'var(--sage)',
    declined: 'var(--terra)',
    expired: 'var(--ink-400)'
}

export default function OrganizationInvitations() {
    const [invitations, setInvitations] = useState<OrganizationInvitation[]>([])
    const [twgs, setTwgs] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize] = useState(20)
    const [pages, setPages] = useState(0)
    const [hoveredRow, setHoveredRow] = useState<string | null>(null)

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
            const response = await twgService.dropdown()
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

    // Counts for LedgerStat
    const pendingCount = invitations.filter(i => i.status === 'pending').length
    const acceptedCount = invitations.filter(i => i.status === 'accepted').length
    const declinedCount = invitations.filter(i => i.status === 'declined').length
    const expiredCount = invitations.filter(i => i.status === 'expired').length

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
                    Management · onboarding
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <h1 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        Organisation invitations
                    </h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={loadInvitations} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>refresh</span>
                            Refresh
                        </button>
                        <button onClick={() => { if (twgs.length === 0) loadTwgs(); setIsCreateModalOpen(true); }} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>mail</span>
                            New Invitation
                        </button>
                    </div>
                </div>
            </div>

            {/* LedgerStat strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', background: 'var(--surface)', border: '1px solid var(--border)', padding: '22px 32px', marginBottom: 24 }}>
                {[
                    { label: 'Pending', value: pendingCount, accent: 'var(--amber)', sub: 'awaiting response' },
                    { label: 'Accepted', value: acceptedCount, accent: 'var(--sage)', sub: 'joined' },
                    { label: 'Declined', value: declinedCount, accent: 'var(--terra)', sub: 'not joining' },
                    { label: 'Expired', value: expiredCount, accent: 'var(--ink-400)', sub: 'timed out' },
                ].map((stat, i, arr) => (
                    <div key={stat.label} style={{ paddingRight: 24, borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none', paddingLeft: i > 0 ? 24 : 0 }}>
                        <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{stat.label}</div>
                        <div style={{ fontFamily: "'Source Serif 4', serif", fontSize: 28, color: stat.accent, letterSpacing: '-0.02em', marginTop: 4, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{stat.value}</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6 }}>{stat.sub}</div>
                    </div>
                ))}
            </div>

            {/* Martin notes strip */}
            <div style={{ borderLeft: '2px solid var(--accent)', padding: '10px 16px', background: 'var(--accent-soft)', marginBottom: 24 }}>
                <span style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 600, fontStyle: 'normal' }}>Martin notes</span>
                <p style={{ fontFamily: "'Source Serif 4', serif", fontSize: 14, color: 'var(--ink-700)', margin: '4px 0 0', fontStyle: 'italic', lineHeight: 1.5 }}>
                    Send personalised invitations to external organisations. Pending invitations expire after 30 days. Use the chat feature to answer questions before they respond.
                </p>
            </div>

            {/* Filters */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
                <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value as OrganizationInvitationStatus | ''); setPage(1); }} style={{ background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 12, padding: '7px 12px', color: 'var(--ink-700)', fontFamily: 'inherit', cursor: 'pointer', outline: 'none' }}>
                    <option value="">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="accepted">Accepted</option>
                    <option value="declined">Declined</option>
                    <option value="expired">Expired</option>
                </select>
                <select value={twgFilter} onChange={(e) => { setTwgFilter(e.target.value); setPage(1); }} style={{ background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 12, padding: '7px 12px', color: 'var(--ink-700)', fontFamily: 'inherit', cursor: 'pointer', outline: 'none' }}>
                    <option value="">All TWGs</option>
                    {twgs.map(twg => (<option key={twg.id} value={twg.id}>{twg.name}</option>))}
                </select>
                <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-400)', marginLeft: 'auto' }}>
                    {total} invitations
                </span>
            </div>

            {/* Table */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                {isLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 256 }}>
                        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', textAlign: 'left', fontSize: 13, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ background: 'var(--ink-50)', borderBottom: '1px solid var(--border)' }}>
                                    {['Organisation', 'Contact', 'TWG', 'Sent', 'Expires', 'Status', 'Actions'].map(col => (
                                        <th key={col} style={{ padding: '10px 16px', fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{col}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {invitations.map((invitation, idx) => (
                                    <tr
                                        key={invitation.id}
                                        onMouseEnter={() => setHoveredRow(invitation.id)}
                                        onMouseLeave={() => setHoveredRow(null)}
                                        style={{
                                            borderBottom: idx < invitations.length - 1 ? '1px solid var(--border)' : 'none',
                                            background: hoveredRow === invitation.id ? 'var(--ink-50)' : 'transparent'
                                        }}
                                    >
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ fontWeight: 500, color: 'var(--ink-900)', fontSize: 13 }}>{invitation.organization_name}</div>
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ fontSize: 13, color: 'var(--ink-700)' }}>{invitation.contact_email}</div>
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <span style={{ fontSize: 11, color: 'var(--ink-600)', background: 'var(--ink-50)', border: '1px solid var(--border)', padding: '2px 8px' }}>
                                                {invitation.twg_name || 'Unknown'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px 16px', fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                                            {formatDate(invitation.sent_at)}
                                        </td>
                                        <td style={{ padding: '12px 16px', fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                                            {formatDate(invitation.expires_at)}
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
                                                <div style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_DOT[invitation.status], flexShrink: 0 }}></div>
                                                <span style={{ color: 'var(--ink-700)', textTransform: 'capitalize' }}>{invitation.status}</span>
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                            <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                                {/* Chat */}
                                                <button
                                                    onClick={() => { setSelectedInvitation(invitation); setIsChatModalOpen(true); }}
                                                    style={{ background: invitation.unread_message_count > 0 ? 'var(--accent-soft)' : 'none', border: 'none', cursor: 'pointer', color: invitation.unread_message_count > 0 ? 'var(--accent)' : 'var(--ink-400)', padding: 5, position: 'relative' }}
                                                    title={invitation.has_messages ? 'View Conversation' : 'Start Conversation'}
                                                >
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>chat</span>
                                                    {invitation.unread_message_count > 0 && (
                                                        <span style={{ position: 'absolute', top: 0, right: 0, width: 14, height: 14, background: 'var(--terra)', color: '#fff', fontSize: 9, fontWeight: 700, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                            {invitation.unread_message_count > 9 ? '9+' : invitation.unread_message_count}
                                                        </span>
                                                    )}
                                                </button>
                                                {/* Copy link */}
                                                <button
                                                    onClick={() => { const link = `${window.location.origin}/invitations/${invitation.id}/respond`; navigator.clipboard.writeText(link); toast.success('Invitation link copied!'); }}
                                                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 5 }}
                                                    title="Copy Link"
                                                >
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>link</span>
                                                </button>
                                                {/* Resend (pending only) */}
                                                {invitation.status === 'pending' && (
                                                    <button
                                                        onClick={() => handleResendInvitation(invitation)}
                                                        disabled={resendingId === invitation.id}
                                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 5, opacity: resendingId === invitation.id ? 0.5 : 1 }}
                                                        title="Resend"
                                                    >
                                                        {resendingId === invitation.id ? (
                                                            <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                                                        ) : (
                                                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>forward_to_inbox</span>
                                                        )}
                                                    </button>
                                                )}
                                                {/* Delete */}
                                                <button onClick={() => handleDeleteInvitation(invitation.id, invitation.organization_name)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--terra)', padding: 5 }} title="Delete">
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>delete</span>
                                                </button>
                                                {/* Response date */}
                                                {invitation.status !== 'pending' && invitation.responded_at && (
                                                    <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 10, color: 'var(--ink-400)', marginLeft: 4, whiteSpace: 'nowrap' }}>
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
                    <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--ink-400)' }}>
                        <p style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>No invitations found</p>
                        <p style={{ fontSize: 13, marginTop: 4 }}>
                            {statusFilter || twgFilter ? 'Try adjusting your filters' : 'Click "New Invitation" to invite an organisation'}
                        </p>
                    </div>
                )}

                {/* Pagination */}
                {!isLoading && pages > 1 && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
                        <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                            {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}
                        </span>
                        <div style={{ display: 'flex', gap: 6 }}>
                            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '4px 12px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', opacity: page === 1 ? 0.4 : 1 }}>Previous</button>
                            <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages} style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '4px 12px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', opacity: page === pages ? 0.4 : 1 }}>Next</button>
                        </div>
                    </div>
                )}
            </div>

            {/* Create Invitation Modal */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 480, overflow: 'hidden' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: '0 0 4px' }}>New Organisation Invitation</h3>
                            <p style={{ fontSize: 13, color: 'var(--ink-500)', margin: 0 }}>Invite an external organisation to join a TWG</p>
                        </div>
                        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16, maxHeight: '60vh', overflowY: 'auto' }}>
                            <div><label style={labelStyle}>Organisation Name *</label><input type="text" value={createForm.organization_name} onChange={(e) => setCreateForm({ ...createForm, organization_name: e.target.value })} style={inputStyle} placeholder="Acme Corporation" /></div>
                            <div><label style={labelStyle}>Contact Email *</label><input type="email" value={createForm.contact_email} onChange={(e) => setCreateForm({ ...createForm, contact_email: e.target.value })} style={inputStyle} placeholder="contact@acme.com" /></div>
                            <div>
                                <label style={labelStyle}>TWG to Join *</label>
                                <select value={createForm.twg_id} onChange={(e) => setCreateForm({ ...createForm, twg_id: e.target.value })} style={{ ...inputStyle, cursor: 'pointer' }}>
                                    <option value="">Select a TWG</option>
                                    {twgs.map(twg => (<option key={twg.id} value={twg.id}>{twg.name}</option>))}
                                </select>
                            </div>
                            <div>
                                <label style={labelStyle}>Custom Message</label>
                                <textarea value={createForm.custom_message || ''} onChange={(e) => setCreateForm({ ...createForm, custom_message: e.target.value })} style={{ ...inputStyle, minHeight: 90, resize: 'vertical' }} placeholder="Optional personal message..." />
                            </div>
                            {/* Attachments */}
                            <div>
                                <label style={labelStyle}>Attachments</label>
                                <div onClick={() => fileInputRef.current?.click()} style={{ border: '1px dashed var(--border)', padding: '16px', textAlign: 'center', cursor: 'pointer' }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: 28, color: 'var(--ink-300)', display: 'block', marginBottom: 4 }}>attach_file</span>
                                    <p style={{ fontSize: 12, color: 'var(--ink-500)', margin: 0 }}>Click to attach files (PDF, images, documents)</p>
                                    <p style={{ fontSize: 11, color: 'var(--ink-400)', margin: '2px 0 0' }}>Max 5 files, 10MB each</p>
                                </div>
                                <input ref={fileInputRef} type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg" onChange={handleFileSelect} className="hidden" />
                                {attachments.length > 0 && (
                                    <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                        {attachments.map((file, index) => (
                                            <div key={index} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--ink-50)', border: '1px solid var(--border)', padding: '6px 10px' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--ink-400)' }}>description</span>
                                                    <div>
                                                        <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink-800)', margin: 0 }}>{file.name}</p>
                                                        <p style={{ fontSize: 10, color: 'var(--ink-400)', margin: 0 }}>{formatFileSize(file.size)}</p>
                                                    </div>
                                                </div>
                                                <button type="button" onClick={() => removeAttachment(index)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--terra)', padding: 4 }}>
                                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>close</span>
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <input type="checkbox" id="send_email" checked={createForm.send_email} onChange={(e) => setCreateForm({ ...createForm, send_email: e.target.checked })} style={{ accentColor: 'var(--accent)' }} />
                                <span style={{ fontSize: 13, color: 'var(--ink-700)' }}>Send invitation email immediately</span>
                            </label>
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                            <button onClick={() => { setIsCreateModalOpen(false); resetCreateForm(); }} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>Cancel</button>
                            <button onClick={handleCreateInvitation} disabled={!createForm.organization_name || !createForm.contact_email || !createForm.twg_id || isSubmitting} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6, opacity: !createForm.organization_name || !createForm.contact_email || !createForm.twg_id || isSubmitting ? 0.5 : 1 }}>
                                {isSubmitting && <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#fff', borderTopColor: 'transparent' }}></div>}
                                Send Invitation
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Chat Modal */}
            {isChatModalOpen && selectedInvitation && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 600, overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: '80vh' }}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                            <div>
                                <h3 style={{ fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 20, color: 'var(--ink-900)', margin: '0 0 4px' }}>
                                    Conversation with {selectedInvitation.organization_name}
                                </h3>
                                <p style={{ fontSize: 12, color: 'var(--ink-500)', margin: 0 }}>
                                    {selectedInvitation.twg_name} · {selectedInvitation.contact_email}
                                </p>
                            </div>
                            <button onClick={() => { setIsChatModalOpen(false); setSelectedInvitation(null); loadInvitations(); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>close</span>
                            </button>
                        </div>
                        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                            <InvitationChat
                                invitationId={selectedInvitation.id}
                                isPublic={false}
                                organizationName={selectedInvitation.organization_name}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
