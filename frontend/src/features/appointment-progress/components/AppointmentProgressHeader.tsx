import { CalendarPlus } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  patientId: string;
}

export function AppointmentProgressHeader({ patientId: _ }: Props) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-2 border-b border-slate-200 dark:border-app-border light:border-app-border">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-app-text light:text-app-text sm:text-3xl">
          Tiến trình điều trị & Lịch hẹn
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">
          Theo dõi trạng thái các lượt khám bác sĩ, gói khám sức khỏe và điều phối AI.
        </p>
      </div>
      <Link
        to="/patient/appointments"
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-700 dark:bg-emerald-700 light:bg-app-primary hover:bg-emerald-800 dark:hover:bg-emerald-600 light:hover:bg-app-primary-hover px-4 py-2.5 text-xs font-bold text-white shadow-2xs transition self-start sm:self-auto"
      >
        <CalendarPlus className="h-4 w-4" /> Đặt lịch mới
      </Link>
    </div>
  );
}

export function HitlTrustBadge() {
  return null;
}

