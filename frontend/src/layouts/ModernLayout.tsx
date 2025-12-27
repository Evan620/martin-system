import { useNavigate, useLocation } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { logout } from '../store/slices/authSlice';
import { toggleTheme } from '../store/slices/themeSlice';
import { fetchNotifications, addNotification } from '../store/slices/notificationsSlice';
import { UserRole } from '../types/auth';
import { useEffect, useRef } from 'react';

interface ModernLayoutProps {
    children: React.ReactNode;
}

export default function ModernLayout({ children }: ModernLayoutProps) {
    const navigate = useNavigate();
    const location = useLocation();
    const dispatch = useAppDispatch();
    const theme = useAppSelector((state) => state.theme.mode);
    const user = useAppSelector((state) => state.auth.user);
    const unreadCount = useAppSelector((state) => state.notifications.unreadCount);
    const token = useAppSelector((state) => state.auth.token);
    const socketRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (token) {
            dispatch(fetchNotifications());

            const setupWebSocket = () => {
                const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
                const wsUrl = `${baseUrl.replace('http', 'ws')}/dashboard/ws?token=${token}`;

                const socket = new WebSocket(wsUrl);
                socketRef.current = socket;

                socket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        if (message.type === 'NEW_NOTIFICATION') {
                            dispatch(addNotification(message.data));
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

    const isAdmin = user?.role === UserRole.ADMIN;
    const isFacilitator = user?.role === UserRole.FACILITATOR || user?.role === UserRole.SECRETARIAT_LEAD || isAdmin;

    const isActive = (path: string) => location.pathname === path;

    return (
        <div className="font-display bg-background-light dark:bg-background-dark text-[#0d121b] dark:text-white min-h-screen flex flex-col">
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
                                TWGs
                            </button>
                            {isFacilitator && (
                                <button className="text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white text-sm font-medium transition-colors">
                                    Reports
                                </button>
                            )}
                            <button
                                onClick={() => navigate('/settings')}
                                className={`${isActive('/settings') ? 'text-[#1152d4]' : 'text-[#4c669a] dark:text-[#a0aec0]'} font-medium text-sm hover:text-[#1152d4] transition-colors`}
                            >
                                Settings
                            </button>
                        </nav>
                        {/* User Profile & Actions */}
                        <div className="flex items-center gap-4 border-l border-[#e7ebf3] dark:border-[#2d3748] pl-6">
                            <button
                                onClick={() => dispatch(toggleTheme())}
                                className="p-2 text-[#4c669a] dark:text-[#a0aec0] hover:text-[#1152d4] dark:hover:text-white transition-colors"
                                title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                            >
                                <span className="material-symbols-outlined">
                                    {theme === 'dark' ? 'light_mode' : 'dark_mode'}
                                </span>
                            </button>
                            <button
                                onClick={() => navigate('/notifications')}
                                className={`relative ${isActive('/notifications') ? 'text-[#1152d4]' : 'text-[#4c669a] dark:text-[#a0aec0]'} hover:text-[#1152d4] transition-colors`}
                            >
                                <span className="material-symbols-outlined">notifications</span>
                                <span className="absolute top-0 right-0 size-2 bg-red-500 rounded-full border-2 border-white dark:border-[#1a202c]"></span>
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
                <aside className="w-64 bg-white dark:bg-[#1a202c] border-r border-[#e7ebf3] dark:border-[#2d3748] hidden lg:block shrink-0">
                    <div className="p-6 space-y-6">
                        <div>
                            <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                Navigation
                            </div>
                            <div className="space-y-1">
                                <button
                                    onClick={() => navigate('/dashboard')}
                                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/dashboard')
                                        ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                        : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                        }`}
                                >
                                    <span className="material-symbols-outlined text-[20px]">dashboard</span>
                                    <span>Dashboard</span>
                                </button>
                                <button
                                    onClick={() => navigate('/twgs')}
                                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/twgs')
                                        ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                        : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                        }`}
                                >
                                    <span className="material-symbols-outlined text-[20px]">groups</span>
                                    <span>TWGs</span>
                                </button>
                                <button
                                    onClick={() => navigate('/documents')}
                                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/documents')
                                        ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                        : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                        }`}
                                >
                                    <span className="material-symbols-outlined text-[20px]">folder</span>
                                    <span>Documents</span>
                                </button>
                                <button
                                    onClick={() => navigate('/notifications')}
                                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/notifications')
                                        ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                        : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                        }`}
                                >
                                    <span className="material-symbols-outlined text-[20px]">notifications</span>
                                    <span>Notifications</span>
                                    {unreadCount > 0 && (
                                        <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                                            {unreadCount > 99 ? '99+' : unreadCount}
                                        </span>
                                    )}
                                </button>
                            </div>
                        </div>

                        {isAdmin && (
                            <div>
                                <div className="text-xs font-bold text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider mb-3">
                                    Admin
                                </div>
                                <div className="space-y-1">
                                    <button
                                        onClick={() => navigate('/admin/team')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/admin/team')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            }`}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">badge</span>
                                        <span>Team</span>
                                    </button>
                                    <button
                                        onClick={() => navigate('/settings')}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors ${isActive('/settings')
                                            ? 'bg-[#e8effe] dark:bg-[#1e3a8a]/20 text-[#1152d4] dark:text-[#60a5fa]'
                                            : 'text-[#4c669a] dark:text-[#a0aec0] hover:bg-[#f6f6f8] dark:hover:bg-[#2d3748]'
                                            }`}
                                    >
                                        <span className="material-symbols-outlined text-[20px]">settings</span>
                                        <span>Settings</span>
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="pt-6 mt-6 border-t border-[#e7ebf3] dark:border-[#2d3748]">
                            <button
                                onClick={() => {
                                    dispatch(logout());
                                    navigate('/login');
                                }}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-bold text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                            >
                                <span className="material-symbols-outlined text-[20px]">logout</span>
                                <span>Sign Out</span>
                            </button>
                        </div>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 overflow-y-auto p-6 lg:p-10">
                    <div className="max-w-[1440px] mx-auto w-full">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
