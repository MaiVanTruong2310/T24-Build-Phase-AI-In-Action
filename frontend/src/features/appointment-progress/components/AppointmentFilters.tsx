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
    <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-slate-100 dark:bg-app-muted light:bg-app-muted p-1.5 border border-slate-200 dark:border-app-border light:border-app-border">
      {filters.map((filter) => {
        const Icon = filter.icon;
        const isActive = filter.value === value;
        return (
          <button
            key={filter.value}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange(filter.value)}
            className={clsx(
              'inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold transition cursor-pointer',
              isActive
                ? 'bg-white dark:bg-app-surface light:bg-app-surface text-emerald-800 dark:text-emerald-300 light:text-app-primary shadow-xs'
                : 'text-slate-600 dark:text-app-secondary light:text-app-secondary hover:bg-white/60 dark:hover:bg-app-surface/60 hover:text-emerald-700 dark:hover:text-emerald-300',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {filter.label}
            <span
              className={clsx(
                'rounded-full px-1.5 py-0.2 text-[10px] font-bold',
                isActive
                  ? 'bg-emerald-100 dark:bg-emerald-950/60 light:bg-app-tint text-emerald-800 dark:text-emerald-300 light:text-app-primary'
                  : 'bg-white/80 dark:bg-app-surface light:bg-app-surface text-slate-500 dark:text-app-secondary',
              )}
            >
              {counts[filter.value]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
