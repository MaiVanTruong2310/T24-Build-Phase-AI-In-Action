import type { Schedule } from '../../../features/appointment-booking/api'
import { scheduleStats } from '../../../features/coordinator/uiLogic'

export function StatCards({ schedules, loading }: { schedules: Schedule[]; loading: boolean }) {
  const stats = scheduleStats(schedules)
  const cards = [['Mốc lịch trong tuần', stats.total], ['Mốc lịch đang mở', stats.available], ['Mốc lịch đang khóa', stats.blocked], ['Sức chứa đã cấu hình', stats.capacity]] as const
  return <section aria-label="Thống kê lịch bác sĩ đang chọn" className="mb-6 grid grid-cols-2 gap-4 xl:grid-cols-4">
    {cards.map(([label, value]) => <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-semibold text-slate-500">{label}</p><strong className="mt-2 block text-3xl text-slate-800">{loading ? '…' : value}</strong>
      <p className="mt-2 text-xs text-slate-500">Bác sĩ và tuần đang chọn</p>
    </div>)}
  </section>
}
