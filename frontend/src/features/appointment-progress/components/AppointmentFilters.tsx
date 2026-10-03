import { CalendarDays, CheckCircle2, Clock3, Filter, XCircle } from 'lucide-react';
import clsx from 'clsx';
import { AppointmentFilter } from '../types';

interface Props {
  value: AppointmentFilter;
  counts: Record<AppointmentFilter, number>;
  onChange: (value: AppointmentFilter) => void;
}

const filters: Array<{ value: AppointmentFilter; label: string; icon: typeof CalendarDays }> = [
  { value: 'all', label: 'Tất cả', icon: Filter },
  { value: 'pending_approval', label: 'Chờ duyệt', icon: Clock3 },
  { value: 'confirmed', label: 'Đã xác nhận', icon: CheckCircle2 },
  { value: 'rejected', label: 'Đã từ chối', icon: XCircle },
  { value: 'cancelled', label: 'Đã hủy', icon: XCircle },
];

export function AppointmentFilters({ value, counts, onChange }: Props) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div className="flex flex-wrap gap-2 rounded-2xl bg-slate-100 light:bg-app-muted p-1.5">
        {filters.map((filter) => {
          const Icon = filter.icon;
          const isActive = filter.value === value;
          return (
            <button
              key={filter.value}
              type="button"
              onClick={() => onChange(filter.value)}
              className={clsx(
                'inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition',
                isActive ? 'bg-white light:bg-app-surface text-sky-700 light:text-app-primary shadow-sm' : 'text-slate-600 light:text-app-secondary hover:bg-white/70 light:hover:bg-app-surface/70 hover:text-sky-700 light:hover:text-app-primary',
              )}
            >
              <Icon className="h-4 w-4" />
              {filter.label}
              <span className={clsx('rounded-full px-1.5 py-0.5 text-[11px]', isActive ? 'bg-sky-100 light:bg-app-tint text-sky-700 light:text-app-primary' : 'bg-white light:bg-app-surface text-slate-500 light:text-app-secondary')}>
                {counts[filter.value]}
              </span>
            </button>
          );
        })}
      </div>
      <div className="hidden items-center gap-2 text-sm font-semibold text-slate-500 light:text-app-secondary lg:flex">
        <CalendarDays className="h-4 w-4" /> Chọn một lịch hẹn để xem chi tiết
      </div>
    </div>
  );
}
