import { ShieldCheck } from 'lucide-react';

interface PageFooterProps {
  filteredCount: number;
  totalCount: number;
}

export function PageFooter({ filteredCount, totalCount }: PageFooterProps) {
  return (
    <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs font-semibold text-slate-500 flex-shrink-0">
      <div className="flex items-center gap-2">
        <ShieldCheck size={14} className="text-teal-600" />
        <span>VCare+ Clinical HITL — Chuẩn HIPAA & Bộ Y Tế</span>
      </div>
      <div className="flex items-center gap-4">
        <span>Hiển thị {filteredCount} / {totalCount} lịch hẹn</span>
        <span className="text-emerald-600">● Hệ thống đang hoạt động</span>
      </div>
    </div>
  );
}
