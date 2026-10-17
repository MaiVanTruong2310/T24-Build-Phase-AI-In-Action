import type { Schedule } from '../../../features/appointment-booking/api';
import { scheduleStats } from '../../../features/coordinator/uiLogic';
import { CalendarDays, CircleCheck, LockKeyhole, Users } from 'lucide-react';

export function StatCards({ schedules, loading }: { schedules: Schedule[]; loading: boolean }) {
  const stats = scheduleStats(schedules);
  const cards = [
    { label: 'Mốc lịch trong tuần', value: stats.total, icon: CalendarDays, tone: 'bg-slate-100 text-slate-600' },
    { label: 'Mốc đang mở', value: stats.available, icon: CircleCheck, tone: 'bg-emerald-100 text-emerald-700' },
    { label: 'Mốc đang khóa', value: stats.blocked, icon: LockKeyhole, tone: 'bg-rose-100 text-rose-700' },
    { label: 'Sức chứa đã cấu hình', value: stats.capacity, icon: Users, tone: 'bg-sky-100 text-sky-700' },
  ] as const;

  return <section aria-label="Thống kê lịch bác sĩ đang chọn" className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
    {cards.map(({ label, value, icon: Icon, tone }) => <div key={label} className="flex min-w-0 items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="min-w-0">
        <p className="text-xs font-semibold leading-5 text-slate-500">{label}</p>
        <strong className="mt-2 block text-3xl tracking-tight text-slate-900">{loading ? '…' : value}</strong>
      </div>
      <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${tone}`}><Icon size={19} aria-hidden="true" /></span>
    </div>)}
    <p className="col-span-full -mt-1 text-xs text-slate-500">Theo bác sĩ và khoảng thời gian đang chọn</p>
  </section>;
}
