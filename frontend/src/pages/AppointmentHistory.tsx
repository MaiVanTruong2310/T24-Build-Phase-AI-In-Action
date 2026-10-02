import { CalendarDays, ChevronRight, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Booking, BookingApiError, fetchBookings } from '../features/appointment-booking/api';

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusLabel(status: Booking['status']): string {
  if (status === 'pending_approval') return 'Chờ duyệt';
  if (status === 'confirmed') return 'Đã xác nhận';
  if (status === 'rejected') return 'Đã từ chối';
  if (status === 'expired') return 'Đã hết hạn';
  return 'Đã huỷ';
}

export default function AppointmentHistory() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchBookings()
      .then(setBookings)
      .catch((cause: unknown) => {
        if (cause instanceof BookingApiError && cause.status === 403) {
          setError('Tài khoản hiện tại không có quyền xem lịch hẹn.');
        } else {
          setError('Không thể tải lịch hẹn. Vui lòng thử lại.');
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <section className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-semibold text-sky-600">VCare+</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">Lịch hẹn của tôi</h1>
          <p className="mt-2 text-sm text-slate-600">Theo dõi các lịch khám đã xác nhận và đã huỷ.</p>
        </div>
        <Link
          to="/patient/appointments"
          className="rounded-lg bg-sky-700 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-sky-800"
        >
          Đặt lịch mới
        </Link>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white py-16 text-sky-700">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Đang tải lịch hẹn...
        </div>
      )}

      {!isLoading && !error && bookings.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
          <CalendarDays className="mx-auto h-10 w-10 text-slate-400" />
          <h2 className="mt-4 font-semibold text-slate-900">Chưa có lịch hẹn</h2>
          <p className="mt-2 text-sm text-slate-600">Bạn có thể chọn bác sĩ và khung giờ để đặt lịch khám.</p>
        </div>
      )}

      {!isLoading && !error && bookings.length > 0 && (
        <div className="space-y-3">
          {bookings.map((booking) => (
            <Link
              key={booking.id}
              to={`/patient/appointments/${booking.id}`}
              className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-300 hover:shadow-md sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-sky-700">
                  <CalendarDays className="h-4 w-4" />
                  {formatDateTime(booking.starts_at)}
                </div>
                <p className="mt-2 text-sm text-slate-700">Mã lịch hẹn: {booking.id}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Mã bác sĩ: {booking.doctor_id} · Mã cơ sở: {booking.facility_id}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={booking.status === 'confirmed'
                  ? 'rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700'
                  : booking.status === 'pending_approval'
                    ? 'rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700'
                    : booking.status === 'rejected'
                      ? 'rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700'
                    : booking.status === 'expired'
                      ? 'rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold text-orange-700'
                      : 'rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600'}>
                  {statusLabel(booking.status)}
                </span>
                <ChevronRight className="h-5 w-5 text-slate-400" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
