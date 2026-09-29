import { ShieldCheck } from 'lucide-react';

export function DualCheckSafetyCard() {
  return (
    <div className="bg-sky-50/70 border border-sky-200/80 rounded-2xl p-4 shadow-2xs space-y-1.5">
      <div className="flex items-center gap-2">
        <ShieldCheck size={18} className="text-sky-700 shrink-0" />
        <h4 className="text-xs font-black text-sky-900 leading-tight">
          Quy Trình An Toàn Hai Lớp (Dual-Check)
        </h4>
      </div>
      <p className="text-[11px] text-sky-800 leading-relaxed font-medium">
        Mọi chỉ định liên quan đến nhóm thuốc cảnh báo cao và bệnh án chuyển tuyến đều bắt buộc có chữ ký số của Bác sĩ Điều Phối Viên trưởng ca trực.
      </p>
    </div>
  );
}
