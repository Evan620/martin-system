import { useState, useEffect, useRef } from 'react'
import {
    organizationInvitationService,
    InvitationMessage,
    InvitationMessageCreate
} from '../../services/organizationInvitationService'
import { toast } from 'react-toastify'

interface InvitationChatProps {
    invitationId: string
    isPublic?: boolean  // true = invitee view, false = admin view
    organizationName: string
}

export default function InvitationChat({ invitationId, isPublic = false, organizationName }: InvitationChatProps) {
    const [messages, setMessages] = useState<InvitationMessage[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSending, setIsSending] = useState(false)
    const [newMessage, setNewMessage] = useState('')
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        loadMessages()
    }, [invitationId, isPublic])

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const loadMessages = async () => {
        setIsLoading(true)
        try {
            const data = isPublic
                ? await organizationInvitationService.getPublicMessages(invitationId)
                : await organizationInvitationService.getMessages(invitationId)
            setMessages(data.items)
        } catch (error) {
            console.error('Failed to load messages', error)
            if (!isPublic) {
                toast.error('Failed to load messages')
            }
        } finally {
            setIsLoading(false)
        }
    }

    const handleSendMessage = async () => {
        if (!newMessage.trim()) return

        setIsSending(true)
        try {
            const messageData: InvitationMessageCreate = { content: newMessage.trim() }
            const sentMessage = isPublic
                ? await organizationInvitationService.sendPublicMessage(invitationId, messageData)
                : await organizationInvitationService.sendMessage(invitationId, messageData)

            setMessages(prev => [...prev, sentMessage])
            setNewMessage('')
        } catch (error) {
            console.error('Failed to send message', error)
            toast.error('Failed to send message')
        } finally {
            setIsSending(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const formatTime = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }

    const isMyMessage = (message: InvitationMessage) => {
        // In public view, invitee messages are "mine"
        // In admin view, admin messages are "mine"
        return isPublic
            ? message.sender_type === 'invitee'
            : message.sender_type === 'admin'
    }

    return (
        <div className="flex flex-col h-full">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {isLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="w-8 h-8 border-4 border-[#1152d4] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <div className="w-16 h-16 bg-gray-100 dark:bg-[#2d3748] rounded-full flex items-center justify-center mb-4">
                            <span className="material-symbols-outlined text-3xl text-[#4c669a]">chat_bubble_outline</span>
                        </div>
                        <p className="text-[#4c669a] dark:text-[#a0aec0] text-sm">
                            No messages yet. Start the conversation!
                        </p>
                    </div>
                ) : (
                    messages.map((message, index) => {
                        const showDate = index === 0 ||
                            formatDate(message.created_at) !== formatDate(messages[index - 1].created_at)

                        return (
                            <div key={message.id}>
                                {showDate && (
                                    <div className="flex items-center justify-center my-4">
                                        <span className="px-3 py-1 bg-gray-100 dark:bg-[#2d3748] rounded-full text-xs text-[#4c669a] dark:text-[#a0aec0]">
                                            {formatDate(message.created_at)}
                                        </span>
                                    </div>
                                )}
                                <div className={`flex ${isMyMessage(message) ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[80%] ${isMyMessage(message) ? 'order-2' : 'order-1'}`}>
                                        {!isMyMessage(message) && (
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] mb-1 ml-1">
                                                {message.sender_name}
                                            </p>
                                        )}
                                        <div className={`rounded-2xl px-4 py-2 ${
                                            isMyMessage(message)
                                                ? 'bg-[#1152d4] text-white rounded-br-md'
                                                : 'bg-gray-100 dark:bg-[#2d3748] text-[#0d121b] dark:text-white rounded-bl-md'
                                        }`}>
                                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                                        </div>
                                        <p className={`text-xs text-[#4c669a] dark:text-[#a0aec0] mt-1 ${
                                            isMyMessage(message) ? 'text-right mr-1' : 'ml-1'
                                        }`}>
                                            {formatTime(message.created_at)}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )
                    })
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-[#e7ebf3] dark:border-[#2d3748] p-4">
                <div className="flex gap-2">
                    <textarea
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={isPublic ? "Type your message..." : `Message to ${organizationName}...`}
                        className="flex-1 px-4 py-2 bg-white dark:bg-[#2d3748] border border-[#e7ebf3] dark:border-[#4a5568] rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1152d4]/20 focus:border-[#1152d4]"
                        rows={1}
                        disabled={isSending}
                    />
                    <button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim() || isSending}
                        className="px-4 py-2 bg-[#1152d4] hover:bg-[#0e44b1] text-white rounded-xl text-sm font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {isSending ? (
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                            <span className="material-symbols-outlined text-[20px]">send</span>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
