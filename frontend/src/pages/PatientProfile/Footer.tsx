import { memo } from 'react';
import {
  Stethoscope,
  HelpCircle,
  Accessibility,
} from 'lucide-react';

/** Page footer — compact, matches screenshot bottom bar */
export const ProfileFooter = memo(function ProfileFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3">
        {/* Left: Brand */}
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-[#0e7490]/10 text-[#0e7490]">
            <Stethoscope className="h-3.5 w-3.5" />
          </div>
          <span className="font-bold text-slate-600">MediCare AI</span>
          <span className="hidden text-slate-300 sm:inline">|</span>
          <span className="hidden text-[11px] sm:inline">
            Hệ Thống Khám Bệnh Dự Tổng Đài 50 Cửa Sổ
          </span>
        </div>

        {/* Right: Compliance + actions */}
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400">
          <span>
            © 2024 MediCare AI Health System. Chuẩn an toàn dữ liệu y tế
            ISO/IEC 27001 & HIPAA.
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="text-slate-400 transition hover:text-slate-600"
              aria-label="Trợ giúp"
            >
              <HelpCircle className="h-3.5 w-3.5" />
            </button>
            <span>Hỗ trợ bệnh nhân</span>
            <button
              type="button"
              className="text-slate-400 transition hover:text-slate-600"
              aria-label="Trợ năng"
            >
              <Accessibility className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
});
