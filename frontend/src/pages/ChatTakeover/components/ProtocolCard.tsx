import { CheckSquare, Square, ShieldCheck, Check } from 'lucide-react';
import { ProtocolItem } from '../types';

interface ProtocolCardProps {
  protocols: ProtocolItem[];
  onToggleProtocol: (id: string) => void;
  onSignProtocol: () => void;
  isSigned?: boolean;
}

export function ProtocolCard({
  protocols,
  onToggleProtocol,
  onSignProtocol,
  isSigned = false,
}: ProtocolCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
      <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase">
        Khuyến nghị phác đồ can thiệp:
      </h3>

      {/* Checklist */}
      <div className="space-y-2">
        {protocols.map((item) => (
          <div
            key={item.id}
            onClick={() => onToggleProtocol(item.id)}
            className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50 hover:bg-slate-100/80 cursor-pointer border border-slate-100 transition-colors"
          >
            <div className="mt-0.5 shrink-0 text-sky-700">
              {item.checked ? (
                <div className="w-4 h-4 rounded bg-sky-700 text-white flex items-center justify-center">
                  <Check size={12} strokeWidth={3} />
                </div>
              ) : (
                <Square size={16} className="text-slate-400" />
              )}
            </div>
            <span
              className={`text-xs leading-snug select-none ${
                item.checked ? 'text-slate-800 font-semibold' : 'text-slate-600 font-normal'
              }`}
            >
              {item.label}
            </span>
          </div>
        ))}
      </div>

      {/* Signature CTA Button */}
      <button
        onClick={onSignProtocol}
        className={`w-full py-3 px-4 rounded-xl text-white font-bold transition-all shadow-sm flex flex-col items-center justify-center gap-0.5 ${
          isSigned
            ? 'bg-emerald-700 hover:bg-emerald-800'
            : 'bg-teal-700 hover:bg-teal-800 active:scale-98'
        }`}
      >
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider font-extrabold">
          <ShieldCheck size={16} />
          <span>{isSigned ? 'ĐÃ KÝ SỐ XÁC NHẬN THÀNH CÔNG' : 'Ký Số Xác Nhận Can Thiệp'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-teal-200 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Trợ lý Lâm sàng Nội bộ AI (Online)</span>
        </div>
      </button>
    </div>
  );
}
