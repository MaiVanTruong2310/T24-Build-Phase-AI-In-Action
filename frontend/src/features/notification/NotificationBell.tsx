import { TypewriterLoader } from '../../components/TypewriterLoader';
import { CheckCheck } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import './NotificationBell.css';

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from './api';

function formatNotificationTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function NotificationBell({ enabled }: { enabled: boolean }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadNotifications = useCallback(async () => {
    if (!enabled || document.hidden) return;
    try {
      setLoading(true);
      setNotifications(await fetchNotifications());
    } catch {
      // The header should remain usable when the notification service is unavailable.
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void loadNotifications();
    if (!enabled) return undefined;
    const timer = window.setInterval(() => void loadNotifications(), 30_000);
    const onVisible = () => { if (!document.hidden) void loadNotifications(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [enabled, loadNotifications]);

  const unreadCount = notifications.filter((notification) => !notification.read_at).length;

  const handleRead = async (notification: AppNotification) => {
    if (notification.read_at) return;
    try {
      const updated = await markNotificationRead(notification.id);
      setNotifications((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch {
      // Keep the item unread so the user can retry.
    }
  };

  const handleReadAll = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((current) => current.map((notification) => ({ ...notification, read_at: new Date().toISOString() })));
    } catch {
      // Keep the current unread state when the request fails.
    }
  };

  if (!enabled) return null;

  return (
    <div className="relative">
      <button
        type="button"
        className="notification-bell-button"
        aria-expanded={open}
        title="Thông báo"
        aria-label={`Thông báo${unreadCount ? `, ${unreadCount} chưa đọc` : ''}`}
        onClick={() => setOpen((current) => !current)}
      >
        <svg viewBox="0 0 448 512" className="notification-bell-button__icon" aria-hidden="true">
          <path d="M224 0c-17.7 0-32 14.3-32 32V49.9C119.5 61.4 64 124.2 64 200v33.4c0 45.4-15.5 89.5-43.8 124.9L5.3 377c-5.8 7.2-6.9 17.1-2.9 25.4S14.8 416 24 416H424c9.2 0 17.6-5.3 21.6-13.6s2.9-18.2-2.9-25.4l-14.9-18.6C399.5 322.9 384 278.8 384 233.4V200c0-75.8-55.5-138.6-128-150.1V32c0-17.7-14.3-32-32-32zm0 96h8c57.4 0 104 46.6 104 104v33.4c0 47.9 13.9 94.6 39.7 134.6H72.3C98.1 328 112 281.3 112 233.4V200c0-57.4 46.6-104 104-104h8zm64 352H224 160c0 17 6.7 33.3 18.7 45.3s28.3 18.7 45.3 18.7s33.3-6.7 45.3-18.7s18.7-28.3 18.7-45.3z" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full border border-white bg-red-500 px-1 text-[9px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-3 w-80 overflow-hidden rounded-2xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 light:border-app-border px-4 py-3">
            <p className="text-sm font-bold text-slate-900 light:text-app-text">Thông báo</p>
            <button type="button" onClick={() => void handleReadAll()} className="inline-flex items-center gap-1 text-xs font-semibold text-sky-700 light:text-app-primary hover:text-sky-900 light:hover:text-app-primary-strong">
              <CheckCheck className="h-3.5 w-3.5" /> Đã đọc hết
            </button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {loading && notifications.length === 0 && <div className="flex justify-center px-4 py-8"><TypewriterLoader /></div>}
            {!loading && notifications.length === 0 && <p className="px-4 py-8 text-center text-sm text-slate-500 light:text-app-secondary">Chưa có thông báo.</p>}
            {notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => void handleRead(notification)}
                className={`block w-full border-b border-slate-100 light:border-app-border px-4 py-3 text-left transition hover:bg-slate-50 light:hover:bg-app-page ${notification.read_at ? 'bg-white light:bg-app-surface' : 'bg-sky-50/60 light:bg-app-muted/60'}`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${notification.read_at ? 'bg-slate-200 light:bg-app-tint' : 'bg-sky-500 light:bg-app-primary'}`} />
                  <span>
                    <span className="block text-sm font-semibold text-slate-800 light:text-app-text">{notification.title}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-600 light:text-app-secondary">{notification.message}</span>
                    <span className="mt-1 block text-[11px] text-slate-400 light:text-app-secondary">{formatNotificationTime(notification.created_at)}</span>
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
