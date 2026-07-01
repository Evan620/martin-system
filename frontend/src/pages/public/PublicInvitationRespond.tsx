import { useState, useEffect, CSSProperties } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
    organizationInvitationService,
    PublicInvitation,
    OrganizationInvitationStatus
} from '../../services/organizationInvitationService'
import InvitationChat from '../../components/invitations/InvitationChat'
import { toast } from 'react-toastify'

const STATUS_STYLES: Record<OrganizationInvitationStatus, CSSProperties> = {
    pending:  { background: 'color-mix(in srgb, var(--amber) 14%, transparent)', color: 'var(--amber)' },
    accepted: { background: 'color-mix(in srgb, var(--sage) 14%, transparent)',  color: 'var(--sage)' },
    declined: { background: 'color-mix(in srgb, var(--terra) 14%, transparent)', color: 'var(--terra)' },
    expired:  { background: 'var(--surface-2)',                                  color: 'var(--ink-500)' }
}

export default function PublicInvitationRespond() {
    const { invitationId } = useParams<{ invitationId: string }>()
    const [searchParams] = useSearchParams()

    const [invitation, setInvitation] = useState<PublicInvitation | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isResponding, setIsResponding] = useState(false)
    const [responseGiven, setResponseGiven] = useState<'accept' | 'decline' | null>(null)

    // Check for action param in URL
    const actionParam = searchParams.get('action')

    useEffect(() => {
        loadInvitation()
    }, [invitationId])

    useEffect(() => {
        // Auto-trigger accept/decline if action param is present and invitation is pending
        if (invitation && invitation.status === 'pending' && actionParam && !responseGiven) {
            if (actionParam === 'accept' || actionParam === 'decline') {
                handleRespond(actionParam)
            }
        }
    }, [invitation, actionParam])

    const loadInvitation = async () => {
        if (!invitationId) return

        setIsLoading(true)
        try {
            const data = await organizationInvitationService.getPublicInvitation(invitationId)
            setInvitation(data)
        } catch (error: any) {
            console.error('Failed to load invitation', error)
            if (error.response?.status === 404) {
                toast.error('Invitation not found')
            } else {
                toast.error('Failed to load invitation')
            }
        } finally {
            setIsLoading(false)
        }
    }

    const handleRespond = async (response: 'accept' | 'decline') => {
        if (!invitationId || !invitation) return

        setIsResponding(true)
        try {
            const result = await organizationInvitationService.respondToInvitation(invitationId, response)
            setResponseGiven(response)
            setInvitation(prev => prev ? { ...prev, status: result.status } : null)
            toast.success(result.message)
        } catch (error: any) {
            console.error('Failed to respond to invitation', error)
            const message = error.response?.data?.detail || 'Failed to respond to invitation'
            toast.error(message)
        } finally {
            setIsResponding(false)
        }
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        })
    }

    const isExpired = invitation && new Date(invitation.expires_at) < new Date()

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg)' }}>
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                    <p className="font-medium" style={{ color: 'var(--ink-500)' }}>Loading invitation...</p>
                </div>
            </div>
        )
    }

    if (!invitation) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--bg)' }}>
                <div className="p-8 max-w-md w-full text-center" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                    <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: 'color-mix(in srgb, var(--terra) 14%, transparent)' }}>
                        <span className="material-symbols-outlined text-3xl" style={{ color: 'var(--terra)' }}>error</span>
                    </div>
                    <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--ink-900)' }}>Invitation Not Found</h1>
                    <p style={{ color: 'var(--ink-500)' }}>
                        This invitation may have been deleted or the link is invalid.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
            <div className="max-w-4xl mx-auto p-4 md:p-8 animate-blur-slide">
                {/* Header */}
                <div className="overflow-hidden mb-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                    <div className="p-6 md:p-8" style={{ background: 'var(--accent)' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <h1 className="text-2xl md:text-3xl font-bold mb-2" style={{ color: 'var(--accent-ink)' }}>
                                    TWG Invitation
                                </h1>
                                <p className="text-lg" style={{ color: 'color-mix(in srgb, var(--accent-ink) 80%, transparent)' }}>
                                    {invitation.twg_name}
                                </p>
                            </div>
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-bold" style={STATUS_STYLES[invitation.status]}>
                                {invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}
                            </span>
                        </div>
                    </div>

                    <div className="p-6 md:p-8">
                        {/* Organization Info */}
                        <div className="mb-6">
                            <p className="qp-eyebrow mb-1">Invited Organization</p>
                            <p className="text-xl font-bold" style={{ color: 'var(--ink-900)' }}>{invitation.organization_name}</p>
                        </div>

                        {/* Custom Message */}
                        {invitation.custom_message && (
                            <div className="mb-6 p-4" style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-ctl)', borderLeft: '4px solid var(--accent)' }}>
                                <p className="qp-eyebrow mb-1">Personal Message</p>
                                <p className="whitespace-pre-wrap" style={{ color: 'var(--ink-800)' }}>{invitation.custom_message}</p>
                            </div>
                        )}

                        {/* Expiry Info */}
                        <div className="flex items-center gap-2 text-sm mb-6" style={{ color: 'var(--ink-500)' }}>
                            <span className="material-symbols-outlined text-[20px]">event</span>
                            {isExpired ? (
                                <span className="font-medium" style={{ color: 'var(--terra)' }}>
                                    This invitation expired on {formatDate(invitation.expires_at)}
                                </span>
                            ) : (
                                <span>
                                    Expires on {formatDate(invitation.expires_at)}
                                </span>
                            )}
                        </div>

                        {/* Response Actions */}
                        {invitation.status === 'pending' && !isExpired && (
                            <div className="flex flex-col sm:flex-row gap-3">
                                <button
                                    onClick={() => handleRespond('accept')}
                                    disabled={isResponding}
                                    className="clickable-scale flex-1 py-3 px-6 font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                    style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)', border: '1px solid var(--accent)' }}
                                >
                                    {isResponding ? (
                                        <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent-ink)', borderTopColor: 'transparent' }}></div>
                                    ) : (
                                        <>
                                            <span className="material-symbols-outlined">check_circle</span>
                                            Accept Invitation
                                        </>
                                    )}
                                </button>
                                <button
                                    onClick={() => handleRespond('decline')}
                                    disabled={isResponding}
                                    className="clickable-scale flex-1 py-3 px-6 font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                    style={{ background: 'var(--surface)', color: 'var(--terra)', borderRadius: 'var(--radius-ctl)', border: '1px solid color-mix(in srgb, var(--terra) 40%, var(--border))' }}
                                >
                                    <span className="material-symbols-outlined">cancel</span>
                                    Decline
                                </button>
                            </div>
                        )}

                        {/* Response Confirmation */}
                        {responseGiven && (
                            <div className="mt-6 p-4" style={{
                                borderRadius: 'var(--radius-ctl)',
                                background: responseGiven === 'accept'
                                    ? 'color-mix(in srgb, var(--sage) 10%, transparent)'
                                    : 'var(--surface-2)',
                                border: responseGiven === 'accept'
                                    ? '1px solid color-mix(in srgb, var(--sage) 30%, var(--border))'
                                    : '1px solid var(--border)'
                            }}>
                                <div className="flex items-center gap-3">
                                    {responseGiven === 'accept' ? (
                                        <span className="material-symbols-outlined text-2xl" style={{ color: 'var(--sage)' }}>check_circle</span>
                                    ) : (
                                        <span className="material-symbols-outlined text-2xl" style={{ color: 'var(--ink-500)' }}>cancel</span>
                                    )}
                                    <div>
                                        <p className="font-bold" style={{ color: responseGiven === 'accept' ? 'var(--sage)' : 'var(--ink-700)' }}>
                                            Invitation {responseGiven === 'accept' ? 'Accepted' : 'Declined'}
                                        </p>
                                        <p className="text-sm" style={{ color: 'var(--ink-500)' }}>
                                            {responseGiven === 'accept'
                                                ? `You will be contacted by the ${invitation.twg_name} team shortly.`
                                                : 'Your response has been recorded.'
                                            }
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Already Responded */}
                        {invitation.status !== 'pending' && !responseGiven && (
                            <div className="p-4" style={{
                                borderRadius: 'var(--radius-ctl)',
                                background: invitation.status === 'accepted'
                                    ? 'color-mix(in srgb, var(--sage) 10%, transparent)'
                                    : invitation.status === 'declined'
                                        ? 'var(--surface-2)'
                                        : 'color-mix(in srgb, var(--terra) 10%, transparent)',
                                border: invitation.status === 'accepted'
                                    ? '1px solid color-mix(in srgb, var(--sage) 30%, var(--border))'
                                    : invitation.status === 'declined'
                                        ? '1px solid var(--border)'
                                        : '1px solid color-mix(in srgb, var(--terra) 30%, var(--border))'
                            }}>
                                <div className="flex items-center gap-3">
                                    <span className="material-symbols-outlined text-2xl" style={{ color: 'var(--ink-500)' }}>info</span>
                                    <div>
                                        <p className="font-bold" style={{ color: 'var(--ink-900)' }}>
                                            This invitation has already been {invitation.status}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Chat Section - Always Visible */}
                <div className="overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                    <div className="p-4" style={{ borderBottom: '1px solid var(--border)' }}>
                        <h2 className="text-lg font-bold" style={{ color: 'var(--ink-900)' }}>Conversation</h2>
                        <p className="text-sm" style={{ color: 'var(--ink-500)' }}>
                            Send a message to the {invitation.twg_name} team
                        </p>
                    </div>
                    <div className="h-[400px]">
                        <InvitationChat
                            invitationId={invitationId!}
                            isPublic={true}
                            organizationName={invitation.organization_name}
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="mt-8 text-center">
                    <p className="text-sm" style={{ color: 'var(--ink-500)' }}>
                        WAIIS Technical Working Group Platform
                    </p>
                </div>
            </div>
        </div>
    )
}
