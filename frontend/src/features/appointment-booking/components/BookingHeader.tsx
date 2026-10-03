import { CalendarDays, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function BookingHeader() {
  return (
    <header className="mb-5 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-700 light:text-app-primary">
          <CalendarDays className="h-4 w-4" /> Đặt lịch trực tuyến
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 light:text-app-text sm:text-3xl">Đặt lịch khám</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600 light:text-app-secondary">
          Chọn chuyên khoa, bác sĩ và giờ phù hợp để gửi yêu cầu đặt lịch.
        </p>
      </div>
      <Link
        to="/patient/appointments/history"
        className="inline-flex w-fit items-center gap-1 rounded-xl border border-sky-200 light:border-app-border bg-white light:bg-app-surface px-3 py-2 text-sm font-semibold text-sky-700 light:text-app-primary hover:bg-sky-50 light:hover:bg-app-muted"
      >
        Lịch hẹn của tôi <ChevronRight className="h-4 w-4" />
      </Link>
    </header>
  );
}
