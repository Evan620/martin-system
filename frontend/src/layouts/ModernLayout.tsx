import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../hooks/useRedux';
import { logout } from '../store/slices/authSlice';

import { fetchNotifications, addNotification } from '../store/slices/notificationsSlice';
import { UserRole } from '../types/auth';
import { NotificationType } from '../services/notificationService';
import { useEffect, useRef, useState } from 'react';
import GlobalCopilot from '../components/copilot/GlobalCopilot';
import ThemeToggle from '../components/ui/ThemeToggle';
import BottomTabBar from './BottomTabBar';

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
    const [isSidebarCollapsed] = useState(() => {
        const saved = localStorage.getItem('sidebar_collapsed');
        return saved !== null ? saved === 'true' : true;
    });
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [copilotOpen, setCopilotOpen] = useState(() => {
        const saved = localStorage.getItem('copilot_open');
        return saved !== null ? saved === 'true' : false;
    });

    // Close mobile menu on route change
    useEffect(() => {
        setIsMobileMenuOpen(false);
    }, [location.pathname]);

    // Persist copilot open state
    useEffect(() => {
        localStorage.setItem('copilot_open', String(copilotOpen));
    }, [copilotOpen]);

    useEffect(() => {
        localStorage.setItem('sidebar_collapsed', String(isSidebarCollapsed));
    }, [isSidebarCollapsed]);

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

    // Nav sections for the new design
    const navSections = [
        {
            label: 'Today',
            items: [
                { path: '/dashboard', icon: 'dashboard', label: 'Dashboard' },
                { path: '/schedule', icon: 'calendar_month', label: 'Meetings' },
                { path: '/actions', icon: 'task_alt', label: 'Actions' },
            ],
        },
        {
            label: 'Work',
            items: [
                { path: '/deal-pipeline', icon: 'work_outline', label: 'Deal Pipeline' },
                { path: '/twgs', icon: 'hub', label: 'TWG Agents' },
                { path: '/documents', icon: 'description', label: 'Documents' },
            ],
        },
        ...(isAdmin ? [{
            label: 'Management',
            items: [
                { path: '/admin/team', icon: 'group', label: 'Team' },
                { path: '/admin/invitations', icon: 'mail_outline', label: 'Org Invitations' },
                { path: '/admin/logs', icon: 'fact_check', label: 'Audit Logs' },
            ],
        }] : []),
    ];

    const userInitials = user?.full_name
        ? user.full_name.split(' ').map((s: string) => s[0]).join('').slice(0, 2).toUpperCase()
        : user?.email?.slice(0, 2).toUpperCase() || 'U';

    return (
        <div
            className="font-geist h-screen overflow-hidden flex"
            style={{ background: 'var(--bg)', color: 'var(--ink-900)', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}
        >
            {/* ── Sidebar ─────────────────────────────────────────────── */}
            <aside
                className="shrink-0 hidden lg:flex flex-col"
                style={{
                    width: 224,
                    background: 'var(--surface)',
                    borderRight: '1px solid var(--border)',
                    padding: '24px 14px 20px',
                }}
            >
                {/* Logo */}
                <div
                    className="flex items-center gap-2.5 cursor-pointer"
                    style={{ padding: '0 10px 22px' }}
                    onClick={() => navigate('/dashboard')}
                >
                    <div style={{
                        width: 26, height: 26, borderRadius: 6,
                        background: 'var(--accent)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: 'var(--accent-ink)',
                        fontFamily: "'Geist', serif",
                        fontSize: 14, fontWeight: 600,
                    }}>W</div>
                    <div>
                        <div style={{ fontFamily: "'Geist', serif", fontSize: 14, color: 'var(--ink-900)', lineHeight: 1.1, letterSpacing: '-0.01em' }}>
                            WAIIS
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--ink-500)', letterSpacing: '0.04em' }}>
                            TWG Workspace
                        </div>
                    </div>
                </div>

                {/* Nav sections */}
                <nav className="flex-1 flex flex-col overflow-y-auto no-scrollbar" style={{ gap: 18 }}>
                    {navSections.map(sec => (
                        <div key={sec.label}>
                            <div style={{
                                fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
                                color: 'var(--ink-400)', fontWeight: 500, padding: '0 10px 8px',
                            }}>{sec.label}</div>
                            <div className="flex flex-col">
                                {sec.items.map(item => {
                                    const on = location.pathname === item.path ||
                                        (location.pathname.startsWith(item.path + '/') &&
                                         !sec.items.some(other => other.path !== item.path && location.pathname.startsWith(other.path)));
                                    return (
                                        <button
                                            key={item.path}
                                            onClick={() => navigate(item.path)}
                                            className="relative flex items-center gap-2.5 text-left transition-colors clickable-scale"
                                            style={{
                                                padding: '7px 10px 7px 14px',
                                                fontSize: 13,
                                                fontWeight: on ? 500 : 400,
                                                color: on ? 'var(--ink-900)' : 'var(--ink-600)',
                                                background: on ? 'var(--accent-soft)' : 'transparent',
                                                borderRadius: 4,
                                                border: 'none',
                                                cursor: 'pointer',
                                                fontFamily: 'inherit',
                                            }}
                                        >
                                            {on && (
                                                <div style={{
                                                    position: 'absolute', left: 0, top: 8, bottom: 8, width: 2,
                                                    background: 'var(--accent)', borderRadius: 1,
                                                }} />
                                            )}
                                            <span className="material-symbols-outlined" style={{ fontSize: 18, color: on ? 'var(--accent)' : 'var(--ink-500)' }}>
                                                {item.icon}
                                            </span>
                                            <span>{item.label}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </nav>

                {/* User footer */}
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14, marginTop: 12 }}>
                    <div className="flex items-center justify-between" style={{ padding: '0 8px' }}>
                        <div
                            className="cursor-pointer"
                            title={`${user?.full_name || user?.email} — ${user?.role?.replace(/_/g, ' ')}`}
                            onClick={() => navigate('/profile')}
                            style={{
                                width: 32, height: 32, borderRadius: '50%',
                                overflow: 'hidden', flexShrink: 0,
                                border: '2px solid var(--border)',
                            }}
                        >
                            {user?.avatar ? (
                                <img src={user.avatar} alt={userInitials} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            ) : (
                                <div style={{
                                    width: '100%', height: '100%',
                                    background: 'var(--ink-200)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: 11, color: 'var(--ink-700)', fontWeight: 700,
                                }}>{userInitials}</div>
                            )}
                        </div>
                        <button
                            onClick={() => { dispatch(logout()); navigate('/login'); }}
                            title="Sign out"
                            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--terra)', display: 'flex', alignItems: 'center', padding: 4 }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>logout</span>
                        </button>
                    </div>
                </div>
            </aside>

            {/* ── Right side: topbar + main ───────────────────────────── */}
            <div className="flex-1 flex flex-col overflow-hidden min-w-0">
                {/* Top Bar */}
                <header
                    className="shrink-0 flex items-center justify-between"
                    style={{
                        height: 56,
                        borderBottom: '1px solid var(--border)',
                        background: 'var(--surface)',
                        padding: '0 32px',
                    }}
                >
                    {/* Mobile hamburger */}
                    <button
                        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                        className="lg:hidden mr-4"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-600)' }}
                    >
                        <span className="material-symbols-outlined">menu</span>
                    </button>

                    {/* Search */}
                    <div
                        className="hidden md:flex items-center gap-2"
                        style={{
                            padding: '6px 12px',
                            border: '1px solid var(--border)',
                            borderRadius: 6,
                            background: 'var(--ink-50)',
                            width: 320,
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--ink-500)' }}>search</span>
                        <input
                            className="bg-transparent border-none outline-none flex-1"
                            style={{ fontSize: 12, color: 'var(--ink-400)', fontFamily: 'inherit' }}
                            placeholder="Search projects, TWGs, investors… (⌘K)"
                            type="text"
                        />
                    </div>

                    {/* Right actions */}
                    <div className="flex items-center gap-4 ml-auto">
                        <span style={{ fontSize: 11, color: 'var(--ink-500)', fontFamily: "'Geist Mono', monospace" }} className="hidden md:block">
                            {new Date().toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()}
                        </span>
                        <button
                            onClick={() => navigate('/notifications')}
                            className="relative"
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-600)', display: 'flex', padding: 4 }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>notifications</span>
                            {unreadCount > 0 && (
                                <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                                    {unreadCount > 9 ? '9+' : unreadCount}
                                </span>
                            )}
                        </button>
                        <ThemeToggle />
                        <button
                            onClick={() => setCopilotOpen(!copilotOpen)}
                            className="flex items-center gap-1.5 clickable-scale qp-transition"
                            style={{
                                background: copilotOpen ? 'var(--accent)' : 'transparent',
                                color: copilotOpen ? 'var(--accent-ink)' : 'var(--ink-700)',
                                border: `1px solid ${copilotOpen ? 'var(--accent)' : 'var(--border)'}`,
                                padding: '7px 14px', borderRadius: 4, fontSize: 12, fontWeight: 500,
                                cursor: 'pointer', fontFamily: 'inherit',
                            }}
                        >
                            <span style={{ fontSize: 11 }}>✦</span> Ask Martin
                        </button>
                    </div>
                </header>

                {/* Mobile nav overlay */}
                {isMobileMenuOpen && (
                    <div className="fixed inset-0 z-40 lg:hidden">
                        <div className="absolute inset-0 bg-black/50" onClick={() => setIsMobileMenuOpen(false)} />
                        <div
                            className="absolute left-0 top-0 bottom-0 w-64 flex flex-col animate-slide-in-left"
                            style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}
                        >
                            <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border)' }}>
                                <div style={{ fontFamily: "'Geist', serif", fontSize: 15, color: 'var(--ink-900)' }}>WAIIS</div>
                                <button onClick={() => setIsMobileMenuOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)' }}>
                                    <span className="material-symbols-outlined">close</span>
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
                                {navSections.map(sec => (
                                    <div key={sec.label}>
                                        <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-400)', fontWeight: 500, marginBottom: 8 }}>
                                            {sec.label}
                                        </div>
                                        {sec.items.map(item => {
                                            const on = location.pathname === item.path;
                                            return (
                                                <button
                                                    key={item.path}
                                                    onClick={() => { navigate(item.path); setIsMobileMenuOpen(false); }}
                                                    className="w-full flex items-center gap-2.5 py-2 px-3 rounded text-sm transition-colors"
                                                    style={{
                                                        color: on ? 'var(--accent)' : 'var(--ink-700)',
                                                        background: on ? 'var(--accent-soft)' : 'transparent',
                                                        border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontWeight: on ? 500 : 400,
                                                    }}
                                                >
                                                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{item.icon}</span>
                                                    {item.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Main content + copilot row */}
                <div className="flex-1 flex overflow-hidden">
                    {location.pathname.startsWith('/twgs') ? (
                        <main className="flex-1 flex flex-col overflow-hidden min-w-0" style={{ background: 'var(--bg)' }}>
                            {children || <Outlet />}
                        </main>
                    ) : (
                    <main
                        className="flex-1 overflow-y-auto min-w-0 px-4 sm:px-6 lg:px-12 pt-4 sm:pt-6 lg:pt-10 pb-24 lg:pb-12 main-mobile-padding"
                        style={{ background: 'var(--bg)' }}
                    >
                        <div key={location.pathname} className="max-w-[1180px] mx-auto w-full animate-blur-slide">
                            {children || <Outlet />}
                        </div>
                    </main>
                    )}

                    {/* Copilot side panel */}
                    {copilotOpen && (
                        <div
                            className="hidden lg:flex w-[380px] shrink-0 overflow-hidden h-full min-h-0"
                            style={{ borderLeft: '1px solid var(--border)' }}
                        >
                            <div className="flex flex-col w-full h-full min-h-0">
                                <GlobalCopilot onClose={() => setCopilotOpen(false)} />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Mobile copilot overlay */}
            {copilotOpen && (
                <div className="lg:hidden fixed inset-0 z-50 flex flex-col" style={{ background: 'var(--surface)' }}>
                    <GlobalCopilot onClose={() => setCopilotOpen(false)} />
                </div>
            )}

            {/* Bottom tab bar — mobile only */}
            <BottomTabBar onMoreClick={() => setIsMobileMenuOpen(true)} />

            {/* Floating Ask Martin — shown when panel is closed */}
            {!copilotOpen && (
                <button
                    onClick={() => setCopilotOpen(true)}
                    className="fixed right-4 lg:right-6 z-40 flex items-center gap-2 bottom-20 lg:bottom-6 clickable-scale"
                    style={{
                        background: 'var(--accent)', color: 'var(--accent-ink)',
                        border: 'none', padding: '10px 18px', borderRadius: 999,
                        fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                        boxShadow: '0 4px 12px rgba(17,82,212,0.35)',
                    }}
                >
                    <span style={{ fontSize: 11 }}>✦</span>
                    <span>Martin</span>
                </button>
            )}
        </div>
    );
}
