import { Bell, CheckCheck, Loader2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { resolveWebSocketUrl } from '../../app/apiClient';
import { readAccessToken } from '../auth/session';
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
  const [error, setError] = useState('');

  const loadNotifications = useCallback(async () => {
    if (!enabled) return;
    try {
      setLoading(true);
      setError('');
      setNotifications(await fetchNotifications());
    } catch {
      setError('Không thể tải thông báo.');
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void loadNotifications();
    if (!enabled) return undefined;

    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let stopped = false;

    const connect = () => {
      if (stopped) return;
      const token = readAccessToken();
      const query = token ? `?${new URLSearchParams({ token }).toString()}` : '';
      socket = new WebSocket(`${resolveWebSocketUrl('/notifications/ws')}${query}`);
      socket.onopen = () => {
        // Reconcile notifications created while the socket was reconnecting.
        void loadNotifications();
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as { type?: string; data?: AppNotification };
          const incoming = payload.data;
          if (payload.type !== 'notification.created' || !incoming) return;
          setNotifications((current) => {
            const next = [incoming, ...current.filter((item) => item.id !== incoming.id)];
            return next.sort((left, right) => right.created_at.localeCompare(left.created_at));
          });
        } catch {
          // Ignore malformed realtime messages and keep the current list.
        }
      };
      socket.onclose = () => {
        if (!stopped) {
          void loadNotifications().finally(() => {
            reconnectTimer = window.setTimeout(connect, 5_000);
          });
        }
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      stopped = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      socket?.close();
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
        className="relative p-1 text-slate-400 transition-colors hover:text-slate-600"
        title="Thông báo"
        aria-label={`Thông báo${unreadCount ? `, ${unreadCount} chưa đọc` : ''}`}
        onClick={() => setOpen((current) => !current)}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full border border-white bg-red-500 px-1 text-[9px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-3 w-80 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <p className="text-sm font-bold text-slate-900">Thông báo</p>
            <button type="button" onClick={() => void handleReadAll()} className="inline-flex items-center gap-1 text-xs font-semibold text-sky-700 hover:text-sky-900">
              <CheckCheck className="h-3.5 w-3.5" /> Đã đọc hết
            </button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {error && (
              <div role="alert" className="border-b border-rose-100 bg-rose-50 px-4 py-3 text-xs text-rose-700">
                <p>{error}</p>
                <button type="button" className="mt-2 font-semibold underline" onClick={() => void loadNotifications()}>
                  Thử lại
                </button>
              </div>
            )}
            {loading && notifications.length === 0 && <div className="flex justify-center px-4 py-8"><Loader2 className="h-5 w-5 animate-spin text-sky-600" /></div>}
            {!loading && notifications.length === 0 && <p className="px-4 py-8 text-center text-sm text-slate-500">Chưa có thông báo.</p>}
            {notifications.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => void handleRead(notification)}
                className={`block w-full border-b border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50 ${notification.read_at ? 'bg-white' : 'bg-sky-50/60'}`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${notification.read_at ? 'bg-slate-200' : 'bg-sky-500'}`} />
                  <span>
                    <span className="block text-sm font-semibold text-slate-800">{notification.title}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-600">{notification.message}</span>
                    <span className="mt-1 block text-[11px] text-slate-400">{formatNotificationTime(notification.created_at)}</span>
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
