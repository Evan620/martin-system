import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import {
    organizationInvitationService,
    PublicInvitation,
    OrganizationInvitationStatus
} from '../../services/organizationInvitationService'
import InvitationChat from '../../components/invitations/InvitationChat'
import { toast } from 'react-toastify'

const STATUS_COLORS: Record<OrganizationInvitationStatus, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    accepted: 'bg-green-100 text-green-700',
    declined: 'bg-red-100 text-red-700',
    expired: 'bg-gray-100 text-gray-700'
}

export default function PublicInvitationRespond() {
    const { invitationId } = useParams<{ invitationId: string }>()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const [invitation, setInvitation] = useState<PublicInvitation | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isResponding, setIsResponding] = useState(false)
    const [showChat, setShowChat] = useState(false)
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
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-[#1152d4] border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-[#4c669a] font-medium">Loading invitation...</p>
                </div>
            </div>
        )
    }

    if (!invitation) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="material-symbols-outlined text-3xl text-red-600">error</span>
                    </div>
                    <h1 className="text-2xl font-bold text-[#0d121b] mb-2">Invitation Not Found</h1>
                    <p className="text-[#4c669a]">
                        This invitation may have been deleted or the link is invalid.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] to-[#e2e8f0]">
            <div className="max-w-4xl mx-auto p-4 md:p-8">
                {/* Header */}
                <div className="bg-white rounded-2xl shadow-lg overflow-hidden mb-6">
                    <div className="bg-gradient-to-r from-[#1152d4] to-[#0e44b1] p-6 md:p-8">
                        <div className="flex items-start justify-between">
                            <div>
                                <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
                                    TWG Invitation
                                </h1>
                                <p className="text-white/80 text-lg">
                                    {invitation.twg_name}
                                </p>
                            </div>
                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${STATUS_COLORS[invitation.status]}`}>
                                {invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}
                            </span>
                        </div>
                    </div>

                    <div className="p-6 md:p-8">
                        {/* Organization Info */}
                        <div className="mb-6">
                            <p className="text-sm text-[#4c669a] mb-1">Invited Organization</p>
                            <p className="text-xl font-bold text-[#0d121b]">{invitation.organization_name}</p>
                        </div>

                        {/* Custom Message */}
                        {invitation.custom_message && (
                            <div className="mb-6 p-4 bg-gray-50 rounded-xl border-l-4 border-[#1152d4]">
                                <p className="text-sm text-[#4c669a] mb-1">Personal Message</p>
                                <p className="text-[#0d121b] whitespace-pre-wrap">{invitation.custom_message}</p>
                            </div>
                        )}

                        {/* Expiry Info */}
                        <div className="flex items-center gap-2 text-sm text-[#4c669a] mb-6">
                            <span className="material-symbols-outlined text-[20px]">event</span>
                            {isExpired ? (
                                <span className="text-red-600 font-medium">
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
                                    className="flex-1 py-3 px-6 bg-green-600 hover:bg-green-700 text-white rounded-xl font-bold transition-all shadow-lg shadow-green-600/20 disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {isResponding ? (
                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
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
                                    className="flex-1 py-3 px-6 bg-white hover:bg-gray-50 text-red-600 border-2 border-red-200 hover:border-red-300 rounded-xl font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    <span className="material-symbols-outlined">cancel</span>
                                    Decline
                                </button>
                            </div>
                        )}

                        {/* Response Confirmation */}
                        {responseGiven && (
                            <div className={`mt-6 p-4 rounded-xl ${
                                responseGiven === 'accept'
                                    ? 'bg-green-50 border border-green-200'
                                    : 'bg-gray-50 border border-gray-200'
                            }`}>
                                <div className="flex items-center gap-3">
                                    {responseGiven === 'accept' ? (
                                        <span className="material-symbols-outlined text-2xl text-green-600">check_circle</span>
                                    ) : (
                                        <span className="material-symbols-outlined text-2xl text-gray-500">cancel</span>
                                    )}
                                    <div>
                                        <p className={`font-bold ${
                                            responseGiven === 'accept' ? 'text-green-700' : 'text-gray-700'
                                        }`}>
                                            Invitation {responseGiven === 'accept' ? 'Accepted' : 'Declined'}
                                        </p>
                                        <p className="text-sm text-[#4c669a]">
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
                            <div className={`mt-4 p-4 rounded-xl ${
                                invitation.status === 'accepted'
                                    ? 'bg-green-50 border border-green-200'
                                    : invitation.status === 'declined'
                                        ? 'bg-gray-50 border border-gray-200'
                                        : 'bg-red-50 border border-red-200'
                            }`}>
                                <div className="flex items-center gap-3">
                                    <span className="material-symbols-outlined text-2xl text-[#4c669a]">info</span>
                                    <div>
                                        <p className="font-bold text-[#0d121b]">
                                            This invitation has already been {invitation.status}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Chat Toggle */}
                        <div className="mt-6 pt-6 border-t border-gray-200">
                            <button
                                onClick={() => setShowChat(!showChat)}
                                className="flex items-center gap-2 text-[#1152d4] hover:text-[#0e44b1] font-medium"
                            >
                                <span className="material-symbols-outlined">
                                    {showChat ? 'expand_less' : 'chat'}
                                </span>
                                {showChat ? 'Hide Conversation' : 'View Conversation'}
                                {invitation.has_messages && !showChat && (
                                    <span className="px-2 py-0.5 bg-[#1152d4] text-white text-xs rounded-full">
                                        New
                                    </span>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Chat Section */}
                {showChat && (
                    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
                        <div className="p-4 border-b border-[#e7ebf3]">
                            <h2 className="text-lg font-bold text-[#0d121b]">Conversation</h2>
                            <p className="text-sm text-[#4c669a]">
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
                )}

                {/* Footer */}
                <div className="mt-8 text-center">
                    <p className="text-sm text-[#4c669a]">
                        ECOWAS Summit Technical Working Group Platform
                    </p>
                </div>
            </div>
        </div>
    )
}
