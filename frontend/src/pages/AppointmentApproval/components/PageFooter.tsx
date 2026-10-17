import { ShieldCheck } from 'lucide-react';

interface PageFooterProps {
  filteredCount: number;
  totalCount: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

export function PageFooter({ filteredCount, totalCount, offset, limit, onPageChange }: PageFooterProps) {
  const start = totalCount ? offset + 1 : 0;
  const end = Math.min(offset + filteredCount, totalCount);
  return (
    <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs font-semibold text-slate-500 flex-shrink-0">
      <div className="flex items-center gap-2">
        <ShieldCheck size={14} className="text-teal-600" />
        <span>VCare+ Clinical HITL — Chuẩn HIPAA & Bộ Y Tế</span>
      </div>
      <div className="flex items-center gap-4">
        <span>Hiển thị {start}-{end} / {totalCount} lịch hẹn</span>
        <div className="flex gap-2">
          <button type="button" onClick={() => onPageChange(Math.max(0, offset - limit))} disabled={offset === 0} className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40">Trước</button>
          <button type="button" onClick={() => onPageChange(offset + limit)} disabled={offset + limit >= totalCount} className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40">Sau</button>
        </div>
        <span className="text-emerald-600">● Hệ thống đang hoạt động</span>
      </div>
    </div>
  );
}
