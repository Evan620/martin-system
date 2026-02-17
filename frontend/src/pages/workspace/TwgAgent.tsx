import { useState, useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { useParams } from 'react-router-dom';
import { RootState } from '../../store';
import { agentService, Citation } from '../../services/agentService';
import { twgs as twgApi, default as api } from '../../services/api';
import { CommandAutocomplete } from '../../components/agent/CommandAutocomplete';
import { MentionAutocomplete } from '../../components/agent/MentionAutocomplete';
import EmailApprovalModal, { EmailApprovalRequest, EmailDraft } from '../../components/agent/EmailApprovalModal';
import DocumentApprovalModal from '../../components/modals/DocumentApprovalModal';
import SettingsModal from '../../components/agent/SettingsModal';
import EnhancedMessageBubble from '../../components/agent/EnhancedMessageBubble';
import ThinkingTimeline, { ThinkingStep } from '../../components/agent/ThinkingTimeline';
import WorkspaceContextPanel from '../../components/workspace/WorkspaceContextPanel';
import { CommandAutocompleteResult } from '../../types/agent';
import { UserRole } from '../../types/auth';

interface Message {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    citations?: Citation[];
    reactions?: MessageReaction[];
    agentName?: string;
    agentIcon?: string;
    approvalRequest?: any;
    suggestions?: string[];
}

interface MessageReaction {
    emoji: string;
    count: number;
    users: string[];
}

interface AgentMentionSuggestion {
    mention: string;
    agent_id: string;
    name: string;
    icon: string;
    description: string;
    match_score?: number;
}

export default function TwgAgent() {
    const user = useSelector((state: RootState) => state.auth.user);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | undefined>();
    const [activeTwg, setActiveTwg] = useState<{ id: string; name: string } | null>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const { id } = useParams<{ id: string }>();

    // Initialize Active TWG Context
    useEffect(() => {
        const initContext = async () => {
            if (!user) return;

            // 1. Priority: URL Param (Direct Link or navigation)
            if (id) {
                // Check if we have it in user's assigned TWGs (saves API call)
                const assignedTwg = user.twgs?.find(t => t.id === id);
                if (assignedTwg) {
                    setActiveTwg({ id: assignedTwg.id, name: assignedTwg.name });
                    return;
                }

                // If not assigned (e.g. Admin or public), fetch details
                try {
                    const res = await twgApi.get(id);
                    setActiveTwg({ id: res.data.id, name: res.data.name });
                } catch (err) {
                    console.error("Failed to load TWG context from URL", err);
                    // Fallback to safe default based on role
                }
            } else {
                // 2. Fallback: Role-based Default
                if (user.role === UserRole.ADMIN || user.role === UserRole.SECRETARIAT_LEAD) {
                    setActiveTwg({ id: 'secretariat', name: 'Secretariat' });
                } else if (user.twgs && user.twgs.length > 0) {
                    // Default to first assigned TWG
                    setActiveTwg({ id: user.twgs[0].id, name: user.twgs[0].name });
                } else if (user.twg_ids && user.twg_ids.length > 0) {
                    // Fallback: If full TWG objects missing, fetch by ID
                    try {
                        console.log('[TwgAgent] Fetching default TWG details for ID:', user.twg_ids[0]);
                        const res = await twgApi.get(user.twg_ids[0]);
                        setActiveTwg({ id: res.data.id, name: res.data.name });
                    } catch (err) {
                        console.error("Failed to fetch default TWG details", err);
                    }
                }
            }
        };

        initContext();
    }, [user, id]);


    // Autocomplete state
    const [commandSuggestions, setCommandSuggestions] = useState<CommandAutocompleteResult[]>([]);
    const [mentionSuggestions, setMentionSuggestions] = useState<AgentMentionSuggestion[]>([]);
    const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
    const [autocompleteType, setAutocompleteType] = useState<'command' | 'mention' | null>(null);

    // Modals
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [emailApprovalRequest, setEmailApprovalRequest] = useState<EmailApprovalRequest | null>(null);
    const [documentApprovalRequest, setDocumentApprovalRequest] = useState<any | null>(null);

    // Context panel state
    const [showContextPanel, setShowContextPanel] = useState(false);

    // Typing state
    const [typingMessage, setTypingMessage] = useState<string | null>(null);
    const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
    const [streamStartTime, setStreamStartTime] = useState<number>(0);

    // ========================================================================
    // CHAT HISTORY PERSISTENCE (localStorage)
    // ========================================================================
    const getChatStorageKey = (twgId: string) => `martin_chat_${twgId}`;

    // Load chat history when activeTwg changes
    useEffect(() => {
        if (!activeTwg?.id) return;

        const storageKey = getChatStorageKey(activeTwg.id);
        try {
            const savedData = localStorage.getItem(storageKey);
            if (savedData) {
                const parsed = JSON.parse(savedData);
                // Restore messages with proper Date objects
                const restoredMessages: Message[] = parsed.messages.map((m: any) => ({
                    ...m,
                    timestamp: new Date(m.timestamp)
                }));
                setMessages(restoredMessages);
                setConversationId(parsed.conversationId);
                console.log(`[TwgAgent] Restored ${restoredMessages.length} messages from localStorage`);
            }
        } catch (error) {
            console.error('[TwgAgent] Failed to restore chat history:', error);
        }
    }, [activeTwg?.id]);

    // Save chat history when messages change
    useEffect(() => {
        if (!activeTwg?.id || messages.length === 0) return;

        const storageKey = getChatStorageKey(activeTwg.id);
        try {
            const dataToSave = {
                messages: messages,
                conversationId: conversationId,
                savedAt: new Date().toISOString()
            };
            localStorage.setItem(storageKey, JSON.stringify(dataToSave));
        } catch (error) {
            console.error('[TwgAgent] Failed to save chat history:', error);
        }
    }, [messages, conversationId, activeTwg?.id]);
    // ========================================================================


    // Helper to get Martin Persona Name

    // Document Approval Handlers
    const handleDocumentApprovalResolve = async (approved: boolean, result?: any) => {
        setDocumentApprovalRequest(null);

        if (!conversationId) return;

        // Resume the agent loop
        try {
            setIsLoading(true);
            await agentService.chatStream({
                message: approved
                    ? `I have approved the document. The ID is ${result?.document_id}. Please proceed.`
                    : "I have declined the document creation.",
                conversation_id: conversationId,
                twg_id: activeTwg?.id
            }, {
                onThinking: (status) => setTypingMessage(status), // Using setTypingMessage as setCurrentThought is not defined
                onResponse: (response) => {
                    // Update the last message if it's from agent, or add new
                    setMessages(prev => {
                        const newMsg: Message = {
                            id: crypto.randomUUID(),
                            role: 'agent',
                            content: response.content || response,
                            timestamp: new Date(),
                            agentName: currentAgentName, // Use dynamic identity
                            citations: response.citations || [],
                            suggestions: response.suggestions
                        };
                        return [...prev, newMsg];
                    });
                    // Clear thought when response comes
                    setTypingMessage(null); // Using setTypingMessage as setCurrentThought is not defined
                },
                onDone: () => setIsLoading(false),
                onError: (err) => {
                    console.error("Error resuming after doc approval", err);
                    setIsLoading(false);
                }
            });
        } catch (error) {
            console.error("Failed to resume conversation", error);
            setIsLoading(false);
        }
    };

    const getAgentIdentity = (twgName?: string) => {
        if (!twgName) return "Martin Copilot";

        // Normalize
        const name = twgName.toLowerCase();

        if (name.includes('secretariat')) return "Secretariat Martin";
        if (name.includes('leads council') || name.includes('council')) return "Council Martin";
        if (name.includes('energy')) return "Energy Martin";
        if (name.includes('agriculture') || name.includes('agribusiness')) return "Agriculture Martin";
        if (name.includes('minerals')) return "Minerals Martin";
        if (name.includes('digital')) return "Digital Martin";
        if (name.includes('protocol')) return "Protocol Martin";
        if (name.includes('resource') || name.includes('mobilization')) return "Investment Martin";

        // Fallback for custom/new TWGs
        return `${twgName} Martin`;
    };

    const currentAgentName = getAgentIdentity(activeTwg?.name);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };


    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading, typingMessage, thinkingSteps]);

    const handleSendMessage = async () => {
        if (!inputMessage.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputMessage,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        const messageToSend = inputMessage;
        setInputMessage('');
        setIsLoading(true);
        setThinkingSteps([]); // Clear previous steps
        setStreamStartTime(Date.now());
        setTypingMessage('Processing...');

        // Create new AbortController for this request
        abortControllerRef.current = new AbortController();

        try {
            await agentService.chatStream({
                message: messageToSend,
                conversation_id: conversationId,
                twg_id: activeTwg?.id !== 'secretariat' ? activeTwg?.id : undefined // Pass TWG ID if not secretariat
            }, {
                onStep: (step: ThinkingStep) => {
                    setThinkingSteps(prev => {
                        const newSteps = [...prev];
                        // Mark previous step as complete
                        if (newSteps.length > 0) {
                            const lastStep = newSteps[newSteps.length - 1];
                            if (lastStep.status === 'active') {
                                lastStep.status = 'complete';
                                lastStep.durationMs = Date.now() - lastStep.timestamp;
                            }
                        }
                        // Add new step
                        newSteps.push({
                            ...step,
                            timestamp: Date.now()
                        });
                        return newSteps;
                    });
                    setTypingMessage(step.label);
                },
                onThinking: (status) => {
                    // Fallback or additional handling if needed
                },
                onResponse: (msg: any) => {
                    console.log('[STREAM] Received response:', msg);

                    // Parse suggestions from content (Format: <<SUGGESTIONS>>["A","B"]<</SUGGESTIONS>>)
                    let content = msg.content;
                    let suggestions: string[] = [];

                    if (content.includes('<<SUGGESTIONS>>')) {
                        try {
                            const start = content.indexOf('<<SUGGESTIONS>>');
                            const end = content.indexOf('<</SUGGESTIONS>>');
                            if (start !== -1 && end !== -1) {
                                const jsonStr = content.substring(start + 15, end);
                                suggestions = JSON.parse(jsonStr);
                                content = content.substring(0, start).trim();
                            }
                        } catch (e) {
                            console.error('Error parsing suggestions:', e);
                        }
                    }

                    const agentMessage: Message = {
                        id: msg.message_id || Date.now().toString(),
                        role: 'agent',
                        content: content,
                        timestamp: new Date(),
                        citations: [], // Stream doesn't support citations yet
                        agentName: currentAgentName,
                        suggestions: suggestions
                    };

                    setMessages(prev => [...prev, agentMessage]);
                    setConversationId(msg.conversation_id);
                },
                onInterrupt: (payload: any) => {
                    console.log('[STREAM] Received interrupt:', payload);
                    if (payload.type === 'email_approval_required') {
                        setEmailApprovalRequest(payload);
                        setIsLoading(false); // Stop loading indicator while waiting for user
                    } else if (payload.type === 'document_approval_required') {
                        setDocumentApprovalRequest(payload);
                        setIsLoading(false);
                    } else {
                        const interruptMsg: Message = {
                            id: `interrupt-${Date.now()}`,
                            role: 'agent',
                            content: payload.message || 'Action required.',
                            timestamp: new Date(),
                            agentName: currentAgentName,
                            approvalRequest: payload
                        };
                        setMessages(prev => [...prev, interruptMsg]);
                        setIsLoading(false);
                        setTypingMessage(null);
                    }
                },
                onDone: () => {
                    setIsLoading(false);
                    setTypingMessage(null);
                },
                onError: (err) => {
                    console.error('Stream error:', err);
                    const errorMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        role: 'agent',
                        content: 'Sorry, I encountered an error. Please try again.',
                        timestamp: new Date(),
                    };
                    setMessages(prev => [...prev, errorMessage]);
                    setIsLoading(false);
                    setTypingMessage(null);
                }
            });

        } catch (error: any) {
            // Fallback handled in onError usually, but strictly catch synchronous startup errors
            setIsLoading(false);
            setTypingMessage(null);
            console.error('Error starting chat:', error);
        } finally {
            abortControllerRef.current = null;
        }
    };

    // Detect slash commands and @mentions in input
    const handleInputChange = async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        setInputMessage(value);

        const cursorPosition = e.target.selectionStart;
        const textBeforeCursor = value.substring(0, cursorPosition);

        // Check for command trigger (/)
        const commandMatch = textBeforeCursor.match(/\/(\w*)$/);
        if (commandMatch) {
            const query = '/' + commandMatch[1];
            try {
                const response = await api.get(`/agents/commands/autocomplete`, {
                    params: { query }
                });
                setCommandSuggestions(response.data.suggestions);
                setAutocompleteType('command');
                setSelectedSuggestionIndex(0);
                return;
            } catch (error) {
                console.error('Error fetching command suggestions:', error);
            }
        }

        // Check for mention trigger (@) - RESTRICTED TO ADMINS
        const mentionMatch = textBeforeCursor.match(/@(\w*)$/);
        if (mentionMatch && user?.role === UserRole.ADMIN) {
            const query = '@' + mentionMatch[1];
            try {
                const response = await api.get(`/agents/mentions/autocomplete`, {
                    params: { query }
                });
                setMentionSuggestions(response.data.suggestions);
                setAutocompleteType('mention');
                setSelectedSuggestionIndex(0);
                return;
            } catch (error) {
                console.error('Error fetching mention suggestions:', error);
            }
        }

        // Clear autocomplete if no trigger detected
        setAutocompleteType(null);
        setCommandSuggestions([]);
        setMentionSuggestions([]);
    };

    const handleCommandSelect = (suggestion: CommandAutocompleteResult) => {
        const cursorPosition = inputRef.current?.selectionStart || 0;
        const textBeforeCursor = inputMessage.substring(0, cursorPosition);
        const textAfterCursor = inputMessage.substring(cursorPosition);

        const commandMatch = textBeforeCursor.match(/\/(\w*)$/);
        if (commandMatch) {
            const beforeCommand = textBeforeCursor.substring(0, textBeforeCursor.length - commandMatch[0].length);
            const newValue = beforeCommand + suggestion.command + ' ' + textAfterCursor;
            setInputMessage(newValue);
            setAutocompleteType(null);
            setCommandSuggestions([]);

            setTimeout(() => {
                if (inputRef.current) {
                    const newCursorPos = beforeCommand.length + suggestion.command.length + 1;
                    inputRef.current.focus();
                    inputRef.current.setSelectionRange(newCursorPos, newCursorPos);
                }
            }, 0);
        }
    };

    const handleMentionSelect = (suggestion: AgentMentionSuggestion) => {
        const cursorPosition = inputRef.current?.selectionStart || 0;
        const textBeforeCursor = inputMessage.substring(0, cursorPosition);
        const textAfterCursor = inputMessage.substring(cursorPosition);

        const mentionMatch = textBeforeCursor.match(/@(\w*)$/);
        if (mentionMatch) {
            const beforeMention = textBeforeCursor.substring(0, textBeforeCursor.length - mentionMatch[0].length);
            const newValue = beforeMention + suggestion.mention + ' ' + textAfterCursor;
            setInputMessage(newValue);
            setAutocompleteType(null);
            setMentionSuggestions([]);

            setTimeout(() => {
                if (inputRef.current) {
                    const newCursorPos = beforeMention.length + suggestion.mention.length + 1;
                    inputRef.current.focus();
                    inputRef.current.setSelectionRange(newCursorPos, newCursorPos);
                }
            }, 0);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (autocompleteType) {
            const suggestions = autocompleteType === 'command' ? commandSuggestions : mentionSuggestions;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedSuggestionIndex((prev) => (prev + 1) % suggestions.length);
                return;
            }

            if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedSuggestionIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
                return;
            }

            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (autocompleteType === 'command' && commandSuggestions[selectedSuggestionIndex]) {
                    handleCommandSelect(commandSuggestions[selectedSuggestionIndex]);
                } else if (autocompleteType === 'mention' && mentionSuggestions[selectedSuggestionIndex]) {
                    handleMentionSelect(mentionSuggestions[selectedSuggestionIndex]);
                }
                return;
            }

            if (e.key === 'Escape') {
                e.preventDefault();
                setAutocompleteType(null);
                setCommandSuggestions([]);
                setMentionSuggestions([]);
                return;
            }
        }

        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const handleClearConversation = () => {
        if (messages.length === 0 && !isLoading) return;

        if (window.confirm('Are you sure you want to clear this conversation? This action cannot be undone.')) {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
            }

            setMessages([]);
            setConversationId(undefined);
            setIsLoading(false);
            setTypingMessage(null);

            // Also clear from localStorage
            if (activeTwg?.id) {
                const storageKey = getChatStorageKey(activeTwg.id);
                localStorage.removeItem(storageKey);
                console.log(`[TwgAgent] Cleared chat history from localStorage for ${activeTwg.id}`);
            }
        }
    };

    const handleReact = (messageId: string, emoji: string) => {
        setMessages(prev => prev.map(msg => {
            if (msg.id === messageId) {
                const reactions = msg.reactions || [];
                const existingReaction = reactions.find(r => r.emoji === emoji);

                if (existingReaction) {
                    return {
                        ...msg,
                        reactions: reactions.map(r =>
                            r.emoji === emoji
                                ? { ...r, count: r.count + 1, users: [...r.users, 'You'] }
                                : r
                        )
                    };
                } else {
                    return {
                        ...msg,
                        reactions: [...reactions, { emoji, count: 1, users: ['You'] }]
                    };
                }
            }
            return msg;
        }));
    };

    const handleInsertContext = (contextType: string, data: any) => {
        let contextText = '';

        switch (contextType) {
            case 'meeting':
                contextText = `Please summarize the meeting "${data.title}" scheduled for ${data.date}`;
                break;
            case 'action':
                contextText = `What is the status of the action item: "${data.task}" assigned to ${data.assignee}?`;
                break;
            case 'document':
                contextText = `Can you provide information about the document "${data.name}"?`;
                break;
            case 'template':
                if (data.type === 'summary') {
                    contextText = 'Generate a summary of all recent TWG activities';
                } else if (data.type === 'stats') {
                    contextText = 'Show me the statistics for this TWG workspace';
                }
                break;
            default:
                contextText = `Context: ${JSON.stringify(data)}`;
        }

        setInputMessage(contextText);
        inputRef.current?.focus();
    };

    const handleEmailApprovalResolve = async (approved: boolean, requestId: string, modifications?: EmailDraft, declineReason?: string) => {
        try {
            if (approved) {
                const approvalData = {
                    request_id: requestId,
                    approved: true,
                    modifications: modifications || null
                };
                const result = await agentService.approveEmail(requestId, approvalData);
                const successMessage: Message = {
                    id: Date.now().toString(),
                    role: 'agent',
                    content: result.email_sent
                        ? `✅ Email sent successfully! Message ID: ${result.message_id}`
                        : `⚠️ ${result.message}`,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, successMessage]);
            } else {
                await agentService.declineEmail(requestId, declineReason);
                const declineMessage: Message = {
                    id: Date.now().toString(),
                    role: 'agent',
                    content: `🚫 Email sending cancelled: ${declineReason || 'Declined by user'}`,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, declineMessage]);
            }
        } catch (error) {
            console.error('Error handling email approval:', error);
            const errorMessage: Message = {
                id: Date.now().toString(),
                role: 'agent',
                content: `❌ Failed to process email approval: ${error}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setEmailApprovalRequest(null);
        }
    };


    const handleSuggestionClick = (suggestion: string) => {
        setInputMessage(suggestion);
        // Using strict timeout to ensure state update before firing
        setTimeout(() => {
            handleSendMessage();
        }, 50);
    };

    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white h-full flex flex-col overflow-hidden">


            {/* Main Content */}
            <main className="flex-1 flex overflow-hidden">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-[#f6f6f8] dark:bg-[#0d121b]">
                    {/* Agent Header */}
                    <div className="bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748] px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <div className="size-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white">
                                    <span className="material-symbols-outlined">smart_toy</span>
                                </div>
                                <span className="absolute bottom-0 right-0 size-3 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                            </div>
                            <div>
                                <h3 className="font-bold text-[#0d121b] dark:text-white">
                                    {currentAgentName}
                                </h3>
                                <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                                    <span className="size-1.5 bg-green-500 rounded-full"></span>
                                    Online
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setShowContextPanel(!showContextPanel)}
                                className={`p-2 rounded-lg transition-colors ${showContextPanel
                                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                                    : 'text-[#4c669a] hover:bg-gray-100 dark:hover:bg-[#2d3748]'
                                    }`}
                                title="Toggle workspace context"
                            >
                                <span className="material-symbols-outlined">view_sidebar</span>
                            </button>
                            {isLoading && (
                                <button
                                    onClick={() => {
                                        if (abortControllerRef.current) {
                                            abortControllerRef.current.abort();
                                            abortControllerRef.current = null;
                                        }
                                        setIsLoading(false);
                                        setTypingMessage(null);
                                    }}
                                    className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                    title="Stop generation"
                                >
                                    <span className="material-symbols-outlined">stop_circle</span>
                                </button>
                            )}
                            <button
                                onClick={() => setSettingsOpen(true)}
                                className="p-2 text-[#4c669a] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
                                title="Settings"
                            >
                                <span className="material-symbols-outlined">settings</span>
                            </button>
                            <button
                                onClick={handleClearConversation}
                                className="p-2 text-[#4c669a] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Clear conversation"
                                disabled={messages.length === 0 && !isLoading}
                            >
                                <span className="material-symbols-outlined">delete</span>
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-gradient-to-b from-gray-50/50 to-transparent dark:from-[#0d121b]/30 dark:to-transparent">
                        {messages.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center px-4">
                                <div className="max-w-3xl w-full text-center mb-8">
                                    <div className="size-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-900/20">
                                        <span className="material-symbols-outlined text-white" style={{ fontSize: '32px' }}>smart_toy</span>
                                    </div>
                                    <h3 className="text-3xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-700 to-purple-600 dark:from-blue-400 dark:to-purple-400 mb-3">
                                        Good day, {user?.full_name ? user.full_name.split(' ')[0] : 'Dr. Sow'}
                                    </h3>
                                    <h4 className="text-xl text-slate-600 dark:text-slate-400 font-medium mb-8">
                                        {currentAgentName} is online. How may I assist?
                                    </h4>

                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-left">
                                        <button
                                            onClick={() => {
                                                setInputMessage("Draft minutes for the last meeting");
                                                inputRef.current?.focus();
                                            }}
                                            className="p-5 bg-white dark:bg-[#1a202c] border border-slate-200 dark:border-slate-700 rounded-2xl hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md dark:hover:bg-[#2d3748] transition-all group"
                                        >
                                            <div className="size-10 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                                                <span className="material-symbols-outlined text-blue-600 dark:text-blue-400">description</span>
                                            </div>
                                            <h5 className="font-bold text-slate-900 dark:text-white mb-1">Draft Minutes</h5>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">Generate formal minutes from the latest meeting transcript.</p>
                                        </button>

                                        <button
                                            onClick={() => {
                                                setInputMessage("Summarize the last session's key outcomes");
                                                inputRef.current?.focus();
                                            }}
                                            className="p-5 bg-white dark:bg-[#1a202c] border border-slate-200 dark:border-slate-700 rounded-2xl hover:border-purple-400 dark:hover:border-purple-500 hover:shadow-md dark:hover:bg-[#2d3748] transition-all group"
                                        >
                                            <div className="size-10 rounded-full bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                                                <span className="material-symbols-outlined text-purple-600 dark:text-purple-400">summarize</span>
                                            </div>
                                            <h5 className="font-bold text-slate-900 dark:text-white mb-1">Summarize Session</h5>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">Get a quick overview of decisions and action items.</p>
                                        </button>

                                        <button
                                            onClick={() => {
                                                setInputMessage("Check availability for the next board meeting");
                                                inputRef.current?.focus();
                                            }}
                                            className="p-5 bg-white dark:bg-[#1a202c] border border-slate-200 dark:border-slate-700 rounded-2xl hover:border-green-400 dark:hover:border-green-500 hover:shadow-md dark:hover:bg-[#2d3748] transition-all group"
                                        >
                                            <div className="size-10 rounded-full bg-green-50 dark:bg-green-900/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                                                <span className="material-symbols-outlined text-green-600 dark:text-green-400">calendar_month</span>
                                            </div>
                                            <h5 className="font-bold text-slate-900 dark:text-white mb-1">Check Availability</h5>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">Find optimal times for cross-functional meetings.</p>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            messages.map((message) => (
                                <EnhancedMessageBubble
                                    key={message.id}
                                    message={{ ...message, approvalRequest: message.approvalRequest }}
                                    onReact={handleReact}
                                    onApprove={message.approvalRequest ? (id, mods) => handleEmailApprovalResolve(true, id, mods) : undefined}
                                    onDecline={message.approvalRequest ? (id) => handleEmailApprovalResolve(false, id) : undefined}
                                    onSuggestionClick={handleSuggestionClick}
                                />
                            ))
                        )}
                        {(isLoading || thinkingSteps.length > 0) && (
                            <ThinkingTimeline
                                steps={thinkingSteps}
                                isComplete={!isLoading && thinkingSteps.length > 0}
                                startTime={streamStartTime}
                                agentName={currentAgentName}
                            />
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="bg-white dark:bg-[#1a202c] border-t border-[#e7ebf3] dark:border-[#2d3748] p-4">


                        <div className="relative bg-white dark:bg-[#0d121b] border-2 border-[#e7ebf3] dark:border-[#2d3748] rounded-2xl shadow-lg focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500 dark:focus-within:border-blue-400 transition-all">
                            {autocompleteType === 'command' && commandSuggestions.length > 0 && (
                                <CommandAutocomplete
                                    suggestions={commandSuggestions}
                                    selectedIndex={selectedSuggestionIndex}
                                    onSelect={handleCommandSelect}
                                    onHover={setSelectedSuggestionIndex}
                                />
                            )}

                            {autocompleteType === 'mention' && mentionSuggestions.length > 0 && (
                                <MentionAutocomplete
                                    suggestions={mentionSuggestions}
                                    selectedIndex={selectedSuggestionIndex}
                                    onSelect={handleMentionSelect}
                                    onHover={setSelectedSuggestionIndex}
                                />
                            )}

                            <textarea
                                ref={inputRef}
                                value={inputMessage}
                                onChange={handleInputChange}
                                onKeyDown={handleKeyPress}
                                disabled={isLoading}
                                className="w-full bg-transparent border-none focus:ring-0 text-sm p-4 pr-36 min-h-[60px] max-h-32 resize-none text-[#0d121b] dark:text-white placeholder:text-[#9ca3af] disabled:opacity-50"
                                placeholder="Ask me anything... Use / for commands or @ for agents"
                            />
                            <div className="absolute bottom-3 right-3 flex items-center gap-1.5">
                                <button className="p-2 text-[#6b7280] dark:text-[#9ca3af] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all" title="Attach file">
                                    <span className="material-symbols-outlined text-[20px]">attach_file</span>
                                </button>
                                <button className="p-2 text-[#6b7280] dark:text-[#9ca3af] hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all" title="Voice input">
                                    <span className="material-symbols-outlined text-[20px]">mic</span>
                                </button>
                                <div className="w-px h-6 bg-[#e7ebf3] dark:bg-[#2d3748] mx-1"></div>
                                <button
                                    onClick={handleSendMessage}
                                    disabled={!inputMessage.trim() || isLoading}
                                    className="p-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-md"
                                    title="Send message"
                                >
                                    <span className="material-symbols-outlined text-[20px]">send</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Workspace Context Panel */}
                {showContextPanel && (
                    <WorkspaceContextPanel
                        twgName={activeTwg?.name || 'Loading...'}
                        twgId={activeTwg?.id}
                        onInsertContext={handleInsertContext}
                    />
                )}
            </main>

            {/* Modals */}
            {/* Modals */}
            {settingsOpen && (
                <SettingsModal
                    onClose={() => setSettingsOpen(false)}
                />
            )}

            {/* Email Approval Modal */}
            {/* Email Approval Modal */}
            {emailApprovalRequest && (
                <EmailApprovalModal
                    approvalRequest={emailApprovalRequest}
                    onApprove={(id, mods) => handleEmailApprovalResolve(true, id, mods)}
                    onDecline={(id, reason) => handleEmailApprovalResolve(false, id, undefined, reason)}
                    onClose={() => setEmailApprovalRequest(null)}
                />
            )}

            {/* Document Approval Modal */}
            {documentApprovalRequest && (
                <DocumentApprovalModal
                    approvalRequest={documentApprovalRequest}
                    onResolve={handleDocumentApprovalResolve}
                />
            )}
        </div>
    );
}
