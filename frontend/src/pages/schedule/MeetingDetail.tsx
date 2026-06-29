import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import { meetings, actionItems, twgs, recurringMeetings } from '../../services/api'
import { UserRole } from '../../types/auth'
import { Card, Badge } from '../../components/ui'
import { toLocalInputValue, formatMeetingDate, formatMeetingTime } from '../../utils/dates'
import MinutesVersionHistory from '../../components/schedule/MinutesVersionHistory'

import ConflictModal from '../../components/modals/ConflictModal'
import InputModal from '../../components/modals/InputModal'
import InvitePreviewModal from '../../components/modals/InvitePreviewModal'
import StatusModal from '../../components/modals/StatusModal'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type TabType = 'agenda' | 'minutes' | 'participants' | 'documents' | 'schedule'

export default function MeetingDetail() {
    const { id: meetingId } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const location = useLocation()
    const [searchParams, setSearchParams] = useSearchParams()
    const user = useSelector((state: RootState) => state.auth.user)
    const isFacilitator = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD || user?.role === UserRole.FACILITATOR
    const [meeting, setMeeting] = useState<any>(null)
    const [activeTab, setActiveTab] = useState<TabType>('minutes')
    const [loading, setLoading] = useState(true)

    // Agenda State
    const [agendaContent, setAgendaContent] = useState('')
    const [isEditingAgenda, setIsEditingAgenda] = useState(false)

    // Minutes State
    const [minutesContent, setMinutesContent] = useState('')
    const [minutesStatus, setMinutesStatus] = useState<string>('DRAFT')
    const [isGeneratingMinutes, setIsGeneratingMinutes] = useState(false)
    const [isSubmittingForApproval, setIsSubmittingForApproval] = useState(false)
    const [isApprovingMinutes, setIsApprovingMinutes] = useState(false)
    const [meetingActionItems, setMeetingActionItems] = useState<any[]>([])

    // Participant State
    const [guestName, setGuestName] = useState('')
    const [guestEmail, setGuestEmail] = useState('')
    const [bulkGuestsText, setBulkGuestsText] = useState('')
    const [isBulkMode, setIsBulkMode] = useState(false)
    const [isAddingGuest, setIsAddingGuest] = useState(false)
    const [isAddingMember, setIsAddingMember] = useState(false)
    const [twgMembers, setTwgMembers] = useState<any[]>([])
    const [selectedMembers, setSelectedMembers] = useState<string[]>([])
    const [applyToSeries, setApplyToSeries] = useState(false)
    const [isSendingInvites, setIsSendingInvites] = useState(false)
    const [isSyncingCalendar, setIsSyncingCalendar] = useState(false)
    const [isCheckingConflicts, setIsCheckingConflicts] = useState(false)
    const [showConflictModal, setShowConflictModal] = useState(false)
    const [detectedConflicts, setDetectedConflicts] = useState<any[]>([])
    const [showCancelModal, setShowCancelModal] = useState(false)
    const [showUpdateModal, setShowUpdateModal] = useState(false)
    const [showInvitePreviewModal, setShowInvitePreviewModal] = useState(false)
    const [isLoadingAction, setIsLoadingAction] = useState(false)
    const [showVersionHistory, setShowVersionHistory] = useState(false)

    // Translation State
    const [isTranslating, setIsTranslating] = useState(false)
    const [translatedContent, setTranslatedContent] = useState<string | null>(null)
    const [translationLanguage, setTranslationLanguage] = useState<string | null>(null)
    const [showTranslateMenu, setShowTranslateMenu] = useState(false)
    const [statusModal, setStatusModal] = useState<{ isOpen: boolean, type: 'success' | 'error' | 'info', title: string, message: string, actionText?: string, onAction?: () => void }>({
        isOpen: false,
        type: 'info',
        title: '',
        message: ''
    })

    // Modal States
    const [isEditingMeeting, setIsEditingMeeting] = useState(false)
    const [isAddingAction, setIsAddingAction] = useState(false)
    const [extractingActions, setExtractingActions] = useState(false)

    const [newActionDescription, setNewActionDescription] = useState('')
    const [newActionOwner, setNewActionOwner] = useState('')
    const [selectedAction, setSelectedAction] = useState<any>(null)
    const [isEditingSelected, setIsEditingSelected] = useState(false)
    const [selectedDescription, setSelectedDescription] = useState('')
    const [selectedOwner, setSelectedOwner] = useState('')
    const [selectedDueDate, setSelectedDueDate] = useState('')
    const [newActionDueDate, setNewActionDueDate] = useState('')

    // Edit Meeting State
    const [editTitle, setEditTitle] = useState('')
    const [editDate, setEditDate] = useState('')
    const [editLocation, setEditLocation] = useState('')

    // Manage Series State
    const [showManageSeriesModal, setShowManageSeriesModal] = useState(false)
    const [seriesData, setSeriesData] = useState<any>(null)
    const [seriesLoading, setSeriesLoading] = useState(false)
    const [seriesEditMode, setSeriesEditMode] = useState(false)
    const [seriesTitle, setSeriesTitle] = useState('')
    const [seriesTime, setSeriesTime] = useState('')
    const [seriesDuration, setSeriesDuration] = useState(60)
    const [seriesLocation, setSeriesLocation] = useState('')
    const [seriesUpdateScope, setSeriesUpdateScope] = useState<'future' | 'all'>('future')
    const [showCancelSeriesConfirm, setShowCancelSeriesConfirm] = useState(false)
    const [seriesActionLoading, setSeriesActionLoading] = useState(false)

    // Transcript State
    const [transcript, setTranscript] = useState('')
    const [isSavingTranscript, setIsSavingTranscript] = useState(false)
    const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(true)

    // Documents State
    const [documents, setDocuments] = useState<any[]>([])
    const [isUploadingDoc, setIsUploadingDoc] = useState(false)

    const handleSaveTranscript = async () => {
        if (!meetingId) return;
        setIsSavingTranscript(true);
        try {
            await meetings.update(meetingId, { transcript });
        } catch (e) {
            console.error("Failed to save transcript", e);
        } finally {
            setIsSavingTranscript(false);
        }
    }

    useEffect(() => {
        loadMeetingDetails()

        // Listen for real-time updates
        const handleUpdate = (event: any) => {
            if (event.detail?.meetingId === meetingId) {
                console.log("Received meeting update via WebSocket, refreshing...");
                loadMeetingDetails();
            }
        };

        window.addEventListener('meeting-update', handleUpdate);
        return () => window.removeEventListener('meeting-update', handleUpdate);
    }, [meetingId])

    // Auto-translate when ?lang= param is present and minutes are loaded
    useEffect(() => {
        const lang = searchParams.get('lang')
        if (lang && ['fr', 'pt', 'en'].includes(lang) && minutesContent && !translatedContent && !isTranslating) {
            handleTranslate(lang)
        }
    }, [minutesContent, searchParams])

    const loadMeetingDetails = async () => {
        if (!meetingId) return;

        setLoading(true)
        try {
            const res = await meetings.get(meetingId)
            setMeeting(res.data)
            setTranscript(res.data.transcript || '')

            // Load agenda
            try {
                const agendaRes = await meetings.getAgenda(meetingId)
                setAgendaContent(agendaRes.data.content || '')
            } catch (e) {
                setAgendaContent('')
            }

            // Load minutes
            try {
                const minutesRes = await meetings.getMinutes(meetingId)
                setMinutesContent(minutesRes.data.content || '')
                setMinutesStatus(minutesRes.data.status || 'DRAFT')
                if (minutesRes.data.content) {
                    setIsTranscriptExpanded(false)
                }
            } catch (e) {
                console.log("No minutes yet")
                setMinutesContent('')
                setMinutesStatus('DRAFT')
            }

            // Load action items
            try {
                const actionsRes = await meetings.getActionItems(meetingId)
                setMeetingActionItems(actionsRes.data || [])
            } catch (e) {
                console.log("No action items yet")
                setMeetingActionItems([])
            }

            // Load documents
            try {
                const docsRes = await meetings.getDocuments(meetingId)
                setDocuments(docsRes.data || [])
            } catch (e) {
                console.log("No documents yet")
                setDocuments([])
            }
        } catch (error) {
            console.error("Failed to load details", error)
        } finally {
            setLoading(false)
        }
    }

    const handleSaveAgenda = async () => {
        if (!meetingId) return
        try {
            await meetings.updateAgenda(meetingId, { content: agendaContent })
            setIsEditingAgenda(false)
            await loadMeetingDetails()
        } catch (error) {
            console.error("Failed to save agenda", error)
            alert("Failed to save agenda")
        }
    }



    const handleGenerateSummary = async () => {
        if (!meetingId || isGeneratingMinutes) return
        setIsGeneratingMinutes(true)
        try {
            const res = await meetings.generateMinutes(meetingId)
            setMinutesContent(res.data.content)
            setTranslatedContent(null)
            setTranslationLanguage(null)
            setMinutesStatus('DRAFT')
            setIsTranscriptExpanded(false)
            setMinutesStatus('DRAFT')  // Generated content starts as draft
        } catch (error: any) {
            console.error("Failed to generate minutes", error)
            let errorMessage = "Failed to generate minutes."
            if (error.response) {
                errorMessage = error.response.data?.detail || `Server error: ${error.response.status}`
            } else if (error.request) {
                errorMessage = "Network error: Could not connect to the server."
            }
            alert(errorMessage)
        } finally {
            setIsGeneratingMinutes(false)
        }
    }

    const handleSubmitForApproval = async () => {
        if (!meetingId || isSubmittingForApproval) return

        // First save the minutes content
        try {
            await meetings.updateMinutes(meetingId, { content: minutesContent })
        } catch (error) {
            console.error("Failed to save minutes before submission", error)
            alert("Failed to save minutes")
            return
        }

        setIsSubmittingForApproval(true)
        try {
            const res = await meetings.submitMinutesForApproval(meetingId)
            setMinutesStatus(res.data.status)
            alert("Minutes submitted! Secretariat Lead has been notified for approval.")
        } catch (error: any) {
            console.error("Failed to submit for approval", error)
            let errorMessage = "Failed to submit for approval."

            if (error.response) {
                errorMessage = error.response.data?.detail || `Server error: ${error.response.status}`
            } else if (error.request) {
                errorMessage = "Network error: Could not connect to the server. Please check your internet connection."
            } else {
                errorMessage = error.message || "An unexpected error occurred."
            }
            alert(errorMessage)
        } finally {
            setIsSubmittingForApproval(false)
        }
    }

    const handleApproveMinutes = async () => {
        if (!meetingId || isApprovingMinutes) return
        setIsApprovingMinutes(true)
        try {
            const res = await meetings.approveMinutes(meetingId)
            setMinutesStatus(res.data.status)
            alert(`Minutes approved by ${res.data.approved_by}!`)
        } catch (error: any) {
            console.error("Failed to approve minutes", error)
            alert(error?.response?.data?.detail || "Failed to approve minutes")
        } finally {
            setIsApprovingMinutes(false)
        }
    }

    const handleDownloadPdf = async () => {
        if (!meetingId) return
        try {
            const response = await meetings.downloadMinutesPdf(meetingId, translationLanguage || undefined)
            // Create blob URL and trigger download
            const blob = new Blob([response.data], { type: 'application/pdf' })
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            // Get filename from Content-Disposition header or use default
            const contentDisposition = response.headers['content-disposition']
            let filename = 'Minutes.pdf'
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename=(.+)/)
                if (filenameMatch) filename = filenameMatch[1]
            }
            link.setAttribute('download', filename)
            document.body.appendChild(link)
            link.click()
            link.remove()
            window.URL.revokeObjectURL(url)
        } catch (error: any) {
            console.error("Failed to download PDF", error)
            alert(error?.response?.data?.detail || "Failed to download PDF")
        }
    }

    const handleTranslate = async (lang: string) => {
        if (!meetingId || isTranslating) return
        setShowTranslateMenu(false)
        setIsTranslating(true)
        try {
            const res = await meetings.translateMinutes(meetingId, lang)
            setTranslatedContent(res.data.translated_content)
            setTranslationLanguage(lang)
            setSearchParams(prev => { prev.set('lang', lang); return prev }, { replace: true })
        } catch (error: any) {
            console.error("Failed to translate minutes", error)
            alert(error?.response?.data?.detail || "Failed to translate minutes")
        } finally {
            setIsTranslating(false)
        }
    }

    const handleClearTranslation = () => {
        setTranslatedContent(null)
        setTranslationLanguage(null)
        setSearchParams(prev => { prev.delete('lang'); return prev }, { replace: true })
    }

    const [showRejectModal, setShowRejectModal] = useState(false)
    const [rejectReason, setRejectReason] = useState('')
    const [isRejectingMinutes, setIsRejectingMinutes] = useState(false)

    const handleRejectMinutes = async () => {
        if (!meetingId || !rejectReason.trim() || isRejectingMinutes) return
        setIsRejectingMinutes(true)
        try {
            const res = await meetings.rejectMinutes(meetingId, rejectReason)
            setMinutesStatus(res.data.status)
            setShowRejectModal(false)
            setRejectReason('')
            alert("Minutes rejected and sent back for revision")
        } catch (error: any) {
            console.error("Failed to reject minutes", error)
            alert(error?.response?.data?.detail || "Failed to reject minutes")
        } finally {
            setIsRejectingMinutes(false)
        }
    }


    const handleAddGuest = async () => {
        if (!meetingId || !guestEmail) return
        setIsLoadingAction(true)
        try {
            await meetings.addParticipants(meetingId, [{
                name: guestName,
                email: guestEmail
            }], applyToSeries)
            setGuestName('')
            setGuestEmail('')
            setIsAddingGuest(false)
            setApplyToSeries(false)
            await loadMeetingDetails()
        } catch (error) {
            console.error("Failed to add guest", error)
            alert("Failed to add guest")
        } finally {
            setIsLoadingAction(false)
        }
    }

    const handleOpenAddMember = async () => {
        if (!meeting?.twg?.id) return
        setIsAddingMember(true)
        setSelectedMembers([])
        try {
            const res = await twgs.listMembers(meeting.twg.id)
            const existingUserIds = new Set(
                (meeting.participants || [])
                    .filter((p: any) => p.user_id || p.user?.id)
                    .map((p: any) => p.user_id || p.user?.id)
            )
            const available = (res.data || []).filter((m: any) => !existingUserIds.has(m.id))
            setTwgMembers(available)
        } catch (error) {
            console.error("Failed to load TWG members", error)
            setTwgMembers([])
        }
    }

    const handleAddSelectedMembers = async () => {
        if (!meetingId || selectedMembers.length === 0) return
        setIsLoadingAction(true)
        try {
            await meetings.addParticipants(
                meetingId,
                selectedMembers.map(uid => ({ user_id: uid })),
                applyToSeries
            )
            setIsAddingMember(false)
            setSelectedMembers([])
            setTwgMembers([])
            setApplyToSeries(false)
            await loadMeetingDetails()
        } catch (error) {
            console.error("Failed to add members", error)
            alert("Failed to add members")
        } finally {
            setIsLoadingAction(false)
        }
    }

    const handleRemoveParticipant = async (participantId: string) => {
        if (!meetingId) return
        let removeFromSeries = false
        if (meeting?.recurring_meeting_id) {
            removeFromSeries = window.confirm('Remove this participant from all future meetings in this series?')
        }
        try {
            await meetings.removeParticipant(meetingId, participantId, removeFromSeries)
            await loadMeetingDetails()
        } catch (error) {
            console.error("Failed to remove participant", error)
            alert("Failed to remove participant")
        }
    }

    // Parse bulk guest input - supports formats:
    // - email@example.com
    // - Name <email@example.com>
    // - Name, email@example.com
    // - One per line or comma/semicolon separated
    const parseBulkGuests = (text: string): Array<{ name?: string; email: string }> => {
        const guests: Array<{ name?: string; email: string }> = []

        // Split by newlines, commas, or semicolons
        const lines = text.split(/[\n,;]+/).map(l => l.trim()).filter(l => l)

        for (const line of lines) {
            // Try "Name <email>" format
            const angleMatch = line.match(/(.+?)\s*<([^>]+)>/)
            if (angleMatch) {
                guests.push({
                    name: angleMatch[1].trim(),
                    email: angleMatch[2].trim()
                })
                continue
            }

            // Just an email
            const emailMatch = line.match(/[\w.-]+@[\w.-]+\.\w+/)
            if (emailMatch) {
                guests.push({ email: emailMatch[0] })
            }
        }

        return guests
    }

    const handleBulkAddGuests = async () => {
        if (!meetingId || !bulkGuestsText.trim()) return

        const guests = parseBulkGuests(bulkGuestsText)
        if (guests.length === 0) {
            alert('No valid email addresses found')
            return
        }

        setIsLoadingAction(true)
        try {
            await meetings.addParticipants(meetingId, guests, applyToSeries)
            setBulkGuestsText('')
            setIsAddingGuest(false)
            setIsBulkMode(false)
            setApplyToSeries(false)
            await loadMeetingDetails()
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: 'Guests Added',
                message: `Successfully added ${guests.length} guest${guests.length > 1 ? 's' : ''} to the meeting.`
            })
        } catch (error) {
            console.error("Failed to add guests", error)
            alert("Failed to add guests")
        } finally {
            setIsLoadingAction(false)
        }
    }

    const handleSendInvites = async () => {
        if (!meetingId || isSendingInvites || isCheckingConflicts) return

        // Step 1: Run conflict check first
        setIsCheckingConflicts(true)
        try {
            const conflictRes = await meetings.conflictCheck(meetingId)
            const conflicts = conflictRes.data.conflicts || []

            if (conflicts.length > 0) {
                // Show custom conflict modal
                setDetectedConflicts(conflicts)
                setShowConflictModal(true)
                setIsCheckingConflicts(false)
                return
            }
        } catch (error: any) {
            console.error("Conflict check failed", error)
            // If conflict check fails, proceed anyway
        }
        setIsCheckingConflicts(false)

        // No conflicts - show HITL preview modal instead of sending directly
        setShowInvitePreviewModal(true)
    }

    const proceedWithSendingInvites = async () => {
        if (!meetingId) return
        setShowConflictModal(false)
        // After conflict resolution, also show HITL preview
        setShowInvitePreviewModal(true)
    }

    const handleApproveAndSend = async () => {
        if (!meetingId) return
        setIsSendingInvites(true)
        try {
            await meetings.approveInvite(meetingId)
            setShowInvitePreviewModal(false)
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: 'Invitations Sent',
                message: 'Meeting invitations have been sent to all participants.'
            })
            await loadMeetingDetails()
        } catch (error: any) {
            console.error("Failed to send invites", error)
            setStatusModal({
                isOpen: true,
                type: 'error',
                title: 'Failed to Send',
                message: error?.response?.data?.detail || 'Failed to send invitations. Please try again.'
            })
        } finally {
            setIsSendingInvites(false)
        }
    }

    const handleSyncCalendar = async () => {
        if (!meetingId) return
        const recipientCount = meeting?.participants?.length || 0
        if (!window.confirm(
            `Sync this meeting to Google Calendar for ${recipientCount} participant(s)?\n\n` +
            `This sends a real Google Calendar invite/notification to every attendee. ` +
            `This action is recorded in the audit log.`
        )) return
        setIsSyncingCalendar(true)
        try {
            const res = await meetings.syncCalendar(meetingId)
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: 'Calendar Synced',
                message: `Meeting ${res.data.status === 'created' ? 'added to' : 'updated on'} Google Calendar for ${res.data.attendees} participants.`
            })
            await loadMeetingDetails()
        } catch (error: any) {
            setStatusModal({
                isOpen: true,
                type: 'error',
                title: 'Calendar Sync Failed',
                message: error?.response?.data?.detail || 'Failed to sync to calendar.'
            })
        } finally {
            setIsSyncingCalendar(false)
        }
    }

    const handleConflictCancel = () => {
        setShowConflictModal(false)
        setDetectedConflicts([])
    }

    const handleCancelMeeting = () => setShowCancelModal(true)

    const confirmCancelMeeting = async (reason: string) => {
        if (!meetingId) return
        setIsLoadingAction(true)
        try {
            await meetings.cancel(meetingId, reason)
            setShowCancelModal(false)
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: 'Meeting Cancelled',
                message: 'The meeting has been cancelled and all participants have been notified via email.'
            })
            await loadMeetingDetails()
        } catch (error: any) {
            console.error("Failed to cancel meeting", error)
            setStatusModal({
                isOpen: true,
                type: 'error',
                title: 'Cancellation Failed',
                message: error?.response?.data?.detail || 'An unexpected error occurred while cancelling the meeting.'
            })
        } finally {
            setIsLoadingAction(false)
        }
    }

    const handleNotifyUpdate = () => setShowUpdateModal(true)

    const confirmNotifyUpdate = async (changeSummary: string) => {
        if (!meetingId) return
        setIsLoadingAction(true)
        try {
            await meetings.notifyUpdate(meetingId, [changeSummary])
            setShowUpdateModal(false)
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: 'Update Sent',
                message: 'Update notifications have been sent to all participants with the new meeting details.'
            })
        } catch (error: any) {
            console.error("Failed to send update", error)
            setStatusModal({
                isOpen: true,
                type: 'error',
                title: 'Update Failed',
                message: error?.response?.data?.detail || 'Failed to send update notifications. Please try again.'
            })
        } finally {
            setIsLoadingAction(false)
        }
    }

    // Action Item Handlers
    const handleActionClick = (action: any) => {
        setSelectedAction(action)
        setSelectedDescription(action.description)
        setSelectedOwner(action.owner?.name || action.owner || '')
        setSelectedDueDate(action.due_date ? action.due_date.split('T')[0] : '')
        setIsEditingSelected(false)
    }

    const handleDeleteAction = async () => {
        if (!selectedAction) return
        if (!confirm('Are you sure you want to delete this action item?')) return

        try {
            setIsLoadingAction(true)
            await actionItems.delete(selectedAction.id)
            const res = await meetings.getActionItems(meetingId!)
            setMeetingActionItems(res.data)
            setSelectedAction(null)
            setStatusModal({ isOpen: true, type: 'success', title: 'Deleted', message: 'Action item deleted' })
        } catch (error) {
            console.error(error)
            setStatusModal({ isOpen: true, type: 'error', title: 'Error', message: 'Failed to delete action item' })
        } finally {
            setIsLoadingAction(false)
        }
    }

    const handleUpdateAction = async () => {
        if (!selectedAction) return

        try {
            setIsLoadingAction(true)
            await actionItems.update(selectedAction.id, {
                description: selectedDescription,
                owner: selectedOwner || null,
                due_date: selectedDueDate || null
            })
            const res = await meetings.getActionItems(meetingId!)
            setMeetingActionItems(res.data)
            setSelectedAction(null)
            setStatusModal({ isOpen: true, type: 'success', title: 'Updated', message: 'Action item updated' })
        } catch (error) {
            console.error(error)
            setStatusModal({ isOpen: true, type: 'error', title: 'Error', message: 'Failed to update action item' })
        } finally {
            setIsLoadingAction(false)
        }
    }



    const handleUpdateRsvp = async (participantId: string, status: string) => {
        if (!meetingId) return;
        try {
            await meetings.updateRsvp(meetingId, participantId, status)
            await loadMeetingDetails()
        } catch (error) {
            console.error("Failed to update RSVP", error)
            alert("Failed to update RSVP")
        }
    }

    const handleAddAction = async () => {
        if (!meetingId || !newActionDescription) return;
        try {
            await meetings.createActionItem(meetingId, {
                description: newActionDescription,
                owner_id: newActionOwner || null,
                due_date: newActionDueDate || null,
                status: 'pending'
            })
            setNewActionDescription('')
            setNewActionOwner('')
            setNewActionDueDate('')
            setIsAddingAction(false)
            await loadMeetingDetails()
        } catch (error) {
            console.error("Failed to add action", error)
            alert("Failed to add action item")
        }
    }

    const handleUpdateMeeting = async () => {
        if (!meetingId) return;
        try {
            // Convert local datetime-local value to UTC ISO string (same as create form)
            const scheduledAtUTC = editDate ? new Date(editDate).toISOString() : undefined;
            await meetings.update(meetingId, {
                title: editTitle,
                scheduled_at: scheduledAtUTC,
                location: editLocation
            })
            setIsEditingMeeting(false)
            await loadMeetingDetails()
            // Prompt user to notify participants about the changes
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: 'Meeting Updated',
                message: 'Changes saved. Would you like to notify participants? They will receive an updated calendar invite via email.',
                actionText: 'Notify Participants',
                onAction: () => {
                    setStatusModal(prev => ({ ...prev, isOpen: false }))
                    setShowUpdateModal(true)
                }
            })
        } catch (error) {
            console.error("Failed to update meeting", error)
            setStatusModal({
                isOpen: true,
                type: 'error',
                title: 'Update Failed',
                message: 'Failed to update meeting. Please try again.'
            })
        }
    }

    const openEditModal = () => {
        setEditTitle(meeting?.title || '')
        setEditDate(meeting?.scheduled_at ? toLocalInputValue(meeting.scheduled_at) : '')
        setEditLocation(meeting?.location || '')
        setIsEditingMeeting(true)
    }

    const openManageSeriesModal = async () => {
        if (!meeting?.recurring_meeting_id) return
        setShowManageSeriesModal(true)
        setSeriesLoading(true)
        setSeriesEditMode(false)
        try {
            const res = await recurringMeetings.get(meeting.recurring_meeting_id)
            setSeriesData(res.data)
            setSeriesTitle(res.data.title_template || '')
            setSeriesTime(res.data.start_time || '')
            setSeriesDuration(res.data.duration_minutes || 60)
            setSeriesLocation(res.data.location || '')
        } catch (error) {
            console.error("Failed to load series data", error)
            setStatusModal({ isOpen: true, type: 'error', title: 'Error', message: 'Failed to load recurring series details.' })
            setShowManageSeriesModal(false)
        } finally {
            setSeriesLoading(false)
        }
    }

    const handleUpdateSeries = async () => {
        if (!seriesData) return
        setSeriesActionLoading(true)
        try {
            const payload: any = { update_scope: seriesUpdateScope }
            if (seriesTitle !== seriesData.title_template) payload.title_template = seriesTitle
            if (seriesTime !== seriesData.start_time) payload.start_time = seriesTime
            if (seriesDuration !== seriesData.duration_minutes) payload.duration_minutes = seriesDuration
            if (seriesLocation !== (seriesData.location || '')) payload.location = seriesLocation

            const res = await recurringMeetings.update(seriesData.id, payload)
            setSeriesData(res.data)
            setSeriesEditMode(false)
            setStatusModal({ isOpen: true, type: 'success', title: 'Series Updated', message: 'Recurring series has been updated.' })
            await loadMeetingDetails()
        } catch (error: any) {
            console.error("Failed to update series", error)
            setStatusModal({ isOpen: true, type: 'error', title: 'Update Failed', message: error?.response?.data?.detail || 'Failed to update series.' })
        } finally {
            setSeriesActionLoading(false)
        }
    }

    const handleTogglePauseSeries = async () => {
        if (!seriesData) return
        setSeriesActionLoading(true)
        try {
            const isPaused = seriesData.status === 'paused'
            const res = isPaused
                ? await recurringMeetings.resume(seriesData.id)
                : await recurringMeetings.pause(seriesData.id)
            setSeriesData(res.data)
            setStatusModal({
                isOpen: true,
                type: 'success',
                title: isPaused ? 'Series Resumed' : 'Series Paused',
                message: isPaused ? 'New instances will be generated again.' : 'No new instances will be generated until resumed.'
            })
        } catch (error: any) {
            console.error("Failed to toggle pause", error)
            setStatusModal({ isOpen: true, type: 'error', title: 'Error', message: error?.response?.data?.detail || 'Failed to update series status.' })
        } finally {
            setSeriesActionLoading(false)
        }
    }

    const handleCancelSeries = async (_reason: string) => {
        if (!seriesData) return
        setSeriesActionLoading(true)
        try {
            await recurringMeetings.delete(seriesData.id, true)
            setShowCancelSeriesConfirm(false)
            setShowManageSeriesModal(false)
            setStatusModal({ isOpen: true, type: 'success', title: 'Series Cancelled', message: 'The recurring series and all future instances have been cancelled.' })
            await loadMeetingDetails()
        } catch (error: any) {
            console.error("Failed to cancel series", error)
            setStatusModal({ isOpen: true, type: 'error', title: 'Error', message: error?.response?.data?.detail || 'Failed to cancel series.' })
        } finally {
            setSeriesActionLoading(false)
        }
    }

    const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!meetingId || !e.target.files || e.target.files.length === 0) return;

        const file = e.target.files[0];
        const formData = new FormData();
        formData.append('file', file);

        setIsUploadingDoc(true);

        try {
            await meetings.uploadDocument(meetingId, formData);
            await loadMeetingDetails();
            // Reset file input
            e.target.value = '';
        } catch (error) {
            console.error("Failed to upload document", error);
            alert("Failed to upload document");
        } finally {
            setIsUploadingDoc(false);
        }
    }

    const handleDownloadDocument = async (docId: string) => {
        const { API_URL } = await import('../../services/api');
        const downloadUrl = `${API_URL}/meetings/documents/${docId}/download`;
        window.open(downloadUrl, '_blank');
    }

    const handleDeleteDocument = async (docId: string) => {
        if (!confirm('Are you sure you want to delete this document?')) return;

        try {
            const { API_URL } = await import('../../services/api');
            await fetch(`${API_URL}/meetings/documents/${docId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            await loadMeetingDetails();
        } catch (error) {
            console.error("Failed to delete document", error);
            alert("Failed to delete document");
        }
    }

    if (!meeting && !loading) return null

    return (
        <>
            <div className="flex flex-col h-full">

                {/* Conflict Warning Modal */}
                <ConflictModal
                    isOpen={showConflictModal}
                    conflicts={detectedConflicts}
                    onProceed={proceedWithSendingInvites}
                    onCancel={handleConflictCancel}
                />
                {/* Cancel Meeting Modal */}
                <InputModal
                    isOpen={showCancelModal}
                    title="Cancel Meeting"
                    description="Are you sure you want to cancel this meeting? This will send a cancellation email to all participants. This action cannot be undone."
                    placeholder="Reason for cancellation (optional)..."
                    confirmText="Cancel Meeting"
                    confirmVariant="danger"
                    icon="🚫"
                    isLoading={isLoadingAction}
                    onConfirm={confirmCancelMeeting}
                    onCancel={() => setShowCancelModal(false)}
                />
                {/* Update Notification Modal */}
                <InputModal
                    isOpen={showUpdateModal}
                    title="Send Update"
                    description="Notify participants about changes to this meeting. An updated calendar invite will be sent."
                    placeholder="Briefly summarize changes (e.g. 'Time changed to 2 PM')..."
                    confirmText="Send Update"
                    confirmVariant="warning"
                    icon="📢"
                    isLoading={isLoadingAction}
                    onConfirm={confirmNotifyUpdate}
                    onCancel={() => setShowUpdateModal(false)}
                />
                {/* Success/Error Status Modal */}
                <StatusModal
                    isOpen={statusModal.isOpen}
                    type={statusModal.type}
                    title={statusModal.title}
                    message={statusModal.message}
                    onClose={() => setStatusModal(prev => ({ ...prev, isOpen: false, actionText: undefined, onAction: undefined }))}
                    actionText={statusModal.actionText}
                    onAction={statusModal.onAction}
                />
                {/* HITL Invite Preview Modal */}
                <InvitePreviewModal
                    isOpen={showInvitePreviewModal}
                    meetingId={meetingId || ''}
                    onClose={() => setShowInvitePreviewModal(false)}
                    onApprove={handleApproveAndSend}
                    isApproving={isSendingInvites}
                />

                {/* Reject Minutes Modal */}
                {showRejectModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                                <span className="text-2xl">❌</span> Reject Minutes
                            </h3>
                            <p className="text-sm text-slate-500 mb-4">
                                Please provide a reason for rejection. The facilitator will be notified and the minutes will be sent back for revision.
                            </p>
                            <textarea
                                className="w-full h-32 p-4 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 outline-none resize-none"
                                placeholder="Reason for rejection..."
                                value={rejectReason}
                                onChange={(e) => setRejectReason(e.target.value)}
                            />
                            <div className="flex justify-end gap-3 mt-4">
                                <button
                                    onClick={() => {
                                        setShowRejectModal(false)
                                        setRejectReason('')
                                    }}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleRejectMinutes}
                                    disabled={!rejectReason.trim() || isRejectingMinutes}
                                    className="btn-primary bg-red-600 hover:bg-red-700 border-red-600 disabled:opacity-50"
                                >
                                    {isRejectingMinutes ? '⏳ Rejecting...' : 'Confirm Rejection'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Header — editorial */}
                <div style={{
                    padding: '24px 32px 20px',
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--surface)',
                    fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
                        <button
                            onClick={() => navigate(-1)}
                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--ink-500)', padding: 0, display: 'inline-flex', alignItems: 'center' }}
                            title="Back"
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_back</span>
                        </button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--ink-500)' }}>
                            <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', letterSpacing: 'inherit', textTransform: 'inherit' }}>Home</button>
                            <span style={{ color: 'var(--ink-300)' }}>·</span>
                            {location.state?.from === 'schedule' || location.pathname.includes('/schedule') ? (
                                <>
                                    <button onClick={() => navigate('/schedule')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', letterSpacing: 'inherit', textTransform: 'inherit' }}>Schedule</button>
                                    <span style={{ color: 'var(--ink-300)' }}>·</span>
                                    <button onClick={() => navigate('/schedule')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', letterSpacing: 'inherit', textTransform: 'inherit' }}>
                                        {loading ? '—' : meeting?.twg?.name || 'Unknown TWG'}
                                    </button>
                                </>
                            ) : (
                                <>
                                    <button onClick={() => navigate(`/workspace/${meeting?.twg_id}`)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', letterSpacing: 'inherit', textTransform: 'inherit' }}>
                                        {loading ? '—' : meeting?.twg?.name || 'Unknown TWG'}
                                    </button>
                                    <span style={{ color: 'var(--ink-300)' }}>·</span>
                                    <button onClick={() => navigate(`/workspace/${meeting?.twg_id}`)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', letterSpacing: 'inherit', textTransform: 'inherit' }}>Meeting history</button>
                                </>
                            )}
                            <span style={{ color: 'var(--ink-300)' }}>·</span>
                            <span style={{ color: 'var(--ink-700)', fontFamily: "'Geist Mono', monospace", letterSpacing: '0.05em' }}>#{meetingId?.slice(0, 6)}</span>
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <h1 style={{
                                fontFamily: "'Source Serif 4', serif", fontWeight: 400,
                                fontSize: 32, letterSpacing: '-0.02em', color: 'var(--ink-900)',
                                margin: 0, lineHeight: 1.15, maxWidth: 820,
                            }}>{meeting?.title}</h1>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 10, flexWrap: 'wrap' }}>
                                {meeting?.status && (
                                    <span style={{
                                        fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600,
                                        color: ['COMPLETED', 'completed'].includes(meeting.status) ? 'var(--sage)' : 'var(--accent)',
                                        display: 'inline-flex', alignItems: 'center', gap: 6,
                                    }}>
                                        <span style={{ width: 6, height: 6, borderRadius: 6, background: 'currentColor', display: 'inline-block' }} />
                                        {String(meeting.status).replace(/_/g, ' ')}
                                    </span>
                                )}
                                {meeting?.recurring_meeting_id && (
                                    <span style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, color: 'var(--accent)', opacity: 0.85 }}>
                                        Recurring series
                                    </span>
                                )}
                                <span style={{ fontSize: 11, color: 'var(--ink-500)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--ink-400)' }}>description</span>
                                    {minutesStatus === 'APPROVED' ? 'Minutes approved' :
                                        minutesStatus === 'PENDING_APPROVAL' ? 'Minutes pending approval' :
                                            minutesStatus === 'REVIEW' ? 'Minutes need revision' :
                                                minutesContent ? 'Minutes in draft' : 'Minutes not started'}
                                </span>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: 8, flexShrink: 0, flexWrap: 'wrap' }}>
                            {['scheduled', 'SCHEDULED'].includes(meeting?.status) && (
                                <>
                                    <button onClick={handleNotifyUpdate} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--amber)', color: 'var(--amber)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>notifications</span>
                                        Send update
                                    </button>
                                    <button onClick={handleCancelMeeting} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--terra)', color: 'var(--terra)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>close</span>
                                        Cancel
                                    </button>
                                </>
                            )}
                            <button onClick={openEditModal} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>edit</span>
                                Edit meeting
                            </button>
                            {meeting?.recurring_meeting_id && (
                                <button onClick={openManageSeriesModal} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>autorenew</span>
                                    Manage series
                                </button>
                            )}
                            {meeting?.video_link && (
                                <button
                                    onClick={() => window.open(meeting.video_link.startsWith('http') ? meeting.video_link : `https://${meeting.video_link}`, '_blank')}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>videocam</span>
                                    Join
                                </button>
                            )}
                            {['in_progress', 'IN_PROGRESS'].includes(meeting?.status) && (
                                <button
                                    onClick={() => navigate(`/meetings/${meetingId}/live`)}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--terra)', color: 'var(--terra)', padding: '7px 14px', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', cursor: 'pointer', fontFamily: 'inherit' }}
                                >
                                    <span style={{ width: 6, height: 6, borderRadius: 6, background: 'var(--terra)', display: 'inline-block' }} className="animate-pulse" />
                                    LIVE
                                </button>
                            )}
                            {minutesStatus === 'PENDING_APPROVAL' && (
                                <button onClick={handleApproveMinutes} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>check_circle</span>
                                    Approve &amp; send
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Version History Modal */}
                <MinutesVersionHistory
                    meetingId={meetingId!}
                    isOpen={showVersionHistory}
                    onClose={() => setShowVersionHistory(false)}
                    onRestore={async () => {
                        // Refresh minutes after restore
                        try {
                            const minutesRes = await meetings.getMinutes(meetingId!)
                            setMinutesContent(minutesRes.data.content || '')
                            setMinutesStatus(minutesRes.data.status || 'DRAFT')
                        } catch (error) {
                            console.error('Failed to refresh minutes', error)
                        }
                    }}
                />

                {/* Ledger strip — at-a-glance meeting facts */}
                {meeting && (() => {
                    const dateStr = meeting.scheduled_at?.endsWith?.('Z') ? meeting.scheduled_at : `${meeting.scheduled_at}Z`
                    const d = meeting.scheduled_at ? new Date(dateStr) : null
                    const dateLabel = meeting.scheduled_at ? formatMeetingDate(meeting.scheduled_at) : '—'
                    const timeLabel = meeting.scheduled_at ? formatMeetingTime(meeting.scheduled_at) : '—'
                    const partTotal = meeting.participants?.length ?? 0
                    const partAccepted = meeting.participants?.filter((p: any) => p.rsvp_status === 'accepted').length ?? 0
                    const docsCount = meeting.documents?.length ?? 0
                    const minutesLabel = minutesStatus === 'APPROVED' ? 'Approved' : minutesStatus === 'PENDING_APPROVAL' ? 'Pending approval' : minutesStatus === 'REVIEW' ? 'Needs revision' : minutesContent ? 'Draft' : 'Not started'
                    const minutesAccent = minutesStatus === 'APPROVED' ? 'var(--sage)' : minutesStatus === 'PENDING_APPROVAL' ? 'var(--amber)' : minutesStatus === 'REVIEW' ? 'var(--terra)' : 'var(--ink-900)'

                    const ledgerCell = (label: string, value: React.ReactNode, sub: string, last = false, color?: string): JSX.Element => (
                        <div style={{ paddingRight: 24, borderRight: last ? 'none' : '1px solid var(--border)' }}>
                            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500 }}>{label}</div>
                            <div style={{
                                fontFamily: "'Source Serif 4', serif", fontWeight: 400, fontSize: 24,
                                color: color || 'var(--ink-900)', letterSpacing: '-0.02em',
                                marginTop: 4, lineHeight: 1.05, fontVariantNumeric: 'tabular-nums',
                            }}>{value}</div>
                            <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 6 }}>{sub}</div>
                        </div>
                    )

                    return (
                        <div
                            className="kpi-strip"
                            style={{
                                background: 'var(--surface)', borderBottom: '1px solid var(--border)',
                                fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                            }}
                        >
                            {ledgerCell('Date', dateLabel, d ? d.toLocaleDateString('en-US', { weekday: 'long' }) : 'unscheduled')}
                            {ledgerCell('Time', timeLabel, `${meeting.duration_minutes ?? '—'}m · ${meeting.location || 'Virtual'}`)}
                            {ledgerCell('Participants', partTotal, partTotal ? `${partAccepted} accepted` : 'none yet')}
                            {ledgerCell('Minutes', minutesLabel, docsCount ? `${docsCount} attachment${docsCount === 1 ? '' : 's'}` : 'no attachments', true, minutesAccent)}
                        </div>
                    )
                })()}

                {/* Tabs — editorial underline */}
                <div style={{
                    display: 'flex', gap: 0, padding: '0 32px',
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--surface)',
                    overflowX: 'auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                }}>
                    {[
                        { id: 'agenda', label: 'Agenda' },
                        { id: 'minutes', label: 'Minutes' },
                        { id: 'participants', label: 'Participants' },
                        { id: 'documents', label: 'Documents' },
                        { id: 'schedule', label: 'Schedule' }
                    ].map(tab => {
                        const on = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as TabType)}
                                style={{
                                    background: 'transparent', border: 'none', cursor: 'pointer',
                                    padding: '14px 18px', fontSize: 12, fontWeight: on ? 500 : 400,
                                    color: on ? 'var(--ink-900)' : 'var(--ink-500)',
                                    borderBottom: on ? '2px solid var(--accent)' : '2px solid transparent',
                                    marginBottom: -1, whiteSpace: 'nowrap',
                                    fontFamily: 'inherit',
                                }}
                            >
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                {/* Content — single column, full width */}
                <div className="flex-1 overflow-y-auto">
                    <div style={{ padding: '32px', maxWidth: 1180, margin: '0 auto' }}>
                            {loading ? (
                                <div className="flex justify-center py-20">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                </div>
                            ) : (
                                <>
                                    {/* AGENDA TAB */}
                                    {activeTab === 'agenda' && (
                                        <div className="max-w-4xl space-y-6">
                                            <div className="flex justify-between items-center">
                                                <h2 className="text-xl font-bold text-slate-900 dark:text-white">Meeting Agenda</h2>
                                                <div className="flex gap-2">
                                                    {!isEditingAgenda ? (
                                                        <button onClick={() => setIsEditingAgenda(true)} className="btn-secondary text-sm">
                                                            Edit Agenda
                                                        </button>
                                                    ) : (
                                                        <>
                                                            <button onClick={() => setIsEditingAgenda(false)} className="btn-secondary text-sm">Cancel</button>
                                                            <button onClick={handleSaveAgenda} className="btn-primary text-sm">Save</button>
                                                        </>
                                                    )}
                                                </div>
                                            </div>

                                            {isEditingAgenda ? (
                                                <textarea
                                                    className="w-full h-96 p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm"
                                                    value={agendaContent}
                                                    onChange={(e) => setAgendaContent(e.target.value)}
                                                    placeholder="Enter meeting agenda..."
                                                />
                                            ) : (
                                                <Card className="p-6">
                                                    {agendaContent ? (
                                                        <div className="prose prose-slate dark:prose-invert max-w-none">
                                                            <ReactMarkdown
                                                                remarkPlugins={[remarkGfm]}
                                                                components={{
                                                                    h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-4" {...props} />,
                                                                    h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200 mt-6 mb-3" {...props} />,
                                                                    h3: ({ node, ...props }) => <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mt-4 mb-2" {...props} />,
                                                                    ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-1" {...props} />,
                                                                    ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-1" {...props} />,
                                                                    li: ({ node, ...props }) => <li className="text-slate-600 dark:text-slate-400" {...props} />,
                                                                    p: ({ node, ...props }) => <p className="mb-3 text-slate-600 dark:text-slate-400" {...props} />,
                                                                    strong: ({ node, ...props }) => <strong className="font-bold text-slate-800 dark:text-slate-200" {...props} />,
                                                                    table: ({ node, ...props }) => <table className="min-w-full border-collapse border border-slate-200 dark:border-slate-700 my-4" {...props} />,
                                                                    th: ({ node, ...props }) => <th className="border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 px-4 py-2 text-left font-bold" {...props} />,
                                                                    td: ({ node, ...props }) => <td className="border border-slate-200 dark:border-slate-700 px-4 py-2" {...props} />,
                                                                }}
                                                            >
                                                                {agendaContent}
                                                            </ReactMarkdown>
                                                        </div>
                                                    ) : (
                                                        <div className="text-slate-400 italic text-center py-10">No agenda has been set for this meeting.</div>
                                                    )}
                                                </Card>
                                            )}
                                        </div>
                                    )}

                                    {/* MINUTES & DECISIONS TAB */}
                                    {activeTab === 'minutes' && (
                                        <div className="max-w-4xl space-y-6">
                                            {/* Transcript Input - Only show if NOT approved */}
                                            {minutesStatus !== 'approved' && minutesStatus !== 'APPROVED' && (
                                                <Card className={`transition-all duration-300 ${isTranscriptExpanded ? 'p-6' : 'p-4'} border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm`}>
                                                    <div className="flex items-center justify-between mb-2">
                                                        <div className="flex items-center gap-2">
                                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${minutesContent ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'}`}>
                                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                                                                </svg>
                                                            </div>
                                                            <div>
                                                                <h3 className="font-bold text-slate-900 dark:text-white text-sm">Transcript & Notes</h3>
                                                                {!isTranscriptExpanded && <p className="text-xs text-slate-500">{transcript.length} chars / {transcript.split(/\s+/).length} words</p>}
                                                            </div>
                                                        </div>

                                                        {!isTranscriptExpanded && (
                                                            <button
                                                                onClick={() => setIsTranscriptExpanded(true)}
                                                                className="text-xs font-bold text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded transition-colors"
                                                            >
                                                                Review / Edit Source
                                                            </button>
                                                        )}
                                                        {isSavingTranscript && isTranscriptExpanded && <span className="text-xs text-blue-600 animate-pulse">Saving...</span>}
                                                    </div>

                                                    {isTranscriptExpanded && (
                                                        <div className="mt-4 animate-in fade-in slide-in-from-top-2 duration-200 space-y-4">


                                                            <textarea
                                                                className="w-full h-64 p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 font-mono text-sm leading-relaxed resize-y mb-4 transition-all"
                                                                placeholder="[Facilitator]: Welcome everyone. Today we are discussing..."
                                                                value={transcript}
                                                                onChange={(e) => setTranscript(e.target.value)}
                                                                onBlur={handleSaveTranscript}
                                                            />
                                                            <div className="flex justify-end gap-3">
                                                                {minutesContent && (
                                                                    <button
                                                                        onClick={() => setIsTranscriptExpanded(false)}
                                                                        className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900"
                                                                    >
                                                                        Cancel
                                                                    </button>
                                                                )}
                                                                <button
                                                                    onClick={async () => {
                                                                        await handleSaveTranscript();
                                                                        handleGenerateSummary();
                                                                    }}
                                                                    disabled={isGeneratingMinutes || !transcript.trim()}
                                                                    className="btn-primary flex items-center gap-2"
                                                                >
                                                                    {isGeneratingMinutes ? (
                                                                        <><span className="animate-spin">⏳</span> Processing...</>
                                                                    ) : (
                                                                        <>{minutesContent ? '🔄 Regenerate Minutes' : '✨ Generate Minutes'}</>
                                                                    )}
                                                                </button>
                                                            </div>
                                                            {!minutesContent && (
                                                                <p className="text-xs text-slate-400 mt-2 text-center">
                                                                    Paste your notes above. The AI will cross-reference them with the Knowledge Repository to draft official minutes.
                                                                </p>
                                                            )}
                                                        </div>
                                                    )}
                                                </Card>
                                            )}

                                            {minutesContent && (
                                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
                                                    {/* Minutes Content */}
                                                    <div>
                                                        <div className="flex items-center justify-between mb-4">
                                                            <div className="flex items-center gap-3">
                                                                <h2 className="text-xl font-bold text-slate-900 dark:text-white">Meeting Minutes</h2>
                                                                {/* Status Badge */}
                                                                <span className={`px-2 py-1 text-xs font-bold rounded-full ${minutesStatus === 'APPROVED' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                                                                    minutesStatus === 'PENDING_APPROVAL' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                                        minutesStatus === 'REVIEW' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                                                                            'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                                                    }`}>
                                                                    {minutesStatus === 'APPROVED' ? '✓ Approved' :
                                                                        minutesStatus === 'PENDING_APPROVAL' ? '⏳ Pending Approval' :
                                                                            minutesStatus === 'REVIEW' ? '🔄 Needs Revision' :
                                                                                '📝 Draft'}
                                                                </span>
                                                            </div>
                                                            <div className="flex gap-2">
                                                                {/* Show Submit for Approval if DRAFT or REVIEW */}
                                                                {(minutesStatus === 'DRAFT' || minutesStatus === 'REVIEW') && minutesContent && (
                                                                    <button
                                                                        onClick={handleSubmitForApproval}
                                                                        disabled={isSubmittingForApproval}
                                                                        className="btn-secondary text-sm flex items-center gap-1 disabled:opacity-50"
                                                                    >
                                                                        {isSubmittingForApproval ? '⏳ Submitting...' : '📤 Submit for Approval'}
                                                                    </button>
                                                                )}
                                                                {/* Show Approve/Reject buttons ONLY if Secretariat Lead (or Admin) */}
                                                                {minutesStatus === 'PENDING_APPROVAL' && (
                                                                    <>
                                                                        {['secretariat_lead', 'admin'].includes(user?.role || '') ? (
                                                                            <>
                                                                                <button
                                                                                    onClick={handleApproveMinutes}
                                                                                    disabled={isApprovingMinutes}
                                                                                    className="btn-primary text-sm flex items-center gap-1 disabled:opacity-50"
                                                                                >
                                                                                    {isApprovingMinutes ? '⏳ Approving...' : '✅ Approve & Send'}
                                                                                </button>
                                                                                <button
                                                                                    onClick={() => setShowRejectModal(true)}
                                                                                    className="btn-secondary text-sm flex items-center gap-1 border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                                                                                >
                                                                                    ❌ Reject
                                                                                </button>
                                                                            </>
                                                                        ) : (
                                                                            <span className="text-sm text-slate-500 italic bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-2">
                                                                                <span>📩</span> Approval Notification Sent to Secretariat
                                                                            </span>
                                                                        )}
                                                                    </>
                                                                )}
                                                                {/* Download PDF button - always available when minutes exist */}
                                                                {minutesContent && (
                                                                    <button
                                                                        onClick={handleDownloadPdf}
                                                                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                                                                        title="Download as PDF"
                                                                    >
                                                                        <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                                        </svg>
                                                                    </button>
                                                                )}
                                                                {/* Version History button */}
                                                                {minutesContent && (
                                                                    <button
                                                                        onClick={() => setShowVersionHistory(true)}
                                                                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                                                                        title="Version History"
                                                                    >
                                                                        <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                        </svg>
                                                                    </button>
                                                                )}
                                                                {/* Translate button */}
                                                                {minutesContent && (
                                                                    <div className="relative">
                                                                        <button
                                                                            onClick={() => setShowTranslateMenu(!showTranslateMenu)}
                                                                            disabled={isTranslating}
                                                                            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50"
                                                                            title="Translate Minutes"
                                                                        >
                                                                            {isTranslating ? (
                                                                                <svg className="w-5 h-5 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                                                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                                                                </svg>
                                                                            ) : (
                                                                                <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                                                                                </svg>
                                                                            )}
                                                                        </button>
                                                                        {showTranslateMenu && (
                                                                            <>
                                                                                <div className="fixed inset-0 z-10" onClick={() => setShowTranslateMenu(false)} />
                                                                                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-20 py-1 min-w-[160px]">
                                                                                    {[
                                                                                        { code: 'fr', label: 'Français (French)' },
                                                                                        { code: 'pt', label: 'Português (Portuguese)' },
                                                                                        { code: 'en', label: 'English' },
                                                                                    ].map((lang) => (
                                                                                        <button
                                                                                            key={lang.code}
                                                                                            onClick={() => handleTranslate(lang.code)}
                                                                                            className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 ${translationLanguage === lang.code ? 'text-blue-600 font-medium' : 'text-slate-700 dark:text-slate-300'}`}
                                                                                        >
                                                                                            {lang.label}
                                                                                        </button>
                                                                                    ))}
                                                                                </div>
                                                                            </>
                                                                        )}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                        {/* Translation banner */}
                                                        {translatedContent && (
                                                            <div className="flex items-center justify-between bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-2 mb-4">
                                                                <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                                                                    Viewing translation ({translationLanguage === 'fr' ? 'French' : translationLanguage === 'pt' ? 'Portuguese' : 'English'})
                                                                </span>
                                                                <button
                                                                    onClick={handleClearTranslation}
                                                                    className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 font-medium underline"
                                                                >
                                                                    Back to Original
                                                                </button>
                                                            </div>
                                                        )}
                                                        {/* Translating indicator */}
                                                        {isTranslating && (
                                                            <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-2 mb-4">
                                                                <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                                                </svg>
                                                                <span className="text-sm text-blue-700 dark:text-blue-300">Translating minutes...</span>
                                                            </div>
                                                        )}
                                                        <Card className="p-8">
                                                            <div className="prose prose-slate dark:prose-invert max-w-none">
                                                                <ReactMarkdown
                                                                    remarkPlugins={[remarkGfm]}
                                                                    components={{
                                                                        h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-4" {...props} />,
                                                                        h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200 mt-6 mb-3" {...props} />,
                                                                        h3: ({ node, ...props }) => <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mt-4 mb-2" {...props} />,
                                                                        ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-1" {...props} />,
                                                                        ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-1" {...props} />,
                                                                        li: ({ node, ...props }) => <li className="text-slate-600 dark:text-slate-400" {...props} />,
                                                                        p: ({ node, ...props }) => <p className="mb-3 text-slate-600 dark:text-slate-400" {...props} />,
                                                                        strong: ({ node, ...props }) => <strong className="font-bold text-slate-800 dark:text-slate-200" {...props} />,
                                                                        table: ({ node, ...props }) => <table className="min-w-full border-collapse border border-slate-200 dark:border-slate-700 my-4" {...props} />,
                                                                        th: ({ node, ...props }) => <th className="border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 px-4 py-2 text-left font-bold" {...props} />,
                                                                        td: ({ node, ...props }) => <td className="border border-slate-200 dark:border-slate-700 px-4 py-2" {...props} />,
                                                                    }}
                                                                >
                                                                    {translatedContent || minutesContent}
                                                                </ReactMarkdown>
                                                            </div>
                                                        </Card>
                                                    </div>

                                                    {/* Action Items */}
                                                    <div>
                                                        <div className="flex items-center justify-between mb-4">
                                                            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Action Items</h2>
                                                            {isFacilitator && (
                                                            <div className="flex gap-2">

                                                                {minutesContent && (
                                                                    <button
                                                                        onClick={async () => {
                                                                            try {
                                                                                setExtractingActions(true)
                                                                                const res = await meetings.extractActionItems(meetingId!)
                                                                                const data = res.data || {}
                                                                                const created = data.created_items?.filter((i: any) => i.created) || []
                                                                                const total = data.extracted_actions?.length || 0
                                                                                const actionsRes = await meetings.getActionItems(meetingId!)
                                                                                setMeetingActionItems(actionsRes.data || [])
                                                                                const msg = created.length > 0
                                                                                    ? `Created ${created.length} action item${created.length !== 1 ? 's' : ''}${total > created.length ? ` (${total - created.length} duplicates skipped)` : ''}.`
                                                                                    : total > 0
                                                                                        ? `All ${total} extracted items already exist for this meeting.`
                                                                                        : 'No action items found in the minutes.'
                                                                                setStatusModal({ isOpen: true, type: created.length > 0 ? 'success' : 'info', title: 'Actions Extracted', message: msg })
                                                                            } catch (error: any) {
                                                                                console.error(error)
                                                                                setStatusModal({ isOpen: true, type: 'error', title: 'Extraction Failed', message: error?.response?.data?.detail || 'Failed to extract action items.' })
                                                                            } finally {
                                                                                setExtractingActions(false)
                                                                            }
                                                                        }}
                                                                        disabled={extractingActions}
                                                                        className="btn-secondary text-sm flex items-center gap-2"
                                                                    >
                                                                        {extractingActions ? (
                                                                            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                                                            </svg>
                                                                        ) : (
                                                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                                            </svg>
                                                                        )}
                                                                        {extractingActions ? 'Extracting...' : 'Extract Actions'}
                                                                    </button>
                                                                )}
                                                                <button onClick={() => setIsAddingAction(true)} className="btn-secondary text-sm flex items-center gap-2">
                                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                                                    </svg>
                                                                    Add Action
                                                                </button>
                                                            </div>
                                                            )}
                                                        </div>

                                                        {/* Add Action Form */}
                                                        {isAddingAction && (
                                                            <Card className="p-4 mb-4 bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
                                                                <h4 className="font-bold text-sm mb-3 text-blue-900 dark:text-blue-100">Create New Action Item</h4>
                                                                <div className="space-y-3">
                                                                    <div>
                                                                        <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Description *</label>
                                                                        <textarea
                                                                            className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm"
                                                                            placeholder="What needs to be done?"
                                                                            rows={2}
                                                                            value={newActionDescription}
                                                                            onChange={e => setNewActionDescription(e.target.value)}
                                                                        />
                                                                    </div>
                                                                    <div className="grid grid-cols-2 gap-3">
                                                                        <div>
                                                                            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Owner (Optional)</label>
                                                                            <input
                                                                                type="text"
                                                                                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm"
                                                                                placeholder="User ID"
                                                                                value={newActionOwner}
                                                                                onChange={e => setNewActionOwner(e.target.value)}
                                                                            />
                                                                        </div>
                                                                        <div>
                                                                            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Due Date (Optional)</label>
                                                                            <input
                                                                                type="date"
                                                                                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm"
                                                                                value={newActionDueDate}
                                                                                onChange={e => setNewActionDueDate(e.target.value)}
                                                                            />
                                                                        </div>
                                                                    </div>
                                                                    <div className="flex gap-2 justify-end">
                                                                        <button
                                                                            onClick={() => {
                                                                                setIsAddingAction(false)
                                                                                setNewActionDescription('')
                                                                                setNewActionOwner('')
                                                                                setNewActionDueDate('')
                                                                            }}
                                                                            className="btn-secondary text-sm"
                                                                        >
                                                                            Cancel
                                                                        </button>
                                                                        <button
                                                                            onClick={handleAddAction}
                                                                            disabled={!newActionDescription}
                                                                            className="btn-primary text-sm"
                                                                        >
                                                                            Create Action
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </Card>
                                                        )}

                                                        <div className="space-y-3">
                                                            {meetingActionItems.map(item => (
                                                                <Card
                                                                    key={item.id}
                                                                    className="p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                                                    onClick={() => handleActionClick(item)}
                                                                >
                                                                    <div className="flex items-center gap-4">
                                                                        <input type="checkbox" className="w-5 h-5 rounded border-slate-300" />
                                                                        <div className="flex-1">
                                                                            <div className="font-bold text-slate-900 dark:text-white">{item.description}</div>
                                                                        </div>
                                                                        <div className="flex items-center gap-3">
                                                                            <div className="flex items-center gap-2">
                                                                                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                                                                                    {item.owner?.avatar || 'U'}
                                                                                </div>
                                                                                <span className="text-sm text-slate-600 dark:text-slate-400">{item.owner?.name || 'Unassigned'}</span>
                                                                            </div>
                                                                            <span className="text-sm text-slate-500">{item.dueDate}</span>
                                                                            <Badge variant={item.status === 'pending' ? 'warning' : 'info'} className="text-xs">
                                                                                {item.status === 'pending' ? 'Pending' : 'In Progress'}
                                                                            </Badge>
                                                                        </div>
                                                                    </div>
                                                                </Card>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* PARTICIPANTS TAB */}
                                    {activeTab === 'participants' && (
                                        <div className="max-w-4xl space-y-6">
                                            <div className="flex justify-between items-center">
                                                <h2 className="text-xl font-bold text-slate-900 dark:text-white">Participant List</h2>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={handleSendInvites}
                                                        disabled={!meeting?.participants?.length || isSendingInvites || isCheckingConflicts}
                                                        className="btn-primary text-sm flex items-center gap-1 disabled:opacity-50"
                                                        title="Send email invitations to all participants"
                                                    >
                                                        {isCheckingConflicts ? (
                                                            <>
                                                                <span className="animate-spin">🔍</span> Checking conflicts...
                                                            </>
                                                        ) : isSendingInvites ? (
                                                            <>
                                                                <span className="animate-spin">⏳</span> Sending...
                                                            </>
                                                        ) : (
                                                            <>📧 Send Invites</>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={handleSyncCalendar}
                                                        disabled={!meeting?.participants?.length || isSyncingCalendar}
                                                        className="btn-secondary text-sm flex items-center gap-1 disabled:opacity-50"
                                                        title="Add this meeting to participants' Google Calendar (no email sent)"
                                                    >
                                                        {isSyncingCalendar ? (
                                                            <><span className="animate-spin">⏳</span> Syncing...</>
                                                        ) : (
                                                            <>📅 Sync Calendar</>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            setIsAddingGuest(!isAddingGuest)
                                                            setIsAddingMember(false)
                                                        }}
                                                        className="btn-secondary text-sm"
                                                    >
                                                        {isAddingGuest ? 'Cancel' : '+ Add Guest'}
                                                    </button>
                                                    {meeting?.twg?.id && (
                                                        <button
                                                            onClick={() => {
                                                                if (isAddingMember) {
                                                                    setIsAddingMember(false)
                                                                } else {
                                                                    setIsAddingGuest(false)
                                                                    handleOpenAddMember()
                                                                }
                                                            }}
                                                            className="btn-secondary text-sm"
                                                        >
                                                            {isAddingMember ? 'Cancel' : '+ Add Member'}
                                                        </button>
                                                    )}
                                                </div>
                                            </div>

                                            {isAddingMember && (
                                                <Card className="p-4 bg-green-50 dark:bg-green-900/10 border-green-100 dark:border-green-800">
                                                    <h4 className="font-bold text-sm text-green-900 dark:text-green-100 mb-3">Add TWG Members</h4>
                                                    {twgMembers.length === 0 ? (
                                                        <p className="text-sm text-slate-500">All TWG members are already participants.</p>
                                                    ) : (
                                                        <>
                                                            <div className="space-y-2 max-h-60 overflow-y-auto mb-3">
                                                                {twgMembers.map((m: any) => (
                                                                    <label key={m.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/20 cursor-pointer">
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={selectedMembers.includes(m.id)}
                                                                            onChange={(e) => {
                                                                                if (e.target.checked) {
                                                                                    setSelectedMembers(prev => [...prev, m.id])
                                                                                } else {
                                                                                    setSelectedMembers(prev => prev.filter(id => id !== m.id))
                                                                                }
                                                                            }}
                                                                            className="rounded border-slate-300"
                                                                        />
                                                                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xs font-bold">
                                                                            {(m.full_name || m.email || '?')[0].toUpperCase()}
                                                                        </div>
                                                                        <div>
                                                                            <div className="text-sm font-medium text-slate-900 dark:text-white">{m.full_name || 'Member'}</div>
                                                                            <div className="text-xs text-slate-500">{m.email}</div>
                                                                        </div>
                                                                    </label>
                                                                ))}
                                                            </div>
                                                            {meeting?.recurring_meeting_id && (
                                                                <label className="flex items-center gap-2 mb-2 cursor-pointer">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={applyToSeries}
                                                                        onChange={e => setApplyToSeries(e.target.checked)}
                                                                        className="rounded border-slate-300"
                                                                    />
                                                                    <span className="text-xs text-slate-600 dark:text-slate-400">Add to all future meetings in this series</span>
                                                                </label>
                                                            )}
                                                            <div className="flex justify-end gap-2">
                                                                <button
                                                                    onClick={() => setIsAddingMember(false)}
                                                                    className="px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                                                                >
                                                                    Cancel
                                                                </button>
                                                                <button
                                                                    onClick={handleAddSelectedMembers}
                                                                    disabled={selectedMembers.length === 0 || isLoadingAction}
                                                                    className="btn-primary text-sm disabled:opacity-50"
                                                                >
                                                                    {isLoadingAction ? 'Adding...' : `Add ${selectedMembers.length} Member${selectedMembers.length !== 1 ? 's' : ''}`}
                                                                </button>
                                                            </div>
                                                        </>
                                                    )}
                                                </Card>
                                            )}

                                            {isAddingGuest && (
                                                <Card className="p-4 bg-blue-50 dark:bg-blue-900/10 border-blue-100 dark:border-blue-800">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h4 className="font-bold text-sm text-blue-900 dark:text-blue-100">
                                                            {isBulkMode ? 'Add Multiple Guests' : 'Add External Guest'}
                                                        </h4>
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => {
                                                                    setIsBulkMode(!isBulkMode)
                                                                    setGuestName('')
                                                                    setGuestEmail('')
                                                                    setBulkGuestsText('')
                                                                }}
                                                                className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-700 transition-colors"
                                                            >
                                                                {isBulkMode ? 'Single Guest' : 'Bulk Add'}
                                                            </button>
                                                        </div>
                                                    </div>

                                                    {meeting?.recurring_meeting_id && (
                                                        <label className="flex items-center gap-2 mb-3 cursor-pointer">
                                                            <input
                                                                type="checkbox"
                                                                checked={applyToSeries}
                                                                onChange={e => setApplyToSeries(e.target.checked)}
                                                                className="rounded border-slate-300"
                                                            />
                                                            <span className="text-xs text-slate-600 dark:text-slate-400">Add to all future meetings in this series</span>
                                                        </label>
                                                    )}

                                                    {isBulkMode ? (
                                                        // Bulk Add Mode
                                                        <div className="space-y-3">
                                                            <textarea
                                                                placeholder={`Paste guest list (one per line or comma-separated)&#10;Supported formats:&#10;• email@example.com&#10;• Name <email@example.com>&#10;• Name, email@example.com`}
                                                                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 text-sm min-h-[120px] font-mono"
                                                                value={bulkGuestsText}
                                                                onChange={e => setBulkGuestsText(e.target.value)}
                                                            />
                                                            <div className="flex items-center justify-between">
                                                                <span className="text-xs text-slate-500">
                                                                    {parseBulkGuests(bulkGuestsText).length} guest(s) detected
                                                                </span>
                                                                <div className="flex gap-2">
                                                                    <button
                                                                        onClick={() => {
                                                                            setIsAddingGuest(false)
                                                                            setIsBulkMode(false)
                                                                            setBulkGuestsText('')
                                                                        }}
                                                                        className="px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                                                                    >
                                                                        Cancel
                                                                    </button>
                                                                    <button
                                                                        onClick={handleBulkAddGuests}
                                                                        disabled={parseBulkGuests(bulkGuestsText).length === 0 || isLoadingAction}
                                                                        className="btn-primary text-sm flex items-center gap-2 disabled:opacity-50"
                                                                    >
                                                                        {isLoadingAction ? (
                                                                            <><span className="animate-spin">⏳</span> Adding...</>
                                                                        ) : (
                                                                            <>Add All Guests</>
                                                                        )}
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        // Single Guest Mode
                                                        <div className="flex gap-3">
                                                            <input
                                                                type="text"
                                                                placeholder="Name (Optional)"
                                                                className="flex-1 px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 text-sm"
                                                                value={guestName}
                                                                onChange={e => setGuestName(e.target.value)}
                                                            />
                                                            <input
                                                                type="email"
                                                                placeholder="Email Address"
                                                                className="flex-1 px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 text-sm"
                                                                value={guestEmail}
                                                                onChange={e => setGuestEmail(e.target.value)}
                                                            />
                                                            <button
                                                                onClick={handleAddGuest}
                                                                disabled={!guestEmail || isLoadingAction}
                                                                className="btn-primary text-sm flex items-center gap-2"
                                                            >
                                                                {isLoadingAction ? (
                                                                    <><span className="animate-spin">⏳</span> Adding...</>
                                                                ) : (
                                                                    'Add'
                                                                )}
                                                            </button>
                                                        </div>
                                                    )}
                                                </Card>
                                            )}

                                            <div className="space-y-2">
                                                {meeting?.participants?.map((p: any) => (
                                                    <Card key={p.id} className="p-4">
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
                                                                    {(p.name || p.user?.full_name || p.email || '?')[0].toUpperCase()}
                                                                </div>
                                                                <div>
                                                                    <div className="font-bold text-sm text-slate-900 dark:text-white">
                                                                        {p.name || p.user?.full_name || 'Guest'}
                                                                    </div>
                                                                    <div className="text-xs text-slate-500">
                                                                        {p.email || p.user?.email}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-3">
                                                                <Badge variant={
                                                                    p.rsvp_status === 'accepted' ? 'success' :
                                                                        p.rsvp_status === 'declined' ? 'danger' : 'warning'
                                                                } className="uppercase text-[10px]">
                                                                    {p.rsvp_status}
                                                                </Badge>
                                                                <select
                                                                    className="text-xs bg-transparent border border-slate-200 dark:border-slate-700 rounded px-2 py-1 text-slate-500"
                                                                    value={p.rsvp_status}
                                                                    onChange={(e) => handleUpdateRsvp(p.id, e.target.value)}
                                                                >
                                                                    <option value="pending">Pending</option>
                                                                    <option value="accepted">Accept</option>
                                                                    <option value="declined">Decline</option>
                                                                </select>
                                                                <button
                                                                    onClick={() => handleRemoveParticipant(p.id)}
                                                                    className="text-slate-400 hover:text-red-500 transition-colors p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20"
                                                                    title="Remove participant"
                                                                >
                                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                                    </svg>
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </Card>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* DOCUMENTS TAB */}
                                    {activeTab === 'documents' && (
                                        <div className="max-w-4xl space-y-6">
                                            <div className="flex justify-between items-center">
                                                <h2 className="text-xl font-bold text-slate-900 dark:text-white">Meeting Documents</h2>
                                                <label className="btn-primary text-sm flex items-center gap-2 cursor-pointer">
                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                                    </svg>
                                                    {isUploadingDoc ? 'Uploading...' : 'Upload Document'}
                                                    <input
                                                        type="file"
                                                        className="hidden"
                                                        onChange={handleDocumentUpload}
                                                        disabled={isUploadingDoc}
                                                    />
                                                </label>
                                            </div>

                                            {documents.length === 0 ? (
                                                <div className="text-center py-20 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700">
                                                    <div className="w-16 h-16 bg-slate-200 dark:bg-slate-700 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                                        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                        </svg>
                                                    </div>
                                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">No Documents Yet</h3>
                                                    <p className="text-slate-500 max-w-sm mx-auto mt-2">Upload meeting documents, presentations, or attachments here.</p>
                                                </div>
                                            ) : (
                                                <div className="space-y-3">
                                                    {documents.map((doc: any) => {
                                                        const isTranscript = doc.document_type === 'transcript'
                                                        return (
                                                        <Card
                                                            key={doc.id}
                                                            onClick={() => handleDownloadDocument(doc.id)}
                                                            className="p-4 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer"
                                                        >
                                                            <div className="flex items-center gap-4">
                                                                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                                                                    isTranscript ? 'bg-purple-100 dark:bg-purple-900/30' :
                                                                    doc.file_name?.endsWith('.pdf') ? 'bg-red-100 dark:bg-red-900/30' :
                                                                    doc.file_name?.endsWith('.docx') || doc.file_name?.endsWith('.doc') ? 'bg-blue-100 dark:bg-blue-900/30' :
                                                                        'bg-slate-100 dark:bg-slate-800'
                                                                    }`}>
                                                                    {isTranscript ? (
                                                                        <span className="material-symbols-outlined text-purple-600 dark:text-purple-400">subtitles</span>
                                                                    ) : (
                                                                    <svg className={`w-6 h-6 ${doc.file_name?.endsWith('.pdf') ? 'text-red-600 dark:text-red-400' :
                                                                        doc.file_name?.endsWith('.docx') || doc.file_name?.endsWith('.doc') ? 'text-blue-600 dark:text-blue-400' :
                                                                            'text-slate-600 dark:text-slate-400'
                                                                        }`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                                    </svg>
                                                                    )}
                                                                </div>
                                                                <div className="flex-1 min-w-0">
                                                                    <div className="font-bold text-sm text-slate-900 dark:text-white truncate flex items-center gap-2">
                                                                        {doc.file_name || 'Untitled Document'}
                                                                        {isTranscript && (
                                                                            <span className="text-[10px] font-bold bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 px-2 py-0.5 rounded-full uppercase">Transcript</span>
                                                                        )}
                                                                    </div>
                                                                    <div className="text-xs text-slate-500">
                                                                        {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : ''}
                                                                        {doc.created_at ? ` Uploaded ${new Date(doc.created_at).toLocaleDateString()}` : ' Recently uploaded'}
                                                                        {' '}&mdash; Click to download
                                                                    </div>
                                                                </div>
                                                                <div className="flex gap-2">
                                                                    <button
                                                                        onClick={(e) => { e.stopPropagation(); handleDownloadDocument(doc.id) }}
                                                                        className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                                                                        title="Download"
                                                                    >
                                                                        <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                                        </svg>
                                                                    </button>
                                                                    <button
                                                                        onClick={(e) => { e.stopPropagation(); handleDeleteDocument(doc.id) }}
                                                                        className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                                                                        title="Delete"
                                                                    >
                                                                        <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                        </svg>
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        </Card>
                                                        )
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* SCHEDULE INTEGRITY TAB */}
                                    {activeTab === 'schedule' && (
                                        <div className="max-w-4xl space-y-8">
                                            {/* Header */}
                                            <div>
                                                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                                                    <span className="material-symbols-outlined text-indigo-600">radar</span>
                                                    Schedule Integrity
                                                </h2>
                                                <p className="text-sm text-slate-500">
                                                    Real-time view of scheduling conflicts and logical dependencies for this meeting.
                                                </p>
                                            </div>

                                            {/* Conflict Status Section */}
                                            <div className="space-y-4">
                                                <h3 className="text-sm font-black uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                    Scheduling Conflicts
                                                </h3>
                                                {detectedConflicts.length === 0 ? (
                                                    <Card className="p-6 border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10">
                                                        <div className="flex items-center gap-4">
                                                            <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600">
                                                                <span className="material-symbols-outlined text-2xl">check_circle</span>
                                                            </div>
                                                            <div>
                                                                <div className="font-bold text-green-800 dark:text-green-300">No Conflicts Detected</div>
                                                                <div className="text-sm text-green-600 dark:text-green-400">This meeting has no scheduling overlaps or participant clashes.</div>
                                                            </div>
                                                            <button
                                                                onClick={async () => {
                                                                    if (!meetingId) return;
                                                                    setIsCheckingConflicts(true);
                                                                    try {
                                                                        const res = await meetings.conflictCheck(meetingId);
                                                                        setDetectedConflicts(res.data.conflicts || []);
                                                                    } catch (e) {
                                                                        console.error('Conflict check failed', e);
                                                                    } finally {
                                                                        setIsCheckingConflicts(false);
                                                                    }
                                                                }}
                                                                disabled={isCheckingConflicts}
                                                                className="ml-auto btn-secondary text-sm flex items-center gap-2"
                                                            >
                                                                {isCheckingConflicts ? (
                                                                    <><span className="animate-spin">⏳</span> Checking...</>
                                                                ) : (
                                                                    <>🔍 Re-check</>)}
                                                            </button>
                                                        </div>
                                                    </Card>
                                                ) : (
                                                    <div className="space-y-3">
                                                        {detectedConflicts.map((conflict: any, idx: number) => (
                                                            <Card key={idx} className="p-4 border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/10">
                                                                <div className="flex items-center gap-4">
                                                                    <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center text-red-600">
                                                                        <span className="material-symbols-outlined">warning</span>
                                                                    </div>
                                                                    <div className="flex-1">
                                                                        <div className="font-bold text-red-800 dark:text-red-300">
                                                                            {conflict.type === 'participant' ? 'Participant Clash' :
                                                                                conflict.type === 'room' ? 'Room Double-Booking' : 'Time Overlap'}
                                                                        </div>
                                                                        <div className="text-sm text-red-600 dark:text-red-400">
                                                                            {conflict.description || conflict.message || `Conflicts with: ${conflict.conflicting_meeting_title || 'Unknown'}`}
                                                                        </div>
                                                                    </div>
                                                                    {conflict.conflicting_meeting_id && (
                                                                        <button
                                                                            onClick={() => navigate(`/meetings/${conflict.conflicting_meeting_id}`)}
                                                                            className="btn-secondary text-xs"
                                                                        >
                                                                            View Conflict
                                                                        </button>
                                                                    )}
                                                                </div>
                                                            </Card>
                                                        ))}
                                                        <button
                                                            onClick={async () => {
                                                                if (!meetingId) return;
                                                                setIsCheckingConflicts(true);
                                                                try {
                                                                    const res = await meetings.conflictCheck(meetingId);
                                                                    setDetectedConflicts(res.data.conflicts || []);
                                                                } catch (e) {
                                                                    console.error('Conflict check failed', e);
                                                                } finally {
                                                                    setIsCheckingConflicts(false);
                                                                }
                                                            }}
                                                            disabled={isCheckingConflicts}
                                                            className="btn-secondary text-sm w-full justify-center flex items-center gap-2"
                                                        >
                                                            {isCheckingConflicts ? (
                                                                <><span className="animate-spin">⏳</span> Checking...</>
                                                            ) : (
                                                                <>🔍 Re-check Conflicts</>)}
                                                        </button>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Predecessors */}
                                            <div className="space-y-4">
                                                <h3 className="text-sm font-black uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                                                    Predecessors (Required Before)
                                                </h3>
                                                {!meeting?.predecessors?.length ? (
                                                    <div className="p-6 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-center text-slate-400 text-sm">
                                                        <span className="block mb-1">No prerequisites defined.</span>
                                                        <span className="text-xs opacity-70">Dependencies are automatically detected from TWG Weekly Packets.</span>
                                                    </div>
                                                ) : (
                                                    <div className="grid gap-3">
                                                        {meeting?.predecessors?.map((dep: any) => (
                                                            <Card
                                                                key={dep.id}
                                                                className="p-4 hover:border-blue-400 transition-all cursor-pointer group"
                                                                onClick={() => navigate(`/meetings/${dep.source_meeting_id}`)}
                                                            >
                                                                <div className="flex items-center justify-between">
                                                                    <div className="flex items-center gap-4">
                                                                        <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600">
                                                                            <span className="material-symbols-outlined">event_available</span>
                                                                        </div>
                                                                        <div>
                                                                            <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                                                                                {dep.source_meeting_title}
                                                                            </div>
                                                                            <div className="text-xs text-slate-500">
                                                                                Type: <span className="font-mono text-blue-600 font-bold">{dep.dependency_type}</span>
                                                                                {dep.lag_minutes > 0 && ` • Lag: ${dep.lag_minutes}m`}
                                                                                <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-700 text-slate-500">
                                                                                    {dep.source_type || 'MANUAL'}
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                    <span className="material-symbols-outlined text-slate-300 group-hover:text-blue-400 transition-colors">arrow_forward</span>
                                                                </div>
                                                            </Card>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Successors */}
                                            <div className="space-y-4">
                                                <h3 className="text-sm font-black uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                                    <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                                                    Successors (Depends on this)
                                                </h3>
                                                {!meeting?.successors?.length ? (
                                                    <div className="p-6 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-center text-slate-400 text-sm">
                                                        <span className="block mb-1">No successors detected.</span>
                                                        <span className="text-xs opacity-70">Future dependencies are automatically identified from weekly packets.</span>
                                                    </div>
                                                ) : (
                                                    <div className="grid gap-3">
                                                        {meeting?.successors?.map((dep: any) => (
                                                            <Card
                                                                key={dep.id}
                                                                className="p-4 hover:border-purple-400 transition-all cursor-pointer group"
                                                                onClick={() => navigate(`/meetings/${dep.target_meeting_id}`)}
                                                            >
                                                                <div className="flex items-center justify-between">
                                                                    <div className="flex items-center gap-4">
                                                                        <div className="w-10 h-10 rounded-full bg-purple-50 flex items-center justify-center text-purple-600">
                                                                            <span className="material-symbols-outlined">forward_to_inbox</span>
                                                                        </div>
                                                                        <div>
                                                                            <div className="font-bold text-slate-900 dark:text-white group-hover:text-purple-600 transition-colors">
                                                                                {dep.target_meeting_title}
                                                                            </div>
                                                                            <div className="text-xs text-slate-500">
                                                                                Type: <span className="font-mono text-purple-600 font-bold">{dep.dependency_type}</span>
                                                                                {dep.lag_minutes > 0 && ` • Lag: ${dep.lag_minutes}m`}
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                    <span className="material-symbols-outlined text-slate-300 group-hover:text-purple-400 transition-colors">arrow_forward</span>
                                                                </div>
                                                            </Card>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                    </div>
                </div>
            </div>

            {/* Edit Meeting Modal */}
            {
                isEditingMeeting && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                            <div className="p-6 border-b border-slate-200 dark:border-slate-800">
                                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Edit Meeting</h2>
                            </div>
                            <div className="p-6 space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Meeting Title *</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={editTitle}
                                        onChange={e => setEditTitle(e.target.value)}
                                        placeholder="Enter meeting title"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Date & Time *</label>
                                    <input
                                        type="datetime-local"
                                        className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={editDate}
                                        onChange={e => setEditDate(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Location</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={editLocation}
                                        onChange={e => setEditLocation(e.target.value)}
                                        placeholder="Meeting location or video link"
                                    />
                                </div>
                            </div>
                            <div className="p-6 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3">
                                <button
                                    onClick={() => setIsEditingMeeting(false)}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleUpdateMeeting}
                                    disabled={!editTitle || !editDate}
                                    className="btn-primary"
                                >
                                    Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
            {/* Manage Series Modal */}
            {showManageSeriesModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Manage Recurring Series</h2>
                                {seriesData && (
                                    <Badge
                                        variant={seriesData.status === 'active' ? 'success' : seriesData.status === 'paused' ? 'warning' : 'neutral'}
                                        className="mt-1 text-xs uppercase"
                                    >
                                        {seriesData.status}
                                    </Badge>
                                )}
                            </div>
                            <button onClick={() => setShowManageSeriesModal(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {seriesLoading ? (
                            <div className="p-12 text-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
                                <p className="mt-3 text-sm text-slate-500">Loading series details...</p>
                            </div>
                        ) : seriesData && !seriesEditMode ? (
                            /* View Mode */
                            <div className="p-4 sm:p-6 space-y-6">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Title</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1">{seriesData.title_template}</p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Frequency</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1 capitalize">
                                            {seriesData.frequency}{seriesData.interval_weeks > 1 ? ` (every ${seriesData.interval_weeks} weeks)` : ''}
                                        </p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Time</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1">{seriesData.start_time}</p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Duration</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1">{seriesData.duration_minutes} min</p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Day</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1">
                                            {seriesData.day_of_week !== null && seriesData.day_of_week !== undefined
                                                ? ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][seriesData.day_of_week]
                                                : 'N/A'}
                                        </p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">End Type</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1 capitalize">
                                            {seriesData.end_type === 'never' ? 'Never' :
                                                seriesData.end_type === 'after_date' ? `Until ${new Date(seriesData.end_date).toLocaleDateString()}` :
                                                    `After ${seriesData.max_occurrences} occurrences`}
                                        </p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Instances Created</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1">{seriesData.occurrences_created}</p>
                                    </div>
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Location</span>
                                        <p className="text-sm font-medium text-slate-900 dark:text-white mt-1">{seriesData.location || 'Not set'}</p>
                                    </div>
                                </div>

                                {/* Upcoming Instances */}
                                {seriesData.upcoming_instances?.length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Upcoming Instances</h3>
                                        <div className="space-y-2 max-h-48 overflow-y-auto">
                                            {seriesData.upcoming_instances.map((inst: any) => (
                                                <div key={inst.id} className="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
                                                    <div>
                                                        <span className="font-medium text-slate-900 dark:text-white">{inst.title}</span>
                                                        <span className="text-slate-500 ml-2">
                                                            {new Date(inst.scheduled_at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                                                            {' '}
                                                            {new Date(inst.scheduled_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                                                        </span>
                                                    </div>
                                                    <Badge variant={inst.status === 'SCHEDULED' ? 'success' : 'neutral'} className="text-xs uppercase">{inst.status}</Badge>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : seriesData && seriesEditMode ? (
                            /* Edit Mode */
                            <div className="p-4 sm:p-6 space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Series Title</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                                        value={seriesTitle}
                                        onChange={e => setSeriesTitle(e.target.value)}
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Start Time</label>
                                        <input
                                            type="time"
                                            className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                                            value={seriesTime}
                                            onChange={e => setSeriesTime(e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Duration (min)</label>
                                        <input
                                            type="number"
                                            min={15}
                                            step={15}
                                            className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                                            value={seriesDuration}
                                            onChange={e => setSeriesDuration(Number(e.target.value))}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Location</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                                        value={seriesLocation}
                                        onChange={e => setSeriesLocation(e.target.value)}
                                        placeholder="Meeting location or video link"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Update Scope</label>
                                    <div className="flex gap-4">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="radio"
                                                name="seriesScope"
                                                checked={seriesUpdateScope === 'future'}
                                                onChange={() => setSeriesUpdateScope('future')}
                                                className="text-indigo-600"
                                            />
                                            <span className="text-sm text-slate-700 dark:text-slate-300">Future instances only</span>
                                        </label>
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="radio"
                                                name="seriesScope"
                                                checked={seriesUpdateScope === 'all'}
                                                onChange={() => setSeriesUpdateScope('all')}
                                                className="text-indigo-600"
                                            />
                                            <span className="text-sm text-slate-700 dark:text-slate-300">All instances</span>
                                        </label>
                                    </div>
                                </div>
                            </div>
                        ) : null}

                        {/* Footer */}
                        {seriesData && !seriesLoading && (
                            <div className="p-4 sm:p-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                                <div className="flex flex-wrap gap-2">
                                    {seriesData.status !== 'cancelled' && (
                                        <button
                                            onClick={() => setShowCancelSeriesConfirm(true)}
                                            disabled={seriesActionLoading}
                                            className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                        >
                                            Cancel Series
                                        </button>
                                    )}
                                    {(seriesData.status === 'active' || seriesData.status === 'paused') && (
                                        <button
                                            onClick={handleTogglePauseSeries}
                                            disabled={seriesActionLoading}
                                            className="px-3 py-2 text-sm font-medium text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                                        >
                                            {seriesActionLoading ? 'Processing...' : seriesData.status === 'paused' ? 'Resume Series' : 'Pause Series'}
                                        </button>
                                    )}
                                </div>
                                <div className="flex flex-wrap gap-2 justify-end">
                                    <button
                                        onClick={() => { setShowManageSeriesModal(false); setSeriesEditMode(false) }}
                                        className="btn-secondary"
                                    >
                                        Close
                                    </button>
                                    {seriesData.status !== 'cancelled' && (
                                        seriesEditMode ? (
                                            <button
                                                onClick={handleUpdateSeries}
                                                disabled={seriesActionLoading || !seriesTitle}
                                                className="btn-primary bg-indigo-600 hover:bg-indigo-700"
                                            >
                                                {seriesActionLoading ? 'Saving...' : 'Save Changes'}
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() => setSeriesEditMode(true)}
                                                className="btn-primary bg-indigo-600 hover:bg-indigo-700"
                                            >
                                                Edit Series
                                            </button>
                                        )
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Cancel Series Confirmation */}
            <InputModal
                isOpen={showCancelSeriesConfirm}
                onCancel={() => setShowCancelSeriesConfirm(false)}
                onConfirm={handleCancelSeries}
                title="Cancel Recurring Series"
                description="This will cancel the entire recurring series and all future meeting instances. This action cannot be undone."
                placeholder="Enter reason for cancellation..."
                confirmText="Cancel Series"
                confirmVariant="danger"
                isLoading={seriesActionLoading}
            />

            {/* Action Item Detail Modal */}
            {
                selectedAction && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setSelectedAction(null)}>
                        <div className="bg-white dark:bg-slate-900 rounded-lg shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Action Item Details</h3>
                                <button onClick={() => setSelectedAction(null)} className="text-slate-400 hover:text-slate-500">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            {isEditingSelected ? (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Description</label>
                                        <textarea
                                            className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-sm"
                                            rows={3}
                                            value={selectedDescription}
                                            onChange={e => setSelectedDescription(e.target.value)}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Owner</label>
                                            <input
                                                type="text"
                                                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-sm"
                                                value={selectedOwner}
                                                onChange={e => setSelectedOwner(e.target.value)}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">Due Date</label>
                                            <input
                                                type="date"
                                                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-sm"
                                                value={selectedDueDate}
                                                onChange={e => setSelectedDueDate(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-2 mt-4">
                                        <button onClick={() => setIsEditingSelected(false)} className="btn-secondary text-sm">Cancel</button>
                                        <button onClick={handleUpdateAction} className="btn-primary text-sm" disabled={isLoadingAction}>Save Changes</button>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-md border border-slate-100 dark:border-slate-700">
                                        <p className="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{selectedAction.description}</p>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <div>
                                            <span className="text-slate-500 block text-xs uppercase tracking-wider font-bold mb-1">Owner</span>
                                            <div className="flex items-center gap-2">
                                                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${selectedAction.owner ? 'bg-indigo-500' : 'bg-slate-400'}`}>
                                                    {selectedAction.owner?.avatar || (typeof selectedAction.owner === 'string' && selectedAction.owner ? selectedAction.owner.charAt(0).toUpperCase() : '?')}
                                                </div>
                                                <span className="font-medium text-slate-700 dark:text-slate-300">{selectedAction.owner?.name || selectedAction.owner || 'Unassigned'}</span>
                                            </div>
                                        </div>
                                        <div>
                                            <span className="text-slate-500 block text-xs uppercase tracking-wider font-bold mb-1">Due Date</span>
                                            <span className="font-medium text-slate-700 dark:text-slate-300">{selectedAction.due_date ? new Date(selectedAction.due_date).toLocaleDateString() : 'None'}</span>
                                        </div>
                                    </div>
                                    <div className="flex justify-between items-center pt-4 border-t border-slate-200 dark:border-slate-700 mt-4">
                                        <button onClick={handleDeleteAction} className="text-red-600 hover:text-red-700 text-sm font-medium flex items-center gap-1">
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                            Delete
                                        </button>
                                        <button onClick={() => setIsEditingSelected(true)} className="btn-secondary text-sm flex items-center gap-2">
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                            </svg>
                                            Edit Action
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )
            }

        </>
    )
}
