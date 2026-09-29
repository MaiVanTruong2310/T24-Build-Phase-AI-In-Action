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
    <div className="rounded-2xl border border-red-200 bg-red-50/90 p-4 sm:p-5 shadow-sm transition-all">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Left: Warning text */}
        <div className="flex items-start gap-3.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-100 text-red-600">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-red-800 sm:text-base leading-snug">
              Phát hiện triệu chứng cấp tính: Đau tức ngực lan ra khớp vai và cánh tay trái. Nguy cơ biến cố tim mạch cần can thiệp sớm.
            </h2>
            <p className="mt-1 text-xs text-red-600/90 leading-relaxed">
              Không được tự ý lái xe hoặc gắng sức. Bấm Chat AI hoặc liên hệ khẩn cấp ngay bên dưới.
            </p>
          </div>
        </div>

        {/* Right: Quick action buttons */}
        <div className="flex items-center gap-2.5 shrink-0 self-start sm:self-auto">
          <button
            type="button"
            onClick={handleCall115}
            className="flex items-center gap-2 rounded-xl bg-red-700 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-red-800 active:scale-95"
          >
            <Phone className="h-4 w-4" />
            <span>Gọi Cấp Cứu 115</span>
          </button>
          <button
            type="button"
            onClick={handleCallNurse}
            className="flex items-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-xs font-semibold text-red-700 shadow-sm transition hover:bg-red-50 active:scale-95"
          >
            <Radio className="h-4 w-4 text-red-600" />
            <span>Nối máy Điều dưỡng</span>
          </button>
        </div>
      </div>
    </div>
  );
});
