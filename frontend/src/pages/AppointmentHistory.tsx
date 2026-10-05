import { TypewriterLoader } from '../components/TypewriterLoader';
import { CalendarDays, ChevronRight } from 'lucide-react';

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

          <p className="text-sm font-semibold text-sky-600 dark:text-sky-300 light:text-app-primary">VCare+</p>

          <h1 className="mt-1 text-3xl font-bold text-slate-900 dark:text-app-text light:text-app-text">Lịch hẹn của tôi</h1>

          <p className="mt-2 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">Theo dõi các lịch khám đã xác nhận và đã huỷ.</p>

        </div>

        <Link

          to="/patient/appointments"

          className="rounded-lg bg-sky-700 dark:bg-sky-700 light:bg-app-primary-hover px-4 py-2 text-center text-sm font-semibold text-white hover:bg-sky-800 dark:hover:bg-sky-700 light:hover:bg-app-primary-hover"

        >

          Đặt lịch mới

        </Link>

      </div>



      {error && (

        <div role="alert" className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 px-4 py-3 text-sm text-red-700 dark:text-red-300">

          {error}

        </div>

      )}



      {isLoading && (

        <div className="flex items-center justify-center rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface py-16 text-sky-700 dark:text-sky-300 light:text-app-primary">

          <TypewriterLoader /> Đang tải lịch hẹn...

        </div>

      )}



      {!isLoading && !error && bookings.length === 0 && (

        <div className="rounded-2xl border border-dashed border-slate-300 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface px-6 py-16 text-center">

          <CalendarDays className="mx-auto h-10 w-10 text-slate-400 dark:text-app-secondary light:text-app-secondary" />

          <h2 className="mt-4 font-semibold text-slate-900 dark:text-app-text light:text-app-text">Chưa có lịch hẹn</h2>

          <p className="mt-2 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">Bạn có thể chọn bác sĩ và khung giờ để đặt lịch khám.</p>

        </div>

      )}



      {!isLoading && !error && bookings.length > 0 && (

        <div className="space-y-3">

          {bookings.map((booking) => (

            <Link

              key={booking.id}

              to={`/patient/appointments/${booking.id}`}

              className="flex flex-col gap-4 rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-5 shadow-sm transition hover:border-sky-300 dark:hover:border-sky-800 hover:shadow-md sm:flex-row sm:items-center sm:justify-between"

            >

              <div>

                <div className="flex items-center gap-2 text-sm font-semibold text-sky-700 dark:text-sky-300 light:text-app-primary">

                  <CalendarDays className="h-4 w-4" />

                  {formatDateTime(booking.starts_at)}

                </div>

                <p className="mt-2 text-sm text-slate-700 dark:text-app-text light:text-app-text">Mã lịch hẹn: {booking.id}</p>

                <p className="mt-1 text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">

                  Mã bác sĩ: {booking.doctor_id} · Mã cơ sở: {booking.facility_id}

                </p>

              </div>

              <div className="flex items-center gap-3">

                <span className={booking.status === 'confirmed'

                  ? 'rounded-full bg-emerald-100 dark:bg-emerald-950/50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300'

                  : booking.status === 'pending_approval'

                    ? 'rounded-full bg-amber-100 dark:bg-amber-950/50 px-3 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300'

                    : booking.status === 'rejected'

                      ? 'rounded-full bg-rose-100 dark:bg-rose-950/50 px-3 py-1 text-xs font-semibold text-rose-700 dark:text-rose-300'

                      : 'rounded-full bg-slate-100 dark:bg-app-muted light:bg-app-muted px-3 py-1 text-xs font-semibold text-slate-600 dark:text-app-secondary light:text-app-secondary'}>

                  {statusLabel(booking.status)}

                </span>

                <ChevronRight className="h-5 w-5 text-slate-400 dark:text-app-secondary light:text-app-secondary" />

              </div>

            </Link>

          ))}

        </div>

      )}

    </section>

  );

}

