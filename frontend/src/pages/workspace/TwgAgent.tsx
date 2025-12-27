import { useState, useRef, useEffect } from 'react';
import { agentService, Citation } from '../../services/agentService';
import { CommandAutocomplete } from '../../components/agent/CommandAutocomplete';
import { MentionAutocomplete } from '../../components/agent/MentionAutocomplete';
import EmailApprovalModal, { EmailApprovalRequest, EmailDraft } from '../../components/agent/EmailApprovalModal';
import SettingsModal from '../../components/agent/SettingsModal';
import { CommandAutocompleteResult } from '../../types/agent';
import axios from 'axios';

interface Message {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    citations?: Citation[];
}

// Function to parse and format markdown-like text
const formatMarkdownText = (text: string): JSX.Element => {
    const lines = text.split('\n');
    const elements: JSX.Element[] = [];

    lines.forEach((line, index) => {
        // Remove markdown bold syntax
        let formattedLine = line.replace(/\*\*(.*?)\*\*/g, '$1');

        // Handle numbered lists
        if (/^\d+\.\s/.test(formattedLine)) {
            const content = formattedLine.replace(/^\d+\.\s/, '');
            elements.push(
                <div key={index} className="mb-2">
                    <span className="font-semibold">{content}</span>
                </div>
            );
        }
        // Handle bullet points with - or *
        else if (/^\s*[-*]\s/.test(formattedLine)) {
            const indent = formattedLine.search(/[-*]/);
            const content = formattedLine.replace(/^\s*[-*]\s/, '');
            elements.push(
                <div key={index} className="mb-1" style={{ paddingLeft: `${indent * 8}px` }}>
                    • {content}
                </div>
            );
        }
        // Empty lines
        else if (formattedLine.trim() === '') {
            elements.push(<div key={index} className="h-2"></div>);
        }
        // Regular text
        else {
            elements.push(
                <div key={index} className="mb-1">
                    {formattedLine}
                </div>
            );
        }
    });

    return <>{elements}</>;
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
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | undefined>();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    // Autocomplete state
    const [commandSuggestions, setCommandSuggestions] = useState<CommandAutocompleteResult[]>([]);
    const [mentionSuggestions, setMentionSuggestions] = useState<AgentMentionSuggestion[]>([]);
    const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
    const [autocompleteType, setAutocompleteType] = useState<'command' | 'mention' | null>(null);

    // Email approval state
    const [pendingEmailApproval, setPendingEmailApproval] = useState<EmailApprovalRequest | null>(null);
    const [showApprovalModal, setShowApprovalModal] = useState(false);

    // Sidebar state
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    // Settings modal state
    const [showSettingsModal, setShowSettingsModal] = useState(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

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

        // Create new AbortController for this request
        abortControllerRef.current = new AbortController();

        try {
            const response = await agentService.chat({
                message: messageToSend,
                conversation_id: conversationId,
            });

            setConversationId(response.conversation_id);

            // Check if response contains an email approval request
            if (response.response.includes('Approval Required') || response.response.includes('approval_request_id')) {
                try {
                    // Try to extract approval request ID from response (handles markdown backticks)
                    const approvalMatch = response.response.match(/(?:approval_request_id|Approval Request ID)['":\s`*]+([a-f0-9-]{36})/i);
                    if (approvalMatch) {
                        const requestId = approvalMatch[1];
                        console.log('Found approval request ID:', requestId);

                        // Fetch the full approval request
                        const approvalData = await agentService.getEmailApproval(requestId);
                        console.log('Fetched approval data:', approvalData);

                        setPendingEmailApproval(approvalData);
                        setShowApprovalModal(true);
                    } else {
                        console.log('Could not extract approval request ID from response:', response.response);
                    }
                } catch (err) {
                    console.error('Error fetching approval request:', err);
                }
            }

            const agentMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: response.response,
                timestamp: new Date(),
                citations: response.citations,
            };

            setMessages(prev => [...prev, agentMessage]);
        } catch (error: any) {
            // Don't show error if request was aborted
            if (error?.name === 'AbortError' || error?.message?.includes('abort')) {
                console.log('Request aborted by user');
            } else {
                console.error('Error sending message:', error);
                const errorMessage: Message = {
                    id: (Date.now() + 1).toString(),
                    role: 'agent',
                    content: 'Sorry, I encountered an error processing your request. Please try again.',
                    timestamp: new Date(),
                };
                setMessages(prev => [...prev, errorMessage]);
            }
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
        }
    };

    // Detect slash commands and @mentions in input
    const handleInputChange = async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        setInputMessage(value);

        // Get cursor position
        const cursorPosition = e.target.selectionStart;
        const textBeforeCursor = value.substring(0, cursorPosition);

        // Check for command trigger (/)
        const commandMatch = textBeforeCursor.match(/\/(\w*)$/);
        if (commandMatch) {
            const query = '/' + commandMatch[1];
            try {
                const response = await axios.get(`/api/agents/commands/autocomplete`, {
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

        // Check for mention trigger (@)
        const mentionMatch = textBeforeCursor.match(/@(\w*)$/);
        if (mentionMatch) {
            const query = '@' + mentionMatch[1];
            try {
                const response = await axios.get(`/api/agents/mentions/autocomplete`, {
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
        // Replace the partial command with the full command
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

            // Focus input and set cursor position
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
        // Replace the partial mention with the full mention
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

            // Focus input and set cursor position
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
        // Handle autocomplete navigation
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

        // Normal message send
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Clear conversation handler
    const handleClearConversation = () => {
        if (messages.length === 0 && !isLoading) return;

        if (window.confirm('Are you sure you want to clear this conversation? This action cannot be undone.')) {
            // Abort any ongoing request
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
            }

            // Clear state
            setMessages([]);
            setConversationId(undefined);
            setIsLoading(false);
        }
    };

    // Email approval handlers
    const handleApproveEmail = async (requestId: string, modifications?: EmailDraft) => {
        try {
            const approvalData = {
                request_id: requestId,
                approved: true,
                modifications: modifications || null
            };

            const result = await agentService.approveEmail(requestId, approvalData);

            // Close modal
            setShowApprovalModal(false);
            setPendingEmailApproval(null);

            // Add success message
            const successMessage: Message = {
                id: Date.now().toString(),
                role: 'agent',
                content: result.email_sent
                    ? `✅ Email sent successfully! Message ID: ${result.message_id}`
                    : `⚠️ ${result.message}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, successMessage]);
        } catch (error) {
            console.error('Error approving email:', error);
            const errorMessage: Message = {
                id: Date.now().toString(),
                role: 'agent',
                content: `❌ Failed to send email: ${error}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        }
    };

    const handleDeclineEmail = async (requestId: string, reason?: string) => {
        try {
            await agentService.declineEmail(requestId, reason);

            // Close modal
            setShowApprovalModal(false);
            setPendingEmailApproval(null);

            // Add decline message
            const declineMessage: Message = {
                id: Date.now().toString(),
                role: 'agent',
                content: `🚫 Email sending cancelled: ${reason || 'Declined by user'}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, declineMessage]);
        } catch (error) {
            console.error('Error declining email:', error);
        }
    };

    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white h-screen flex flex-col overflow-hidden">
            {/* Top Navbar */}
            <header className="sticky top-0 z-50 w-full bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748] shrink-0">
                <div className="px-6 lg:px-10 py-3 flex items-center justify-between gap-6">
                    <div className="flex items-center gap-8">
                        {/* Brand */}
                        <div className="flex items-center gap-3">
                            <div className="size-8 rounded-full bg-[#1152d4]/10 flex items-center justify-center text-[#1152d4]">
                                <span className="material-symbols-outlined">shield_person</span>
                            </div>
                            <h2 className="text-lg font-bold leading-tight tracking-[-0.015em] hidden sm:block">ECOWAS Summit TWG Support</h2>
                        </div>
                        {/* Search */}
                        <div className="hidden md:flex items-center bg-[#f0f2f5] dark:bg-[#2d3748] rounded-lg h-10 w-64 px-3 gap-2">
                            <span className="material-symbols-outlined text-[#4c669a] dark:text-[#a0aec0]">search</span>
                            <input
                                className="bg-transparent border-none outline-none text-sm w-full placeholder:text-[#4c669a] dark:placeholder:text-[#a0aec0] text-[#0d121b] dark:text-white focus:ring-0 p-0"
                                placeholder="Search Workspace..."
                                type="text"
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        {/* Nav Links */}
                        <nav className="hidden lg:flex items-center gap-6">
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="/dashboard">Dashboard</a>
                            <a className="text-[#1152d4] dark:text-white text-sm font-medium transition-colors" href="/twgs">TWGs</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Reports</a>
                            <a className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors" href="#">Settings</a>
                        </nav>
                        {/* User Profile */}
                        <div className="flex items-center gap-4 border-l border-[#e7ebf3] dark:border-[#2d3748] pl-6">
                            <button className="relative text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white transition-colors">
                                <span className="material-symbols-outlined">notifications</span>
                            </button>
                            <div className="h-10 w-10 rounded-full bg-cover bg-center border border-[#e7ebf3] dark:border-[#2d3748] bg-gray-300"></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex overflow-hidden">
                {/* Sidebar */}
                <aside className={`${isSidebarCollapsed ? 'w-0' : 'w-80'} bg-white dark:bg-[#1a202c] border-r border-[#e7ebf3] dark:border-[#2d3748] flex flex-col transition-all duration-300 overflow-hidden hidden lg:flex`}>
                    <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Active Workspace</div>
                            <button
                                onClick={() => setIsSidebarCollapsed(true)}
                                className="p-1 hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded transition-colors"
                                title="Collapse sidebar"
                            >
                                <span className="material-symbols-outlined text-[18px] text-[#6b7280]">chevron_left</span>
                            </button>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="size-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-[#1152d4] flex items-center justify-center">
                                <span className="material-symbols-outlined">local_shipping</span>
                            </div>
                            <div>
                                <h3 className="font-bold text-[#0d121b] dark:text-white leading-tight">Trade & Customs</h3>
                                <p className="text-xs text-[#4c669a] dark:text-[#a0aec0]">Member States: 15</p>
                            </div>
                            <button className="ml-auto text-[#4c669a] hover:text-[#1152d4]">
                                <span className="material-symbols-outlined">expand_more</span>
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                        <div>
                            <h4 className="px-2 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">AI Agents</h4>
                            <div className="space-y-1">
                                {/* Secretariat Assistant (Main Supervisor) */}
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 bg-[#1152d4]/10 text-[#1152d4] dark:text-blue-400 rounded-lg transition-colors">
                                    <div className="relative">
                                        <span className="material-symbols-outlined">smart_toy</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-bold text-sm">Secretariat Assistant</div>
                                        <div className="text-[11px] opacity-80">Main Coordinator</div>
                                    </div>
                                </button>

                                {/* TWG Agents */}
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative size-8 rounded-full bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center flex-shrink-0">
                                        <span className="material-symbols-outlined text-white text-[16px]">bolt</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Energy Agent</div>
                                        <div className="text-[11px] opacity-70">@EnergyAgent</div>
                                    </div>
                                </button>

                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative size-8 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center flex-shrink-0">
                                        <span className="material-symbols-outlined text-white text-[16px]">agriculture</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Agriculture Agent</div>
                                        <div className="text-[11px] opacity-70">@AgricultureAgent</div>
                                    </div>
                                </button>

                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative size-8 rounded-full bg-gradient-to-br from-gray-500 to-slate-600 flex items-center justify-center flex-shrink-0">
                                        <span className="material-symbols-outlined text-white text-[16px]">science</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Minerals Agent</div>
                                        <div className="text-[11px] opacity-70">@MineralsAgent</div>
                                    </div>
                                </button>

                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative size-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                                        <span className="material-symbols-outlined text-white text-[16px]">computer</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Digital Agent</div>
                                        <div className="text-[11px] opacity-70">@DigitalAgent</div>
                                    </div>
                                </button>

                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative size-8 rounded-full bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center flex-shrink-0">
                                        <span className="material-symbols-outlined text-white text-[16px]">gavel</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Protocol Agent</div>
                                        <div className="text-[11px] opacity-70">@ProtocolAgent</div>
                                    </div>
                                </button>

                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative size-8 rounded-full bg-gradient-to-br from-amber-500 to-yellow-600 flex items-center justify-center flex-shrink-0">
                                        <span className="material-symbols-outlined text-white text-[16px]">account_balance</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Resource Agent</div>
                                        <div className="text-[11px] opacity-70">@ResourceAgent</div>
                                    </div>
                                </button>
                            </div>
                        </div>

                        <div>
                            <h4 className="px-2 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">Chat History</h4>
                            <div className="space-y-2 max-h-96 overflow-y-auto">
                                {messages.length === 0 ? (
                                    <div className="px-3 py-6 text-center">
                                        <span className="material-symbols-outlined text-[#9ca3af] text-[32px] mb-2 block">chat_bubble_outline</span>
                                        <p className="text-xs text-[#9ca3af]">No messages yet</p>
                                    </div>
                                ) : (
                                    messages.map((message) => (
                                        <div
                                            key={message.id}
                                            className="flex items-start gap-2 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg group cursor-pointer transition-colors"
                                        >
                                            <div className="flex-shrink-0 mt-0.5">
                                                {message.role === 'user' ? (
                                                    <div className="size-6 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-white text-[14px]">person</span>
                                                    </div>
                                                ) : (
                                                    <div className="size-6 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-white text-[14px]">smart_toy</span>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-xs font-medium text-[#0d121b] dark:text-white truncate">
                                                    {message.role === 'user' ? 'You' : 'Assistant'}
                                                </div>
                                                <div className="text-[11px] text-[#6b7280] dark:text-[#9ca3af] truncate">
                                                    {message.content.substring(0, 50)}{message.content.length > 50 ? '...' : ''}
                                                </div>
                                                <div className="text-[10px] text-[#9ca3af] mt-0.5">
                                                    {message.timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </aside>

                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-[#f6f6f8] dark:bg-[#0d121b]">
                    {/* Agent Header */}
                    <div className="bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748] px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {/* Expand sidebar button (shown when collapsed) */}
                            {isSidebarCollapsed && (
                                <button
                                    onClick={() => setIsSidebarCollapsed(false)}
                                    className="p-2 hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors"
                                    title="Expand sidebar"
                                >
                                    <span className="material-symbols-outlined text-[#6b7280]">menu</span>
                                </button>
                            )}
                            <div className="relative">
                                <div className="size-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white">
                                    <span className="material-symbols-outlined">smart_toy</span>
                                </div>
                                <span className="absolute bottom-0 right-0 size-3 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                            </div>
                            <div>
                                <h3 className="font-bold text-[#0d121b] dark:text-white">Secretariat Assistant</h3>
                                <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                                    <span className="size-1.5 bg-green-500 rounded-full"></span>
                                    Online
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {isLoading && (
                                <button
                                    onClick={() => {
                                        if (abortControllerRef.current) {
                                            abortControllerRef.current.abort();
                                            abortControllerRef.current = null;
                                        }
                                        setIsLoading(false);
                                    }}
                                    className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                    title="Stop generation"
                                >
                                    <span className="material-symbols-outlined">stop_circle</span>
                                </button>
                            )}
                            <button
                                onClick={() => setShowSettingsModal(true)}
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
                            <div className="h-full flex items-center justify-center px-4">
                                <div className="max-w-4xl w-full">
                                    <div className="text-center mb-12">
                                        <div className="size-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 flex items-center justify-center backdrop-blur-sm">
                                            <span className="material-symbols-outlined text-blue-600 dark:text-blue-400" style={{ fontSize: '48px' }}>chat_bubble</span>
                                        </div>
                                        <h3 className="text-2xl font-semibold text-[#0d121b] dark:text-white mb-3">Welcome to ECOWAS Summit Assistant</h3>
                                        <p className="text-base text-[#6b7280] dark:text-[#9ca3af] max-w-xl mx-auto leading-relaxed">
                                            I'm here to help with TWG coordination, document drafting, and summit preparation. What can I assist you with today?
                                        </p>
                                    </div>

                                    {/* Available Commands */}
                                    <div className="mb-8">
                                        <h4 className="text-sm font-semibold text-[#0d121b] dark:text-white mb-4 flex items-center gap-2">
                                            <span className="material-symbols-outlined text-[20px] text-blue-600">terminal</span>
                                            Quick Commands
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                                        <span className="material-symbols-outlined text-[20px] text-blue-600 dark:text-blue-400">email</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-1">/email</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af] leading-relaxed">Send emails or search inbox</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-lg bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                                        <span className="material-symbols-outlined text-[20px] text-purple-600 dark:text-purple-400">search</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-1">/search</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af] leading-relaxed">Search knowledge base</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-green-300 dark:hover:border-green-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-lg bg-green-50 dark:bg-green-900/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                                        <span className="material-symbols-outlined text-[20px] text-green-600 dark:text-green-400">event</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-1">/schedule</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af] leading-relaxed">Check schedules or create meetings</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-orange-300 dark:hover:border-orange-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-lg bg-orange-50 dark:bg-orange-900/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                                        <span className="material-symbols-outlined text-[20px] text-orange-600 dark:text-orange-400">description</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-1">/draft</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af] leading-relaxed">Draft documents</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                                        <span className="material-symbols-outlined text-[20px] text-indigo-600 dark:text-indigo-400">analytics</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-1">/analyze</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af] leading-relaxed">Analyze documents or data</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-pink-300 dark:hover:border-pink-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-lg bg-pink-50 dark:bg-pink-900/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                                        <span className="material-symbols-outlined text-[20px] text-pink-600 dark:text-pink-400">campaign</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-1">/broadcast</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af] leading-relaxed">Broadcast to all TWGs</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Available Agents */}
                                    <div>
                                        <h4 className="text-sm font-semibold text-[#0d121b] dark:text-white mb-4 flex items-center gap-2">
                                            <span className="material-symbols-outlined text-[20px] text-purple-600">alternate_email</span>
                                            TWG Specialist Agents
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-orange-300 dark:hover:border-orange-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-full bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                                                        <span className="material-symbols-outlined text-white text-[18px]">bolt</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-0.5">@EnergyAgent</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Energy & Infrastructure TWG</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-emerald-300 dark:hover:border-emerald-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                                                        <span className="material-symbols-outlined text-white text-[18px]">agriculture</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-0.5">@AgricultureAgent</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Agriculture & Food Security TWG</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-full bg-gradient-to-br from-gray-500 to-slate-600 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                                                        <span className="material-symbols-outlined text-white text-[18px]">science</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-0.5">@MineralsAgent</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Mineral Industrialization TWG</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-cyan-300 dark:hover:border-cyan-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                                                        <span className="material-symbols-outlined text-white text-[18px]">computer</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-0.5">@DigitalAgent</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Digital Economy TWG</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-rose-300 dark:hover:border-rose-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-full bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                                                        <span className="material-symbols-outlined text-white text-[18px]">gavel</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-0.5">@ProtocolAgent</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Protocol & Procedures TWG</div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="group bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-xl p-4 hover:border-amber-300 dark:hover:border-amber-600 hover:shadow-md transition-all cursor-pointer">
                                                <div className="flex items-start gap-3">
                                                    <div className="size-10 rounded-full bg-gradient-to-br from-amber-500 to-yellow-600 flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                                                        <span className="material-symbols-outlined text-white text-[18px]">account_balance</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="text-sm font-semibold text-[#0d121b] dark:text-white font-mono mb-0.5">@ResourceAgent</div>
                                                        <div className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Resource Mobilization TWG</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            messages.map((message) => (
                                <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                                    {message.role === 'agent' && (
                                        <div className="size-9 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white shrink-0 shadow-md">
                                            <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                                        </div>
                                    )}
                                    <div className={`max-w-[75%] ${message.role === 'user' ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg' : 'bg-white dark:bg-[#1a202c] shadow-md border border-[#e7ebf3] dark:border-[#2d3748]'} rounded-2xl p-4`}>
                                        <div className={`text-sm leading-relaxed ${message.role === 'agent' ? 'text-[#0d121b] dark:text-white' : 'text-white'}`}>
                                            {message.role === 'agent' ? formatMarkdownText(message.content) : message.content}
                                        </div>
                                        {message.citations && message.citations.length > 0 && (
                                            <div className="mt-4 pt-3 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                                <div className="text-xs font-semibold text-[#6b7280] dark:text-[#9ca3af] mb-2 flex items-center gap-1">
                                                    <span className="material-symbols-outlined text-[14px]">library_books</span>
                                                    Sources
                                                </div>
                                                {message.citations.map((citation, idx) => (
                                                    <div key={idx} className="text-xs text-[#6b7280] dark:text-[#9ca3af] flex items-center gap-2 mb-1.5 hover:text-blue-600 dark:hover:text-blue-400 transition-colors cursor-pointer">
                                                        <span className="material-symbols-outlined text-[14px]">article</span>
                                                        <span>{citation.source} (Page {citation.page})</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        <div className={`text-[10px] mt-2.5 ${message.role === 'user' ? 'text-white/70' : 'text-[#9ca3af]'}`}>
                                            {message.timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    {message.role === 'user' && (
                                        <div className="size-9 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center shrink-0 shadow-md">
                                            <span className="material-symbols-outlined text-white text-[18px]">person</span>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                        {isLoading && (
                            <div className="flex gap-3 justify-start animate-in fade-in duration-300">
                                <div className="size-9 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white shrink-0 shadow-md">
                                    <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                                </div>
                                <div className="bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-2xl p-4 shadow-md">
                                    <div className="flex gap-1.5 items-center">
                                        <div className="size-2.5 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="size-2.5 bg-purple-600 dark:bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="size-2.5 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="bg-white dark:bg-[#1a202c] border-t border-[#e7ebf3] dark:border-[#2d3748] p-4">
                        <div className="flex gap-2 mb-3 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
                            <button className="shrink-0 text-xs font-medium px-4 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-700 dark:text-blue-300 transition-all flex items-center gap-1.5 border border-blue-200 dark:border-blue-800 hover:shadow-sm">
                                <span className="material-symbols-outlined text-[16px]">description</span>
                                Draft Minutes
                            </button>
                            <button className="shrink-0 text-xs font-medium px-4 py-2 rounded-lg bg-purple-50 dark:bg-purple-900/20 hover:bg-purple-100 dark:hover:bg-purple-900/30 text-purple-700 dark:text-purple-300 transition-all flex items-center gap-1.5 border border-purple-200 dark:border-purple-800 hover:shadow-sm">
                                <span className="material-symbols-outlined text-[16px]">summarize</span>
                                Summarize Last Session
                            </button>
                            <button className="shrink-0 text-xs font-medium px-4 py-2 rounded-lg bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/30 text-green-700 dark:text-green-300 transition-all flex items-center gap-1.5 border border-green-200 dark:border-green-800 hover:shadow-sm">
                                <span className="material-symbols-outlined text-[16px]">calendar_month</span>
                                Check Availability
                            </button>
                        </div>

                        <div className="relative bg-white dark:bg-[#0d121b] border-2 border-[#e7ebf3] dark:border-[#2d3748] rounded-2xl shadow-lg focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500 dark:focus-within:border-blue-400 transition-all">
                            {/* Command Autocomplete */}
                            {autocompleteType === 'command' && commandSuggestions.length > 0 && (
                                <CommandAutocomplete
                                    suggestions={commandSuggestions}
                                    selectedIndex={selectedSuggestionIndex}
                                    onSelect={handleCommandSelect}
                                    onHover={setSelectedSuggestionIndex}
                                />
                            )}

                            {/* Mention Autocomplete */}
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
            </main>

            {/* Email Approval Modal */}
            {showApprovalModal && pendingEmailApproval && (
                <EmailApprovalModal
                    approvalRequest={pendingEmailApproval}
                    onApprove={handleApproveEmail}
                    onDecline={handleDeclineEmail}
                    onClose={() => {
                        setShowApprovalModal(false);
                        setPendingEmailApproval(null);
                    }}
                />
            )}

            {/* Settings Modal */}
            {showSettingsModal && (
                <SettingsModal
                    onClose={() => setShowSettingsModal(false)}
                />
            )}
        </div>
    );
}
