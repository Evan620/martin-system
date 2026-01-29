import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { logout } from '../store/slices/authSlice';
import { fetchNotifications, addNotification } from '../store/slices/notificationsSlice';
import { UserRole } from '../types/auth';
import { NotificationType } from '../services/notificationService';
import { useEffect, useRef, useState } from 'react';

interface ModernLayoutProps {
    children?: React.ReactNode;
}

export default function ModernLayout({ children }: ModernLayoutProps) {
    const navigate = useNavigate();
    const location = useLocation();
    const dispatch = useAppDispatch();
    const { user } = useAppSelector((state) => state.auth)
    const { unreadCount } = useAppSelector((state) => state.notifications)
    const token = useAppSelector((state) => state.auth.token);
    const socketRef = useRef<WebSocket | null>(null);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    useEffect(() => {
        if (token) {
            dispatch(fetchNotifications());

            const setupWebSocket = () => {
                const envUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
                const baseUrl = envUrl.replace('localhost', '127.0.0.1');
                const wsUrl = `${baseUrl.replace('http', 'ws')}/dashboard/ws?token=${token}`;

                const socket = new WebSocket(wsUrl);
                socketRef.current = socket;

                socket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        if (message.type === 'NEW_NOTIFICATION') {
                            dispatch(addNotification(message.data));
                        } else if (message.type === 'transcript_processed' || message.type === 'MEETING_UPDATED') {
                            // Dispatch custom event for components to listen to
                            const event = new CustomEvent('meeting-update', {
                                detail: {
                                    meetingId: message.data?.meeting_id || message.meeting_id,
                                    type: message.type
                                }
                            });
                            window.dispatchEvent(event);

                            // Also show notification if relevant
                            if (message.data?.message) {
                                dispatch(addNotification({
                                    id: Date.now().toString(),
                                    user_id: user?.id || 'current-user',
                                    title: 'Meeting Updated',
                                    content: message.data.message,
                                    type: NotificationType.INFO,
                                    is_read: false,
                                    created_at: new Date().toISOString()
                                }));
                            }
                        }
                    } catch (err) {
                        console.error('Error parsing WebSocket message:', err);
                    }
                };

                socket.onclose = () => {
                    setTimeout(() => {
                        if (token) setupWebSocket();
                    }, 5000);
                };
            };

            setupWebSocket();
        }

        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, [token, dispatch]);

    const isAdmin = user?.role === UserRole.ADMIN || user?.role === UserRole.SECRETARIAT_LEAD;
    const isFacilitator = user?.role === UserRole.FACILITATOR || user?.role === UserRole.SECRETARIAT_LEAD || isAdmin;

    const isActive = (path: string) => location.pathname === path;

    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white h-screen overflow-hidden flex flex-col">
            {/* Top Navbar */}
            <header className="sticky top-0 z-50 w-full bg-white dark:bg-[#1a202c] border-b border-[#e7ebf3] dark:border-[#2d3748]">
                <div className="px-6 lg:px-10 py-3 flex items-center justify-between gap-6">
                    <div className="flex items-center gap-8">
                        {/* Brand */}
                        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/dashboard')}>
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
                                placeholder="Search TWGs, Agents, Reports..."
                                type="text"
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        {/* Nav Links */}
                        <nav className="hidden lg:flex items-center gap-6">
                            <button
                                onClick={() => navigate('/dashboard')}
                                className={`${isActive('/dashboard') ? 'text-[#1152d4]' : 'text-[#4c669a] dark:text-[#a0aec0]'} font-medium text-sm hover:text-[#1152d4] transition-colors`}
                            >
                                Dashboard
                            </button>
                            <button
                                onClick={() => navigate('/twgs')}
                                className={`${isActive('/twgs') ? 'text-[#1152d4]' : 'text-[#4c669a] dark:text-[#a0aec0]'} font-medium text-sm hover:text-[#1152d4] transition-colors`}
                            >
                                TWG Agents
                            </button>
                            {isFacilitator && (
                                <button className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors">
                                    Reports
                                </button>
                            )}
                        </nav>
                        {/* User Profile & Actions */}
                        <div className="flex items-center gap-4 border-l border-[#e7ebf3] dark:border-[#2d3748] pl-6">
                            <button
                                onClick={() => navigate('/notifications')}
                                className={`relative p-1 ${isActive('/notifications') ? 'text-[#1152d4]' : 'text-[#4c669a] dark:text-[#a0aec0]'} hover:text-[#1152d4] transition-colors`}
                            >
                                <span className="material-symbols-outlined">notifications</span>
                                {unreadCount > 0 && (
                                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white ring-2 ring-white dark:ring-[#1a202c] animate-pulse">
                                        {unreadCount > 9 ? '9+' : unreadCount}
                                    </span>
                                )}
                            </button>
                            <div
                                onClick={() => navigate('/profile')}
                                className="h-10 w-10 rounded-full bg-cover bg-center border border-[#e7ebf3] dark:border-[#2d3748] bg-gray-300 cursor-pointer"
                            ></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content with Sidebar */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Sidebar Navigation */}
                <aside className={`bg-white dark:bg-[#1a202c] border-r border-[#e7ebf3] dark:border-[#2d3748] hidden lg:block shrink-0 transition-all duration-300 ${isSidebarCollapsed ? 'w-20' : 'w-64'}`}>
                    <div className={`flex flex-col h-full ${isSidebarCollapsed ? 'p-3' : 'p-6'} transition-all duration-300`}>
                        <div className="flex-1 space-y-6 overflow-y-auto custom-scrollbar">
                            <div>
                                {!isSidebarCollapsed && (
                                    <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3 px-3 transition-opacity duration-300">
                                        Navigation
                                    </div>
                                )}
                                <div className="space-y-1">
                                    <button
                                        onClick={() => navigate('/dashboard')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/dashboard')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                        title={isSidebarCollapsed ? "Dashboard" : ""}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">dashboard</span>
                                        {!isSidebarCollapsed && <span>Dashboard</span>}
                                    </button>
                                    <button
                                        onClick={() => navigate('/twgs')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/twgs')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                        title={isSidebarCollapsed ? "TWG Agents" : ""}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                                        {!isSidebarCollapsed && <span>TWG Agents</span>}
                                    </button>
                                    <button
                                        onClick={() => navigate('/documents')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/documents')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                        title={isSidebarCollapsed ? "Documents" : ""}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">folder</span>
                                        {!isSidebarCollapsed && <span>Documents</span>}
                                    </button>
                                    <button
                                        onClick={() => navigate('/schedule')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/schedule')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                        title={isSidebarCollapsed ? "Schedule" : ""}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">calendar_month</span>
                                        {!isSidebarCollapsed && <span>Meetings (Schedule)</span>}
                                    </button>

                                    <button
                                        onClick={() => navigate('/deal-pipeline')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/deal-pipeline')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                        title={isSidebarCollapsed ? "Deal Pipeline" : ""}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">work</span>
                                        {!isSidebarCollapsed && <span>Deal Pipeline</span>}
                                    </button>
                                    <button
                                        onClick={() => navigate('/conflicts')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/conflicts')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                        title={isSidebarCollapsed ? "Conflicts" : ""}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">warning</span>
                                        {!isSidebarCollapsed && <span>Conflicts</span>}
                                    </button>
                                </div>
                            </div>

                            {isAdmin && (
                                <div>
                                    {!isSidebarCollapsed && (
                                        <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3 px-3 transition-opacity duration-300">
                                            Management
                                        </div>
                                    )}
                                    <div className="space-y-1">
                                        <button
                                            onClick={() => navigate('/admin/team')}
                                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/admin/team')
                                                ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                                : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                                } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                            title={isSidebarCollapsed ? "Team" : ""}
                                        >
                                            <span className="material-symbols-outlined text-[20px]">badge</span>
                                            {!isSidebarCollapsed && <span>Team</span>}
                                        </button>
                                        <button
                                            onClick={() => navigate('/admin/control-tower')}
                                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/admin/control-tower')
                                                ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                                : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                                } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                            title={isSidebarCollapsed ? "Control Tower" : ""}
                                        >
                                            <span className="material-symbols-outlined text-[20px]">radar</span>
                                            {!isSidebarCollapsed && <span>Control Tower</span>}
                                        </button>
                                        <button
                                            onClick={() => navigate('/admin/logs')}
                                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/admin/logs')
                                                ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                                : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                                } ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                            title={isSidebarCollapsed ? "Logs" : ""}
                                        >
                                            <span className="material-symbols-outlined text-[20px]">history</span>
                                            {!isSidebarCollapsed && <span>Audit Logs</span>}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="pt-3 mt-3 border-t border-[#e7ebf3] dark:border-[#2d3748] space-y-1">
                            <button
                                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg font-medium text-sm text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748] transition-colors ${isSidebarCollapsed ? 'justify-center !px-2' : 'justify-end'}`}
                                title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
                            >
                                <span className="material-symbols-outlined">
                                    {isSidebarCollapsed ? 'last_page' : 'first_page'}
                                </span>
                            </button>

                            <button
                                onClick={() => {
                                    dispatch(logout());
                                    navigate('/login');
                                }}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-bold text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors ${isSidebarCollapsed ? 'justify-center !px-2' : ''}`}
                                title={isSidebarCollapsed ? "Sign Out" : ""}
                            >
                                <span className="material-symbols-outlined text-[20px]">logout</span>
                                {!isSidebarCollapsed && <span>Sign Out</span>}
                            </button>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 overflow-y-auto p-4 lg:p-6 pb-20">
                    <div className="max-w-[1440px] mx-auto w-full h-full">
                        {children || <Outlet />}
                    </div>
                </main>
            </div>
        </div>
    );
}
