import { TypewriterLoader } from '../../components/TypewriterLoader';
import { Bell, CheckCheck } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const lastFetchedRef = useRef(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const loadNotifications = useCallback(async (force = false) => {
    if (!enabled || document.hidden) return;
    const now = Date.now();
    if (!force && now - lastFetchedRef.current < 60_000) return;
    lastFetchedRef.current = now;
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
    void loadNotifications(true);
    if (!enabled) return undefined;
    const timer = window.setInterval(() => void loadNotifications(true), 60_000);
    const onVisible = () => { if (!document.hidden) void loadNotifications(false); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [enabled, loadNotifications]);

  // Đóng hộp thoại khi bấm ra ngoài hoặc nhấn Escape.
  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

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

  const openNotification = (notification: AppNotification) => {
    void handleRead(notification);
    const destination = notification.kind === 'booking_pending_approval'
      ? '/staff/booking-approvals'
      : notification.kind === 'deposit_requested'
        ? '/patient/requests'
        : notification.booking_id
          ? `/patient/progress/${encodeURIComponent(notification.booking_id)}`
          : null;
    if (destination) {
      setOpen(false);
      navigate(destination);
    }
  };

  if (!enabled) return null;

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="notification-bell-button"
        aria-expanded={open}
        aria-haspopup="dialog"
        title="Thông báo"
        aria-label={`Thông báo${unreadCount ? `, ${unreadCount} chưa đọc` : ''}`}
        onClick={() => setOpen((current) => !current)}
      >
        <Bell className="notification-bell-button__icon" strokeWidth={2.2} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="notification-bell-badge" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <polygon points="12,1 14.6,7.2 21,5 18.2,11.2 23,14 16.5,15.5 17,22 12,17.8 7,22 7.5,15.5 1,14 5.8,11.2 3,5 9.4,7.2" />
            </svg>
            <span>{unreadCount > 9 ? '9+' : unreadCount}</span>
          </span>
        )}
      </button>

      {open && (
        <div className="hd-notif" role="dialog" aria-label="Thông báo">
          <div className="hd-notif__head">
            <p className="hd-notif__title">
              Thông báo
              {unreadCount > 0 && <span className="hd-notif__count">{unreadCount} mới</span>}
            </p>
            <button type="button" onClick={() => void handleReadAll()} className="hd-notif__readall">
              <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" /> Đã đọc hết
            </button>
          </div>
          <div className="hd-notif__list">
            {loading && notifications.length === 0 && <div className="flex justify-center px-4 py-8"><TypewriterLoader /></div>}
            {!loading && notifications.length === 0 && <p className="px-4 py-8 text-center text-sm text-app-secondary">Chưa có thông báo.</p>}
            {notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => openNotification(notification)}
                className={`notification-item block w-full border-b border-slate-100 light:border-app-border px-4 py-3 text-left ${notification.read_at ? 'bg-white light:bg-app-surface' : 'bg-sky-50/60 light:bg-app-muted/60'}`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${notification.read_at ? 'bg-slate-200 light:bg-app-tint' : 'bg-sky-500 light:bg-app-primary'}`} />
                  <span>
                    <span className="block text-sm font-semibold text-slate-800 light:text-app-text">{notification.title}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-600 light:text-app-secondary">{notification.message}</span>
                    {(notification.booking_id || notification.kind === 'booking_pending_approval' || notification.kind === 'deposit_requested') && (
                      <span className="mt-2 block text-xs font-semibold text-sky-700 light:text-app-primary">
                        {notification.kind === 'booking_pending_approval' ? 'Mở danh sách booking cần duyệt' : notification.kind === 'deposit_requested' ? 'Xem phiếu điều phối' : 'Xem chi tiết lịch khám'}
                      </span>
                    )}
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
