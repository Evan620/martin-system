import { useState, useRef, useEffect } from 'react';
import { agentService, AgentChatResponse, Citation } from '../../services/agentService';

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

export default function TwgAgent() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | undefined>();
    const messagesEndRef = useRef<HTMLDivElement>(null);

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
        setInputMessage('');
        setIsLoading(true);

        try {
            const response: AgentChatResponse = await agentService.chat({
                message: inputMessage,
                conversation_id: conversationId,
            });

            setConversationId(response.conversation_id);

            const agentMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: response.response,
                timestamp: new Date(),
                citations: response.citations,
            };

            setMessages(prev => [...prev, agentMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: 'Sorry, I encountered an error processing your request. Please try again.',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
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
                <aside className="w-80 bg-white dark:bg-[#1a202c] border-r border-[#e7ebf3] dark:border-[#2d3748] flex flex-col hidden lg:flex">
                    <div className="p-6 border-b border-[#e7ebf3] dark:border-[#2d3748]">
                        <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-2">Active Workspace</div>
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
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 bg-[#1152d4]/10 text-[#1152d4] dark:text-blue-400 rounded-lg transition-colors">
                                    <div className="relative">
                                        <span className="material-symbols-outlined">smart_toy</span>
                                        <span className="absolute -bottom-0.5 -right-0.5 size-2.5 border-2 border-white dark:border-[#1a202c] bg-green-500 rounded-full"></span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-bold text-sm">Secretariat Assistant</div>
                                        <div className="text-[11px] opacity-80">Drafting & Scheduling</div>
                                    </div>
                                </button>
                                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[#4c669a] dark:text-[#a0aec0] hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg transition-colors">
                                    <div className="relative">
                                        <span className="material-symbols-outlined">manage_search</span>
                                    </div>
                                    <div className="text-left flex-1">
                                        <div className="font-medium text-sm text-[#0d121b] dark:text-white">Research Analyst</div>
                                        <div className="text-[11px] opacity-70">Policy Data Retrieval</div>
                                    </div>
                                </button>
                            </div>
                        </div>

                        <div>
                            <h4 className="px-2 text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">Recent Context</h4>
                            <div className="space-y-2">
                                <a className="flex items-start gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg group" href="#">
                                    <span className="material-symbols-outlined text-[18px] text-[#4c669a] mt-0.5">description</span>
                                    <div>
                                        <div className="text-sm font-medium text-[#0d121b] dark:text-white group-hover:text-[#1152d4] transition-colors">Trade Protocol v2.pdf</div>
                                        <div className="text-[11px] text-[#4c669a]">Added yesterday</div>
                                    </div>
                                </a>
                                <a className="flex items-start gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#2d3748] rounded-lg group" href="#">
                                    <span className="material-symbols-outlined text-[18px] text-[#4c669a] mt-0.5">groups</span>
                                    <div>
                                        <div className="text-sm font-medium text-[#0d121b] dark:text-white group-hover:text-[#1152d4] transition-colors">Meeting Minutes - Oct 20</div>
                                        <div className="text-[11px] text-[#4c669a]">2 days ago</div>
                                    </div>
                                </a>
                            </div>
                        </div>
                    </div>
                </aside>

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
                                <h3 className="font-bold text-[#0d121b] dark:text-white">Secretariat Assistant</h3>
                                <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                                    <span className="size-1.5 bg-green-500 rounded-full"></span>
                                    Online
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button className="p-2 text-[#4c669a] hover:bg-gray-100 dark:hover:bg-[#2d3748] rounded-lg transition-colors" title="Clear conversation">
                                <span className="material-symbols-outlined">delete</span>
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-6">
                        {messages.length === 0 ? (
                            <div className="h-full flex items-center justify-center">
                                <div className="text-center max-w-md">
                                    <div className="size-16 mx-auto mb-4 rounded-full bg-[#1152d4]/10 flex items-center justify-center">
                                        <span className="material-symbols-outlined text-[#1152d4] text-3xl">chat</span>
                                    </div>
                                    <h3 className="text-lg font-bold text-[#0d121b] dark:text-white mb-2">Start a conversation</h3>
                                    <p className="text-sm text-[#4c669a] dark:text-[#a0aec0]">
                                        Ask me anything about the summit, request document drafts, or get help with your TWG tasks.
                                    </p>
                                </div>
                            </div>
                        ) : (
                            messages.map((message) => (
                                <div key={message.id} className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    {message.role === 'agent' && (
                                        <div className="size-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white shrink-0">
                                            <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                                        </div>
                                    )}
                                    <div className={`max-w-[70%] ${message.role === 'user' ? 'bg-[#1152d4] text-white' : 'bg-white dark:bg-[#1a202c]'} rounded-2xl p-4 shadow-sm`}>
                                        <div className={`text-sm leading-relaxed ${message.role === 'agent' ? 'text-[#0d121b] dark:text-white' : 'text-white'}`}>
                                            {message.role === 'agent' ? formatMarkdownText(message.content) : message.content}
                                        </div>
                                        {message.citations && message.citations.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                                                <div className="text-xs font-semibold text-[#4c669a] dark:text-[#a0aec0] mb-2">Sources:</div>
                                                {message.citations.map((citation, idx) => (
                                                    <div key={idx} className="text-xs text-[#4c669a] dark:text-[#a0aec0] flex items-center gap-2 mb-1">
                                                        <span className="material-symbols-outlined text-[14px]">article</span>
                                                        <span>{citation.source} (Page {citation.page})</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        <div className={`text-[10px] mt-2 ${message.role === 'user' ? 'text-white/70' : 'text-[#4c669a] dark:text-[#a0aec0]'}`}>
                                            {message.timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    {message.role === 'user' && (
                                        <div className="size-8 rounded-full bg-gray-300 dark:bg-gray-600 shrink-0"></div>
                                    )}
                                </div>
                            ))
                        )}
                        {isLoading && (
                            <div className="flex gap-4 justify-start">
                                <div className="size-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white shrink-0">
                                    <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                                </div>
                                <div className="bg-white dark:bg-[#1a202c] rounded-2xl p-4 shadow-sm">
                                    <div className="flex gap-1">
                                        <div className="size-2 bg-[#4c669a] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="size-2 bg-[#4c669a] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="size-2 bg-[#4c669a] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="bg-white dark:bg-[#1a202c] border-t border-[#e7ebf3] dark:border-[#2d3748] p-4">
                        <div className="flex gap-2 mb-3 overflow-x-auto pb-2">
                            <button className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-full border border-[#e7ebf3] dark:border-[#4a5568] hover:bg-gray-50 dark:hover:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] transition-colors flex items-center gap-1">
                                <span className="material-symbols-outlined text-[14px]">description</span>
                                Draft Minutes
                            </button>
                            <button className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-full border border-[#e7ebf3] dark:border-[#4a5568] hover:bg-gray-50 dark:hover:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] transition-colors flex items-center gap-1">
                                <span className="material-symbols-outlined text-[14px]">summarize</span>
                                Summarize Last Session
                            </button>
                            <button className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-full border border-[#e7ebf3] dark:border-[#4a5568] hover:bg-gray-50 dark:hover:bg-[#2d3748] text-[#4c669a] dark:text-[#a0aec0] transition-colors flex items-center gap-1">
                                <span className="material-symbols-outlined text-[14px]">calendar_month</span>
                                Check Room Availability
                            </button>
                        </div>

                        <div className="relative bg-white dark:bg-[#0d121b] border border-[#cfd7e7] dark:border-[#4a5568] rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-[#1152d4]/20 focus-within:border-[#1152d4] transition-all">
                            <textarea
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyPress={handleKeyPress}
                                disabled={isLoading}
                                className="w-full bg-transparent border-none focus:ring-0 text-sm p-4 pr-32 min-h-[56px] max-h-32 resize-none text-[#0d121b] dark:text-white placeholder:text-[#9ca3af] disabled:opacity-50"
                                placeholder="Type a message to your agent..."
                            />
                            <div className="absolute bottom-2 right-2 flex items-center gap-1">
                                <button className="p-2 text-[#4c669a] hover:text-[#0d121b] dark:hover:text-white rounded-lg transition-colors" title="Attach file">
                                    <span className="material-symbols-outlined text-[20px]">attach_file</span>
                                </button>
                                <button className="p-2 text-[#4c669a] hover:text-[#0d121b] dark:hover:text-white rounded-lg transition-colors" title="Voice input">
                                    <span className="material-symbols-outlined text-[20px]">mic</span>
                                </button>
                                <button
                                    onClick={handleSendMessage}
                                    disabled={!inputMessage.trim() || isLoading}
                                    className="p-2 bg-[#1152d4] text-white rounded-lg hover:bg-[#0d3ea8] transition-colors shadow-sm ml-1 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <span className="material-symbols-outlined text-[20px]">send</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
