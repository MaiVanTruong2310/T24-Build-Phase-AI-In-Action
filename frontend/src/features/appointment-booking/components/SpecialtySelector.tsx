import { HeartPulse, Brain, Ear, Stethoscope, CheckCircle2, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

const SPECIALTIES = [
  { id: 'tm', name: 'Tim Mạch Can Thiệp', desc: 'Khớp 98% biểu hiện tức ngực', icon: HeartPulse },
  { id: 'hh', name: 'Nội Hô Hấp', desc: 'Khó thở, ho kéo dài', icon: Brain }, // Brain placeholder
  { id: 'tmh', name: 'Tai Mũi Họng', desc: 'Viêm xoang, amidan, họng hạt', icon: Ear },
  { id: 'tk', name: 'Nội Thần Kinh', desc: 'Chóng mặt, tiền đình, mất ngủ', icon: Brain },
  { id: 'th', name: 'Tiêu Hóa - Gan Mật', desc: 'Trào ngược, đại tràng, đau dạ dày', icon: Stethoscope },
];

interface Props {
  selectedId: string;
  onSelect: (id: string) => void;
}

export function SpecialtySelector({ selectedId, onSelect }: Props) {
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
        {SPECIALTIES.map(item => {
          const isSelected = item.id === selectedId;
          const Icon = item.icon;
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
                  <div className={clsx("text-[11px] mt-0.5 transition-colors", isSelected ? "text-sky-700" : "text-slate-500")}>{item.desc}</div>
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
