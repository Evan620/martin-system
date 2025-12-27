import { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../hooks/useRedux';
import ModernLayout from '../../layouts/ModernLayout';
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

    const getIconColor = (type: NotificationType) => {
        switch (type) {
            case NotificationType.ALERT: return 'text-red-500 bg-red-50 dark:bg-red-900/20';
            case NotificationType.WARNING: return 'text-amber-500 bg-amber-50 dark:bg-amber-900/20';
            case NotificationType.SUCCESS: return 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20';
            case NotificationType.DOCUMENT: return 'text-blue-500 bg-blue-50 dark:bg-blue-900/20';
            case NotificationType.TASK: return 'text-indigo-500 bg-indigo-50 dark:bg-indigo-900/20';
            default: return 'text-gray-500 bg-gray-50 dark:bg-gray-900/20';
        }
    };

    const formatTime = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 60) return `${diffMins} mins ago`;
        if (diffHours < 24) return `${diffHours} hours ago`;
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
        <ModernLayout>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-black text-[#0d121b] dark:text-white tracking-tight">Notification Center</h1>
                    <p className="text-[#4c669a] dark:text-[#a0aec0] font-medium mt-1">Stay updated on TWG progress, mentions, and system alerts.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleMarkAllAsRead}
                        className="px-4 py-2 text-sm font-bold text-[#4c669a] hover:text-[#0d121b] dark:hover:text-white transition-colors"
                    >
                        Mark all as read
                    </button>
                    <button
                        onClick={() => dispatch(fetchNotifications())}
                        className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-[#1a202c] border border-[#e7ebf3] dark:border-[#2d3748] rounded-lg text-sm font-bold text-[#0d121b] dark:text-white hover:bg-gray-50 dark:hover:bg-[#2d3748] transition-colors shadow-sm"
                    >
                        <span className="material-symbols-outlined text-[18px]">refresh</span>
                        Refresh
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-280px)]">
                {/* Notification List Sidebar */}
                <div className="lg:col-span-1 bg-white dark:bg-[#1a202c] rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm overflow-hidden flex flex-col">
                    <div className="p-4 border-b border-[#e7ebf3] dark:border-[#2d3748] bg-gray-50/50 dark:bg-[#1a202c]/50">
                        <div className="flex items-center justify-between">
                            <h3 className="font-bold text-[#0d121b] dark:text-white">Notifications</h3>
                            <span className="bg-[#1152d4] text-white text-[10px] font-black px-2 py-0.5 rounded-full">
                                {notifications.filter(n => !n.is_read).length} UNREAD
                            </span>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto divide-y divide-[#e7ebf3] dark:divide-[#2d3748]">
                        {loading && notifications.length === 0 ? (
                            <div className="p-8 text-center">
                                <div className="size-8 border-2 border-[#1152d4] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                                <p className="text-xs text-[#4c669a]">Syncing alerts...</p>
                            </div>
                        ) : notifications.length === 0 ? (
                            <div className="p-8 text-center">
                                <span className="material-symbols-outlined text-4xl text-gray-300 mb-2">notifications_off</span>
                                <p className="text-sm text-[#4c669a]">All caught up!</p>
                            </div>
                        ) : (
                            <>
                                {todayNotifications.length > 0 && (
                                    <div className="bg-gray-50/30 dark:bg-[#2d3748]/10 py-2 px-4">
                                        <span className="text-[10px] font-black text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-widest">Today</span>
                                    </div>
                                )}
                                {todayNotifications.map(n => (
                                    <div
                                        key={n.id}
                                        onClick={() => {
                                            setSelectedNotificationId(n.id);
                                            if (!n.is_read) handleMarkAsRead(n.id);
                                        }}
                                        className={`p-4 flex gap-4 cursor-pointer transition-all hover:bg-gray-50 dark:hover:bg-[#2d3748]/50 relative group ${selectedNotification?.id === n.id ? 'bg-[#1152d4]/5 dark:bg-[#1152d4]/10 border-l-4 border-[#1152d4]' : ''}`}
                                    >
                                        <div className={`size-10 rounded-xl flex items-center justify-center shrink-0 ${getIconColor(n.type)}`}>
                                            <span className="material-symbols-outlined text-[20px]">{getIcon(n.type)}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-0.5">
                                                <h4 className={`text-sm truncate ${n.is_read ? 'text-[#4c669a] font-medium' : 'text-[#0d121b] dark:text-white font-bold'}`}>{n.title}</h4>
                                                {!n.is_read && <div className="size-2 rounded-full bg-[#1152d4] shrink-0 ml-2"></div>}
                                            </div>
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] truncate">{n.content}</p>
                                            <span className="text-[10px] text-[#a0aec0] mt-1 block">{formatTime(n.created_at)}</span>
                                        </div>
                                    </div>
                                ))}

                                {earlierNotifications.length > 0 && (
                                    <div className="bg-gray-50/30 dark:bg-[#2d3748]/10 py-2 px-4">
                                        <span className="text-[10px] font-black text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-widest">Earlier</span>
                                    </div>
                                )}
                                {earlierNotifications.map(n => (
                                    <div
                                        key={n.id}
                                        onClick={() => {
                                            setSelectedNotificationId(n.id);
                                            if (!n.is_read) handleMarkAsRead(n.id);
                                        }}
                                        className={`p-4 flex gap-4 cursor-pointer transition-all hover:bg-gray-50 dark:hover:bg-[#2d3748]/50 relative group ${selectedNotification?.id === n.id ? 'bg-[#1152d4]/5 dark:bg-[#1152d4]/10 border-l-4 border-[#1152d4]' : ''}`}
                                    >
                                        <div className={`size-10 rounded-xl flex items-center justify-center shrink-0 ${getIconColor(n.type)}`}>
                                            <span className="material-symbols-outlined text-[20px]">{getIcon(n.type)}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-0.5">
                                                <h4 className={`text-sm truncate ${n.is_read ? 'text-[#4c669a] font-medium' : 'text-[#0d121b] dark:text-white font-bold'}`}>{n.title}</h4>
                                                {!n.is_read && <div className="size-2 rounded-full bg-[#1152d4] shrink-0 ml-2"></div>}
                                            </div>
                                            <p className="text-xs text-[#4c669a] dark:text-[#a0aec0] truncate">{n.content}</p>
                                            <span className="text-[10px] text-[#a0aec0] mt-1 block">{formatTime(n.created_at)}</span>
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                </div>

                {/* Notification Detail View */}
                <div className="lg:col-span-2 bg-white dark:bg-[#1a202c] rounded-2xl border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm flex flex-col glassmorphism overflow-hidden">
                    {selectedNotification ? (
                        <div className="flex flex-col h-full">
                            <div className="p-8 flex-1">
                                <div className="flex items-start justify-between mb-10">
                                    <div className="flex items-center gap-4">
                                        <div className={`size-16 rounded-2xl flex items-center justify-center ${getIconColor(selectedNotification.type)} shadow-lg shadow-blue-500/10`}>
                                            <span className="material-symbols-outlined text-[32px]">{getIcon(selectedNotification.type)}</span>
                                        </div>
                                        <div>
                                            <span className="text-[10px] font-black text-[#1152d4] uppercase tracking-[0.2em]">{selectedNotification.type}</span>
                                            <h2 className="text-2xl font-black text-[#0d121b] dark:text-white mt-1">{selectedNotification.title}</h2>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleDelete(selectedNotification.id)}
                                            className="p-2 text-[#4c669a] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all"
                                            title="Delete notification"
                                        >
                                            <span className="material-symbols-outlined">delete</span>
                                        </button>
                                    </div>
                                </div>

                                <div className="prose dark:prose-invert max-w-none">
                                    <p className="text-lg text-[#4c669a] dark:text-[#a0aec0] leading-relaxed font-medium">
                                        {selectedNotification.content}
                                    </p>
                                </div>

                                {selectedNotification.link && (
                                    <div className="mt-12 bg-gray-50 dark:bg-[#2d3748]/50 rounded-2xl p-6 border border-[#e7ebf3] dark:border-[#4a5568] flex items-center justify-between group">
                                        <div className="flex items-center gap-4">
                                            <div className="size-12 rounded-xl bg-white dark:bg-[#1a202c] flex items-center justify-center text-[#1152d4] border border-[#e7ebf3] dark:border-[#2d3748] shadow-sm">
                                                <span className="material-symbols-outlined">link</span>
                                            </div>
                                            <div>
                                                <p className="text-xs font-black text-[#4c669a] dark:text-[#a0aec0] uppercase tracking-wider">Related Action</p>
                                                <p className="text-sm font-bold text-[#0d121b] dark:text-white">View linked resource</p>
                                            </div>
                                        </div>
                                        <a
                                            href={selectedNotification.link}
                                            className="px-6 py-2.5 bg-[#1152d4] hover:bg-[#0d3ea8] text-white text-sm font-bold rounded-xl transition-all shadow-md active:scale-95"
                                        >
                                            Go to Detail
                                        </a>
                                    </div>
                                )}
                            </div>

                            <div className="p-8 border-t border-[#e7ebf3] dark:border-[#2d3748] bg-gray-50/50 dark:bg-[#1a202c]/50 flex items-center justify-between">
                                <div className="flex items-center gap-2 text-[#a0aec0]">
                                    <span className="material-symbols-outlined text-[18px]">calendar_today</span>
                                    <span className="text-sm font-medium">{formatTime(selectedNotification.created_at)}</span>
                                </div>
                                <div className="flex items-center gap-2 text-[#a0aec0]">
                                    <span className="material-symbols-outlined text-[18px]">history</span>
                                    <span className="text-sm font-medium">{new Date(selectedNotification.created_at).toLocaleTimeString()}</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                            <div className="size-24 rounded-full bg-gray-50 dark:bg-[#2d3748] flex items-center justify-center text-gray-200 dark:text-[#4a5568] mb-6">
                                <span className="material-symbols-outlined text-[48px]">mark_email_read</span>
                            </div>
                            <h3 className="text-xl font-black text-[#0d121b] dark:text-white">Select an alert to view details</h3>
                            <p className="text-[#4c669a] dark:text-[#a0aec0] mt-2 max-w-sm">
                                Track system events, TWG updates, and AI agent reports in high fidelity.
                            </p>
                        </div>
                    )}
                </div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .glassmorphism {
                    background: rgba(255, 255, 255, 0.7);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                }
                .dark .glassmorphism {
                    background: rgba(26, 32, 44, 0.7);
                }
            `}} />
        </ModernLayout>
    );
}
