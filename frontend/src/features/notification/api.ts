import { fetchWithAuth } from '../../app/apiClient';

export type NotificationKind = 'booking_confirmed' | 'booking_rejected' | 'appointment_reminder';

export interface AppNotification {
  id: string;
  booking_id: string | null;
  kind: NotificationKind;
  title: string;
  message: string;
  available_at: string;
  read_at: string | null;
  created_at: string;
}

async function readResponse<T>(response: Response): Promise<T> {
  const json = await response.json();
  if (!response.ok) throw new Error(json.message || 'Không thể tải thông báo');
  return json.data as T;
}

export async function fetchNotifications(unreadOnly = false): Promise<AppNotification[]> {
  const query = new URLSearchParams({ unread_only: String(unreadOnly), offset: '0', limit: '50' });
  return readResponse<AppNotification[]>(await fetchWithAuth(`/notifications?${query.toString()}`));
}

export async function markNotificationRead(notificationId: string): Promise<AppNotification> {
  return readResponse<AppNotification>(
    await fetchWithAuth(`/notifications/${notificationId}/read`, { method: 'POST' }),
  );
}

export async function markAllNotificationsRead(): Promise<number> {
  const data = await readResponse<{ updated: number }>(
    await fetchWithAuth('/notifications/read-all', { method: 'POST' }),
  );
  return data.updated;
}
