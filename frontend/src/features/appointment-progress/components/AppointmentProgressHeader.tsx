import { Activity, CalendarPlus, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  patientId: string;
}

export function AppointmentProgressHeader({ patientId }: Props) {
  return (
    <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-teal-100 px-3 py-1.5 text-xs font-bold text-teal-700">
            <Activity className="h-3.5 w-3.5" /> Hệ thống theo dõi trực tiếp
          </span>
          <span className="text-xs font-semibold text-slate-500 light:text-app-secondary">Mã BN: #{patientId.slice(0, 8).toUpperCase()}</span>
        </div>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-900 light:text-app-text md:text-4xl">Lịch hẹn &amp; Tiến trình Khám</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600 light:text-app-secondary md:text-base">Theo dõi các lịch hẹn và tiến trình xét duyệt HITL của bạn.</p>
      </div>
      <Link
        to="/patient/appointments"
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-sky-700 light:bg-app-primary-hover px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-sky-800 light:hover:bg-app-primary-hover"
      >
        <CalendarPlus className="h-4 w-4" /> Đặt lịch khám mới
      </Link>
    </div>
  );
}

export function HitlTrustBadge() {
  return (
    <div className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500 light:text-app-secondary">
      <ShieldCheck className="h-4 w-4 text-slate-500 light:text-app-secondary" /> HITL: dữ liệu theo booking thực tế
    </div>
  );
}
