import { HeartPulse, CheckCircle2, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import { Specialty } from '../api';

interface Props {
  specialties: Specialty[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function SpecialtySelector({ specialties, selectedId, onSelect }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-slate-900 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-sky-500"></div>
          1. Chuyên Khoa Phù Hợp
        </h2>
        <span className="text-[10px] font-semibold text-sky-600 bg-sky-50 px-2 py-0.5 rounded">Tự động gợi ý từ AI</span>
      </div>
      <div className="space-y-2">
        {specialties.length === 0 && <p className="text-sm text-slate-500 p-2">Đang tải...</p>}
        {specialties.map(item => {
          const isSelected = item.id === selectedId;
          const Icon = HeartPulse; // Can map icons based on code later

          return (
            <button
              key={item.id}
              onClick={() => onSelect(item.id)}
              className={clsx(
                "w-full text-left p-3 rounded-xl border flex items-center justify-between transition-all duration-200 group",
                isSelected ? "border-sky-500 bg-sky-50 shadow-sm ring-1 ring-sky-500" : "border-slate-200 bg-white hover:border-sky-300"
              )}
            >
              <div className="flex items-center gap-3">
                <div className={clsx("p-2.5 rounded-lg transition-colors shrink-0", isSelected ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-500 group-hover:bg-sky-100 group-hover:text-sky-600")}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <div className={clsx("font-semibold text-sm transition-colors", isSelected ? "text-sky-900" : "text-slate-800")}>{item.name}</div>
                  <div className={clsx("text-[11px] mt-0.5 transition-colors", isSelected ? "text-sky-700" : "text-slate-500")}>{item.description}</div>
                </div>
              </div>
              {isSelected ? (
                <CheckCircle2 className="w-5 h-5 text-sky-600 shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-300 shrink-0 group-hover:text-sky-400" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
