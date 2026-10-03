import { Bell, CheckCircle2, Clock3, Loader2, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import { fetchNotifications, type AppNotification } from '../../features/notification/api';
import { fetchPendingBookings, type PendingBooking } from '../AppointmentApproval/api';

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function isToday(value: string): boolean {
  const date = new Date(value);
  const today = new Date();
  return date.getFullYear() === today.getFullYear()
    && date.getMonth() === today.getMonth()
    && date.getDate() === today.getDate();
}

export default function StaffDashboard() {
  const [pendingBookings, setPendingBookings] = useState<PendingBooking[]>([]);
  const [confirmedBookings, setConfirmedBookings] = useState<PendingBooking[]>([]);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadDashboard = useCallback(async (isRefresh = false) => {
    setError('');
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const [pending, confirmed, unreadNotifications] = await Promise.all([
        fetchPendingBookings({ status: 'pending_approval' }),
        fetchPendingBookings({ status: 'confirmed' }),
        fetchNotifications(true),
      ]);
      setPendingBookings(pending);
      setConfirmedBookings(confirmed);
      setNotifications(unreadNotifications);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : 'Không thể tải dữ liệu tổng quan.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const confirmedToday = useMemo(
    () => confirmedBookings.filter((booking) => isToday(booking.starts_at)),
    [confirmedBookings],
  );

  return (
    <section className="min-h-full space-y-6 bg-slate-50 p-4 text-slate-800 xl:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-sky-600">VCare+ · Staff</p>
          <h1 className="mt-1 text-3xl font-extrabold text-slate-900">Tổng quan điều phối</h1>
          <p className="mt-2 text-sm text-slate-600">Dữ liệu được lấy trực tiếp từ booking và notification API.</p>
        </div>
        <button
          type="button"
          onClick={() => void loadDashboard(true)}
          disabled={loading || refreshing}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:border-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={refreshing ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />
          Làm mới
        </button>
      </div>

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      {loading ? (
        <div className="flex min-h-56 items-center justify-center rounded-2xl border border-slate-200 bg-white text-sky-700">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Đang tải dữ liệu...
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard icon={<Clock3 className="h-5 w-5" />} label="Chờ duyệt" value={pendingBookings.length} tone="amber" />
            <MetricCard icon={<Bell className="h-5 w-5" />} label="Thông báo chưa đọc" value={notifications.length} tone="sky" />
            <MetricCard icon={<CheckCircle2 className="h-5 w-5" />} label="Lịch đã duyệt hôm nay" value={confirmedToday.length} tone="emerald" />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="font-bold text-slate-900">Lịch đang chờ duyệt</h2>
                <p className="mt-1 text-xs text-slate-500">Danh sách lấy từ `/staff/bookings?status=pending_approval`.</p>
              </div>
              <a href="/staff/appointments" className="text-sm font-semibold text-sky-700 hover:text-sky-900">Mở hàng đợi</a>
            </div>
            {pendingBookings.length === 0 ? (
              <p className="px-5 py-12 text-center text-sm text-slate-500">Hiện không có lịch chờ duyệt.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {pendingBookings.slice(0, 10).map((booking) => (
                  <a key={booking.id} href={`/staff/appointments/approve/${booking.id}`} className="flex flex-col gap-2 px-5 py-4 transition hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-semibold text-slate-900">{booking.patient_name}</p>
                      <p className="mt-1 text-sm text-slate-600">{booking.doctor_name} · {booking.specialty_name}</p>
                    </div>
                    <div className="text-left text-sm text-slate-500 sm:text-right">
                      <p>{formatDateTime(booking.starts_at)}</p>
                      <p className="mt-1 text-xs">Hết hạn duyệt: {formatDateTime(booking.expired_at)}</p>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  tone: 'amber' | 'sky' | 'emerald';
}) {
  const styles = {
    amber: 'bg-amber-50 text-amber-700',
    sky: 'bg-sky-50 text-sky-700',
    emerald: 'bg-emerald-50 text-emerald-700',
  }[tone];
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl ${styles}`}>{icon}</div>
      <p className="text-sm font-semibold text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-extrabold text-slate-900">{value}</p>
    </div>
  );
}
