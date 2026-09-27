import { BrainCircuit, Cross } from 'lucide-react'

export function BrandMark() {
  return (
    <div className="flex items-center gap-3" aria-label="MediCare AI">
      <div className="relative grid size-10 place-items-center rounded-xl bg-sky-600 text-white shadow-sm">
        <Cross aria-hidden="true" className="size-6 stroke-[3]" />
        <BrainCircuit aria-hidden="true" className="absolute size-5 text-cyan-100" />
      </div>
      <div className="leading-tight">
        <div className="text-lg font-bold tracking-tight text-slate-900">
          MediCare <span className="text-sky-600">AI</span>
        </div>
        <div className="text-[10px] font-medium text-slate-500">
          Hệ Thống Y Tế Số Đa Tầng Bác Sĩ Giám Sát
        </div>
      </div>
    </div>
  )
}
