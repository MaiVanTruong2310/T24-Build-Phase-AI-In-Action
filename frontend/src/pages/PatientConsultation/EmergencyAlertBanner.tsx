import { memo } from 'react';
import { AlertTriangle, Phone, Radio } from 'lucide-react';

export const EmergencyAlertBanner = memo(function EmergencyAlertBanner() {
  const handleCall115 = () => {
    window.location.href = 'tel:115';
  };

  const handleCallNurse = () => {
    alert('Đang kết nối tổng đài điều dưỡng khẩn cấp...');
  };

  return (
    <div className="rounded-2xl border border-red-500/40 bg-red-950/60 p-4 sm:p-5 shadow-lg backdrop-blur-md transition-all">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Left: Warning text */}
        <div className="flex items-start gap-3.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-900/50 border border-red-500/50 text-red-400">
            <AlertTriangle className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="border border-red-500/40 bg-red-900/60 text-red-300 text-[10px] font-bold px-2 py-0.5 rounded-md uppercase">
                Cảnh Báo Cấp Cứu (Triage Đỏ)
              </span>
              <span className="text-xs text-red-300/80 font-mono">Độ trễ phản xạ: &lt; 0.5s</span>
            </div>
            <h2 className="text-sm font-semibold text-slate-100 sm:text-base leading-snug">
              Phát hiện dấu hiệu cấp tính: Đau tức ngực lan lên vai và cánh tay trái. Nguy cơ biến cố mạch vành cần can thiệp khẩn cấp.
            </h2>
            <p className="mt-1 text-xs text-red-300 leading-relaxed">
              Khuyến cáo: Nghỉ ngơi tại chỗ, không gắng sức. Liên hệ cấp cứu 115 hoặc bấm trao đổi trực tiếp với Bác sĩ lâm sàng trực ban.
            </p>
          </div>
        </div>

        {/* Right: Quick action buttons */}
        <div className="flex items-center gap-2.5 shrink-0 self-start sm:self-auto">
          <button
            type="button"
            onClick={handleCall115}
            className="flex items-center gap-2 rounded-xl bg-red-600 hover:bg-red-500 px-4 py-2.5 text-xs font-semibold text-white shadow-md transition active:scale-95 border border-red-400/40"
          >
            <Phone className="h-4 w-4" />
            <span>Gọi Cấp Cứu 115</span>
          </button>
          <button
            type="button"
            onClick={handleCallNurse}
            className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-red-300 shadow-md transition hover:bg-slate-800 active:scale-95"
          >
            <Radio className="h-4 w-4 text-red-400" />
            <span>Nối Máy Bác Sĩ Trực</span>
          </button>
        </div>
      </div>
    </div>
  );
});
