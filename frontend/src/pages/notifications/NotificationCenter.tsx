import { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../hooks/useRedux';
import { Link } from 'react-router-dom';

import * as notificationService from '../../services/notificationService';
import { NotificationType } from '../../services/notificationService';
import { fetchNotifications, markRead, removeNotification, markAllRead } from '../../store/slices/notificationsSlice';

export default function NotificationCenter() {
    const dispatch = useAppDispatch();
    const { notifications, loading } = useAppSelector((state) => state.notifications);
    const [selectedNotificationId, setSelectedNotificationId] = useState<string | null>(null);

    const selectedNotification = notifications.find(n => n.id === selectedNotificationId) ||
        (notifications.length > 0 ? notifications[0] : null);

    useEffect(() => {
        dispatch(fetchNotifications());
    }, [dispatch]);

    const handleMarkAsRead = async (id: string) => {
        try {
            await notificationService.markAsRead(id);
            dispatch(markRead(id));
        } catch (error) {
            console.error("Error marking as read:", error);
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await notificationService.markAllAsRead();
            dispatch(markAllRead());
        } catch (error) {
            console.error("Error marking all as read:", error);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await notificationService.deleteNotification(id);
            dispatch(removeNotification(id));
            if (selectedNotificationId === id) {
                setSelectedNotificationId(null);
            }
        } catch (error) {
            console.error("Error deleting notification:", error);
        }
    };

    const getIcon = (type: NotificationType) => {
        switch (type) {
            case NotificationType.ALERT: return 'warning';
            case NotificationType.WARNING: return 'report_problem';
            case NotificationType.SUCCESS: return 'check_circle';
            case NotificationType.DOCUMENT: return 'description';
            case NotificationType.TASK: return 'task';
            case NotificationType.MESSAGE: return 'chat';
            default: return 'notifications';
        }
    };

    const getIconColor = (type: NotificationType): { color: string; background: string } => {
        switch (type) {
            case NotificationType.ALERT: return { color: 'var(--terra)', background: 'color-mix(in srgb, var(--terra) 12%, transparent)' };
            case NotificationType.WARNING: return { color: 'var(--amber)', background: 'color-mix(in srgb, var(--amber) 12%, transparent)' };
            case NotificationType.SUCCESS: return { color: 'var(--sage)', background: 'color-mix(in srgb, var(--sage) 12%, transparent)' };
            case NotificationType.DOCUMENT: return { color: 'var(--accent)', background: 'var(--accent-soft)' };
            case NotificationType.TASK: return { color: 'var(--navy)', background: 'color-mix(in srgb, var(--navy) 12%, transparent)' };
            default: return { color: 'var(--ink-500)', background: 'var(--surface-2)' };
        }
    };

    const formatTime = (dateString: string) => {
        // Force UTC interpretation if no timezone info is present
        // Backend sends naive UTC strings (e.g., "2023-01-01T12:00:00")
        // Browser defaults to local time for these, so we append 'Z' to treat as UTC
        const dateStr = dateString.endsWith('Z') || dateString.includes('+') ? dateString : `${dateString}Z`;
        const date = new Date(dateStr);
        const now = new Date();

        // Calculate difference in milliseconds
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        if (diffDays === 1) return 'Yesterday';
        return date.toLocaleDateString();
    };

    const isToday = (dateString: string) => {
        const date = new Date(dateString);
        const today = new Date();
        return date.getDate() === today.getDate() &&
            date.getMonth() === today.getMonth() &&
            date.getFullYear() === today.getFullYear();
    };

    const todayNotifications = notifications.filter(n => isToday(n.created_at));
    const earlierNotifications = notifications.filter(n => !isToday(n.created_at));

    return (
        <>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 gap-4">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black tracking-tight" style={{ color: 'var(--ink-900)' }}>Notification Center</h1>
                    <p className="font-medium mt-1 text-sm sm:text-base" style={{ color: 'var(--ink-500)' }}>Stay updated on TWG progress, mentions, and system alerts.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleMarkAllAsRead}
                        className="px-4 py-2 text-sm font-bold qp-transition"
                        style={{ color: 'var(--ink-500)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                    >
                        Mark all as read
                    </button>
                    <button
                        onClick={() => dispatch(fetchNotifications())}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold qp-transition"
                        style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ink-900)', cursor: 'pointer' }}
                    >
                        <span className="material-symbols-outlined text-[18px]">refresh</span>
                        Refresh
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-8 h-auto lg:h-[calc(100vh-280px)]">
                {/* Notification List Sidebar */}
                <div className="lg:col-span-1 rounded-2xl overflow-hidden flex flex-col max-h-[50vh] lg:max-h-none" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    <div className="p-4" style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                        <div className="flex items-center justify-between">
                            <h3 className="font-bold" style={{ color: 'var(--ink-900)' }}>Notifications</h3>
                            <span className="text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider" style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}>
                                <span className="font-mono-geist">{notifications.filter(n => !n.is_read).length}</span> Unread
                            </span>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto" style={{ borderTop: 'none' }}>
                        {loading && notifications.length === 0 ? (
                            <div className="p-8 text-center">
                                <div className="size-8 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-3" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
                                <p className="text-xs" style={{ color: 'var(--ink-500)' }}>Syncing alerts...</p>
                            </div>
                        ) : notifications.length === 0 ? (
                            <div className="p-8 text-center">
                                <span className="material-symbols-outlined text-4xl mb-2" style={{ color: 'var(--ink-300)' }}>notifications_off</span>
                                <p className="text-sm" style={{ color: 'var(--ink-500)' }}>All caught up!</p>
                            </div>
                        ) : (
                            <>
                                {todayNotifications.length > 0 && (
                                    <div className="py-2 px-4" style={{ background: 'var(--surface-2)' }}>
                                        <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: 'var(--ink-500)' }}>Today</span>
                                    </div>
                                )}
                                {todayNotifications.map(n => (
                                    <div
                                        key={n.id}
                                        onClick={() => {
                                            setSelectedNotificationId(n.id);
                                            if (!n.is_read) handleMarkAsRead(n.id);
                                        }}
                                        className="p-4 flex gap-4 cursor-pointer transition-all relative group"
                                        style={{
                                            borderTop: '1px solid var(--border-soft)',
                                            borderLeft: selectedNotification?.id === n.id ? '4px solid var(--accent)' : '4px solid transparent',
                                            background: selectedNotification?.id === n.id ? 'var(--accent-soft)' : 'transparent',
                                        }}
                                    >
                                        <div className="size-10 rounded-xl flex items-center justify-center shrink-0" style={getIconColor(n.type)}>
                                            <span className="material-symbols-outlined text-[20px]">{getIcon(n.type)}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-0.5">
                                                <h4 className="text-sm truncate" style={{ color: n.is_read ? 'var(--ink-500)' : 'var(--ink-900)', fontWeight: n.is_read ? 500 : 700 }}>{n.title}</h4>
                                                {!n.is_read && <div className="size-2 rounded-full shrink-0 ml-2" style={{ background: 'var(--accent)' }}></div>}
                                            </div>
                                            <p className="text-xs truncate" style={{ color: 'var(--ink-500)' }}>{n.content}</p>
                                            <span className="text-[10px] mt-1 block font-mono-geist" style={{ color: 'var(--ink-400)' }}>{formatTime(n.created_at)}</span>
                                        </div>
                                    </div>
                                ))}

                                {earlierNotifications.length > 0 && (
                                    <div className="py-2 px-4" style={{ background: 'var(--surface-2)' }}>
                                        <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: 'var(--ink-500)' }}>Earlier</span>
                                    </div>
                                )}
                                {earlierNotifications.map(n => (
                                    <div
                                        key={n.id}
                                        onClick={() => {
                                            setSelectedNotificationId(n.id);
                                            if (!n.is_read) handleMarkAsRead(n.id);
                                        }}
                                        className="p-4 flex gap-4 cursor-pointer transition-all relative group"
                                        style={{
                                            borderTop: '1px solid var(--border-soft)',
                                            borderLeft: selectedNotification?.id === n.id ? '4px solid var(--accent)' : '4px solid transparent',
                                            background: selectedNotification?.id === n.id ? 'var(--accent-soft)' : 'transparent',
                                        }}
                                    >
                                        <div className="size-10 rounded-xl flex items-center justify-center shrink-0" style={getIconColor(n.type)}>
                                            <span className="material-symbols-outlined text-[20px]">{getIcon(n.type)}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-0.5">
                                                <h4 className="text-sm truncate" style={{ color: n.is_read ? 'var(--ink-500)' : 'var(--ink-900)', fontWeight: n.is_read ? 500 : 700 }}>{n.title}</h4>
                                                {!n.is_read && <div className="size-2 rounded-full shrink-0 ml-2" style={{ background: 'var(--accent)' }}></div>}
                                            </div>
                                            <p className="text-xs truncate" style={{ color: 'var(--ink-500)' }}>{n.content}</p>
                                            <span className="text-[10px] mt-1 block font-mono-geist" style={{ color: 'var(--ink-400)' }}>{formatTime(n.created_at)}</span>
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                </div>

                {/* Notification Detail View */}
                <div className="lg:col-span-2 rounded-2xl flex flex-col overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    {selectedNotification ? (
                        <div className="flex flex-col h-full">
                            <div className="p-8 flex-1">
                                <div className="flex items-start justify-between mb-10">
                                    <div className="flex items-center gap-4">
                                        <div className="size-16 rounded-2xl flex items-center justify-center" style={getIconColor(selectedNotification.type)}>
                                            <span className="material-symbols-outlined text-[32px]">{getIcon(selectedNotification.type)}</span>
                                        </div>
                                        <div>
                                            <span className="text-[10px] font-black uppercase tracking-[0.2em]" style={{ color: 'var(--accent)' }}>{selectedNotification.type}</span>
                                            <h2 className="text-2xl font-black mt-1" style={{ color: 'var(--ink-900)' }}>{selectedNotification.title}</h2>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleDelete(selectedNotification.id)}
                                            className="p-2 rounded-lg transition-all qp-transition"
                                            style={{ color: 'var(--ink-500)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                                            title="Delete notification"
                                        >
                                            <span className="material-symbols-outlined">delete</span>
                                        </button>
                                    </div>
                                </div>

                                <div className="prose dark:prose-invert max-w-none">
                                    <p className="text-lg leading-relaxed font-medium" style={{ color: 'var(--ink-700)' }}>
                                        {selectedNotification.content}
                                    </p>
                                </div>

                                <div className="mt-12 rounded-2xl p-6 flex items-center justify-between group" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                                    <div className="flex items-center gap-4">
                                        <div className="size-12 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                                            <span className="material-symbols-outlined">link</span>
                                        </div>
                                        <div>
                                            <p className="text-xs font-black uppercase tracking-wider" style={{ color: 'var(--ink-500)' }}>Related Action</p>
                                            <p className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>View linked resource</p>
                                        </div>
                                    </div>
                                    {selectedNotification.link && selectedNotification.link.startsWith('http') ? (
                                        <a
                                            href={selectedNotification.link}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="px-6 py-2.5 text-sm font-bold rounded-xl transition-all active:scale-95"
                                            style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
                                        >
                                            Go to Detail
                                        </a>
                                    ) : (
                                        <Link
                                            to={selectedNotification.link || '#'}
                                            className="px-6 py-2.5 text-sm font-bold rounded-xl transition-all active:scale-95"
                                            style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
                                        >
                                            Go to Detail
                                        </Link>
                                    )}
                                </div>
                            </div>

                            <div className="p-8 flex items-center justify-between" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                                <div className="flex items-center gap-2" style={{ color: 'var(--ink-400)' }}>
                                    <span className="material-symbols-outlined text-[18px]">calendar_today</span>
                                    <span className="text-sm font-medium font-mono-geist">{formatTime(selectedNotification.created_at)}</span>
                                </div>
                                <div className="flex items-center gap-2" style={{ color: 'var(--ink-400)' }}>
                                    <span className="material-symbols-outlined text-[18px]">history</span>
                                    <span className="text-sm font-medium font-mono-geist">{new Date(selectedNotification.created_at).toLocaleTimeString()}</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                            <div className="size-24 rounded-full flex items-center justify-center mb-6" style={{ background: 'var(--surface-2)', color: 'var(--ink-300)' }}>
                                <span className="material-symbols-outlined text-[48px]">mark_email_read</span>
                            </div>
                            <h3 className="text-xl font-black" style={{ color: 'var(--ink-900)' }}>Select an alert to view details</h3>
                            <p className="mt-2 max-w-sm" style={{ color: 'var(--ink-500)' }}>
                                Track system events, TWG updates, and AI agent reports in high fidelity.
                            </p>
                        </div>
                    )}
                </div>
            </div>

        </>
    );
}
