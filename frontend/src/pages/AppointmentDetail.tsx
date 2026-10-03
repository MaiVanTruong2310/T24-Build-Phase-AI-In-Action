import { TypewriterLoader } from '../components/TypewriterLoader';
import { ArrowLeft, CalendarDays } from 'lucide-react';

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

      <div className="flex items-center justify-center rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface py-20 text-sky-700 dark:text-sky-300 light:text-app-primary">

        <TypewriterLoader /> Đang tải chi tiết lịch hẹn...

      </div>

    );

  }



  if (!booking) {

    return (

      <section className="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 p-6">

        <h1 className="text-xl font-bold text-red-900 dark:text-red-300">Không thể mở lịch hẹn</h1>

        <p className="mt-2 text-sm text-red-700 dark:text-red-300">{error}</p>

        <Link to="/patient/appointments/history" className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-red-800 dark:text-red-300 hover:underline">

          <ArrowLeft className="h-4 w-4" /> Quay lại lịch hẹn

        </Link>

      </section>

    );

  }



  return (

    <section className="mx-auto max-w-3xl space-y-6">

      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-app-secondary light:text-app-secondary hover:text-sky-700 dark:hover:text-sky-300 light:hover:text-app-primary">

        <ArrowLeft className="h-4 w-4" /> Quay lại

      </button>



      <div className="rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-6 shadow-sm">

        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">

          <div>

            <p className="text-sm font-semibold text-sky-600 dark:text-sky-300 light:text-app-primary">Chi tiết lịch hẹn</p>

            <h1 className="mt-1 break-all text-2xl font-bold text-slate-900 dark:text-app-text light:text-app-text">{booking.id}</h1>

          </div>

          <span className={booking.status === 'confirmed'

            ? 'rounded-full bg-emerald-100 dark:bg-emerald-950/50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300'

            : booking.status === 'pending_approval'

              ? 'rounded-full bg-amber-100 dark:bg-amber-950/50 px-3 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300'

              : booking.status === 'rejected'

                ? 'rounded-full bg-rose-100 dark:bg-rose-950/50 px-3 py-1 text-xs font-semibold text-rose-700 dark:text-rose-300'

                : 'rounded-full bg-slate-100 dark:bg-app-muted light:bg-app-muted px-3 py-1 text-xs font-semibold text-slate-600 dark:text-app-secondary light:text-app-secondary'}>

            {statusLabel(booking.status)}

          </span>

        </div>



        <div className="mt-6 grid gap-4 sm:grid-cols-2">

          <div className="rounded-xl bg-slate-50 dark:bg-app-surface light:bg-app-page p-4 sm:col-span-2">

            <div className="flex items-center gap-2 text-sm font-semibold text-sky-700 dark:text-sky-300 light:text-app-primary">

              <CalendarDays className="h-4 w-4" /> Thời gian khám

            </div>

            <p className="mt-2 font-semibold text-slate-900 dark:text-app-text light:text-app-text">{formatDateTime(booking.starts_at)}</p>

            <p className="mt-1 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">Kết thúc: {formatDateTime(booking.ends_at)}</p>

          </div>

          <Info label="Mã bác sĩ" value={booking.doctor_id} />

          <Info label="Mã cơ sở" value={booking.facility_id} />

          <Info label="Mã dịch vụ" value={booking.service_id} />

          <Info label="Mã chuyên khoa" value={booking.specialty_id} />

          <Info label="Hình thức" value={booking.encounter_type === 'in_person' ? 'Khám trực tiếp' : 'Telehealth'} />

          <Info label="Loại lịch" value={booking.booking_mode === 'group' ? 'Theo sức chứa' : 'Khám riêng bác sĩ'} />

        </div>



        <div className="mt-4 rounded-xl border border-slate-200 dark:border-app-border light:border-app-border p-4">

          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">Lý do khám</p>

          <p className="mt-2 text-sm text-slate-800 dark:text-app-text light:text-app-text">{booking.reason}</p>

          {booking.patient_note && <p className="mt-2 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">Ghi chú: {booking.patient_note}</p>}

        </div>



        {error && <div role="alert" className="mt-4 rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>}



        {(booking.status === 'pending_approval' || booking.status === 'confirmed') && (

          <div className="mt-6 border-t border-slate-200 dark:border-app-border light:border-app-border pt-6">

            <h2 className="font-semibold text-slate-900 dark:text-app-text light:text-app-text">Huỷ lịch hẹn</h2>

            <p className="mt-1 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">Kiểm tra lại thông tin trên và xác nhận nếu bạn muốn huỷ lịch này.</p>

            <textarea

              value={cancelReason}

              onChange={(event) => setCancelReason(event.target.value)}

              maxLength={500}

              rows={3}

              placeholder="Lý do huỷ (không bắt buộc)"

              className="mt-3 w-full rounded-xl border border-slate-300 dark:border-app-border light:border-app-border px-3 py-2 text-sm outline-none focus:border-sky-500 dark:focus:border-sky-800 light:focus:border-app-primary focus:ring-2 focus:ring-sky-100 dark:focus:ring-sky-400"

            />

            <button

              onClick={handleCancel}

              disabled={isCancelling}

              className="mt-3 rounded-lg border border-red-200 dark:border-red-800 px-4 py-2 text-sm font-semibold text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/50 disabled:cursor-not-allowed disabled:opacity-50"

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

      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">{label}</p>

      <p className="mt-1 break-all text-sm font-medium text-slate-900 dark:text-app-text light:text-app-text">{value}</p>

    </div>

  );

}

