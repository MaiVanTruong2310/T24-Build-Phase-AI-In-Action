import { ArrowLeft, CalendarDays, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Booking,
  BookingApiError,
  cancelBooking,
  fetchBooking,
} from '../features/appointment-booking/api';

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    weekday: 'long',
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
  return 'Đã huỷ';
}

export default function AppointmentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) {
      setError('Mã lịch hẹn không hợp lệ.');
      setIsLoading(false);
      return;
    }

    fetchBooking(id)
      .then(setBooking)
      .catch((cause: unknown) => {
        if (cause instanceof BookingApiError && cause.status === 404) {
          setError('Không tìm thấy lịch hẹn hoặc lịch hẹn không thuộc tài khoản này.');
        } else {
          setError('Không thể tải chi tiết lịch hẹn. Vui lòng thử lại.');
        }
      })
      .finally(() => setIsLoading(false));
  }, [id]);

  const handleCancel = async () => {
    if (!booking || booking.status === 'cancelled' || isCancelling) return;
    setError('');
    setIsCancelling(true);
    try {
      setBooking(await cancelBooking(booking.id, cancelReason));
    } catch (cause: unknown) {
      if (cause instanceof BookingApiError && cause.status === 409) {
        setError('Lịch hẹn đã thay đổi trạng thái. Vui lòng tải lại trang.');
      } else {
        setError('Không thể huỷ lịch hẹn lúc này. Vui lòng thử lại.');
      }
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white py-20 text-sky-700">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Đang tải chi tiết lịch hẹn...
      </div>
    );
  }

  if (!booking) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-6">
        <h1 className="text-xl font-bold text-red-900">Không thể mở lịch hẹn</h1>
        <p className="mt-2 text-sm text-red-700">{error}</p>
        <Link to="/patient/appointments/history" className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-red-800 hover:underline">
          <ArrowLeft className="h-4 w-4" /> Quay lại lịch hẹn
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-sky-700">
        <ArrowLeft className="h-4 w-4" /> Quay lại
      </button>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <p className="text-sm font-semibold text-sky-600">Chi tiết lịch hẹn</p>
            <h1 className="mt-1 break-all text-2xl font-bold text-slate-900">{booking.id}</h1>
          </div>
          <span className={booking.status === 'confirmed'
            ? 'rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700'
            : booking.status === 'pending_approval'
              ? 'rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700'
              : booking.status === 'rejected'
                ? 'rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700'
                : 'rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600'}>
            {statusLabel(booking.status)}
          </span>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-slate-50 p-4 sm:col-span-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-sky-700">
              <CalendarDays className="h-4 w-4" /> Thời gian khám
            </div>
            <p className="mt-2 font-semibold text-slate-900">{formatDateTime(booking.starts_at)}</p>
            <p className="mt-1 text-sm text-slate-600">Kết thúc: {formatDateTime(booking.ends_at)}</p>
          </div>
          <Info label="Mã bác sĩ" value={booking.doctor_id} />
          <Info label="Mã cơ sở" value={booking.facility_id} />
          <Info label="Mã dịch vụ" value={booking.service_id} />
          <Info label="Mã chuyên khoa" value={booking.specialty_id} />
          <Info label="Hình thức" value={booking.encounter_type === 'in_person' ? 'Khám trực tiếp' : 'Telehealth'} />
          <Info label="Loại lịch" value={booking.booking_mode === 'group' ? 'Theo sức chứa' : 'Khám riêng bác sĩ'} />
        </div>

        <div className="mt-4 rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Lý do khám</p>
          <p className="mt-2 text-sm text-slate-800">{booking.reason}</p>
          {booking.patient_note && <p className="mt-2 text-sm text-slate-600">Ghi chú: {booking.patient_note}</p>}
        </div>

        {error && <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        {(booking.status === 'pending_approval' || booking.status === 'confirmed') && (
          <div className="mt-6 border-t border-slate-200 pt-6">
            <h2 className="font-semibold text-slate-900">Huỷ lịch hẹn</h2>
            <p className="mt-1 text-sm text-slate-600">Kiểm tra lại thông tin trên và xác nhận nếu bạn muốn huỷ lịch này.</p>
            <textarea
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Lý do huỷ (không bắt buộc)"
              className="mt-3 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            />
            <button
              onClick={handleCancel}
              disabled={isCancelling}
              className="mt-3 rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isCancelling ? 'Đang huỷ...' : 'Xác nhận huỷ lịch'}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm font-medium text-slate-900">{value}</p>
    </div>
  );
}
